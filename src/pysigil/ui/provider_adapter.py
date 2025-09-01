from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .. import api
from ..policy import policy
from ..authoring import get as get_dev_link, list_links


@dataclass(frozen=True)
class ValueInfo:
    """UI facing value information."""

    value: Any | None
    error: str | None = None


class ProviderAdapter:
    """Adapter exposing provider data and configuration values for the UI."""

    def __init__(self, *, author_mode: bool = False) -> None:
        self.author_mode = author_mode
        self._handle: api.ProviderHandle | None = None
        self._default_path: Path | None = None
        self._default_writable = False

    # ------------------------------------------------------------------
    # Provider / scope discovery
    # ------------------------------------------------------------------
    def list_providers(self) -> List[str]:
        """Return all known provider ids, including dev-link only ones."""
        providers = set(api.providers())
        try:
            providers.update(list_links(must_exist_on_disk=True))
        except Exception:  # pragma: no cover - defensive
            pass
        return sorted(providers)

    def set_provider(self, provider_id: str) -> None:
        """Bind the adapter to *provider_id*."""
        self._handle = api.handle(provider_id)
        dl = get_dev_link(provider_id)
        if dl and dl.defaults_path.exists():
            self._default_path = dl.defaults_path
            self._default_writable = True
        else:
            links = list_links(must_exist_on_disk=True)
            self._default_path = links.get(provider_id)
            self._default_writable = self._default_path is not None

    # internal ----------------------------------------------------------
    def _require_handle(self) -> api.ProviderHandle:
        if self._handle is None:
            raise RuntimeError("provider not set")
        return self._handle

    def scopes(self) -> List[str]:
        """Return scope ids in display order."""
        known = set(policy.scopes)
        order = [s for s in policy.precedence(read=True) if s in known]
        return [s for s in order if s != "core"]

    _SHORT_LABELS = {
        "env": "Env",
        "user": "User",
        "user-local": "Machine",
        "project": "Project",
        "project-local": "Project·Machine",
        "default": "Default",
    }

    _LONG_LABELS = {
        "env": "Environment",
        "user": "User",
        "user-local": "Machine",
        "project": "Project",
        "project-local": "Project on this Machine",
        "default": "Default",
    }

    def scope_label(self, scope_id: str, short: bool = False) -> str:
        """Return human readable label for *scope_id*."""
        mapping = self._SHORT_LABELS if short else self._LONG_LABELS
        return mapping.get(scope_id, scope_id)

    def can_write(self, scope_id: str) -> bool:
        """Return ``True`` if *scope_id* is writable according to policy."""
        if scope_id == "default":
            return self.author_mode and self._default_writable
        try:
            return policy.allows(scope_id)
        except Exception:  # pragma: no cover - defensive
            return False

    def is_overlay(self, scope_id: str) -> bool:
        """Return ``True`` if *scope_id* represents an overlay (e.g. env)."""
        return scope_id == "env"

    # ------------------------------------------------------------------
    # Values
    # ------------------------------------------------------------------
    def values_for_key(self, key: str) -> Dict[str, ValueInfo]:
        """Return values per scope for *key* (only present scopes)."""
        handle = self._require_handle()
        layers = handle.layers()
        per_scope = layers.get(key, {})
        result: Dict[str, ValueInfo] = {}
        for scope, val in per_scope.items():
            if val is None:
                continue
            result[scope] = ValueInfo(value=val.value, error=None)
        return result

    def effective_for_key(self, key: str) -> Tuple[Any | None, str | None]:
        """Return the effective value and its source scope for *key*."""
        handle = self._require_handle()
        eff = handle.effective()
        vi = eff.get(key)
        if vi is None:
            return None, None
        return vi.value, vi.source

    def default_for_key(self, key: str) -> Any | None:
        """Return the value from the ``default`` scope for *key*."""
        handle = self._require_handle()
        layers = handle.layers()
        per_scope = layers.get(key, {})
        val = per_scope.get("default")
        return None if val is None else val.value

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------
    def set_value(self, key: str, scope_id: str, value: object) -> None:
        handle = self._require_handle()
        if scope_id == "default":
            if not (self.author_mode and self._default_writable):
                raise PermissionError("default scope is read-only")
            handle._manager().set(key, value, scope="default")  # type: ignore[attr-defined]
            return
        handle.set(key, value, scope=scope_id)

    def clear_value(self, key: str, scope_id: str) -> None:
        handle = self._require_handle()
        if scope_id == "default":
            if not (self.author_mode and self._default_writable):
                raise PermissionError("default scope is read-only")
            handle._manager().clear(key, scope="default")  # type: ignore[attr-defined]
            return
        handle.clear(key, scope=scope_id)

    # ------------------------------------------------------------------
    # Hints and metadata
    # ------------------------------------------------------------------
    def target_path(self, scope_id: str) -> str:
        """Return filesystem path for *scope_id* writes."""
        handle = self._require_handle()
        if scope_id == "default" and self._default_path is not None:
            return str(self._default_path)
        return str(handle.target_path(scope_id))

    def fields(self) -> List[str]:
        """Return field keys defined by the provider in spec order."""
        handle = self._require_handle()
        return [f.key for f in handle.fields()]

    def field_info(self, key: str) -> api.FieldInfo:
        """Return field metadata for *key*."""
        handle = self._require_handle()
        for field in handle.fields():
            if field.key == key:
                return field
        raise KeyError(key)
