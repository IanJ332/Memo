"""Offline qualification of an owned OpenAI-compatible completions resource.

This is NOT a Hindsight launcher or complete runtime interception. No upstream
module is imported or patched. Real-provider startup is deliberately blocked.
An independently verified endpoint contract would be needed to replace the
fake-only token contracts here; prompt estimates are never admission bounds.
"""

from __future__ import annotations

import contextvars
import hashlib
import json
import os
import threading
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Any, Iterator, Mapping
from urllib.parse import urlsplit

from .phase08d3 import (
    AccountingRejected, ArtifactIdentity, AttemptArtifactStore, SendAccounting,
    SendReservation, _now, verify_inventory,
)


@dataclass(frozen=True)
class SendContext:
    attempt_id: str
    role: str
    operation: str
    logical_call_id: str
    task_id: str | None = None
    condition_id: str | None = None
    channel: str = "provider_internal_hosted_llm"


_context: contextvars.ContextVar[SendContext | None] = contextvars.ContextVar(
    "phase08d5_send_context", default=None
)


@contextmanager
def send_context(value: SendContext) -> Iterator[None]:
    token = _context.set(value)
    try:
        yield
    finally:
        _context.reset(token)


def _integer(value: Any, *, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


@dataclass(frozen=True)
class ProcessTopology:
    api_processes: int = 1
    worker_processes: int = 0
    reload: bool = False
    standalone_worker: bool = False

    def validate(self) -> None:
        # API background tasks may share this process; standalone workers may not.
        if (type(self.api_processes) is not int or self.api_processes != 1
                or type(self.worker_processes) is not int or self.worker_processes != 0
                or self.reload is not False or self.standalone_worker is not False):
            raise AccountingRejected("multiprocess, reload and standalone workers are unsupported")


def require_hindsight_runtime_ready(topology: ProcessTopology) -> None:
    """Mandatory gate for any future launcher, BEFORE engine construction.

    There is no approved live configuration. This cannot qualify an endpoint,
    installed SDK, other client instances, or native CLI workers by assertion.
    """
    topology.validate()
    raise AccountingRejected(
        "BLOCKED: complete client ownership, installed transport coverage and "
        "endpoint-enforced token bounds are unverified"
    )


@dataclass(frozen=True)
class OfflineTokenContract:
    """Total inclusive token maximum from a deterministic fake's specification.

    Evidence must be an existing immutable attempt artifact. The basis is
    intentionally fake-only: neither a context-window guess nor a tokenizer
    estimate nor an output cap establishes an endpoint's hard total maximum.
    """
    endpoint: str
    model: str
    maximum_total_tokens: int
    evidence: ArtifactIdentity
    basis: str = "DETERMINISTIC_FAKE_TOTAL"


class GovernedSendSession:
    """Single-process, multi-thread/event-loop admission shared by owned clients.

    Call slots are consumed permanently before dispatch. Unreceipted tokens
    remain reserved; any ambiguous outcome latches admission closed. Already
    admitted concurrent calls may finish and settle, but no new calls enter.
    """

    def __init__(
        self, store: AttemptArtifactStore, *, attempt_id: str,
        contracts: tuple[OfflineTokenContract, ...], call_ceiling: int,
        token_ceiling: int, concurrency_ceiling: int,
        topology: ProcessTopology = ProcessTopology(),
    ) -> None:
        topology.validate()
        if not attempt_id or any(not _integer(v, minimum=1) for v in (
            call_ceiling, token_ceiling, concurrency_ceiling
        )) or not contracts:
            raise AccountingRejected("explicit identity and finite positive ceilings are required")
        allowed: dict[tuple[str, str], OfflineTokenContract] = {}
        for contract in contracts:
            url = urlsplit(contract.endpoint)
            # Public fake endpoints only; no credential/query-bearing evidence.
            if (contract.basis != "DETERMINISTIC_FAKE_TOTAL"
                    or not _integer(contract.maximum_total_tokens, minimum=1)
                    or not contract.model or url.scheme not in {"http", "https"}
                    or not url.hostname or not url.hostname.endswith(".test")
                    or url.username or url.password or url.query or url.fragment
                    or not verify_inventory(store, (contract.evidence,))):
                raise AccountingRejected("verified fake total-token contract is required")
            try:
                proof = json.loads((store.root / contract.evidence.path).read_bytes())
                if not isinstance(proof, dict) or any(proof.get(k) != getattr(contract, k) for k in (
                    "basis", "endpoint", "model", "maximum_total_tokens"
                )):
                    raise ValueError("contract binding mismatch")
            except (OSError, ValueError, TypeError) as exc:
                raise AccountingRejected("fake contract evidence binding is invalid") from exc
            key = (contract.endpoint, contract.model)
            if key in allowed:
                raise AccountingRejected("duplicate endpoint/model contract")
            allowed[key] = contract
        self.store = store
        self.attempt_id = attempt_id
        self._contracts = allowed
        self._accounting = SendAccounting(token_ceiling)
        self._pid = os.getpid()
        self._lock = threading.Lock()
        self._calls = 0
        self._active = 0
        self._event_count = 0
        self._blocked = False
        self._call_ceiling = call_ceiling
        self._concurrency_ceiling = concurrency_ceiling
        self._identities: list[ArtifactIdentity] = []
        self._write("POLICY", contracts=[asdict(c) for c in contracts],
                    call_ceiling=call_ceiling, token_ceiling=token_ceiling,
                    concurrency_ceiling=concurrency_ceiling,
                    topology=asdict(topology), qualification="OFFLINE_FAKE_ONLY")

    def _owner(self) -> None:
        # Check before taking a lock: a fork can inherit a locked parent mutex.
        if os.getpid() != self._pid:
            raise AccountingRejected("inherited session cannot admit in another process")

    def _write(self, state: str, **payload: Any) -> None:
        self._event_count += 1
        try:
            identity = self.store.write_json(f"internal-sends/event-{self._event_count:06d}.json", {
                "attempt_id": self.attempt_id, "channel": "provider_internal_hosted_llm",
                "pid": self._pid, "at": _now(), "state": state, **payload,
            })
            self._identities.append(identity)
        except BaseException:
            self._blocked = True
            raise

    def _deny(self, reason: str) -> None:
        self._blocked = True
        self._write("REJECTED", reason=reason)
        raise AccountingRejected(reason)

    def reserve(self, endpoint: str, kwargs: Mapping[str, Any]) -> tuple[SendReservation, SendContext]:
        self._owner()
        with self._lock:
            if self._blocked:
                raise AccountingRejected("session admission is latched closed")
            try:
                intact = verify_inventory(self.store, tuple(self._identities) + tuple(
                    c.evidence for c in self._contracts.values()
                ))
            except OSError:
                intact = False
            if not intact:
                self._deny("accounting or contract evidence integrity failed")
            context = _context.get()
            if (context is None or context.attempt_id != self.attempt_id
                    or context.channel != "provider_internal_hosted_llm"
                    or not all(isinstance(v, str) and v for v in (
                        context.role, context.operation, context.logical_call_id
                    ))):
                self._deny("missing or unauthorized send attribution")
            model = kwargs.get("model")
            if not isinstance(model, str):
                self._deny("endpoint/model is not allowlisted")
            contract = self._contracts.get((endpoint, model))
            if contract is None:
                self._deny("endpoint/model is not allowlisted")
            # These can override the wire body/destination, multiply outputs or
            # bypass receipt collection. Do not silently strip or change them.
            allowed_keys = {"model", "messages", "max_tokens", "max_completion_tokens",
                            "temperature", "response_format", "tools", "tool_choice",
                            "reasoning_effort", "seed", "user", "prompt_cache_key",
                            "stream", "n", "timeout"}
            caps = [kwargs[k] for k in ("max_tokens", "max_completion_tokens") if k in kwargs]
            if (set(kwargs) - allowed_keys or kwargs.get("stream", False) is not False
                    or type(kwargs.get("n", 1)) is not int or kwargs.get("n", 1) != 1
                    or len(caps) != 1 or not _integer(caps[0], minimum=1)
                    or caps[0] > contract.maximum_total_tokens):
                self._deny("unknown request bounds, override or unsupported request mode")
            if self._calls >= self._call_ceiling:
                self._deny("call ceiling exhausted")
            if self._active >= self._concurrency_ceiling:
                self._deny("concurrency ceiling exhausted")
            try:
                reservation = self._accounting.admit(
                    endpoint=endpoint, model=contract.model,
                    maximum_units=contract.maximum_total_tokens,
                )
            except AccountingRejected:
                self._deny("token ceiling exhausted")
            self._calls += 1
            self._active += 1
            self._write("RESERVED", reservation=asdict(reservation),
                        attribution=asdict(context), contract_evidence=asdict(contract.evidence),
                        requested_completion_cap=caps[0],
                        request_sha256=hashlib.sha256(json.dumps(
                            dict(kwargs), sort_keys=True, separators=(",", ":"),
                            allow_nan=False,
                        ).encode("utf-8")).hexdigest())
            return reservation, context

    def settle(self, reservation: SendReservation, context: SendContext,
               usage: dict[str, Any] | None, *, outcome: str) -> None:
        self._owner()
        with self._lock:
            if usage is None:
                self._blocked = True
            try:
                self._accounting.receipt(reservation,
                    actual_units=usage["total_tokens"] if usage else None, outcome=outcome)
            except AccountingRejected:
                # Preserve full reservation on an over-bound receipt, never refund.
                self._blocked = True
                self._accounting.receipt(reservation, actual_units=None, outcome="BOUND_VIOLATION")
                self._write("BOUND_VIOLATION", reservation=asdict(reservation),
                            attribution=asdict(context), usage=usage)
                raise
            finally:
                self._active -= 1
            self._write(reservation.state, reservation=asdict(reservation),
                        attribution=asdict(context), outcome=outcome, usage=usage)
            if usage is None:
                raise AccountingRejected("usage unresolved; session admission is latched closed")

    def invalidate(self, reason: str) -> None:
        self._owner()
        with self._lock:
            self._deny(reason)

    def snapshot(self) -> dict[str, Any]:
        self._owner()
        with self._lock:
            return {"attempt_id": self.attempt_id, "calls_reserved": self._calls,
                    "active": self._active, "committed_tokens": self._accounting.committed_units,
                    "outstanding_tokens": self._accounting.outstanding_units,
                    "blocked": self._blocked, "evidence": tuple(self._identities)}


def _field(value: Any, name: str) -> Any:
    return value.get(name) if isinstance(value, Mapping) else getattr(value, name, None)


def _usage(response: Any) -> dict[str, Any] | None:
    raw = _field(response, "usage")
    counts = {k: _field(raw, k) for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
    if (not all(_integer(v) for v in counts.values())
            or counts["total_tokens"] != counts["prompt_tokens"] + counts["completion_tokens"]):
        return None
    # OpenAI completion_tokens includes reasoning; prompt_tokens includes cache.
    # Keep subsets separately, without adding them a second time.
    for key, parent, field, maximum in (
        ("reasoning_tokens", "completion_tokens_details", "reasoning_tokens", counts["completion_tokens"]),
        ("cached_tokens", "prompt_tokens_details", "cached_tokens", counts["prompt_tokens"]),
    ):
        subset = _field(_field(raw, parent), field)
        if subset is not None and (not _integer(subset) or subset > maximum):
            return None
        counts[key] = subset
    return counts


class GovernedCompletions:
    """Owned-instance wrapper, one reservation for every create invocation.

    Qualifies deterministic fake clients only. SDK/HTTP/transport retries below
    create, redirects, and sends through other clients are not proven here.
    """
    def __init__(self, original: Any, client: Any, session: GovernedSendSession) -> None:
        self._original = original
        self._client = client
        self._session = session
        self._endpoint = str(client.base_url)

    async def create(self, **kwargs: Any) -> Any:
        self._session._owner()
        if (str(self._client.base_url) != self._endpoint
                or type(self._client.max_retries) is not int or self._client.max_retries != 0
                or self._client.chat.completions is not self):
            self._session.invalidate("owned client identity, endpoint or SDK retries changed")
        # Freeze request arguments before admission to avoid caller mutation while
        # awaiting the client. This subset is JSON-shaped; no schema re-encoding.
        try:
            request = json.loads(json.dumps(kwargs, allow_nan=False))
        except (ValueError, TypeError):
            self._session.invalidate("request is outside the audited JSON-shaped subset")
        reservation, context = self._session.reserve(self._endpoint, request)
        try:
            response = await self._original.create(**request)
        except BaseException as exc:
            # Errors/cancellations cannot be assumed unbilled, even at connection
            # time. Admission failure is a terminal non-SDK exception.
            try:
                self._session.settle(reservation, context, None, outcome=type(exc).__name__)
            except AccountingRejected as denied:
                if not isinstance(exc, Exception):
                    raise exc
                raise denied from exc
            raise
        try:
            usage = _usage(response)
        except Exception:
            usage = None
        self._session.settle(reservation, context, usage, outcome="RESPONSE")
        return response


def instrument_owned_provider(provider: Any, *, enabled: bool = False,
                              session: GovernedSendSession | None = None,
                              topology: ProcessTopology = ProcessTopology()) -> Any:
    """Explicit, optional instance injection; does not wrap factories or classes.

    Call only on owned deterministic fakes in this phase. A future runtime
    launcher MUST pass require_hindsight_runtime_ready first (currently BLOCKED).
    Disabled instrumentation returns without reading or mutating the provider.
    """
    if not enabled:
        return provider
    topology.validate()
    if session is None:
        raise AccountingRejected("send session is required")
    session._owner()
    client = provider._client
    if (provider.provider != "openai" or type(client.max_retries) is not int
            or client.max_retries != 0
            or not any(endpoint == str(client.base_url) for endpoint, _ in session._contracts)
            or isinstance(client.chat.completions, GovernedCompletions)):
        session.invalidate("unsupported provider, endpoint, SDK retries or existing wrapper")
    client.chat.completions = GovernedCompletions(client.chat.completions, client, session)
    return provider
