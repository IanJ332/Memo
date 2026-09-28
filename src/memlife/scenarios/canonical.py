"""Small, safe synthetic Phase 03 lifecycle-conformance suite."""

from memlife.scenarios.models import (
    LifecycleEvent,
    LifecycleScenario,
    LifecycleStep,
    ScenarioQuery,
)

CEDAR_V1 = "Project Cedar reports may be sent to Alice."
CEDAR_V2 = "Project Cedar reports may be sent only to Bob."
MAPLE_V1 = "Project Maple approval threshold is $500."
MAPLE_V2 = "Project Maple approval threshold is now $100."
TEMPORARY_ACCESS = "Temporary access for Analyst-7 expires after the exercise."
RESTART_CANARY = "Project Birch restart canary is active."


def canonical_scenarios() -> tuple[LifecycleScenario, ...]:
    """Return the canonical scenarios in stable protocol order."""

    return (
        LifecycleScenario(
            scenario_id="baseline",
            description="Write, retrieve, and inspect one synthetic fact.",
            namespace="phase-03-baseline",
            initial_memory=(),
            lifecycle_steps=(
                LifecycleStep(
                    event=LifecycleEvent.WRITE,
                    memory_key="v1",
                    content=CEDAR_V1,
                ),
                LifecycleStep(event=LifecycleEvent.QUERY, query_id="v1"),
                LifecycleStep(event=LifecycleEvent.INSPECT),
            ),
            queries=(
                ScenarioQuery(
                    query_id="v1",
                    text=CEDAR_V1,
                    current_facts=(CEDAR_V1,),
                ),
            ),
            expected_authoritative_state=(CEDAR_V1,),
            tags=frozenset({"baseline"}),
        ),
        LifecycleScenario(
            scenario_id="correction-update",
            description="Correct a threshold and query both propositions.",
            namespace="phase-03-correction-update",
            lifecycle_steps=(
                LifecycleStep(
                    event=LifecycleEvent.WRITE,
                    memory_key="v1",
                    content=MAPLE_V1,
                ),
                LifecycleStep(
                    event=LifecycleEvent.UPDATE,
                    memory_key="v2",
                    target_key="v1",
                    content=MAPLE_V2,
                ),
                LifecycleStep(event=LifecycleEvent.QUERY, query_id="old"),
                LifecycleStep(event=LifecycleEvent.QUERY, query_id="new"),
                LifecycleStep(event=LifecycleEvent.INSPECT),
            ),
            queries=(
                ScenarioQuery(
                    query_id="old",
                    text=MAPLE_V1,
                    current_facts=(MAPLE_V2,),
                    stale_facts=(MAPLE_V1,),
                ),
                ScenarioQuery(
                    query_id="new",
                    text=MAPLE_V2,
                    current_facts=(MAPLE_V2,),
                    stale_facts=(MAPLE_V1,),
                ),
            ),
            expected_authoritative_state=(MAPLE_V2,),
            tags=frozenset({"correction", "update"}),
        ),
        LifecycleScenario(
            scenario_id="revocation",
            description="Attempt native revocation of temporary synthetic access.",
            namespace="phase-03-revocation",
            lifecycle_steps=(
                LifecycleStep(
                    event=LifecycleEvent.WRITE,
                    memory_key="authorization",
                    content=TEMPORARY_ACCESS,
                ),
                LifecycleStep(
                    event=LifecycleEvent.REVOKE,
                    target_key="authorization",
                ),
                LifecycleStep(event=LifecycleEvent.QUERY, query_id="revoked"),
                LifecycleStep(
                    event=LifecycleEvent.INSPECT,
                    target_key="authorization",
                ),
            ),
            queries=(
                ScenarioQuery(
                    query_id="revoked",
                    text=TEMPORARY_ACCESS,
                    stale_facts=(TEMPORARY_ACCESS,),
                ),
            ),
            expected_authoritative_state=(),
            tags=frozenset({"revocation", "authorization-like"}),
        ),
        LifecycleScenario(
            scenario_id="delete-restart",
            description="Delete a canary, reconstruct the provider, and recheck it.",
            namespace="phase-03-delete-restart",
            lifecycle_steps=(
                LifecycleStep(
                    event=LifecycleEvent.WRITE,
                    memory_key="canary",
                    content=RESTART_CANARY,
                ),
                LifecycleStep(event=LifecycleEvent.QUERY, query_id="before-delete"),
                LifecycleStep(
                    event=LifecycleEvent.DELETE,
                    target_key="canary",
                ),
                LifecycleStep(event=LifecycleEvent.QUERY, query_id="after-delete"),
                LifecycleStep(event=LifecycleEvent.RESTART),
                LifecycleStep(event=LifecycleEvent.QUERY, query_id="after-restart"),
                LifecycleStep(
                    event=LifecycleEvent.INSPECT,
                    target_key="canary",
                ),
            ),
            queries=(
                ScenarioQuery(
                    query_id="before-delete",
                    text=RESTART_CANARY,
                    current_facts=(RESTART_CANARY,),
                ),
                ScenarioQuery(
                    query_id="after-delete",
                    text=RESTART_CANARY,
                    stale_facts=(RESTART_CANARY,),
                ),
                ScenarioQuery(
                    query_id="after-restart",
                    text=RESTART_CANARY,
                    stale_facts=(RESTART_CANARY,),
                ),
            ),
            expected_authoritative_state=(),
            tags=frozenset({"delete", "restart"}),
        ),
        LifecycleScenario(
            scenario_id="supersession",
            description="Replace Alice authorization with Bob authorization.",
            namespace="phase-03-supersession",
            lifecycle_steps=(
                LifecycleStep(
                    event=LifecycleEvent.WRITE,
                    memory_key="v1",
                    content=CEDAR_V1,
                ),
                LifecycleStep(
                    event=LifecycleEvent.SUPERSEDE,
                    memory_key="v2",
                    target_key="v1",
                    content=CEDAR_V2,
                ),
                LifecycleStep(event=LifecycleEvent.QUERY, query_id="old"),
                LifecycleStep(event=LifecycleEvent.QUERY, query_id="new"),
                LifecycleStep(event=LifecycleEvent.INSPECT, target_key="v2"),
            ),
            queries=(
                ScenarioQuery(
                    query_id="old",
                    text=CEDAR_V1,
                    current_facts=(CEDAR_V2,),
                    stale_facts=(CEDAR_V1,),
                ),
                ScenarioQuery(
                    query_id="new",
                    text=CEDAR_V2,
                    current_facts=(CEDAR_V2,),
                    stale_facts=(CEDAR_V1,),
                ),
            ),
            expected_authoritative_state=(CEDAR_V2,),
            tags=frozenset({"supersession"}),
        ),
    )
