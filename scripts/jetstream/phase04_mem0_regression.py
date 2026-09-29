#!/usr/bin/env python3
"""Fail-closed Phase 02B semantic gate for the clean Phase 04 harness."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

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


def run() -> dict[str, Any]:
    """Exercise the Phase 02B lifecycle before Hindsight may be configured."""

    namespace = f"phase04-clean-harness-{uuid.uuid4().hex}"
    original = "Project Cedar reports may be sent to Alice."
    corrected = "Project Cedar reports may be sent only to Bob."
    adapter = Mem0MemoryAdapter.from_runtime(REPO_ROOT)
    try:
        adapter.reset_namespace(namespace)
        written = adapter.write(WriteCommand(namespace=namespace, content=original))
        write_ok = written.memory_id != ""
        query_ok = any(
            item.memory_id == written.memory_id
            for item in adapter.query(QueryCommand(namespace=namespace, query=original))
        )

        updated = adapter.update_or_supersede(
            SupersedeCommand(
                namespace=namespace,
                memory_id=written.memory_id,
                content=corrected,
            )
        )
        update_ok = updated.memory_id == written.memory_id and updated.content == corrected
        history_before_delete = adapter.native_history(updated.memory_id)
        history_ok = [str(item.get("event")) for item in history_before_delete] == [
            "ADD",
            "UPDATE",
        ]

        adapter.restart()
        reconstruction_ok = any(
            item.memory_id == updated.memory_id and item.content == corrected
            for item in adapter.query(
                QueryCommand(namespace=namespace, query=corrected)
            )
        )

        adapter.delete_or_invalidate(
            DeleteCommand(namespace=namespace, memory_id=updated.memory_id)
        )
        history_after_delete = adapter.native_history(updated.memory_id)
        delete_ok = bool(
            history_after_delete
            and history_after_delete[-1].get("event") == "DELETE"
            and history_after_delete[-1].get("is_deleted") is True
        )

        adapter.restart()
        absence_ok = not adapter.query(
            QueryCommand(namespace=namespace, query=corrected)
        )
        history_after_reconstruction = adapter.native_history(updated.memory_id)
        history_reconstruction_ok = bool(
            history_after_reconstruction
            and history_after_reconstruction[-1].get("event") == "DELETE"
        )
        checks = {
            "construct": True,
            "write": write_ok,
            "query": query_ok,
            "update": update_ok,
            "history": history_ok,
            "delete": delete_ok,
            "reconstruction": reconstruction_ok and history_reconstruction_ok,
            "query_absence_after_delete": absence_ok,
        }
        if not all(checks.values()):
            raise RuntimeError(f"Phase 02B clean-harness regression failed: {checks}")
        return {
            "status": "PASS",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mem0ai_version": version("mem0ai"),
            "checks": checks,
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
