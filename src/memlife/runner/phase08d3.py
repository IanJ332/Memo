"""Offline-only evidence primitives for the proposed Phase 08D capture path.

These classes deliberately do not start a provider, send a model request, or
decide that a provider has quiesced.  They make omissions explicit so a future
authorized runner can fail closed rather than turn missing evidence into a
successful condition.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


class CaptureFailure(RuntimeError):
    """Evidence could not be written; the corresponding exchange is unsafe."""


class AccountingRejected(RuntimeError):
    """A send has no admission reservation and must not be attempted."""


@dataclass(frozen=True)
class ArtifactIdentity:
    path: str
    sha256: str
    byte_count: int


class AttemptArtifactStore:
    """An exclusive, private attempt root with no overwrite path."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(mode=0o700, parents=True, exist_ok=False)
        os.chmod(self.root, 0o700)

    def write_bytes(self, relative_path: str, data: bytes) -> ArtifactIdentity:
        destination = (self.root / relative_path).resolve()
        if self.root.resolve() not in destination.parents:
            raise CaptureFailure("artifact path escapes attempt root")
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            with destination.open("xb") as stream:
                stream.write(data)
            os.chmod(destination, 0o600)
        except OSError as exc:
            raise CaptureFailure(f"exclusive artifact write failed: {relative_path}") from exc
        return ArtifactIdentity(relative_path, _sha256(data), len(data))

    def write_json(self, relative_path: str, payload: object) -> ArtifactIdentity:
        return self.write_bytes(relative_path, _json(payload))


class HttpExchangeCapture:
    """Writes exact request/response bytes before any decoding or parsing."""

    def __init__(self, store: AttemptArtifactStore, *, attempt_id: str) -> None:
        self.store = store
        self.attempt_id = attempt_id
        self._lock = threading.Lock()
        self._ordinal = 0

    def capture(
        self,
        *,
        method: str,
        path: str,
        request_body: bytes | None,
        response_body: bytes,
        status_code: int,
        response_headers: Mapping[str, str] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            self._ordinal += 1
            exchange_id = f"exchange-{self._ordinal:06d}"
        try:
            request = self.store.write_bytes(
                f"http/{exchange_id}.request.bin", request_body or b""
            )
            response = self.store.write_bytes(
                f"http/{exchange_id}.response.bin", response_body
            )
            manifest = {
                "attempt_id": self.attempt_id,
                "exchange_id": exchange_id,
                "captured_at": _now(),
                "method": method.upper(),
                "path": path,
                "request_id": request_id,
                "status_code": status_code,
                "request": request.__dict__,
                "response": response.__dict__,
                "response_headers": dict(response_headers or {}),
            }
            identity = self.store.write_json(f"http/{exchange_id}.json", manifest)
            manifest["manifest"] = identity.__dict__
            return manifest
        except CaptureFailure:
            raise
        except Exception as exc:
            raise CaptureFailure("HTTP exchange capture failed") from exc


@dataclass(frozen=True)
class CandidateEvidence:
    position: int
    native_id: str | None
    included: bool
    discard_reason: str | None
    decoded_field_bytes: bytes | None
    normalized_bytes: bytes | None
    surface: str | None
    source_ids: tuple[str, ...]
    provenance_basis: str


def capture_candidates(
    results: object, *, selected_ids: set[str], limit: int
) -> tuple[CandidateEvidence, ...]:
    """Retain each original result and separately record extraction outcomes.

    `decoded_field_bytes` is UTF-8 encoding of the decoded string field, never
    reconstructed response JSON.  Raw response identity belongs to D1.
    """
    if not isinstance(results, list):
        raise CaptureFailure("recall response results is not a list")
    evidence: list[CandidateEvidence] = []
    selected_count = 0
    for position, item in enumerate(results, start=1):
        if not isinstance(item, Mapping):
            evidence.append(CandidateEvidence(position, None, False, "non_object", None, None, None, (), "UNKNOWN"))
            continue
        native_id = str(item.get("id")) if item.get("id") is not None else None
        text = item.get("text")
        decoded = text.encode("utf-8") if isinstance(text, str) else None
        normalized = text.strip().encode("utf-8") if isinstance(text, str) else None
        included = native_id in selected_ids if native_id else False
        if included:
            selected_count += 1
        reason = None
        if not isinstance(text, str):
            reason = "missing_or_nonstring_text"
        elif not text.strip():
            reason = "blank_after_existing_strip"
        elif not included:
            reason = "filtered_or_truncated"
        sources = item.get("source_memory_ids", item.get("source_fact_ids", []))
        evidence.append(CandidateEvidence(
            position, native_id, included, reason, decoded, normalized,
            str(item.get("fact_type")) if item.get("fact_type") is not None else None,
            tuple(str(value) for value in sources) if isinstance(sources, list) else (),
            "PROVIDER_NATIVE" if isinstance(sources, list) else "UNKNOWN",
        ))
    if selected_count > limit:
        raise CaptureFailure("selected candidate count exceeds command limit")
    return tuple(evidence)


@dataclass
class SendReservation:
    reservation_id: str
    endpoint: str
    model: str
    maximum_units: int
    state: str = "RESERVED"


class SendAccounting:
    """Thread-safe admission ledger; callers must reserve before each send.

    The caller supplies an independently justified upper bound.  This class
    refuses an unspecified bound, so it cannot pretend that a guessed token
    limit is a budget control.
    """

    def __init__(self, ceiling_units: int) -> None:
        if ceiling_units < 0:
            raise ValueError("ceiling_units must not be negative")
        self.ceiling_units = ceiling_units
        self._reserved = 0
        self._counter = 0
        self._lock = threading.Lock()
        self.records: list[dict[str, Any]] = []

    def admit(self, *, endpoint: str, model: str, maximum_units: int | None) -> SendReservation:
        if maximum_units is None or maximum_units < 0:
            raise AccountingRejected("per-send independently justified bound is required")
        with self._lock:
            if self._reserved + maximum_units > self.ceiling_units:
                raise AccountingRejected("outstanding reservations exhaust call ceiling")
            self._counter += 1
            reservation = SendReservation(f"send-{self._counter:06d}", endpoint, model, maximum_units)
            self._reserved += maximum_units
            self.records.append({"reservation_id": reservation.reservation_id, "state": "RESERVED", "at": _now(), "endpoint": endpoint, "model": model, "reserved_units": maximum_units})
            return reservation

    def receipt(self, reservation: SendReservation, *, actual_units: int | None, outcome: str) -> None:
        with self._lock:
            if reservation.state != "RESERVED":
                raise AccountingRejected("reservation is not outstanding")
            reservation.state = "RECEIPTED" if actual_units is not None else "USAGE_MISSING"
            self._reserved -= reservation.maximum_units
            self.records.append({"reservation_id": reservation.reservation_id, "state": reservation.state, "at": _now(), "outcome": outcome, "actual_units": actual_units, "reserved_units": reservation.maximum_units})


def assess_operation_coverage(pages: tuple[tuple[Mapping[str, Any], ...], ...]) -> str:
    """Return COMPLETE only for explicitly terminal, paginated evidence."""
    terminal = {"completed", "failed", "cancelled"}
    for page in pages:
        for operation in page:
            if str(operation.get("status") or "") not in terminal:
                return "UNKNOWN"
    return "COMPLETE" if pages else "UNKNOWN"


def attempt_outcome(*, evidence_integrity: bool, resource_gate: bool, prior_outcome: str | None = None) -> str:
    """Fail closed and never upgrade a pre-existing incomplete outcome."""
    if prior_outcome in {"FAILED", "INCOMPLETE", "BLOCKED"}:
        return prior_outcome
    if not evidence_integrity:
        return "FAILED"
    if not resource_gate:
        return "BLOCKED"
    return "INCOMPLETE"


def freeze_attempt_manifest(
    store: AttemptArtifactStore,
    *,
    attempt_id: str,
    source_authority_sha256: str,
    configuration_sha256: str,
    resource_gate: bool,
) -> ArtifactIdentity:
    """Freeze the two independent inputs before a future attempt can proceed."""
    for label, value in (("source_authority_sha256", source_authority_sha256), ("configuration_sha256", configuration_sha256)):
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise CaptureFailure(f"{label} is not a lowercase SHA-256")
    return store.write_json("attempt-manifest.json", {
        "attempt_id": attempt_id,
        "created_at": _now(),
        "source_authority_sha256": source_authority_sha256,
        "configuration_sha256": configuration_sha256,
        "resource_gate": resource_gate,
        "private_artifact_root": True,
        "conclusive_denominator_eligible": False,
    })


def verify_inventory(store: AttemptArtifactStore, identities: tuple[ArtifactIdentity, ...]) -> bool:
    """Verify exact bytes against an immutable evidence inventory."""
    for identity in identities:
        path = (store.root / identity.path).resolve()
        if store.root.resolve() not in path.parents or not path.is_file():
            return False
        data = path.read_bytes()
        if len(data) != identity.byte_count or _sha256(data) != identity.sha256:
            return False
    return True
