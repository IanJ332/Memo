"""Negative ownership qualification; these are NOT native SDK/runtime tests."""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from memlife.runner.phase08d3 import AccountingRejected, AttemptArtifactStore
from memlife.runner.phase08d5 import (
    GovernedSendSession, OfflineTokenContract, ProcessTopology, SendContext,
    instrument_owned_provider, require_hindsight_runtime_ready, send_context,
)


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "phase08d6_audit", ROOT / "scripts/qualify_phase08d6_offline.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)
ENDPOINT = "https://qualification.test/v1/"
REQUEST = {"model": "offline", "messages": [{"role": "user", "content": "fixture"}],
           "max_completion_tokens": 8}
CONTEXT = SendContext("d6-negative", "retain", "foreground", "logical-1")


class OfflineResource:
    """In-memory response stub, no socket or SDK access."""
    def __init__(self):
        self.sends = 0

    async def create(self, **kwargs):
        self.sends += 1
        return SimpleNamespace(usage=SimpleNamespace(
            prompt_tokens=8, completion_tokens=8, total_tokens=16))


def boundary(tmp_path):
    store = AttemptArtifactStore(tmp_path / "negative-ownership")
    proof = store.write_json("contract.json", {
        "basis": "DETERMINISTIC_FAKE_TOTAL", "endpoint": ENDPOINT,
        "model": "offline", "maximum_total_tokens": 32,
    })
    session = GovernedSendSession(store, attempt_id="d6-negative",
        contracts=(OfflineTokenContract(ENDPOINT, "offline", 32, proof),),
        call_ceiling=1, token_ceiling=32, concurrency_ceiling=1)
    original = OfflineResource()
    client = SimpleNamespace(base_url=ENDPOINT, max_retries=0,
                             chat=SimpleNamespace(completions=original))
    provider = SimpleNamespace(provider="openai", _client=client)
    instrument_owned_provider(provider, enabled=True, session=session)
    return provider, original, session


@pytest.mark.parametrize("bypass", ["retained_resource", "replaced_resource", "replaced_client",
                                   "responses", "batch_submission", "unowned_member"])
def test_resource_wrapper_cannot_enforce_a_ceiling_on_uncovered_paths(tmp_path, bypass):
    """Counterexample to completeness, never evidence of native send coverage.

    D5's old-wrapper identity check only runs if that wrapper is invoked. The
    ordinary lookup of a replaced object and retained references avoid it.
    """
    provider, original, gate = boundary(tmp_path)
    with send_context(CONTEXT):
        asyncio.run(provider._client.chat.completions.create(**REQUEST))
    assert gate.snapshot()["calls_reserved"] == 1
    resource = OfflineResource()
    if bypass == "retained_resource":
        resource = original
    elif bypass == "replaced_resource":
        provider._client.chat.completions = resource
        resource = provider._client.chat.completions
    elif bypass == "replaced_client":
        provider._client = SimpleNamespace(chat=SimpleNamespace(completions=resource))
        resource = provider._client.chat.completions
    elif bypass == "responses":
        provider._client.responses = resource
        resource = provider._client.responses
    elif bypass == "batch_submission":
        provider._client.batches = resource
        resource = provider._client.batches
    else:
        member = SimpleNamespace(chat=SimpleNamespace(completions=resource))
        resource = member.chat.completions
    before = resource.sends
    # No attribution, no capacity remaining, yet a direct ungoverned path runs.
    asyncio.run(resource.create(**REQUEST))
    assert resource.sends == before + 1
    assert gate.snapshot()["calls_reserved"] == 1
    assert gate.snapshot()["blocked"] is False


@pytest.mark.parametrize("topology", [ProcessTopology(), ProcessTopology(api_processes=2),
    ProcessTopology(reload=True), ProcessTopology(worker_processes=1),
    ProcessTopology(standalone_worker=True)])
def test_gate_stops_before_any_engine_factory_even_when_dependencies_are_available(topology):
    constructed = []

    def offline_launch_order():
        require_hindsight_runtime_ready(topology)
        constructed.append("engine factory entered")

    with pytest.raises(AccountingRejected):
        offline_launch_order()
    assert constructed == []


def test_call_invocation_ceiling_is_not_a_physical_transport_send_ceiling(tmp_path):
    provider, _, gate = boundary(tmp_path)
    wrapper = provider._client.chat.completions

    class MultiplyingResource(OfflineResource):
        async def create(self, **kwargs):
            await super().create(**kwargs)
            return await super().create(**kwargs)

    # Synthetic below-create redirect/retry counterexample. This does NOT
    # assert any particular SDK actually redirects or retries.
    multiplying = MultiplyingResource()
    wrapper._original = multiplying
    with send_context(CONTEXT):
        asyncio.run(wrapper.create(**REQUEST))
    assert multiplying.sends == 2
    assert gate.snapshot()["calls_reserved"] == 1
    assert gate.snapshot()["committed_tokens"] == 16


@pytest.mark.parametrize("mutation", ["body", "eol", "size", "sha256", "blob"])
def test_static_audit_refuses_different_source_bytes(mutation):
    data = b"x = 1\n"
    expected = {"git_blob_sha1": hashlib.sha1(b"blob 6\0" + data).hexdigest(),
                "sha256": hashlib.sha256(data).hexdigest(), "byte_count": 6}
    if mutation == "body":
        data = b"x = 2\n"
    elif mutation == "eol":
        data = b"x = 1\r\n"
    elif mutation == "size":
        expected["byte_count"] = 7
    elif mutation == "sha256":
        expected["sha256"] = "0" * 64
    else:
        expected["git_blob_sha1"] = "0" * 40
    with pytest.raises(ValueError, match="identity mismatch"):
        audit.verify_source("fixture.py", data, expected)


def test_dependency_metadata_probe_does_not_import_runtime(monkeypatch):
    checked = []

    def absent(module):
        checked.append(module)
        return None

    def absent_version(distribution):
        raise audit.importlib.metadata.PackageNotFoundError(distribution)

    monkeypatch.setattr(audit.importlib.util, "find_spec", absent)
    monkeypatch.setattr(audit.importlib.metadata, "version", absent_version)
    inventory = audit.dependency_inventory()
    assert set(checked) == set(audit.DEPENDENCIES)
    assert all(item["import_available"] is False and item["version"] is None
               for item in inventory.values())
