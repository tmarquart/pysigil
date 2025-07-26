from __future__ import annotations

import os
from typing import Mapping, MutableMapping


def read_env(app_name: str) -> MutableMapping[str, str]:
    prefix = f"SIGIL_{app_name.upper()}_"
    result: MutableMapping[str, str] = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            path = key[len(prefix):].lower().replace("_", ".")
            result[path] = value
    return result
