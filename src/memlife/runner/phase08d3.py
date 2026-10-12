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


SAFE_RESPONSE_HEADERS = frozenset({"content-type", "content-encoding", "x-request-id"})


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
                "response_headers": {
                    str(name): str(value)
                    for name, value in (response_headers or {}).items()
                    if str(name).lower() in SAFE_RESPONSE_HEADERS
                },
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
    delivery: str = "CALLBACK_ONLY"
    durable_artifact_persisted: bool = False
    selection_reason: str | None = None
    exchange_id: str | None = None
    decoded_field_artifact: ArtifactIdentity | None = None
    normalized_artifact: ArtifactIdentity | None = None
    http_response_artifact: ArtifactIdentity | None = None
    extraction_rule: str | None = None
    extraction_version: str | None = None
    json_path: str = ""
    field_path: str = ""

    @property
    def parent_ids(self) -> tuple[str, ...]:
        return self.source_ids


def capture_candidates(
    results: object, *, selected_positions: set[int], limit: int
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
            evidence.append(CandidateEvidence(
                position=position,
                native_id=None,
                included=False,
                discard_reason="non_object",
                decoded_field_bytes=None,
                normalized_bytes=None,
                surface=None,
                source_ids=(),
                provenance_basis="UNKNOWN",
                delivery="CALLBACK_ONLY",
                durable_artifact_persisted=False,
            ))
            continue
        native_id = str(item.get("id")) if item.get("id") is not None else None
        text = item.get("text")
        decoded = text.encode("utf-8") if isinstance(text, str) else None
        normalized = text.strip().encode("utf-8") if isinstance(text, str) else None
        included = position in selected_positions
        if included:
            selected_count += 1
        selection_reason = "selected" if included else None
        discard_reason = None
        if not isinstance(text, str):
            discard_reason = "missing_or_nonstring_text"
        elif not text.strip():
            discard_reason = "blank_after_existing_strip"
        elif not included:
            discard_reason = "filtered_or_truncated"
        sources = item.get("source_memory_ids", item.get("source_fact_ids", []))
        surface = str(item.get("fact_type") or item.get("type")) if (item.get("fact_type") is not None or item.get("type") is not None) else None
        evidence.append(CandidateEvidence(
            position=position,
            native_id=native_id,
            included=included,
            discard_reason=discard_reason,
            decoded_field_bytes=decoded,
            normalized_bytes=normalized,
            surface=surface,
            source_ids=tuple(str(value) for value in sources) if isinstance(sources, list) else (),
            provenance_basis="PROVIDER_NATIVE" if isinstance(sources, list) else "UNKNOWN",
            delivery="CALLBACK_ONLY",
            durable_artifact_persisted=False,
            selection_reason=selection_reason,
        ))
    if selected_count > limit:
        raise CaptureFailure("selected candidate count exceeds command limit")
    return tuple(evidence)


class CandidateArtifactSink:
    """Persists candidate evidence to AttemptArtifactStore linked to D1 HTTP response."""

    def __init__(
        self,
        store: AttemptArtifactStore,
        *,
        extraction_rule: str = "hindsight-recall-results-v1",
        extraction_version: str = "phase-08d4-v1",
    ) -> None:
        self.store = store
        self.extraction_rule = extraction_rule
        self.extraction_version = extraction_version
        self.persisted_manifests: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def capture_and_persist(
        self,
        results: object,
        *,
        selected_positions: set[int],
        limit: int,
        exchange_manifest: Mapping[str, Any] | None,
        raw_response: Mapping[str, Any] | None = None,
    ) -> tuple[CandidateEvidence, ...]:
        if exchange_manifest is None:
            raise CaptureFailure("missing D1 HTTP response exchange reference")
        if not isinstance(exchange_manifest, Mapping):
            raise CaptureFailure("invalid D1 HTTP exchange manifest")

        exchange_id = str(exchange_manifest.get("exchange_id") or "")
        if not exchange_id:
            raise CaptureFailure("exchange manifest missing exchange_id")

        response_meta = exchange_manifest.get("response")
        if not isinstance(response_meta, Mapping):
            raise CaptureFailure("exchange manifest missing response artifact metadata")

        resp_rel_path = str(response_meta.get("path") or "")
        resp_sha256 = str(response_meta.get("sha256") or "")
        resp_byte_count = int(response_meta.get("byte_count") or 0)
        if not resp_rel_path or not resp_sha256:
            raise CaptureFailure("exchange response metadata missing path or sha256")

        # Fail closed on missing or corrupt D1 response artifact in the store
        resp_file = (self.store.root / resp_rel_path).resolve()
        if self.store.root.resolve() not in resp_file.parents or not resp_file.is_file():
            raise CaptureFailure(f"D1 HTTP response artifact missing: {resp_rel_path}")
        resp_bytes = resp_file.read_bytes()
        if len(resp_bytes) != resp_byte_count or _sha256(resp_bytes) != resp_sha256:
            raise CaptureFailure("D1 HTTP response artifact hash mismatch")

        http_response_artifact = ArtifactIdentity(resp_rel_path, resp_sha256, resp_byte_count)

        # Reparse persisted response bytes and validate source binding
        try:
            resp_text = resp_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CaptureFailure(f"D1 HTTP response bytes are not valid UTF-8: {exc}") from exc
        try:
            parsed_resp = json.loads(resp_text)
        except json.JSONDecodeError as exc:
            raise CaptureFailure(f"D1 HTTP response is not valid JSON: {exc}") from exc

        if not isinstance(parsed_resp, Mapping):
            raise CaptureFailure("D1 HTTP response JSON is not an object")
        if "results" not in parsed_resp:
            raise CaptureFailure("D1 HTTP response JSON missing 'results' field")
        raw_results = parsed_resp["results"]
        if not isinstance(raw_results, list):
            raise CaptureFailure("D1 HTTP response 'results' field is not a list")

        if results is not None:
            if not isinstance(results, list):
                raise CaptureFailure("recall response results is not a list")
            if results != raw_results:
                raise CaptureFailure("candidate results do not match persisted HTTP response results")

        if limit < 0:
            raise CaptureFailure("limit must not be negative")

        total_results = len(raw_results)
        for pos in selected_positions:
            if not isinstance(pos, int) or pos < 1 or pos > total_results:
                raise CaptureFailure(f"invalid selection position {pos}; total results={total_results}")
        if len(selected_positions) > limit:
            raise CaptureFailure("selected candidate count exceeds command limit")

        for pos in selected_positions:
            item = raw_results[pos - 1]
            if not isinstance(item, Mapping) or not isinstance(item.get("text"), str) or not item.get("text").strip():
                raise CaptureFailure(f"position {pos} cannot be selected: candidate has non-object, non-string, or blank text")

        acceptable_positions = [
            idx + 1 for idx, item in enumerate(raw_results)
            if isinstance(item, Mapping) and isinstance(item.get("text"), str) and item.get("text").strip()
        ]
        expected_selected = set(acceptable_positions[:limit])
        if selected_positions != expected_selected:
            raise CaptureFailure(
                f"selection positions {selected_positions} do not match expected candidate prefix selection {expected_selected}"
            )

        if total_results == 0:
            disposition = "COMPLETE_EMPTY"
        elif len(selected_positions) == 0:
            disposition = "FILTERED_ALL"
        else:
            disposition = "COMPLETE_NONEMPTY"

        evidence_list: list[CandidateEvidence] = []
        with self._lock:
            for idx, item in enumerate(raw_results):
                position = idx + 1
                json_path = f"/results/{idx}"
                field_path = f"/results/{idx}/text"
                if not isinstance(item, Mapping):
                    evidence_list.append(CandidateEvidence(
                        position=position,
                        native_id=None,
                        included=False,
                        discard_reason="non_object",
                        decoded_field_bytes=None,
                        normalized_bytes=None,
                        surface=None,
                        source_ids=(),
                        provenance_basis="UNKNOWN",
                        delivery="STORE_PERSISTED",
                        durable_artifact_persisted=True,
                        selection_reason=None,
                        exchange_id=exchange_id,
                        decoded_field_artifact=None,
                        normalized_artifact=None,
                        http_response_artifact=http_response_artifact,
                        extraction_rule=self.extraction_rule,
                        extraction_version=self.extraction_version,
                        json_path=json_path,
                        field_path=field_path,
                    ))
                    continue

                native_id = str(item.get("id")) if item.get("id") is not None else None
                text = item.get("text")
                decoded = text.encode("utf-8") if isinstance(text, str) else None
                normalized = text.strip().encode("utf-8") if isinstance(text, str) else None
                included = position in selected_positions

                selection_reason = "selected" if included else None
                discard_reason = None
                if not isinstance(text, str):
                    discard_reason = "missing_or_nonstring_text"
                elif not text.strip():
                    discard_reason = "blank_after_existing_strip"
                elif not included:
                    discard_reason = "filtered_or_truncated"

                sources = item.get("source_memory_ids", item.get("source_fact_ids", []))
                source_tuple = tuple(str(v) for v in sources) if isinstance(sources, list) else ()
                provenance_basis = "PROVIDER_NATIVE" if isinstance(sources, list) else "UNKNOWN"
                surface = str(item.get("fact_type") or item.get("type")) if (item.get("fact_type") is not None or item.get("type") is not None) else None

                decoded_art = None
                normalized_art = None
                if decoded is not None:
                    decoded_art = self.store.write_bytes(
                        f"candidates/{exchange_id}/candidate-{position:04d}.decoded.bin",
                        decoded,
                    )
                if normalized is not None:
                    normalized_art = self.store.write_bytes(
                        f"candidates/{exchange_id}/candidate-{position:04d}.normalized.bin",
                        normalized,
                    )

                evidence_list.append(CandidateEvidence(
                    position=position,
                    native_id=native_id,
                    included=included,
                    discard_reason=discard_reason,
                    decoded_field_bytes=decoded,
                    normalized_bytes=normalized,
                    surface=surface,
                    source_ids=source_tuple,
                    provenance_basis=provenance_basis,
                    delivery="STORE_PERSISTED",
                    durable_artifact_persisted=True,
                    selection_reason=selection_reason,
                    exchange_id=exchange_id,
                    decoded_field_artifact=decoded_art,
                    normalized_artifact=normalized_art,
                    http_response_artifact=http_response_artifact,
                    extraction_rule=self.extraction_rule,
                    extraction_version=self.extraction_version,
                    json_path=json_path,
                    field_path=field_path,
                ))

            candidate_manifest = {
                "attempt_id": str(exchange_manifest.get("attempt_id") or ""),
                "exchange_id": exchange_id,
                "captured_at": _now(),
                "retrieval_disposition": disposition,
                "http_exchange": {
                    "exchange_id": exchange_id,
                    "request_id": exchange_manifest.get("request_id"),
                    "manifest": exchange_manifest.get("manifest"),
                    "response": dict(response_meta),
                },
                "extraction": {
                    "rule": self.extraction_rule,
                    "version": self.extraction_version,
                    "charset": "utf-8",
                },
                "total_candidates": len(evidence_list),
                "selected_count": sum(1 for e in evidence_list if e.included),
                "candidates": [
                    {
                        "position": item.position,
                        "json_path": item.json_path,
                        "field_path": item.field_path,
                        "native_id": item.native_id,
                        "included": item.included,
                        "selection_reason": item.selection_reason,
                        "discard_reason": item.discard_reason,
                        "surface": item.surface,
                        "parent_ids": list(item.parent_ids),
                        "provenance_basis": item.provenance_basis,
                        "decoded_field": {
                            "artifact": item.decoded_field_artifact.__dict__ if item.decoded_field_artifact else None,
                            "sha256": item.decoded_field_artifact.sha256 if item.decoded_field_artifact else None,
                            "byte_count": item.decoded_field_artifact.byte_count if item.decoded_field_artifact else None,
                        },
                        "normalized": {
                            "artifact": item.normalized_artifact.__dict__ if item.normalized_artifact else None,
                            "sha256": item.normalized_artifact.sha256 if item.normalized_artifact else None,
                            "byte_count": item.normalized_artifact.byte_count if item.normalized_artifact else None,
                        },
                        "transformations": [
                            {
                                "transformation_id": f"trans-{exchange_id}-{item.position:04d}-decode",
                                "rule": "json_pointer_to_utf8_decoded_field",
                                "json_pointer": item.field_path,
                                "input_artifact_path": resp_rel_path,
                                "input_sha256": resp_sha256,
                                "output_sha256": item.decoded_field_artifact.sha256 if item.decoded_field_artifact else None,
                                "lossless": True,
                            },
                            {
                                "transformation_id": f"trans-{exchange_id}-{item.position:04d}-normalize",
                                "rule": "utf8_decoded_field_to_strip_normalized",
                                "input_sha256": item.decoded_field_artifact.sha256 if item.decoded_field_artifact else None,
                                "output_sha256": item.normalized_artifact.sha256 if item.normalized_artifact else None,
                                "lossless": False,
                            },
                        ] if item.decoded_field_artifact else [],
                    }
                    for item in evidence_list
                ],
            }
            manifest_identity = self.store.write_json(f"candidates/{exchange_id}.json", candidate_manifest)
            candidate_manifest["manifest"] = manifest_identity.__dict__
            self.persisted_manifests.append(candidate_manifest)

        return tuple(evidence_list)

    def __call__(
        self,
        evidence: tuple[CandidateEvidence, ...],
        exchange_manifest: Mapping[str, Any] | None = None,
    ) -> None:
        if exchange_manifest is not None:
            raw_results = []
            selected_positions = set()
            for item in evidence:
                raw_results.append({
                    "id": item.native_id,
                    "text": item.decoded_field_bytes.decode("utf-8") if item.decoded_field_bytes else None,
                    "fact_type": item.surface,
                    "source_memory_ids": list(item.source_ids),
                })
                if item.included:
                    selected_positions.add(item.position)
            self.capture_and_persist(
                raw_results,
                selected_positions=selected_positions,
                limit=len(selected_positions),
                exchange_manifest=exchange_manifest,
            )


def verify_candidate_integrity(store: AttemptArtifactStore, exchange_id: str) -> bool:
    """Verify that all candidate artifacts and linked HTTP response for an exchange are intact,
    and prove candidates originated from that response with exact values, positions, transformations,
    and dispositions.
    """
    manifest_path = (store.root / f"candidates/{exchange_id}.json").resolve()
    if store.root.resolve() not in manifest_path.parents or not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return False

    http_meta = manifest.get("http_exchange", {}).get("response", {})
    resp_rel = http_meta.get("path")
    resp_sha = http_meta.get("sha256")
    resp_len = http_meta.get("byte_count")
    if not resp_rel or not resp_sha:
        return False
    resp_file = (store.root / resp_rel).resolve()
    if store.root.resolve() not in resp_file.parents or not resp_file.is_file():
        return False
    resp_data = resp_file.read_bytes()
    if len(resp_data) != resp_len or _sha256(resp_data) != resp_sha:
        return False

    # Reparse persisted response bytes to verify candidates originated from that response
    try:
        resp_obj = json.loads(resp_data.decode("utf-8"))
    except Exception:
        return False
    if not isinstance(resp_obj, Mapping) or "results" not in resp_obj:
        return False
    raw_results = resp_obj["results"]
    if not isinstance(raw_results, list):
        return False

    candidates = manifest.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != len(raw_results):
        return False
    if manifest.get("total_candidates") != len(raw_results):
        return False

    selected_count = sum(1 for c in candidates if isinstance(c, Mapping) and c.get("included") is True)
    if manifest.get("selected_count") != selected_count:
        return False

    # Verify disposition consistency
    expected_disposition = (
        "COMPLETE_EMPTY" if len(raw_results) == 0
        else ("FILTERED_ALL" if selected_count == 0 else "COMPLETE_NONEMPTY")
    )
    if manifest.get("retrieval_disposition") != expected_disposition:
        return False

    # Verify candidate values, positions, and transformations against response
    for idx, raw_item in enumerate(raw_results):
        cand = candidates[idx]
        if not isinstance(cand, Mapping):
            return False
        if cand.get("position") != idx + 1:
            return False
        if cand.get("json_path") != f"/results/{idx}":
            return False
        if cand.get("field_path") != f"/results/{idx}/text":
            return False

        if not isinstance(raw_item, Mapping):
            if cand.get("included") is not False or cand.get("discard_reason") != "non_object":
                return False
            if cand.get("decoded_field", {}).get("artifact") is not None:
                return False
            continue

        raw_id = str(raw_item.get("id")) if raw_item.get("id") is not None else None
        if cand.get("native_id") != raw_id:
            return False

        raw_text = raw_item.get("text")
        if not isinstance(raw_text, str):
            if cand.get("included") is not False or cand.get("discard_reason") != "missing_or_nonstring_text":
                return False
            if cand.get("decoded_field", {}).get("artifact") is not None:
                return False
            continue

        if not raw_text.strip():
            if cand.get("included") is not False or cand.get("discard_reason") != "blank_after_existing_strip":
                return False

        # Verify decoded_field artifact
        dec_info = cand.get("decoded_field", {})
        dec_art = dec_info.get("artifact")
        if not dec_art:
            return False
        dec_p = (store.root / dec_art["path"]).resolve()
        if store.root.resolve() not in dec_p.parents or not dec_p.is_file():
            return False
        dec_data = dec_p.read_bytes()
        expected_dec = raw_text.encode("utf-8")
        if dec_data != expected_dec or dec_art["byte_count"] != len(expected_dec) or dec_art["sha256"] != _sha256(expected_dec):
            return False

        # Verify normalized artifact
        norm_info = cand.get("normalized", {})
        norm_art = norm_info.get("artifact")
        if not norm_art:
            return False
        norm_p = (store.root / norm_art["path"]).resolve()
        if store.root.resolve() not in norm_p.parents or not norm_p.is_file():
            return False
        norm_data = norm_p.read_bytes()
        expected_norm = raw_text.strip().encode("utf-8")
        if norm_data != expected_norm or norm_art["byte_count"] != len(expected_norm) or norm_art["sha256"] != _sha256(expected_norm):
            return False

        # Verify transformations
        transforms = cand.get("transformations", [])
        if len(transforms) != 2:
            return False
        t0 = transforms[0]
        if t0.get("rule") != "json_pointer_to_utf8_decoded_field":
            return False
        if t0.get("input_artifact_path") != resp_rel or t0.get("input_sha256") != resp_sha:
            return False
        if t0.get("output_sha256") != dec_art["sha256"]:
            return False
        if t0.get("lossless") is not True:
            return False

        t1 = transforms[1]
        if t1.get("rule") != "utf8_decoded_field_to_strip_normalized":
            return False
        if t1.get("input_sha256") != dec_art["sha256"] or t1.get("output_sha256") != norm_art["sha256"]:
            return False
        if t1.get("lossless") is not False:
            return False

        # Verify surface and parents
        expected_surface = str(raw_item.get("fact_type") or raw_item.get("type")) if (raw_item.get("fact_type") is not None or raw_item.get("type") is not None) else None
        if cand.get("surface") != expected_surface:
            return False
        sources = raw_item.get("source_memory_ids", raw_item.get("source_fact_ids", []))
        expected_parents = [str(v) for v in sources] if isinstance(sources, list) else []
        if cand.get("parent_ids") != expected_parents:
            return False

    return True


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
        self._outstanding = 0
        self.committed_units = 0
        self._counter = 0
        self._lock = threading.Lock()
        self.records: list[dict[str, Any]] = []

    def admit(self, *, endpoint: str, model: str, maximum_units: int | None) -> SendReservation:
        if maximum_units is None or maximum_units < 0:
            raise AccountingRejected("per-send independently justified bound is required")
        with self._lock:
            if self.committed_units + self._outstanding + maximum_units > self.ceiling_units:
                raise AccountingRejected("committed usage and outstanding reservations exhaust call ceiling")
            self._counter += 1
            reservation = SendReservation(f"send-{self._counter:06d}", endpoint, model, maximum_units)
            self._outstanding += maximum_units
            self.records.append({"reservation_id": reservation.reservation_id, "state": "RESERVED", "at": _now(), "endpoint": endpoint, "model": model, "reserved_units": maximum_units})
            return reservation

    def receipt(self, reservation: SendReservation, *, actual_units: int | None, outcome: str) -> None:
        with self._lock:
            if reservation.state != "RESERVED":
                raise AccountingRejected("reservation is not outstanding")
            if actual_units is not None and (actual_units < 0 or actual_units > reservation.maximum_units):
                raise AccountingRejected("actual usage exceeds admitted bound")
            if actual_units is None:
                reservation.state = "USAGE_MISSING"
            else:
                reservation.state = "RECEIPTED"
                self._outstanding -= reservation.maximum_units
                self.committed_units += actual_units
            self.records.append({"reservation_id": reservation.reservation_id, "state": reservation.state, "at": _now(), "outcome": outcome, "actual_units": actual_units, "reserved_units": reservation.maximum_units})

    @property
    def outstanding_units(self) -> int:
        """Reserved capacity, including sends whose usage receipt is missing."""
        with self._lock:
            return self._outstanding


def assess_operation_coverage(pages: tuple[tuple[Mapping[str, Any], ...], ...]) -> str:
    """Return COMPLETE only for explicitly terminal, paginated evidence."""
    terminal = {"completed"}
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
