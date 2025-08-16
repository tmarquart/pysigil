from __future__ import annotations

import os
import re
from collections.abc import MutableMapping

KeyPath = tuple[str, ...]

_SPLIT_RX = re.compile(r"[._]")


def parse_key(raw: str | KeyPath) -> KeyPath:
    if isinstance(raw, tuple):
        return raw
    parts = _SPLIT_RX.split(raw) if _SPLIT_RX.search(raw) else [raw]
    if any(p == "" for p in parts):
        raise ValueError(f"Malformed key '{raw}'")
    return tuple(parts)


def read_env(app_name: str) -> MutableMapping[KeyPath, str]:
    sanitized = app_name.upper().replace("-", "_")
    prefix = f"SIGIL_{sanitized}_"
    result: MutableMapping[KeyPath, str] = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            raw = key[len(prefix):].lower()
            result[parse_key(raw)] = value
    return result


CORE_DEFAULTS = {"pysigil": {"policy": "project_over_user"}}
