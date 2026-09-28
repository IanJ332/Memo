"""Validation and ordering for lifecycle scenario intent."""

import pytest
from pydantic import ValidationError

from memlife.scenarios import (
    BENCHMARK_VERSION,
    LifecycleEvent,
    LifecycleScenario,
    LifecycleStep,
    ScenarioQuery,
    canonical_scenarios,
)


def test_canonical_suite_has_stable_scenarios_and_event_order() -> None:
    scenarios = canonical_scenarios()
    assert [scenario.scenario_id for scenario in scenarios] == [
        "baseline",
        "correction-update",
        "revocation",
        "delete-restart",
        "supersession",
    ]
    assert all(scenario.benchmark_version == BENCHMARK_VERSION for scenario in scenarios)
    assert [step.event for step in scenarios[3].lifecycle_steps] == [
        LifecycleEvent.WRITE,
        LifecycleEvent.QUERY,
        LifecycleEvent.DELETE,
        LifecycleEvent.QUERY,
        LifecycleEvent.RESTART,
        LifecycleEvent.QUERY,
        LifecycleEvent.INSPECT,
    ]


def test_scenario_rejects_target_before_write() -> None:
    with pytest.raises(ValidationError, match="undeclared target_key"):
        LifecycleScenario(
            scenario_id="bad-order",
            description="Invalid ordering fixture.",
            namespace="bad-order",
            lifecycle_steps=(
                LifecycleStep(event=LifecycleEvent.DELETE, target_key="missing"),
            ),
            expected_authoritative_state=(),
        )


def test_scenario_rejects_unknown_or_unused_queries() -> None:
    query = ScenarioQuery(query_id="declared", text="synthetic")
    with pytest.raises(ValidationError, match="unknown query_id"):
        LifecycleScenario(
            scenario_id="unknown-query",
            description="Unknown query fixture.",
            namespace="unknown-query",
            lifecycle_steps=(
                LifecycleStep(event=LifecycleEvent.QUERY, query_id="missing"),
            ),
            queries=(query,),
            expected_authoritative_state=(),
        )

    with pytest.raises(ValidationError, match="not used"):
        LifecycleScenario(
            scenario_id="unused-query",
            description="Unused query fixture.",
            namespace="unused-query",
            lifecycle_steps=(LifecycleStep(event=LifecycleEvent.RESTART),),
            queries=(query,),
            expected_authoritative_state=(),
        )


def test_query_facts_cannot_be_both_current_and_stale() -> None:
    with pytest.raises(ValidationError, match="must not overlap"):
        ScenarioQuery(
            query_id="overlap",
            text="synthetic fact",
            current_facts=("synthetic fact",),
            stale_facts=("synthetic fact",),
        )
