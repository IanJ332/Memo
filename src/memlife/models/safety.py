"""Shared validation helpers for data that may be serialized into traces."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

_SENSITIVE_KEY = re.compile(
    r"(^|[_-])(api[_-]?key|password|passwd|secret|token|private[_-]?key)($|[_-])",
    re.IGNORECASE,
)


def reject_sensitive_keys(value: Any, *, field_name: str = "metadata") -> Any:
    """Reject credential-shaped keys recursively without inspecting values."""

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _SENSITIVE_KEY.search(str(key)):
                raise ValueError(f"{field_name} contains a sensitive key")
            reject_sensitive_keys(nested, field_name=field_name)
    elif isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        for nested in value:
            reject_sensitive_keys(nested, field_name=field_name)
    return value
