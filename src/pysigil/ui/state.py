from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..paths import user_data_dir


def gui_state_file() -> Path:
    """Return the path storing per-user GUI state."""

    return user_data_dir() / "gui-state.json"


def _load_state(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    if isinstance(data, dict):
        return data
    return {}


def load_last_provider() -> str | None:
    """Return the last provider selected in the GUI, if available."""

    state = _load_state(gui_state_file())
    value = state.get("last_provider")
    if isinstance(value, str) and value.strip():
        return value
    return None


def save_last_provider(provider_id: str) -> None:
    """Persist *provider_id* as the last provider selected in the GUI."""

    if not provider_id:
        return
    path = gui_state_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        state = _load_state(path)
        state["last_provider"] = provider_id
        path.write_text(json.dumps(state))
    except Exception:
        # Persistence failures are non-fatal for the GUI.
        return


__all__ = ["gui_state_file", "load_last_provider", "save_last_provider"]
