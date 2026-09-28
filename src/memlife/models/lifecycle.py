"""Minimal lifecycle vocabulary shared across memory providers."""

from enum import Enum


class LifecycleState(str, Enum):
    """Normalized observation states, not an enforcement policy."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"
    DELETED = "deleted"
    EXPIRED = "expired"
