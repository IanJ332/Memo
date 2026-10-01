"""Canonical lifecycle statuses and backward-compatible historical aliases."""

from __future__ import annotations

CANONICAL_LIFECYCLE_STATUSES = frozenset({"PASS", "PARTIAL", "BLOCKED"})
HISTORICAL_LIFECYCLE_STATUS_ALIASES = {
    "SUPPLEMENT_COMPLETE": "PASS",
    "SUPPLEMENT_PARTIAL": "PARTIAL",
    "SUPPLEMENT_BLOCKED": "BLOCKED",
}


def normalize_lifecycle_status(value: object) -> str:
    """Return PASS/PARTIAL/BLOCKED, accepting only documented old aliases."""

    status = str(value or "").strip().upper()
    status = HISTORICAL_LIFECYCLE_STATUS_ALIASES.get(status, status)
    if status not in CANONICAL_LIFECYCLE_STATUSES:
        raise ValueError(f"unknown lifecycle status: {value!r}")
    return status
