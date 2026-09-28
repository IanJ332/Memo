"""Shared local-only Mem0 integration fixture."""

from pathlib import Path

import pytest

from memlife.adapters.mem0 import Mem0MemoryAdapter


@pytest.fixture
def mem0_adapter(monkeypatch: pytest.MonkeyPatch) -> Mem0MemoryAdapter:
    """Create Mem0 from the pre-fetched cache and forbid LLM inference."""

    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    adapter = Mem0MemoryAdapter.from_runtime(Path.cwd())
    llm_calls: list[object] = []

    def fail_on_llm_call(*args: object, **kwargs: object) -> None:
        llm_calls.append((args, kwargs))
        pytest.fail("Mem0 attempted an LLM call during the infer=False baseline")

    adapter.native_memory.llm.generate_response = fail_on_llm_call
    adapter._phase02a_llm_calls = llm_calls  # type: ignore[attr-defined]
    try:
        yield adapter
    finally:
        adapter.close()
