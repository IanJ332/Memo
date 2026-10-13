"""Deterministic fake-only send-boundary tests; no provider SDK is imported."""

from __future__ import annotations

import asyncio
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace

import pytest

from memlife.runner.phase08d3 import AccountingRejected, AttemptArtifactStore, CaptureFailure, verify_inventory
from memlife.runner.phase08d5 import (
    GovernedSendSession, OfflineTokenContract, ProcessTopology, SendContext,
    instrument_owned_provider, require_hindsight_runtime_ready, send_context,
)


ENDPOINT = "https://llm.test/v1/"
MODEL = "fake-text"
CTX = SendContext("offline-1", "retain", "foreground", "logical-1")
REQUEST = {"model": MODEL, "messages": [{"role": "user", "content": "é\n  source"}],
           "max_completion_tokens": 16}


def response(prompt=10, completion=6, **usage):
    return SimpleNamespace(usage=SimpleNamespace(
        prompt_tokens=prompt, completion_tokens=completion,
        total_tokens=prompt + completion, **usage
    ))


class FakeCompletions:
    def __init__(self, replies=None):
        self.replies = list(replies or [response()])
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        answer = self.replies.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return answer


class FakeProvider:
    provider = "openai"

    def __init__(self, completions):
        self._client = SimpleNamespace(base_url=ENDPOINT, max_retries=0,
                                       chat=SimpleNamespace(completions=completions))

    async def call(self, **kwargs):
        return await self._client.chat.completions.create(**kwargs)

    async def verify_connection(self):
        return await self.call(**REQUEST)


def session(tmp_path, *, calls=20, tokens=1000, concurrent=4):
    store = AttemptArtifactStore(tmp_path / "attempt")
    evidence = store.write_json("fake-contract.json", {
        "basis": "DETERMINISTIC_FAKE_TOTAL", "endpoint": ENDPOINT,
        "model": MODEL, "maximum_total_tokens": 100,
        "source": "FakeCompletions deterministic test specification; no endpoint qualification",
    })
    gate = GovernedSendSession(store, attempt_id="offline-1",
        contracts=(OfflineTokenContract(ENDPOINT, MODEL, 100, evidence),),
        call_ceiling=calls, token_ceiling=tokens, concurrency_ceiling=concurrent)
    return gate


def instrument(gate, original=None):
    original = original or FakeCompletions()
    provider = FakeProvider(original)
    instrument_owned_provider(provider, enabled=True, session=gate)
    return provider, original


def invoke(provider, context=CTX, **changes):
    with send_context(context):
        return asyncio.run(provider.call(**{**REQUEST, **changes}))


def events(gate):
    return [json.loads((gate.store.root / identity.path).read_bytes())
            for identity in gate.snapshot()["evidence"]]


@pytest.mark.parametrize("operation,role", [
    ("startup", "default"), ("health", "default"), ("foreground", "retain"),
    ("background", "consolidation"), ("background", "dedup"), ("tools", "reflect"),
])
def test_owned_startup_health_foreground_background_and_tools(tmp_path, operation, role):
    gate = session(tmp_path)
    provider, original = instrument(gate)
    expected = original.replies[0]
    context = replace(CTX, operation=operation, role=role, task_id="task-1", condition_id="c-1")
    with send_context(context):
        result = asyncio.run(provider.verify_connection() if operation in {"startup", "health"}
                             else provider.call(**REQUEST))
    assert result is expected
    assert original.calls == [REQUEST]
    assert gate.snapshot()["committed_tokens"] == 16
    assert gate.snapshot()["outstanding_tokens"] == 0
    record = events(gate)[1]
    assert record["state"] == "RESERVED" and record["attribution"] == context.__dict__
    assert record["reservation"]["maximum_units"] == 100
    assert verify_inventory(gate.store, gate.snapshot()["evidence"])


def test_receipted_sends_retried_after_parse_failure_have_distinct_reservations(tmp_path):
    gate = session(tmp_path, calls=3)
    provider, original = instrument(gate, FakeCompletions([response(), response(), response()]))

    async def logical_call():
        for _ in range(3):
            answer = await provider.call(**REQUEST)
            # A native result-validation retry follows a successful usage receipt.
            try:
                json.loads("not JSON" if len(original.calls) < 3 else "{}")
            except json.JSONDecodeError:
                continue
            return answer

    with send_context(CTX):
        asyncio.run(logical_call())
    admitted = [e for e in events(gate) if e["state"] == "RESERVED"]
    assert len(admitted) == len(original.calls) == 3
    assert len({e["reservation"]["reservation_id"] for e in admitted}) == 3
    assert {e["attribution"]["logical_call_id"] for e in admitted} == {"logical-1"}
    with pytest.raises(AccountingRejected, match="call ceiling"):
        invoke(provider)
    assert len(original.calls) == 3


@pytest.mark.parametrize("bad", [
    SimpleNamespace(usage=None), SimpleNamespace(usage={}),
    SimpleNamespace(usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 3}),
    SimpleNamespace(usage={"prompt_tokens": True, "completion_tokens": 1, "total_tokens": 2}),
    SimpleNamespace(usage={"prompt_tokens": 1, "completion_tokens": -1, "total_tokens": 0}),
    SimpleNamespace(usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": float("nan")}),
    response(completion_tokens_details={"reasoning_tokens": 7}),
    response(prompt_tokens_details={"cached_tokens": "10"}),
])
def test_missing_malformed_and_inconsistent_usage_retains_bound_and_stops(tmp_path, bad):
    gate = session(tmp_path)
    provider, original = instrument(gate, FakeCompletions([bad, response()]))
    with pytest.raises(AccountingRejected, match="usage unresolved"):
        invoke(provider)
    assert gate.snapshot()["outstanding_tokens"] == 100
    assert gate.snapshot()["committed_tokens"] == 0
    with pytest.raises(AccountingRejected, match="latched"):
        invoke(provider)
    assert len(original.calls) == 1
    assert events(gate)[-1]["state"] == "USAGE_MISSING"


def test_reasoning_cache_are_inclusive_subsets_not_extra_tokens(tmp_path):
    gate = session(tmp_path)
    provider, _ = instrument(gate, FakeCompletions([response(
        completion_tokens_details={"reasoning_tokens": 5},
        prompt_tokens_details={"cached_tokens": 8})]))
    invoke(provider)
    assert gate.snapshot()["committed_tokens"] == 16
    assert events(gate)[-1]["usage"]["reasoning_tokens"] == 5
    assert events(gate)[-1]["usage"]["cached_tokens"] == 8


@pytest.mark.parametrize("failure", [TimeoutError("private prompt"), RuntimeError("private token"),
                                     asyncio.CancelledError()])
def test_failure_or_cancellation_is_not_zero_cost_and_cannot_retry(tmp_path, failure):
    gate = session(tmp_path)
    provider, original = instrument(gate, FakeCompletions([failure, response()]))
    with pytest.raises(asyncio.CancelledError if isinstance(failure, asyncio.CancelledError)
                       else AccountingRejected):
        invoke(provider)
    with pytest.raises(AccountingRejected, match="latched"):
        invoke(provider)
    assert len(original.calls) == 1
    assert gate.snapshot()["outstanding_tokens"] == 100
    assert events(gate)[-1]["outcome"] == type(failure).__name__
    assert b"private" not in b"".join(p.read_bytes() for p in (gate.store.root / "internal-sends").glob("*.json"))


def test_bound_violation_preserves_full_reservation_and_receipt(tmp_path):
    gate = session(tmp_path)
    provider, _ = instrument(gate, FakeCompletions([response(100, 1)]))
    with pytest.raises(AccountingRejected, match="exceeds admitted"):
        invoke(provider)
    assert gate.snapshot()["outstanding_tokens"] == 100
    assert gate.snapshot()["blocked"] is True
    assert events(gate)[-1]["state"] == "BOUND_VIOLATION"
    assert events(gate)[-1]["usage"]["total_tokens"] == 101


@pytest.mark.parametrize("changes", [
    {"model": "unauthorized"}, {"model": []}, {"max_completion_tokens": None},
    {"max_completion_tokens": True}, {"max_completion_tokens": 101},
    {"max_tokens": 16}, {"stream": True}, {"n": 2},
    {"extra_body": {"model": "unauthorized"}}, {"extra_headers": {"x": "y"}},
    {"estimated_prompt_tokens": 1}, {"extra_query": {}},
])
def test_unknown_bounds_overrides_and_unauthorized_models_never_dispatch(tmp_path, changes):
    gate = session(tmp_path)
    provider, original = instrument(gate)
    with pytest.raises(AccountingRejected):
        invoke(provider, **changes)
    assert original.calls == [] and gate.snapshot()["calls_reserved"] == 0


@pytest.mark.parametrize("context", [None, replace(CTX, attempt_id="other-attempt"),
    replace(CTX, channel="local_onnx_embedding"), replace(CTX, channel="downstream_rq3"),
    replace(CTX, task_id="background", logical_call_id="")])
def test_missing_wrong_attempt_embedding_and_rq3_context_rejected(tmp_path, context):
    gate = session(tmp_path)
    provider, original = instrument(gate)
    with pytest.raises(AccountingRejected, match="attribution"):
        invoke(provider, context)
    assert original.calls == []
    assert gate.snapshot()["committed_tokens"] == 0


@pytest.mark.parametrize("tokens,calls", [(100, 20), (1000, 1)])
def test_concurrent_threads_reserve_atomically_across_roles_and_event_loops(tmp_path, tokens, calls):
    gate = session(tmp_path, tokens=tokens, calls=calls)
    entered, release = threading.Event(), threading.Event()

    class WaitingFake(FakeCompletions):
        async def create(self, **kwargs):
            entered.set()
            assert release.wait(5)
            return await super().create(**kwargs)

    first, original = instrument(gate, WaitingFake())
    second, other = instrument(gate)
    with ThreadPoolExecutor(2) as pool:
        pending = pool.submit(invoke, first, replace(CTX, operation="background", task_id="t1"))
        try:
            assert entered.wait(5)
            assert gate.snapshot()["outstanding_tokens"] == 100
            with pytest.raises(AccountingRejected, match="ceiling"):
                invoke(second)
        finally:
            release.set()
        assert pending.result().usage.total_tokens == 16
    assert len(original.calls) == 1 and other.calls == []
    assert gate.snapshot()["committed_tokens"] == 16
    assert gate.snapshot()["blocked"] is True


def test_concurrency_ceiling_stops_new_admissions_but_settles_inflight(tmp_path):
    gate = session(tmp_path, concurrent=1)
    entered, release = threading.Event(), threading.Event()

    class WaitingFake(FakeCompletions):
        async def create(self, **kwargs):
            entered.set()
            assert release.wait(5)
            return await super().create(**kwargs)

    provider, original = instrument(gate, WaitingFake())
    with ThreadPoolExecutor(1) as pool:
        pending = pool.submit(invoke, provider)
        try:
            assert entered.wait(5)
            with pytest.raises(AccountingRejected, match="concurrency"):
                invoke(provider)
        finally:
            release.set()
        pending.result()
    assert len(original.calls) == 1 and gate.snapshot()["active"] == 0


@pytest.mark.parametrize("change", ["endpoint", "retries", "replacement"])
def test_mutated_owned_client_fails_before_dispatch(tmp_path, change):
    gate = session(tmp_path)
    provider, original = instrument(gate)
    wrapper = provider._client.chat.completions
    if change == "endpoint":
        provider._client.base_url = "https://unauthorized.test/v1/"
    elif change == "retries":
        provider._client.max_retries = 1
    else:
        provider._client.chat.completions = FakeCompletions()
    with send_context(CTX), pytest.raises(AccountingRejected, match="changed"):
        asyncio.run(wrapper.create(**REQUEST))
    assert original.calls == []


@pytest.mark.parametrize("field,value", [("provider", "ollama"), ("retries", 2), ("endpoint", "https://other.test/")])
def test_startup_rejects_native_alternate_provider_endpoint_or_sdk_retries(tmp_path, field, value):
    gate = session(tmp_path)
    provider = FakeProvider(FakeCompletions())
    if field == "provider":
        provider.provider = value
    else:
        setattr(provider._client, "max_retries" if field == "retries" else "base_url", value)
    with pytest.raises(AccountingRejected, match="unsupported"):
        instrument_owned_provider(provider, enabled=True, session=gate)


@pytest.mark.parametrize("topology", [ProcessTopology(api_processes=2),
    ProcessTopology(worker_processes=1), ProcessTopology(reload=True),
    ProcessTopology(standalone_worker=True), ProcessTopology(api_processes=True)])
def test_multiprocess_config_is_rejected_before_provider_construction(topology):
    with pytest.raises(AccountingRejected, match="unsupported"):
        require_hindsight_runtime_ready(topology)


def test_real_runtime_is_blocked_even_for_single_process():
    with pytest.raises(AccountingRejected, match="BLOCKED"):
        require_hindsight_runtime_ready(ProcessTopology())


@pytest.mark.skipif(not hasattr(os, "fork"), reason="requires local fork")
def test_inherited_session_rejected_before_parent_lock_in_child(tmp_path):
    gate = session(tmp_path)
    provider, original = instrument(gate)
    read_fd, write_fd = os.pipe()
    # An inherited locked mutex must not deadlock a forked worker.
    with gate._lock:
        pid = os.fork()
        if pid == 0:
            os.close(read_fd)
            try:
                invoke(provider)
            except AccountingRejected:
                os.write(write_fd, b"rejected")
                os._exit(0)
            os._exit(1)
    os.close(write_fd)
    try:
        assert os.read(read_fd, 32) == b"rejected"
        assert os.waitpid(pid, 0)[1] == 0
    finally:
        os.close(read_fd)
    assert original.calls == [] and gate.snapshot()["calls_reserved"] == 0


def test_exclusive_evidence_collision_prevents_send(tmp_path):
    gate = session(tmp_path)
    provider, original = instrument(gate)
    before = gate.store.write_bytes("internal-sends/event-000002.json", b"original evidence")
    with pytest.raises(CaptureFailure, match="exclusive"):
        invoke(provider)
    assert original.calls == []
    assert gate.snapshot()["outstanding_tokens"] == 100
    assert gate.snapshot()["blocked"] is True
    assert verify_inventory(gate.store, (before,))


def test_receipt_write_failure_withholds_response_and_stops(tmp_path, monkeypatch):
    gate = session(tmp_path)
    provider, original = instrument(gate)
    write = gate.store.write_json

    def fail_receipt(path, payload):
        if payload["state"] == "RECEIPTED":
            raise CaptureFailure("receipt write failed")
        return write(path, payload)

    monkeypatch.setattr(gate.store, "write_json", fail_receipt)
    with pytest.raises(CaptureFailure, match="receipt write failed"):
        invoke(provider)
    with pytest.raises(AccountingRejected, match="latched"):
        invoke(provider)
    assert len(original.calls) == 1
    assert gate.snapshot()["committed_tokens"] == 16
    assert events(gate)[-1]["state"] == "RESERVED"


def test_disabled_instrumentation_identity_payload_response_and_exception_parity(tmp_path):
    # Disabled branch must not even inspect unsupported startup config.
    opaque = object()
    assert instrument_owned_provider(opaque, enabled=False, topology=ProcessTopology(api_processes=8)) is opaque
    answer, error = response(), TimeoutError("same exception")
    original = FakeCompletions([answer, error])
    provider = FakeProvider(original)
    assert instrument_owned_provider(provider, enabled=False) is provider
    assert provider._client.chat.completions is original
    assert invoke(provider) is answer
    with pytest.raises(TimeoutError) as raised:
        invoke(provider)
    assert raised.value is error and original.calls == [REQUEST, REQUEST]
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("basis,maximum", [("PROMPT_ESTIMATE", 100), ("ENDPOINT_ENFORCED_TOTAL", 100),
    ("DETERMINISTIC_FAKE_TOTAL", None), ("DETERMINISTIC_FAKE_TOTAL", float("inf")),
    ("DETERMINISTIC_FAKE_TOTAL", True)])
def test_estimates_unknown_or_unverified_real_bounds_rejected(tmp_path, basis, maximum):
    store = AttemptArtifactStore(tmp_path / "attempt")
    proof = store.write_json("proof.json", {"fake": True})
    with pytest.raises(AccountingRejected, match="contract"):
        GovernedSendSession(store, attempt_id="offline-1",
            contracts=(OfflineTokenContract(ENDPOINT, MODEL, maximum, proof, basis),),
            call_ceiling=1, token_ceiling=100, concurrency_ceiling=1)


def test_context_does_not_leak_between_calls(tmp_path):
    gate = session(tmp_path)
    provider, original = instrument(gate, FakeCompletions([response(), response()]))
    invoke(provider)
    with pytest.raises(AccountingRejected, match="attribution"):
        asyncio.run(provider.call(**REQUEST))
    assert len(original.calls) == 1


def test_missing_usage_blocks_fallback_to_another_owned_role_client(tmp_path):
    gate = session(tmp_path)
    primary, first = instrument(gate, FakeCompletions([SimpleNamespace(usage=None)]))
    fallback, second = instrument(gate)
    with pytest.raises(AccountingRejected, match="usage unresolved"):
        invoke(primary)
    with pytest.raises(AccountingRejected, match="latched"):
        invoke(fallback, replace(CTX, role="fallback"))
    assert len(first.calls) == 1 and second.calls == []


def test_json_shaped_tool_send_preserves_payload_and_response(tmp_path):
    gate = session(tmp_path)
    provider, original = instrument(gate)
    answer = original.replies[0]
    tools = [{"type": "function", "function": {"name": "lookup", "parameters": {"type": "object"}}}]
    assert invoke(provider, replace(CTX, role="reflect", operation="tools"),
                  tools=tools, tool_choice="required") is answer
    assert original.calls == [{**REQUEST, "tools": tools, "tool_choice": "required"}]


def test_committed_plus_full_next_bound_exhausts_even_when_estimate_would_fit(tmp_path):
    gate = session(tmp_path, tokens=100)
    provider, original = instrument(gate, FakeCompletions([response(), response()]))
    invoke(provider)
    with pytest.raises(AccountingRejected, match="token ceiling"):
        invoke(provider)
    assert len(original.calls) == 1
    assert gate.snapshot()["committed_tokens"] == 16


def test_concurrent_async_background_tasks_keep_distinct_attribution(tmp_path):
    gate = session(tmp_path, tokens=200, concurrent=2)

    class ConcurrentFake:
        def __init__(self):
            self.calls = []
            self.ready = asyncio.Event()

        async def create(self, **kwargs):
            self.calls.append(kwargs)
            if len(self.calls) == 2:
                assert gate.snapshot()["outstanding_tokens"] == 200
                self.ready.set()
            await self.ready.wait()
            return response()

    async def run():
        original = ConcurrentFake()
        provider, _ = instrument(gate, original)

        async def task(label):
            context = replace(CTX, operation="background", task_id=label, logical_call_id=label)
            with send_context(context):
                return await provider.call(**REQUEST)

        await asyncio.wait_for(asyncio.gather(task("t1"), task("t2")), timeout=5)
        assert len(original.calls) == 2

    asyncio.run(run())
    assert gate.snapshot()["committed_tokens"] == 32
    assert gate.snapshot()["outstanding_tokens"] == 0
    assert {e["attribution"]["task_id"] for e in events(gate) if e["state"] == "RESERVED"} == {"t1", "t2"}


@pytest.mark.parametrize("target", ["contract", "accounting"])
def test_tampered_immutable_evidence_stops_before_send(tmp_path, target):
    gate = session(tmp_path)
    provider, original = instrument(gate)
    path = gate.store.root / ("fake-contract.json" if target == "contract" else "internal-sends/event-000001.json")
    path.write_bytes(b"tampered by external actor")
    with pytest.raises(AccountingRejected, match="integrity"):
        invoke(provider)
    assert original.calls == []


@pytest.mark.parametrize("ceiling", [None, True, -1, 0, float("inf"), 1.5])
def test_nonfinite_or_ambiguous_ceilings_fail_at_startup(tmp_path, ceiling):
    store = AttemptArtifactStore(tmp_path / "attempt")
    proof = store.write_json("proof.json", {"fake": True})
    with pytest.raises(AccountingRejected, match="ceilings"):
        GovernedSendSession(store, attempt_id="offline-1",
            contracts=(OfflineTokenContract(ENDPOINT, MODEL, 100, proof),),
            call_ceiling=ceiling, token_ceiling=100, concurrency_ceiling=1)
