"""Small Phase 06 protocol helpers; live batch orchestration remains Phase 06B."""

from __future__ import annotations

from collections import Counter
from enum import Enum
from statistics import median
from typing import Iterable

from pydantic import Field

from memlife.models.authority import AuthorityExposureOutcome
from memlife.models.benchmark import NormalizedOutcome, OperationStatus
from memlife.models.memory import NonEmptyText, StrictModel

REPETITIONS_PER_SUPPORTED_SCENARIO = 3
RUN_ID_TEMPLATE = "freeze-v1__{provider}__{scenario}__r{repetition}"
NAMESPACE_TEMPLATE = "memlife-freeze-v1-{provider}-{scenario}-r{repetition}"


def experiment_run_id(provider: str, scenario: str, repetition: int) -> str:
    if repetition < 1:
        raise ValueError("repetition must be at least 1")
    return RUN_ID_TEMPLATE.format(
        provider=provider, scenario=scenario, repetition=repetition
    )


def experiment_namespace(provider: str, scenario: str, repetition: int) -> str:
    if repetition < 1:
        raise ValueError("repetition must be at least 1")
    return NAMESPACE_TEMPLATE.format(
        provider=provider, scenario=scenario, repetition=repetition
    )


class AggregationStatus(str, Enum):
    CONSISTENT = "CONSISTENT"
    INCONSISTENT = "INCONSISTENT"


class RepetitionObservation(StrictModel):
    exact_outcome: NormalizedOutcome
    authority_outcome: AuthorityExposureOutcome
    operation_status: OperationStatus
    latency_ms: float = Field(ge=0)
    provenance_known: bool
    residual: bool = False


class RepetitionAggregate(StrictModel):
    supported_repetitions: int = Field(ge=0)
    exact_outcome_counts: dict[str, int]
    authority_exposure_outcome_counts: dict[str, int]
    residual: bool
    inconsistent: bool
    status: AggregationStatus
    operation_error_count: int = Field(ge=0)
    median_latency_ms: float = Field(ge=0)
    provenance_known_fraction: float = Field(ge=0, le=1)


def aggregate_repetitions(
    observations: Iterable[RepetitionObservation],
) -> RepetitionAggregate:
    raw = tuple(observations)
    if not raw:
        raise ValueError("at least one repetition is required")
    exact = Counter(item.exact_outcome.value for item in raw)
    authority = Counter(item.authority_outcome.value for item in raw)
    inconsistent = len(exact) > 1 or len(authority) > 1
    return RepetitionAggregate(
        supported_repetitions=sum(
            item.operation_status is not OperationStatus.UNSUPPORTED for item in raw
        ),
        exact_outcome_counts=dict(sorted(exact.items())),
        authority_exposure_outcome_counts=dict(sorted(authority.items())),
        residual=any(item.residual for item in raw) or inconsistent,
        inconsistent=inconsistent,
        status=(
            AggregationStatus.INCONSISTENT
            if inconsistent
            else AggregationStatus.CONSISTENT
        ),
        operation_error_count=sum(
            item.operation_status is OperationStatus.ERROR for item in raw
        ),
        median_latency_ms=median(item.latency_ms for item in raw),
        provenance_known_fraction=(
            sum(item.provenance_known for item in raw) / len(raw)
        ),
    )


class ResidualSignals(StrictModel):
    nonauthoritative_exact_visible: bool = False
    nonauthoritative_correlated_derived_visible: bool = False
    deleted_or_revoked_descendant_visible: bool = False
    reappeared_after_restart: bool = False
    reappeared_after_rederivation: bool = False
    source_derived_authority_disagreement: bool = False
    repetition_authority_disagreement: bool = False


def advances_to_root_cause(signals: ResidualSignals) -> bool:
    return any(signals.model_dump().values())


def advances_to_rq3(
    *,
    reproducible_nonauthoritative_exposure: bool,
    delivered_context_frozen: bool,
    authority_known_for_defense: bool,
    reaches_model_boundary: bool,
) -> bool:
    return all(
        (
            reproducible_nonauthoritative_exposure,
            delivered_context_frozen,
            authority_known_for_defense,
            reaches_model_boundary,
        )
    )

