from __future__ import annotations

import json
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path.home() / ".config" / "sigil" / "gui_state.json"


def read_state(path: Path | None = None) -> MutableMapping[str, Any]:
    path = path or DEFAULT_PATH
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def write_state(state: MutableMapping[str, Any], path: Path | None = None) -> None:
    path = path or DEFAULT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state))


__all__ = ["read_state", "write_state"]
