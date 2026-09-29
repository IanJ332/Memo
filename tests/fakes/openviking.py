"""Deterministic fake of the OpenViking 0.4.22 HTTP shapes MemLife consumes."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Mapping
from urllib.parse import unquote

from memlife.adapters.openviking import OpenVikingHTTPError


class FakeOpenVikingTransport:
    def __init__(self) -> None:
        self.sessions: dict[str, dict[str, Any]] = {}
        self.tasks: dict[str, dict[str, Any]] = {}
        self.memory: dict[str, str] = {}
        self.diffs: dict[str, dict[str, Any]] = {}
        self.requests: list[tuple[str, str, Mapping[str, Any] | None, Any]] = []
        self.next_task = 1
        self.task_statuses: list[str] = ["pending", "running", "completed"]
        self.memory_count_per_commit = 1
        self.fail_task = False

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        payload: Any | None = None,
    ) -> Any:
        method = method.upper()
        self.requests.append((method, path, deepcopy(query), deepcopy(payload)))
        if path == "/ready" and method == "GET":
            return {"ready": True, "version": "0.4.22"}
        if path == "/api/v1/sessions" and method == "GET":
            return [
                {"session_id": session_id, "uri": f"viking://user/test/sessions/{session_id}"}
                for session_id in sorted(self.sessions)
            ]
        if path == "/api/v1/sessions" and method == "POST":
            session_id = payload["session_id"]
            self.sessions[session_id] = {"messages": [], "uris": []}
            return {"session_id": session_id}
        if path.startswith("/api/v1/sessions/"):
            parts = [unquote(part) for part in path.strip("/").split("/")]
            session_id = parts[3]
            if len(parts) == 4 and method == "DELETE":
                session = self.sessions.pop(session_id, {"uris": []})
                for uri in session.get("uris", []):
                    self.memory.pop(uri, None)
                return {"session_id": session_id}
            if parts[4:] == ["messages"] and method == "POST":
                self.sessions[session_id]["messages"].append(payload)
                return {"session_id": session_id, "message_count": 1, "added": 1}
            if parts[4:] == ["commit"] and method == "POST":
                task_id = f"task-{self.next_task:04d}"
                archive_uri = f"viking://user/test/sessions/{session_id}/history/archive_001"
                self.next_task += 1
                source = self.sessions[session_id]["messages"][-1]["content"]
                operations = []
                for index in range(self.memory_count_per_commit):
                    uri = f"viking://user/test/memories/events/{task_id}-{index}.md"
                    content = source if index == 0 else f"{source} (part {index + 1})"
                    self.memory[uri] = content
                    self.sessions[session_id]["uris"].append(uri)
                    operations.append(
                        {"uri": uri, "memory_type": "events", "after": content}
                    )
                diff = {
                    "archive_uri": archive_uri,
                    "extracted_at": "2026-09-28T12:00:00Z",
                    "operations": {"adds": operations, "updates": [], "deletes": []},
                    "skipped_operations": [],
                    "summary": {
                        "total_adds": len(operations),
                        "total_updates": 0,
                        "total_deletes": 0,
                        "total_skipped": 0,
                    },
                }
                self.diffs[archive_uri] = diff
                statuses = ["failed"] if self.fail_task else list(self.task_statuses)
                self.tasks[task_id] = {"statuses": statuses, "poll": 0}
                return {
                    "session_id": session_id,
                    "status": "accepted",
                    "task_id": task_id,
                    "archive_uri": archive_uri,
                    "archived": True,
                }
            if parts[4:] == ["extract"] and method == "POST":
                return [{"status": "extracted", "session_id": session_id}]
        if path.startswith("/api/v1/tasks/") and method == "GET":
            task_id = unquote(path.rsplit("/", 1)[-1])
            task = self.tasks[task_id]
            index = min(task["poll"], len(task["statuses"]) - 1)
            status = task["statuses"][index]
            task["poll"] += 1
            return {
                "task_id": task_id,
                "task_type": "session_commit",
                "status": status,
                "error": "synthetic failure" if status == "failed" else None,
            }
        if path == "/api/v1/content/read" and method == "GET":
            uri = str(query["uri"])
            if uri.endswith("/memory_diff.json"):
                archive_uri = uri[: -len("/memory_diff.json")]
                return json.dumps(self.diffs[archive_uri], sort_keys=True)
            if uri not in self.memory:
                raise OpenVikingHTTPError(404, "not found")
            return self.memory[uri]
        if path == "/api/v1/search/find" and method == "POST":
            text = str(payload.get("query", "")).casefold()
            rows = [
                {
                    "uri": uri,
                    "context_type": "memory",
                    "level": 2,
                    "abstract": content,
                    "content": content,
                    "category": "events",
                    "score": 0.9,
                    "match_reason": "vector",
                }
                for uri, content in sorted(self.memory.items())
                if not text or all(word in content.casefold() for word in text.split())
            ]
            return {"memories": rows[: int(payload["limit"])], "resources": [], "skills": [], "total": len(rows)}
        if path == "/api/v1/fs" and method == "DELETE":
            self.memory.pop(str(query["uri"]), None)
            return {"uri": query["uri"]}
        raise AssertionError(f"unhandled fake request: {method} {path}")
