"""In-memory implementation of the Hindsight REST shapes consumed by MemLife."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping
from urllib.parse import unquote

from memlife.adapters.hindsight import HindsightHTTPError


class FakeHindsightTransport:
    def __init__(self) -> None:
        self.banks: dict[str, dict[str, dict[str, Any]]] = {}
        self.next_id = 1
        self.requests: list[tuple[str, str, Mapping[str, Any] | None, Any]] = []
        self.operations: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _parts(path: str) -> list[str]:
        return [unquote(part) for part in path.strip("/").split("/")]

    def _bank(self, path: str) -> tuple[str, dict[str, dict[str, Any]], list[str]]:
        parts = self._parts(path)
        bank_id = parts[3]
        return bank_id, self.banks.setdefault(bank_id, {}), parts

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        payload: Any | None = None,
    ) -> Any:
        method = method.upper()
        self.requests.append((method, path, query, deepcopy(payload)))
        if path == "/version":
            return {"api_version": "0.10.1", "features": {}}
        if path == "/health":
            return {"status": "healthy"}

        bank_id, bank, parts = self._bank(path)
        tail = parts[4:]
        if tail == ["memories"] and method == "DELETE":
            bank.clear()
            return {"success": True, "deleted_count": 0}
        if tail == ["memories"] and method == "POST":
            for item in payload["items"]:
                memory_id = f"memory-{self.next_id:04d}"
                self.next_id += 1
                bank[memory_id] = {
                    "id": memory_id,
                    "text": item["content"],
                    "fact_type": "world",
                    "document_id": item["document_id"],
                    "chunk_id": f"chunk-{memory_id}",
                    "state": "valid",
                    "source_memory_ids": [],
                }
            return {
                "success": True,
                "bank_id": bank_id,
                "items_count": len(payload["items"]),
                "async": False,
            }
        if tail == ["memories", "list"] and method == "GET":
            state = str((query or {}).get("state", "valid"))
            document_id = (query or {}).get("document_id")
            items = [
                deepcopy(item)
                for item in bank.values()
                if item["state"] == state
                and (document_id is None or item.get("document_id") == document_id)
            ]
            return {
                "items": items,
                "total": len(items),
                "limit": 100,
                "offset": 0,
            }
        if tail == ["memories", "recall"] and method == "POST":
            return {
                "results": [
                    {
                        "id": item["id"],
                        "text": item["text"],
                        "type": item["fact_type"],
                        "document_id": item.get("document_id"),
                        "chunk_id": item.get("chunk_id"),
                        "source_fact_ids": item.get("source_memory_ids", []),
                    }
                    for item in bank.values()
                    if item["state"] == "valid"
                    and item["fact_type"] in payload["types"]
                ]
            }
        if tail == ["operations"] and method == "GET":
            return {
                "bank_id": bank_id,
                "total": len(self.operations),
                "limit": 100,
                "offset": 0,
                "operations": list(self.operations.values()),
            }
        if len(tail) == 2 and tail[0] == "operations" and method == "GET":
            return deepcopy(self.operations[tail[1]])
        if tail == ["consolidate"] and method == "POST":
            operation_id = "00000000-0000-0000-0000-000000000001"
            self.operations[operation_id] = {
                "id": operation_id,
                "operation_id": operation_id,
                "task_type": "consolidation",
                "status": "completed",
            }
            return {"operation_id": operation_id, "deduplicated": False}
        if len(tail) == 2 and tail[0] == "memories":
            memory_id = tail[1]
            if memory_id not in bank:
                raise HindsightHTTPError(404, "not found")
            if method == "GET":
                return deepcopy(bank[memory_id])
            if method == "PATCH":
                if "text" in payload:
                    bank[memory_id]["text"] = payload["text"]
                    bank[memory_id]["edited_at"] = "2026-09-28T00:00:00Z"
                if "state" in payload:
                    bank[memory_id]["state"] = payload["state"]
                    bank[memory_id]["invalidation_reason"] = payload.get("reason")
                    bank[memory_id]["invalidated_at"] = "2026-09-28T00:00:00Z"
                return deepcopy(bank[memory_id])
        if len(tail) == 3 and tail[0] == "memories" and tail[2] == "history":
            return []
        if len(tail) == 2 and tail[0] == "documents" and method == "DELETE":
            document_id = tail[1]
            doomed = [
                memory_id
                for memory_id, item in bank.items()
                if item.get("document_id") == document_id
            ]
            if not doomed:
                raise HindsightHTTPError(404, "document not found")
            for memory_id in doomed:
                del bank[memory_id]
            return {
                "success": True,
                "document_id": document_id,
                "memory_units_deleted": len(doomed),
            }
        raise AssertionError(f"unhandled fake request: {method} {path}")

    def add_observation(
        self,
        bank_id: str,
        *,
        text: str,
        source_ids: list[str],
    ) -> dict[str, Any]:
        bank = self.banks.setdefault(bank_id, {})
        memory_id = f"observation-{self.next_id:04d}"
        self.next_id += 1
        row = {
            "id": memory_id,
            "text": text,
            "fact_type": "observation",
            "document_id": None,
            "chunk_id": None,
            "state": "valid",
            "source_memory_ids": list(source_ids),
        }
        bank[memory_id] = row
        return row
