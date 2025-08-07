from __future__ import annotations

import os
from collections.abc import MutableMapping

from .keys import KeyPath, parse_key


def read_env(app_name: str) -> MutableMapping[KeyPath, str]:
    prefix = f"SIGIL_{app_name.upper()}_"
    result: MutableMapping[KeyPath, str] = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            raw = key[len(prefix):].lower()
            result[parse_key(raw)] = value
    return result
