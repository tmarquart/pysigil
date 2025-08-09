from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

try:
    from appdirs import user_config_dir
except ModuleNotFoundError:  # pragma: no cover
    from ._appdirs_stub import user_config_dir

# Store GUI state alongside preference files under the same base directory.
STATE_PATH = Path(user_config_dir("sigil")) / "gui_state.json"


def read_state(path: Path | None = None) -> dict:
    """Read GUI state from *path* or default location."""
    p = path or STATE_PATH
    try:
        data = json.loads(p.read_text())
        if isinstance(data, Mapping):
            return dict(data)
    except Exception:
        pass
    return {}


def write_state(state: Mapping[str, Any], path: Path | None = None) -> None:
    """Persist *state* as JSON to *path* (default :data:`STATE_PATH`)."""
    p = path or STATE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf8") as fh:
        json.dump(dict(state), fh)
