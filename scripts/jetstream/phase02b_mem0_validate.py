#!/usr/bin/env python3
"""Collect the targeted Mem0 lifecycle result for Jetstream Phase 02B."""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import uuid
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from memlife.adapters.mem0 import Mem0MemoryAdapter  # noqa: E402
from memlife.models.memory import (  # noqa: E402
    DeleteCommand,
    QueryCommand,
    SupersedeCommand,
    WriteCommand,
)
from memlife.runner.manifest import hash_configuration  # noqa: E402


def _os_release() -> str:
    values: dict[str, str] = {}
    for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            values[key] = value.strip().strip('"')
    return values.get("PRETTY_NAME", platform.platform())


def _integer_environment(name: str) -> int:
    return int(os.environ[name])


def run() -> dict[str, object]:
    namespace = f"memlife-phase02b-cedar-{uuid.uuid4().hex}"
    v1 = "Project Cedar reports may be sent to Alice."
    v2 = "Project Cedar reports may be sent only to Bob."
    adapter = Mem0MemoryAdapter.from_runtime(REPO_ROOT)
    expected_root = Path(os.environ["MEMLIFE_DATA_ROOT"]) / "providers" / "mem0" / "phase-02b"
    if adapter.paths.provider_root != expected_root:
        raise RuntimeError("Mem0 provider state did not resolve to the Phase 02B persistent path")
    try:
        adapter.reset_namespace(namespace)
        written = adapter.write(WriteCommand(namespace=namespace, content=v1))
        add_history = adapter.native_history(written.memory_id)
        queried_v1 = adapter.query(QueryCommand(namespace=namespace, query=v1))

        adapter.restart()
        after_write_restart = adapter.query(QueryCommand(namespace=namespace, query=v1))

        updated = adapter.update_or_supersede(
            SupersedeCommand(namespace=namespace, memory_id=written.memory_id, content=v2)
        )
        queried_v2 = adapter.query(QueryCommand(namespace=namespace, query=v2))
        inspected_v2 = adapter.list_or_inspect(namespace)
        update_history = adapter.native_history(updated.memory_id)

        adapter.delete_or_invalidate(
            DeleteCommand(namespace=namespace, memory_id=updated.memory_id)
        )
        query_after_delete = adapter.query(QueryCommand(namespace=namespace, query=v2))
        list_after_delete = adapter.list_or_inspect(namespace)
        delete_history = adapter.native_history(updated.memory_id)

        adapter.restart()
        query_after_delete_restart = adapter.query(
            QueryCommand(namespace=namespace, query=v2)
        )
        history_after_delete_restart = adapter.native_history(updated.memory_id)

        configuration = adapter.manifest_configuration()
        configuration.update(
            phase="02B",
            vector_store_path_class="<live-volume>/memlife/providers/mem0/phase-02b/qdrant",
            history_path_class="<live-volume>/memlife/providers/mem0/phase-02b/history/history.db",
            model_cache_path_class="<live-volume>/memlife/model_cache/huggingface",
        )
        commit = __import__("subprocess").run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        events = [str(item.get("event")) for item in delete_history]
        lifecycle = {
            "memory_id": written.memory_id,
            "write_add_history_visible": bool(add_history and add_history[-1].get("event") == "ADD"),
            "query_v1_retrieved": any(item.memory_id == written.memory_id for item in queried_v1),
            "write_survived_reconstruction": any(item.memory_id == written.memory_id for item in after_write_restart),
            "update_id_same": updated.memory_id == written.memory_id,
            "query_v2_current": any(item.memory_id == updated.memory_id and item.content == v2 for item in queried_v2),
            "list_v2_current": [(item.memory_id, item.content) for item in inspected_v2] == [(updated.memory_id, v2)],
            "history_events_before_delete": [str(item.get("event")) for item in update_history],
            "query_after_delete_empty": not query_after_delete,
            "list_after_delete_empty": not list_after_delete,
            "history_events_after_delete": events,
            "delete_history_visible": bool(delete_history and delete_history[-1].get("event") == "DELETE"),
            "delete_history_is_deleted": bool(delete_history and delete_history[-1].get("is_deleted") is True),
            "deleted_absent_after_reconstruction": not query_after_delete_restart,
            "history_visible_after_reconstruction": bool(history_after_delete_restart and history_after_delete_restart[-1].get("event") == "DELETE"),
        }
        if not all(
            value
            for key, value in lifecycle.items()
            if key not in {"memory_id", "history_events_before_delete", "history_events_after_delete"}
        ):
            raise RuntimeError(f"one or more targeted lifecycle checks failed: {lifecycle}")
        return {
            "phase": "02B",
            "provider": "mem0",
            "provider_version": version("mem0ai"),
            "branch": "phase-02b-mem0-jetstream",
            "git_commit_tested": commit,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "remote_os": _os_release(),
            "machine_class": "Jetstream2 m3.small (2 vCPU, approximately 5.78 GiB RAM, no GPU)",
            "remote_python": platform.python_version(),
            "live_volume_device": "/dev/sdb",
            "live_volume_source": os.environ["PHASE02B_LIVE_VOLUME_SOURCE"],
            "live_volume_mount": os.environ["PHASE02B_LIVE_VOLUME_MOUNT"],
            "live_volume_fstype": os.environ["PHASE02B_LIVE_VOLUME_FSTYPE"],
            "memlife_data_root": os.environ["MEMLIFE_DATA_ROOT"],
            "root_free_before_bytes": _integer_environment("PHASE02B_ROOT_FREE_BEFORE"),
            "root_free_after_bytes": _integer_environment("PHASE02B_ROOT_FREE_AFTER"),
            "volume_free_before_bytes": _integer_environment("PHASE02B_VOLUME_FREE_BEFORE"),
            "volume_free_after_bytes": _integer_environment("PHASE02B_VOLUME_FREE_AFTER"),
            "embedding_provider": "huggingface",
            "embedding_model": "sentence-transformers/paraphrase-MiniLM-L3-v2",
            "pytest_version": version("pytest"),
            "sentence_transformers_version": version("sentence-transformers"),
            "torch_version": version("torch"),
            "torch_cpu_only": True,
            "installed_nvidia_packages": [],
            "pip_dry_run_nvidia_packages": [
                item
                for item in os.environ["PHASE02B_DRY_RUN_NVIDIA_PACKAGES"].split(",")
                if item
            ],
            "vector_store": "qdrant",
            "vector_store_mode": "embedded/local",
            "vector_store_path": str(adapter.paths.qdrant),
            "qdrant_client_version": version("qdrant-client"),
            "history_store": "sqlite",
            "history_path": str(adapter.paths.history / "history.db"),
            "infer": False,
            "telemetry": False,
            "model_cache": os.environ["HF_HOME"],
            "config_sha256": hash_configuration(configuration),
            "contract_result": os.environ["PHASE02B_CONTRACT_SUMMARY"],
            "integration_result": os.environ["PHASE02B_INTEGRATION_SUMMARY"],
            "restart_result": "PASS",
            "lifecycle": lifecycle,
        }
    finally:
        adapter.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
