"""Minimal lifecycle vocabulary shared across memory providers."""

from enum import StrEnum


class LifecycleState(StrEnum):
    """Normalized observation states, not an enforcement policy."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"
    DELETED = "deleted"
    EXPIRED = "expired"
