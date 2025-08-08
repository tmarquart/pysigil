from __future__ import annotations

from pathlib import Path
from typing import Any

from .keys import KeyPath

_META: dict[str, dict[str, Any]] = {}


def _parse_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        v = val.strip().lower()
        if v in {"1", "true", "y", "yes", "on"}:
            return True
        if v in {"0", "false", "n", "no", "off"}:
                return False
    return bool(val)


def load(path: Path | None) -> None:
    """Load metadata from *path* applying defaults for policy/locked."""
    global _META
    _META = {}
    if path is None:
        return
    from .helpers import load_meta as _load_meta

    raw = _load_meta(Path(path))
    for key, entry in raw.items():
        data = dict(entry)
        policy = data.get("policy", "project_over_user")
        if policy not in {"project_over_user", "user_over_project"}:
            policy = "project_over_user"
        data["policy"] = policy
        locked = _parse_bool(data.get("locked", False))
        data["locked"] = locked
        _META[key] = data


def get_meta_for(keypath: KeyPath) -> dict[str, Any]:
    dotted = ".".join(keypath)
    data = dict(_META.get(dotted, {}))
    if "policy" not in data:
        data["policy"] = "project_over_user"
    if "locked" not in data:
        data["locked"] = False
    return data
