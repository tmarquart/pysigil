from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

from ..core import Sigil


class PrefModel:
    """UI-agnostic adapter exposing Sigil preferences."""

    def __init__(self, sigil: Sigil, meta: Mapping[str, Mapping]):
        self.sigil = sigil
        self._meta = dict(meta)
        self._dirty: dict[str, MutableMapping[str, Any]] = {
            "default": {},
            "user": {},
            "project": {},
        }

    # ----- read-only helpers -----
    def all_keys(self) -> list[str]:
        keys = set(self._meta)
        keys.update(self._merged().keys())
        keys.update(self._dirty["user"].keys())
        keys.update(self._dirty["project"].keys())
        def sort_key(k: str) -> tuple[int, str]:
            order = self._meta.get(k, {}).get("order")
            if isinstance(order, int | float):
                return (int(order), k)
            return (9999, k)
        return sorted(keys, key=sort_key)

    def origin(self, key: str) -> str:
        merged = self._merged()
        if key not in merged:
            return "default"
        if key in self.sigil._env:
            return "env"
        proj = self.sigil._flatten(self.sigil._project)
        if key in self._dirty["project"] or key in proj:
            return "project"
        user = self.sigil._flatten(self.sigil._user)
        if key in self._dirty["user"] or key in user:
            return "user"
        return "default"

    def get(self, key: str) -> Any:
        merged = self._merged()
        return merged.get(key)

    def meta(self, key: str) -> Mapping:
        return self._meta.get(key, {})

    def scoped_values(self) -> Mapping[str, MutableMapping[str, str]]:
        """Return preferences grouped by scope."""
        return self.sigil.scoped_values()

    # ----- write operations -----
    def set(self, key: str, value: Any, scope: str = "user") -> None:
        if scope not in {"user", "project", "default"}:
            raise ValueError("scope must be 'user', 'project' or 'default'")
        self._dirty[scope][key] = value

    def save(self, scope: str) -> None:
        dirty = self._dirty.get(scope)
        if dirty:
            for key, value in dirty.items():
                self.sigil.set_pref(key, value, scope=scope)
            self._dirty[scope].clear()

    def reload(self) -> None:
        self.sigil.invalidate_cache()
        for scope in self._dirty:
            self._dirty[scope].clear()

    # ----- change tracking -----
    def is_dirty(self, scope: str) -> bool:
        return bool(self._dirty.get(scope))

    # internal helper
    def _merged(self) -> MutableMapping[str, Any]:
        merged = self.sigil._flatten(self.sigil._defaults)
        user = self.sigil._flatten(self.sigil._user)
        user.update(self._dirty["user"])
        proj = self.sigil._flatten(self.sigil._project)
        proj.update(self._dirty["project"])
        default_dirty = self._dirty["default"]
        merged.update(default_dirty)
        merged.update(user)
        merged.update(proj)
        merged.update(self.sigil._env)
        return merged
