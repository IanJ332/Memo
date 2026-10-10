"""Focused regression and evidence tests for the minimal offline RQ4 pilot."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from memlife.models.lifecycle import LifecycleState
from memlife.models.mediator import (
    AuthoritySnapshot,
    CandidateEnvelope,
    EvidenceClass,
    MediatorAction,
    RelationEdge,
)
from memlife.models.provenance import MemorySurface
from memlife.runner.rq4_policy import (
    CONTEXT_MAGIC,
    RQ4_POLICY_VERSION,
    AuthorityBundle,
    BaselineDecision,
    BaselinePolicy,
    ContentIdentityBinding,
    evaluate_baseline,
    evaluate_candidates,
)
from memlife.runner.tracked_text import materialize_tracked_text

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "experiments" / "rq4" / "pilot" / "manifest.json"
FIXED_TIME = datetime(2026, 10, 8, 18, 0, tzinfo=timezone.utc)
DATASET_SHA256 = "821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c"


@dataclass(frozen=True)
class PilotCase:
    case_id: str
    candidate: CandidateEnvelope
    content: bytes
    expected: MediatorAction


def _sha(value: bytes | str) -> str:
    exact = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(exact).hexdigest()


def _manifest() -> dict[str, object]:
    value = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _snapshot(
    *,
    logical_fact_id: str,
    version_id: str,
    source_event_id: str,
    lifecycle_state: LifecycleState,
    authoritative: bool,
    sequence: int,
    proposition_sha256: str,
    source_record_sha256: str,
    supersedes: str | None = None,
    superseded_by: str | None = None,
) -> AuthoritySnapshot:
    return AuthoritySnapshot(
        logical_fact_id=logical_fact_id,
        version_id=version_id,
        source_event_id=source_event_id,
        lifecycle_state=lifecycle_state,
        authoritative=authoritative,
        sequence=sequence,
        supersedes=supersedes,
        superseded_by=superseded_by,
        canonical_proposition_sha256=proposition_sha256,
        source_record_sha256=source_record_sha256,
    )


def _candidate(
    *,
    case_id: str,
    content: bytes,
    proposition_sha256: str | None,
    logical_fact_id: str | None,
    source_ids: tuple[str, ...],
    evidence_class: EvidenceClass,
    surface: MemorySurface = MemorySurface.RETRIEVAL,
    canonicalization_id: str = "fixture-exact-proposition-v1",
) -> CandidateEnvelope:
    return CandidateEnvelope(
        provider="rq4-pilot-fixture",
        namespace="rq4-pilot",
        candidate_id=case_id,
        retrieval_rank=1,
        surface=surface,
        raw_bytes_sha256=_sha(content),
        canonical_body_sha256=proposition_sha256,
        canonicalization_id=(
            canonicalization_id if proposition_sha256 else None
        ),
        logical_fact_id=logical_fact_id,
        source_ids=source_ids,
        relation_edges=tuple(
            RelationEdge(
                source_id=source_id,
                target_id=case_id,
                relation="DERIVED_FROM",
            )
            for source_id in source_ids
        ),
        retrieval_timestamp=FIXED_TIME,
        evidence_class=evidence_class,
    )


def _binding(
    candidate: CandidateEnvelope,
    *,
    source_event_id: str,
    evidence_source_id: str = "fixture-authority-ledger",
    evidence_source_sha256: str = "a" * 64,
) -> ContentIdentityBinding:
    assert candidate.canonical_body_sha256 is not None
    assert candidate.logical_fact_id is not None
    assert candidate.canonicalization_id is not None
    return ContentIdentityBinding(
        binding_id=f"binding:{candidate.candidate_id}:{source_event_id}",
        raw_bytes_sha256=candidate.raw_bytes_sha256,
        canonical_proposition_sha256=candidate.canonical_body_sha256,
        logical_fact_id=candidate.logical_fact_id,
        source_event_id=source_event_id,
        canonicalization_id=candidate.canonicalization_id,
        evidence_source_id=evidence_source_id,
        evidence_source_sha256=evidence_source_sha256,
    )


def _bundle(
    snapshots: tuple[AuthoritySnapshot, ...],
    *,
    content_bindings: tuple[ContentIdentityBinding, ...] = (),
    source_sha256: str = "a" * 64,
    source_id: str = "fixture-authority-ledger",
) -> AuthorityBundle:
    return AuthorityBundle(
        ledger_version="rq4-pilot-ledger-v1",
        authority_source_id=source_id,
        authority_source_sha256=source_sha256,
        snapshots=snapshots,
        content_bindings=content_bindings,
    )


def _evaluate(
    cases: tuple[PilotCase, ...], authority: AuthorityBundle
) -> tuple[MediatorAction, ...]:
    result = evaluate_candidates(
        tuple(case.candidate for case in cases),
        authority,
        {case.case_id: case.content for case in cases},
        policy_version=RQ4_POLICY_VERSION,
        evaluation_timestamp=FIXED_TIME,
    )
    return tuple(decision.decision for decision in result.decisions)


def _unframe(value: bytes) -> dict[str, bytes]:
    assert value.startswith(CONTEXT_MAGIC)
    offset = len(CONTEXT_MAGIC)
    result: dict[str, bytes] = {}
    while offset < len(value):
        identifier_length = int.from_bytes(value[offset : offset + 8], "big")
        offset += 8
        identifier = value[offset : offset + identifier_length].decode("utf-8")
        offset += identifier_length
        content_length = int.from_bytes(value[offset : offset + 8], "big")
        offset += 8
        result[identifier] = value[offset : offset + content_length]
        offset += content_length
    assert offset == len(value)
    return result


def _empirical_fixtures() -> tuple[tuple[PilotCase, ...], AuthorityBundle]:
    controls = [
        item
        for item in _manifest()["empirical_controls"]
        if item["eligible"]
    ]
    cases: list[PilotCase] = []
    snapshots: list[AuthoritySnapshot] = []
    bindings: list[ContentIdentityBinding] = []
    for item in controls:
        current_fact = item["logical_fact_id"]
        stale_fact = current_fact.replace("fact-v2", "fact-v1")
        current_source = item["current_source_event_id"]
        stale_source = item["stale_source_event_id"]
        content = item["candidate_content_utf8"].encode("utf-8")
        candidate = _candidate(
            case_id=item["case_id"],
            content=content,
            proposition_sha256=item["canonical_proposition_sha256"],
            logical_fact_id=current_fact,
            source_ids=(current_source, stale_source),
            evidence_class=EvidenceClass.PROVIDER_OBSERVED,
            surface=(
                MemorySurface.DERIVED
                if item["provider"] == "hindsight"
                else MemorySurface.UNKNOWN
            ),
            canonicalization_id=item["canonicalization_id"],
        )
        assert candidate.raw_bytes_sha256 == item["candidate_raw_sha256"]
        cases.append(
            PilotCase(
                case_id=item["case_id"],
                candidate=candidate,
                content=content,
                expected=MediatorAction(item["expected_action"]),
            )
        )
        bindings.append(
            _binding(
                candidate,
                source_event_id=current_source,
                evidence_source_id=item["content_binding_evidence_source_id"],
                evidence_source_sha256=item[
                    "content_binding_evidence_source_sha256"
                ],
            )
        )
        snapshots.extend(
            (
                _snapshot(
                    logical_fact_id=stale_fact,
                    version_id=stale_fact,
                    source_event_id=stale_source,
                    lifecycle_state=LifecycleState.SUPERSEDED,
                    authoritative=False,
                    sequence=len(snapshots) + 1,
                    proposition_sha256=item["stale_canonical_proposition_sha256"],
                    source_record_sha256=item["stale_source_record_sha256"],
                    superseded_by=current_fact,
                ),
                _snapshot(
                    logical_fact_id=current_fact,
                    version_id=current_fact,
                    source_event_id=current_source,
                    lifecycle_state=LifecycleState.ACTIVE,
                    authoritative=True,
                    sequence=len(snapshots) + 2,
                    proposition_sha256=item["canonical_proposition_sha256"],
                    source_record_sha256=item["current_source_record_sha256"],
                    supersedes=stale_fact,
                ),
            )
        )
    return tuple(cases), _bundle(
        tuple(snapshots),
        content_bindings=tuple(bindings),
        source_sha256="80b82f177adf4a15659bc583df61c78dafaa034ac931b5592e22a47d01f67a9f",
        source_id="phase06b-and-phase07-independent-authority-evidence",
    )


def _benchmark_fixtures() -> tuple[tuple[PilotCase, ...], AuthorityBundle]:
    manifest = _manifest()
    histories = {
        item["question_id"]: item for item in manifest["benchmark_histories"]
    }
    cases: list[PilotCase] = []
    snapshots: list[AuthoritySnapshot] = []
    bindings: list[ContentIdentityBinding] = []
    for history in histories.values():
        versions = history["versions"]
        for index, version in enumerate(versions, 1):
            snapshots.append(
                _snapshot(
                    logical_fact_id=history["logical_fact_id"],
                    version_id=f"lme:{history['question_id']}:{version['version_id']}",
                    source_event_id=version["source_session_id"],
                    lifecycle_state=LifecycleState(version["lifecycle_state"]),
                    authoritative=version["authoritative"],
                    sequence=len(snapshots) + 1,
                    proposition_sha256=version["canonical_sha256"],
                    source_record_sha256=version["source_record_sha256"],
                    supersedes=(
                        f"lme:{history['question_id']}:v1" if index == 2 else None
                    ),
                    superseded_by=(
                        f"lme:{history['question_id']}:v2" if index == 1 else None
                    ),
                )
            )
    for item in manifest["benchmark_cases"]:
        if item["question_id"].endswith("_abs"):
            content = b"software_engineer_manager_team_size=unknown"
            candidate = _candidate(
                case_id=item["case_id"],
                content=content,
                proposition_sha256=None,
                logical_fact_id=None,
                source_ids=(),
                evidence_class=EvidenceClass.SYNTHETIC_RQ4_CHALLENGE,
            )
        else:
            history = histories[item["question_id"]]
            version = next(
                value
                for value in history["versions"]
                if value["version_id"] == item["version_id"]
            )
            content = version["canonical_content"].encode("utf-8")
            candidate = _candidate(
                case_id=item["case_id"],
                content=content,
                proposition_sha256=version["canonical_sha256"],
                logical_fact_id=history["logical_fact_id"],
                source_ids=(version["source_session_id"],),
                evidence_class=EvidenceClass.SYNTHETIC_RQ4_CHALLENGE,
                canonicalization_id=version["canonicalization_id"],
            )
            bindings.append(
                _binding(
                    candidate,
                    source_event_id=version["source_session_id"],
                    evidence_source_id="longmemeval-oracle-pinned-dataset",
                    evidence_source_sha256=DATASET_SHA256,
                )
            )
        cases.append(
            PilotCase(
                case_id=item["case_id"],
                candidate=candidate,
                content=content,
                expected=MediatorAction(item["expected_action"]),
            )
        )
    return tuple(cases), _bundle(
        tuple(snapshots),
        content_bindings=tuple(bindings),
        source_sha256=DATASET_SHA256,
        source_id="longmemeval-oracle-pinned-dataset",
    )


def _synthetic_fixtures() -> tuple[tuple[PilotCase, ...], AuthorityBundle]:
    snapshots: list[AuthoritySnapshot] = []
    bindings: list[ContentIdentityBinding] = []
    cases: list[PilotCase] = []
    controls = {
        item["control"]: item for item in _manifest()["synthetic_cases"]
    }

    def add_case(
        control: str,
        content: bytes,
        proposition_sha256: str | None,
        logical_fact_id: str | None,
        source_ids: tuple[str, ...],
        binding_source_ids: tuple[str, ...] = (),
    ) -> None:
        item = controls[control]
        candidate = _candidate(
            case_id=item["case_id"],
            content=content,
            proposition_sha256=proposition_sha256,
            logical_fact_id=logical_fact_id,
            source_ids=source_ids,
            evidence_class=EvidenceClass.SYNTHETIC_RQ4_CHALLENGE,
        )
        cases.append(
            PilotCase(
                case_id=item["case_id"],
                candidate=candidate,
                content=content,
                expected=MediatorAction(item["expected_action"]),
            )
        )
        bindings.extend(
            _binding(candidate, source_event_id=source_id)
            for source_id in binding_source_ids
        )

    for control, state, authoritative in (
        ("EXACT_CURRENT_AUTHORITY", LifecycleState.ACTIVE, True),
        ("EXACT_STALE_VERSION", LifecycleState.SUPERSEDED, False),
        ("REVOKED_SOURCE", LifecycleState.REVOKED, False),
        ("DELETED_SOURCE", LifecycleState.DELETED, False),
    ):
        item = controls[control]
        content = f"unique:{item['case_id']}".encode()
        fact = f"fact:{item['case_id']}"
        source = f"source:{item['case_id']}"
        snapshots.append(
            _snapshot(
                logical_fact_id=fact,
                version_id=f"version:{item['case_id']}",
                source_event_id=source,
                lifecycle_state=state,
                authoritative=authoritative,
                sequence=len(snapshots) + 1,
                proposition_sha256=_sha(content),
                source_record_sha256=_sha(f"record:{item['case_id']}"),
            )
        )
        add_case(
            control,
            content,
            _sha(content),
            fact,
            (source,),
            (source,),
        )

    missing = controls["MISSING_PROPOSITION_IDENTITY"]
    missing_content = f"unique:{missing['case_id']}".encode()
    missing_source = f"source:{missing['case_id']}"
    snapshots.append(
        _snapshot(
            logical_fact_id=f"fact:{missing['case_id']}",
            version_id=f"version:{missing['case_id']}",
            source_event_id=missing_source,
            lifecycle_state=LifecycleState.ACTIVE,
            authoritative=True,
            sequence=len(snapshots) + 1,
            proposition_sha256=_sha(missing_content),
            source_record_sha256=_sha(f"record:{missing['case_id']}"),
        )
    )
    add_case(
        "MISSING_PROPOSITION_IDENTITY",
        missing_content,
        None,
        None,
        (missing_source,),
    )

    contradictory = controls["CONTRADICTORY_AUTHORITY"]
    contradictory_content = f"unique:{contradictory['case_id']}".encode()
    contradictory_fact = f"fact:{contradictory['case_id']}"
    contradictory_sources = (
        f"source:{contradictory['case_id']}:active",
        f"source:{contradictory['case_id']}:revoked",
    )
    for source, state, authoritative in (
        (contradictory_sources[0], LifecycleState.ACTIVE, True),
        (contradictory_sources[1], LifecycleState.REVOKED, False),
    ):
        snapshots.append(
            _snapshot(
                logical_fact_id=contradictory_fact,
                version_id=f"version:{source}",
                source_event_id=source,
                lifecycle_state=state,
                authoritative=authoritative,
                sequence=len(snapshots) + 1,
                proposition_sha256=_sha(contradictory_content),
                source_record_sha256=_sha(f"record:{source}"),
            )
        )
    add_case(
        "CONTRADICTORY_AUTHORITY",
        contradictory_content,
        _sha(contradictory_content),
        contradictory_fact,
        contradictory_sources,
        contradictory_sources,
    )

    ancestry = controls["SUPERSEDED_ANCESTRY_CURRENT_CONTENT"]
    ancestry_content = f"unique:{ancestry['case_id']}:current".encode()
    ancestry_fact = f"fact:{ancestry['case_id']}:current"
    current_source = f"source:{ancestry['case_id']}:current"
    stale_source = f"source:{ancestry['case_id']}:stale"
    snapshots.extend(
        (
            _snapshot(
                logical_fact_id=f"fact:{ancestry['case_id']}:stale",
                version_id=f"version:{ancestry['case_id']}:stale",
                source_event_id=stale_source,
                lifecycle_state=LifecycleState.SUPERSEDED,
                authoritative=False,
                sequence=len(snapshots) + 1,
                proposition_sha256=_sha(b"unique:stale-ancestor-content"),
                source_record_sha256=_sha(b"record:stale-ancestor"),
                superseded_by=f"version:{ancestry['case_id']}:current",
            ),
            _snapshot(
                logical_fact_id=ancestry_fact,
                version_id=f"version:{ancestry['case_id']}:current",
                source_event_id=current_source,
                lifecycle_state=LifecycleState.ACTIVE,
                authoritative=True,
                sequence=len(snapshots) + 2,
                proposition_sha256=_sha(ancestry_content),
                source_record_sha256=_sha(b"record:current-with-stale-ancestry"),
                supersedes=f"version:{ancestry['case_id']}:stale",
            ),
        )
    )
    add_case(
        "SUPERSEDED_ANCESTRY_CURRENT_CONTENT",
        ancestry_content,
        _sha(ancestry_content),
        ancestry_fact,
        (current_source, stale_source),
        (current_source,),
    )

    mixed = controls["MIXED_AUTHORITY_AGGREGATE"]
    mixed_content = f"unique:{mixed['case_id']}:current".encode()
    mixed_sources = (
        f"source:{mixed['case_id']}:current",
        f"source:{mixed['case_id']}:revoked",
    )
    for suffix, source, state, authoritative in (
        ("current", mixed_sources[0], LifecycleState.ACTIVE, True),
        ("revoked", mixed_sources[1], LifecycleState.REVOKED, False),
    ):
        snapshots.append(
            _snapshot(
                logical_fact_id=f"fact:{mixed['case_id']}:{suffix}",
                version_id=f"version:{mixed['case_id']}:{suffix}",
                source_event_id=source,
                lifecycle_state=state,
                authoritative=authoritative,
                sequence=len(snapshots) + 1,
                proposition_sha256=_sha(f"unique:{mixed['case_id']}:{suffix}"),
                source_record_sha256=_sha(f"record:{mixed['case_id']}:{suffix}"),
            )
        )
    add_case(
        "MIXED_AUTHORITY_AGGREGATE",
        mixed_content,
        _sha(f"unique:{mixed['case_id']}:current"),
        f"fact:{mixed['case_id']}:current",
        mixed_sources,
        (mixed_sources[0],),
    )
    return tuple(cases), _bundle(
        tuple(snapshots), content_bindings=tuple(bindings)
    )


def test_manifest_pins_sources_hashes_evidence_classes_and_case_counts() -> None:
    manifest = _manifest()
    assert manifest["pilot_schema_version"] == "memlife-rq4-pilot-v2"
    assert manifest["policy_version"] == RQ4_POLICY_VERSION
    assert manifest["base_main_sha"] == "43b50ae437e5dfb7f56b20a06509ac2bb0a49094"
    assert manifest["longmemeval"]["revision"] == (
        "98d7416c24c778c2fee6e6f3006e7a073259d48f"
    )
    assert manifest["longmemeval"]["artifact_sha256"] == DATASET_SHA256
    assert manifest["longmemeval"]["license"] == "MIT"
    assert manifest["longmemeval"]["tracked_source_dataset"] is False
    assert len(manifest["benchmark_cases"]) == 9
    assert len(manifest["synthetic_cases"]) == 8
    assert manifest["benchmark_abstention"]["resolution"] == (
        "UNRESOLVED_TARGET_FACT"
    )

    for source in manifest["source_artifacts"]:
        materialized = materialize_tracked_text(ROOT / source["path"])
        assert materialized.sha256 == source["sha256"]
    for value in manifest["evidence_classes"].values():
        assert value in {item.value for item in EvidenceClass}
    assert manifest["evidence_classes"]["benchmark_derived"] != "PROVIDER_OBSERVED"
    assert manifest["evidence_classes"]["hand_authored"] != "PROVIDER_OBSERVED"
    for history in manifest["benchmark_histories"]:
        assert history["transition"] == {
            "from": "v1",
            "to": "v2",
            "relation": "SUPERSEDED_BY",
        }
        for version in history["versions"]:
            assert _sha(version["source_text"]) == version["source_record_sha256"]
            assert version["source_claim_text"] in version["source_text"]
            assert _sha(version["canonical_content"]) == version["canonical_sha256"]


def test_empirical_controls_are_evidence_limited_and_preserve_current_content() -> None:
    controls = _manifest()["empirical_controls"]
    eligible = [item for item in controls if item["eligible"]]
    ineligible = [item for item in controls if not item["eligible"]]
    assert [item["case_id"] for item in eligible] == [
        "empirical-mem0-s1-r1-current-mixed-lineage",
        "empirical-hindsight-s1-r1-current-derived-mixed-lineage",
    ]
    assert {item["case_id"] for item in ineligible} == {
        "empirical-hindsight-s4",
        "empirical-openviking-s4",
    }
    assert all(
        item["eligibility_status"] == "NOT_ELIGIBLE_FOR_EMPIRICAL_MEDIATION"
        for item in ineligible
    )

    cases, authority = _empirical_fixtures()
    assert _evaluate(cases, authority) == tuple(case.expected for case in cases)
    result = evaluate_candidates(
        tuple(case.candidate for case in cases),
        authority,
        {case.case_id: case.content for case in cases},
        policy_version=RQ4_POLICY_VERSION,
        evaluation_timestamp=FIXED_TIME,
    )
    assert all(decision.stale_witnesses for decision in result.decisions)
    assert _unframe(result.delivered_context) == {
        case.case_id: case.content for case in cases
    }
    assert result.audit_decisions == ()


def test_longmemeval_subset_has_exact_source_ids_and_expected_decisions() -> None:
    cases, authority = _benchmark_fixtures()
    assert len(cases) == 9
    assert all(
        case.candidate.evidence_class is EvidenceClass.SYNTHETIC_RQ4_CHALLENGE
        for case in cases
    )
    result = evaluate_candidates(
        tuple(case.candidate for case in cases),
        authority,
        {case.case_id: case.content for case in cases},
        policy_version=RQ4_POLICY_VERSION,
        evaluation_timestamp=FIXED_TIME,
    )
    actual = tuple(decision.decision for decision in result.decisions)
    assert actual == tuple(case.expected for case in cases)
    assert actual.count(MediatorAction.ALLOW) == 4
    assert actual.count(MediatorAction.DENY) == 4
    assert actual.count(MediatorAction.QUARANTINE) == 1
    framed = _unframe(result.delivered_context)
    for case in cases:
        if case.expected is MediatorAction.ALLOW:
            assert framed[case.case_id] == case.content
        else:
            assert case.content not in result.delivered_context


def test_every_conclusive_decision_has_an_exact_authority_witness() -> None:
    for fixture_factory in (
        _empirical_fixtures,
        _benchmark_fixtures,
        _synthetic_fixtures,
    ):
        cases, authority = fixture_factory()
        result = evaluate_candidates(
            tuple(case.candidate for case in cases),
            authority,
            {case.case_id: case.content for case in cases},
            policy_version=RQ4_POLICY_VERSION,
            evaluation_timestamp=FIXED_TIME,
        )
        for decision in result.decisions:
            if decision.decision is MediatorAction.ALLOW:
                assert decision.current_witnesses
            elif decision.decision is MediatorAction.DENY:
                assert decision.stale_witnesses


def test_synthetic_branches_fail_closed_and_leak_no_unauthorized_bytes() -> None:
    cases, authority = _synthetic_fixtures()
    result = evaluate_candidates(
        tuple(case.candidate for case in cases),
        authority,
        {case.case_id: case.content for case in cases},
        policy_version=RQ4_POLICY_VERSION,
        evaluation_timestamp=FIXED_TIME,
    )
    actual = tuple(decision.decision for decision in result.decisions)
    assert actual == tuple(case.expected for case in cases)
    assert actual.count(MediatorAction.ALLOW) == 2
    assert actual.count(MediatorAction.DENY) == 3
    assert actual.count(MediatorAction.QUARANTINE) == 3

    framed = _unframe(result.delivered_context)
    assert set(framed) == {
        case.case_id for case in cases if case.expected is MediatorAction.ALLOW
    }
    for case in cases:
        if case.expected is MediatorAction.ALLOW:
            assert framed[case.case_id] == case.content
        else:
            assert case.content not in result.delivered_context
    assert len(result.audit_decisions) == 6
    decision_by_id = {
        case.case_id: decision
        for case, decision in zip(cases, result.decisions, strict=True)
    }
    assert "AMBIGUOUS_CONTENT_BINDING" in decision_by_id[
        "synthetic-contradictory-authority"
    ].reason_codes


def test_baselines_expose_expected_failure_modes_on_identical_fixtures() -> None:
    def errors(
        decisions: tuple[BaselineDecision, ...],
        expected: dict[str, MediatorAction],
    ) -> tuple[int, int]:
        incorrect_allow = sum(
            item.decision is MediatorAction.ALLOW
            and expected[item.candidate_id] is not MediatorAction.ALLOW
            for item in decisions
        )
        incorrect_deny = sum(
            item.decision is MediatorAction.DENY
            and expected[item.candidate_id] is not MediatorAction.DENY
            for item in decisions
        )
        return incorrect_allow, incorrect_deny

    expected_by_fixture = (
        (_empirical_fixtures, (0, 0), (0, 2)),
        (_benchmark_fixtures, (5, 0), (0, 0)),
        (_synthetic_fixtures, (6, 0), (1, 3)),
    )
    for fixture_factory, pass_errors, ancestry_errors in expected_by_fixture:
        cases, authority = fixture_factory()
        candidates = tuple(case.candidate for case in cases)
        expected = {case.case_id: case.expected for case in cases}
        pass_through = evaluate_baseline(
            BaselinePolicy.PASS_THROUGH,
            candidates,
            authority,
        )
        ancestry = evaluate_baseline(
            BaselinePolicy.NAIVE_ANCESTRY_ONLY,
            candidates,
            authority,
        )
        assert errors(pass_through, expected) == pass_errors
        assert errors(ancestry, expected) == ancestry_errors
        policy_actions = _evaluate(cases, authority)
        assert all(
            action is case.expected
            for case, action in zip(cases, policy_actions, strict=True)
        )


def test_three_way_confusion_matrices_are_exact_by_evidence_class() -> None:
    expected_matrices = (
        (
            _empirical_fixtures,
            {
                (MediatorAction.ALLOW, MediatorAction.ALLOW): 2,
            },
        ),
        (
            _benchmark_fixtures,
            {
                (MediatorAction.ALLOW, MediatorAction.ALLOW): 4,
                (MediatorAction.DENY, MediatorAction.DENY): 4,
                (MediatorAction.QUARANTINE, MediatorAction.QUARANTINE): 1,
            },
        ),
        (
            _synthetic_fixtures,
            {
                (MediatorAction.ALLOW, MediatorAction.ALLOW): 2,
                (MediatorAction.DENY, MediatorAction.DENY): 3,
                (MediatorAction.QUARANTINE, MediatorAction.QUARANTINE): 3,
            },
        ),
    )
    total = 0
    correct = 0
    for fixture_factory, expected_matrix in expected_matrices:
        cases, authority = fixture_factory()
        actual = _evaluate(cases, authority)
        matrix = Counter(
            (case.expected, observed)
            for case, observed in zip(cases, actual, strict=True)
        )
        assert matrix == expected_matrix
        total += len(cases)
        correct += sum(
            count for (expected, observed), count in matrix.items() if expected is observed
        )
    assert (correct, total) == (19, 19)


def test_replay_is_byte_for_byte_deterministic() -> None:
    cases, authority = _synthetic_fixtures()
    kwargs = {
        "candidates": tuple(case.candidate for case in cases),
        "authority": authority,
        "content_by_candidate_id": {
            case.case_id: case.content for case in cases
        },
        "policy_version": RQ4_POLICY_VERSION,
        "evaluation_timestamp": FIXED_TIME,
    }
    first = evaluate_candidates(**kwargs)
    second = evaluate_candidates(**kwargs)
    assert first == second
    assert first.delivered_context == second.delivered_context
    assert [item.model_dump(mode="json") for item in first.decisions] == [
        item.model_dump(mode="json") for item in second.decisions
    ]


@pytest.mark.parametrize("mode", ["missing", "mismatch"])
def test_missing_or_mismatched_raw_bytes_quarantines(mode: str) -> None:
    cases, authority = _synthetic_fixtures()
    case = cases[0]
    content = {} if mode == "missing" else {case.case_id: b"tampered"}
    result = evaluate_candidates(
        (case.candidate,),
        authority,
        content,
        policy_version=RQ4_POLICY_VERSION,
        evaluation_timestamp=FIXED_TIME,
    )
    assert result.decisions[0].decision is MediatorAction.QUARANTINE
    assert result.delivered_candidate_ids == ()
    assert result.delivered_context == CONTEXT_MAGIC


def test_source_surface_requires_exact_authoritative_source_record_bytes() -> None:
    content = b"source candidate"
    source = "source:exact-record"
    candidate = _candidate(
        case_id="source-record-mismatch",
        content=content,
        proposition_sha256=_sha(content),
        logical_fact_id="fact:source-record",
        source_ids=(source,),
        evidence_class=EvidenceClass.SYNTHETIC_RQ4_CHALLENGE,
        surface=MemorySurface.SOURCE,
    )
    authority = _bundle(
        (
            _snapshot(
                logical_fact_id="fact:source-record",
                version_id="version:source-record",
                source_event_id=source,
                lifecycle_state=LifecycleState.ACTIVE,
                authoritative=True,
                sequence=1,
                proposition_sha256=_sha(content),
                source_record_sha256=_sha(b"different source record"),
            ),
        ),
        content_bindings=(_binding(candidate, source_event_id=source),),
    )
    result = evaluate_candidates(
        (candidate,),
        authority,
        {candidate.candidate_id: content},
        policy_version=RQ4_POLICY_VERSION,
        evaluation_timestamp=FIXED_TIME,
    )
    assert result.decisions[0].decision is MediatorAction.QUARANTINE
    assert "SOURCE_RECORD_SHA256_MISMATCH" in result.decisions[0].reason_codes


def test_authority_artifact_cannot_be_the_retrieved_candidate_artifact() -> None:
    cases, authority = _synthetic_fixtures()
    case = cases[0]
    dependent = authority.model_copy(
        update={"authority_source_sha256": case.candidate.raw_bytes_sha256}
    )
    with pytest.raises(ValueError, match="must not be the candidate"):
        evaluate_candidates(
            (case.candidate,),
            dependent,
            {case.case_id: case.content},
            policy_version=RQ4_POLICY_VERSION,
            evaluation_timestamp=FIXED_TIME,
        )


@pytest.mark.parametrize("collision", ["id", "hash"])
def test_binding_evidence_cannot_be_candidate_controlled(collision: str) -> None:
    cases, authority = _synthetic_fixtures()
    case = cases[0]
    binding = authority.content_bindings[0]
    update = (
        {"evidence_source_id": case.candidate.candidate_id}
        if collision == "id"
        else {"evidence_source_sha256": case.candidate.raw_bytes_sha256}
    )
    dependent_binding = binding.model_copy(update=update)
    dependent = authority.model_copy(
        update={
            "content_bindings": (
                dependent_binding,
                *authority.content_bindings[1:],
            )
        }
    )
    with pytest.raises(ValueError, match="binding evidence"):
        evaluate_candidates(
            (case.candidate,),
            dependent,
            {case.case_id: case.content},
            policy_version=RQ4_POLICY_VERSION,
            evaluation_timestamp=FIXED_TIME,
        )


def test_candidate_hints_never_override_independent_current_authority() -> None:
    cases, authority = _synthetic_fixtures()
    case = cases[0]
    hinted = case.candidate.model_copy(
        update={"lifecycle_hint": LifecycleState.DELETED}
    )
    result = evaluate_candidates(
        (hinted,),
        authority,
        {case.case_id: case.content},
        policy_version=RQ4_POLICY_VERSION,
        evaluation_timestamp=FIXED_TIME,
    )
    assert result.decisions[0].decision is MediatorAction.ALLOW


def test_candidate_declared_hash_cannot_bind_unrelated_bytes_to_authority() -> None:
    cases, authority = _synthetic_fixtures()
    case = cases[0]
    unauthorized = b"unrelated unauthorized bytes"
    forged = case.candidate.model_copy(
        update={"raw_bytes_sha256": _sha(unauthorized)}
    )
    result = evaluate_candidates(
        (forged,),
        authority,
        {forged.candidate_id: unauthorized},
        policy_version=RQ4_POLICY_VERSION,
        evaluation_timestamp=FIXED_TIME,
    )
    assert result.decisions[0].decision is MediatorAction.QUARANTINE
    assert "UNRESOLVED_CONTENT_BINDING" in result.decisions[0].reason_codes
    assert result.delivered_candidate_ids == ()
    assert result.delivered_context == CONTEXT_MAGIC
    assert unauthorized not in result.delivered_context


@pytest.mark.parametrize("duplicate", ["version", "source"])
def test_authority_snapshot_primary_coordinates_are_unique(duplicate: str) -> None:
    first = _snapshot(
        logical_fact_id="fact:first",
        version_id="version:first",
        source_event_id="source:first",
        lifecycle_state=LifecycleState.ACTIVE,
        authoritative=True,
        sequence=1,
        proposition_sha256=_sha(b"first"),
        source_record_sha256=_sha(b"record:first"),
    )
    second = _snapshot(
        logical_fact_id="fact:second",
        version_id="version:first" if duplicate == "version" else "version:second",
        source_event_id="source:first" if duplicate == "source" else "source:second",
        lifecycle_state=LifecycleState.ACTIVE,
        authoritative=True,
        sequence=2,
        proposition_sha256=_sha(b"second"),
        source_record_sha256=_sha(b"record:second"),
    )
    with pytest.raises(ValueError, match=f"snapshot {duplicate}_event_id|snapshot {duplicate}_id"):
        _bundle((first, second))


def test_out_of_window_candidate_and_unsupported_lineage_fail_closed() -> None:
    cases, authority = _synthetic_fixtures()
    case = cases[0]
    future = case.candidate.model_copy(
        update={"valid_from": FIXED_TIME + timedelta(seconds=1)}
    )
    unsupported = case.candidate.model_copy(
        update={
            "relation_edges": (
                RelationEdge(
                    source_id=case.candidate.source_ids[0],
                    target_id=case.case_id,
                    relation="CLAIMS_SOURCE",
                ),
            )
        }
    )
    for candidate in (future, unsupported):
        result = evaluate_candidates(
            (candidate,),
            authority,
            {case.case_id: case.content},
            policy_version=RQ4_POLICY_VERSION,
            evaluation_timestamp=FIXED_TIME,
        )
        assert result.decisions[0].decision is MediatorAction.QUARANTINE
