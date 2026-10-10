"""Verify Phase 08C-1 LongMemEval adaptations against the pinned oracle.

The approximately 15 MB upstream dataset remains outside Git. This verifier
checks its byte hash and then validates every selected source record and the
manifest's deterministic annotations. It uses only the Python standard
library.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

PINNED_REVISION = "98d7416c24c778c2fee6e6f3006e7a073259d48f"
PINNED_SHA256 = "821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c"
SELECTED_HISTORY_IDS = {"01493427", "0e4e4c46", "0f05491a", "18bc8abd"}
ABSTENTION_ID = "031748ae_abs"


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _session(record: dict[str, Any], session_id: str) -> tuple[str, list[Any]]:
    ids = record["haystack_session_ids"]
    matches = [index for index, value in enumerate(ids) if value == session_id]
    _require(len(matches) == 1, f"{record['question_id']}: session {session_id!r} not unique")
    index = matches[0]
    return record["haystack_dates"][index], record["haystack_sessions"][index]


def verify(dataset_path: Path, manifest_path: Path) -> dict[str, int | str]:
    manifest = _load_json(manifest_path)
    _require(
        manifest["longmemeval"]["revision"] == PINNED_REVISION,
        "manifest LongMemEval revision is not pinned revision",
    )
    _require(
        manifest["longmemeval"]["artifact_sha256"] == PINNED_SHA256,
        "manifest LongMemEval hash is not pinned hash",
    )
    actual_dataset_sha = _sha256_bytes(dataset_path.read_bytes())
    _require(actual_dataset_sha == PINNED_SHA256, "dataset SHA-256 mismatch")

    dataset = _load_json(dataset_path)
    _require(isinstance(dataset, list), "oracle root must be a JSON list")
    selected_ids = SELECTED_HISTORY_IDS | {ABSTENTION_ID}
    selected = [item for item in dataset if item.get("question_id") in selected_ids]
    by_question_id = {item["question_id"]: item for item in selected}
    _require(len(selected) == len(by_question_id) == 5, "selected question IDs not unique")
    _require(set(by_question_id) == selected_ids, "selected question IDs incomplete")

    histories = manifest["benchmark_histories"]
    _require(len(histories) == 4, "manifest must contain four update histories")
    _require(
        {history["question_id"] for history in histories} == SELECTED_HISTORY_IDS,
        "manifest update-history IDs differ from pinned selection",
    )

    expected_cases: dict[tuple[str, str], str] = {}
    verified_versions = 0
    for history in histories:
        question_id = history["question_id"]
        source = by_question_id[question_id]
        for field in ("question_type", "question"):
            _require(
                history[field] == source[field],
                f"{question_id}: {field} mismatch",
            )
        _require(str(history["answer"]) == str(source["answer"]), f"{question_id}: answer mismatch")
        _require(
            history["transition"]
            == {"from": "v1", "to": "v2", "relation": "SUPERSEDED_BY"},
            f"{question_id}: transition annotation mismatch",
        )
        versions = history["versions"]
        _require([item["version_id"] for item in versions] == ["v1", "v2"], f"{question_id}: versions must be v1/v2")
        _require(
            [(item["authoritative"], item["lifecycle_state"]) for item in versions]
            == [(False, "superseded"), (True, "active")],
            f"{question_id}: lifecycle transition mismatch",
        )
        dates: list[datetime] = []
        for version in versions:
            session_id = version["source_session_id"]
            _require(session_id in source["answer_session_ids"], f"{question_id}: source is not answer session")
            source_date, messages = _session(source, session_id)
            _require(source_date == version["source_date"], f"{question_id}/{version['version_id']}: date mismatch")
            dates.append(datetime.strptime(source_date, "%Y/%m/%d (%a) %H:%M"))
            answer_messages = [
                message
                for message in messages
                if message.get("role") == "user" and message.get("has_answer") is True
            ]
            _require(len(answer_messages) == 1, f"{question_id}/{version['version_id']}: expected one answer-bearing user message")
            exact_text = answer_messages[0]["content"]
            _require(exact_text == version["source_text"], f"{question_id}/{version['version_id']}: source text mismatch")
            _require(_sha256_text(exact_text) == version["source_record_sha256"], f"{question_id}/{version['version_id']}: source hash mismatch")
            _require(version["source_claim_text"] in exact_text, f"{question_id}/{version['version_id']}: claim is not exact source substring")
            _require(_sha256_text(version["canonical_content"]) == version["canonical_sha256"], f"{question_id}/{version['version_id']}: canonical annotation hash mismatch")
            _require(
                version["canonicalization_id"]
                == "rq4-longmemeval-explicit-annotation-v1",
                f"{question_id}/{version['version_id']}: canonicalizer mismatch",
            )
            expected_cases[(question_id, version["version_id"])] = (
                "DENY" if version["version_id"] == "v1" else "ALLOW"
            )
            verified_versions += 1
        _require(dates[0] < dates[1], f"{question_id}: source dates are not ordered")

    abstention = manifest["benchmark_abstention"]
    source_abstention = by_question_id[ABSTENTION_ID]
    for field in ("question_id", "question_type", "question", "answer"):
        _require(
            str(abstention[field]) == str(source_abstention[field]),
            f"{ABSTENTION_ID}: {field} mismatch",
        )
    _require(abstention["canonical_annotation"] is None, "abstention invents canonical annotation")
    _require(abstention["resolution"] == "UNRESOLVED_TARGET_FACT", "abstention resolution mismatch")
    _require(abstention["expected_action"] == "QUARANTINE", "abstention action mismatch")
    abstention_sessions = abstention["source_sessions"]
    _require(
        [item["source_session_id"] for item in abstention_sessions]
        == source_abstention["answer_session_ids"],
        "abstention answer-session IDs mismatch",
    )
    for annotated in abstention_sessions:
        source_date, messages = _session(source_abstention, annotated["source_session_id"])
        _require(source_date == annotated["source_date"], "abstention source date mismatch")
        count = sum(
            message.get("role") == "user" and message.get("has_answer") is True
            for message in messages
        )
        _require(count == annotated["answer_bearing_user_message_count"] == 0, "abstention has answer-bearing target evidence")

    cases = manifest["benchmark_cases"]
    _require(len(cases) == 9, "manifest must contain exactly nine benchmark cases")
    conclusive = [item for item in cases if item["question_id"] != ABSTENTION_ID]
    _require(len(conclusive) == 8, "manifest must contain eight conclusive version cases")
    _require(
        {(item["question_id"], item["version_id"]) for item in conclusive}
        == set(expected_cases),
        "benchmark cases do not cover each verified version exactly once",
    )
    for case in conclusive:
        key = (case["question_id"], case["version_id"])
        _require(case["expected_action"] == expected_cases[key], f"{case['case_id']}: action mismatch")
    unresolved = [item for item in cases if item["question_id"] == ABSTENTION_ID]
    _require(len(unresolved) == 1, "benchmark must contain one abstention case")
    _require(unresolved[0]["expected_action"] == "QUARANTINE", "abstention case must quarantine")
    _require(
        unresolved[0]["source_session_ids"]
        == [item["source_session_id"] for item in abstention_sessions],
        "abstention case session IDs mismatch",
    )

    return {
        "dataset_sha256": actual_dataset_sha,
        "histories": len(histories),
        "versions": verified_versions,
        "abstentions": 1,
        "cases": len(cases),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("experiments/rq4/pilot/manifest.json"),
    )
    args = parser.parse_args()
    result = verify(args.dataset, args.manifest)
    print(
        "PASS: pinned LongMemEval provenance verified "
        f"({result['histories']} histories, {result['versions']} versions, "
        f"{result['abstentions']} abstention, {result['cases']} cases; "
        f"sha256={result['dataset_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
