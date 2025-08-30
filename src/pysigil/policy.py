from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple, MutableMapping, Iterator

from .errors import UnknownScopeError, SigilWriteError

# Predefined defaults for the core scope
CORE_DEFAULTS = {"pysigil": {"policy": "project_over_user"}}

# Precedence orders from highest to lowest scope
PRECEDENCE_USER_WINS: Tuple[str, ...] = (
    "env",
    "user-local",
    "user",
    "project-local",
    "project",
    "default",
    "core",
)
PRECEDENCE_PROJECT_WINS: Tuple[str, ...] = (
    "env",
    "project-local",
    "project",
    "user-local",
    "user",
    "default",
    "core",
)


@dataclass(frozen=True)
class Scope:
    """Representation of a configuration scope."""

    name: str
    writable: bool = False


class ScopePolicy:
    """Manager providing policy information for configuration scopes."""

    def __init__(self, scopes: Iterable[Scope]):
        self._scopes: List[Scope] = list(scopes)
        self._by_name = {s.name: s for s in self._scopes}
        self._stores: dict[str, MutableMapping] = {}

    @property
    def scopes(self) -> List[str]:
        """Ordered list of known scope names."""
        return [s.name for s in self._scopes]

    def precedence(self, mode: str) -> Tuple[str, ...]:
        """Return the read precedence order for *mode*.

        ``mode`` must be one of ``"user_over_project"`` or
        ``"project_over_user"``.
        """

        if mode == "user_over_project":
            return PRECEDENCE_USER_WINS
        if mode == "project_over_user":
            return PRECEDENCE_PROJECT_WINS
        raise ValueError(f"Unknown precedence mode: {mode}")

    def allows(self, scope: str) -> bool:
        """Return ``True`` if *scope* is writable."""
        info = self._by_name.get(scope)
        if info is None:
            raise UnknownScopeError(scope)
        return info.writable

    # ----- helpers for Sigil integration -----

    def clone(self, *, default_writable: bool | None = None) -> "ScopePolicy":
        """Return a shallow copy optionally adjusting default scope writability."""

        scopes = [Scope(s.name, s.writable) for s in self._scopes]
        if default_writable is not None:
            scopes = [
                Scope(s.name, default_writable if s.name == "default" else s.writable)
                for s in scopes
            ]
        return ScopePolicy(scopes)

    def set_store(self, scope: str, store: MutableMapping) -> None:
        """Associate *store* with *scope* for later retrieval."""

        if scope not in self._by_name:
            raise UnknownScopeError(scope)
        self._stores[scope] = store

    def get_store(self, scope: str) -> MutableMapping:
        """Return the mapping associated with *scope*."""

        try:
            return self._stores[scope]
        except KeyError as exc:
            raise UnknownScopeError(scope) from exc

    def iter_scopes(self, *, read: bool = False) -> Iterator[str]:
        """Yield scope names in precedence order."""

        # For now reading order is identical to definition order
        for s in self._scopes:
            yield s.name

    def path(self, scope: str, provider_id: str, *, auto: bool = False) -> Path:
        """Return configuration path for *scope* and *provider_id*.

        This delegates to :func:`pysigil.config.target_path` and enforces
        the write policy for scopes.
        """

        if not self.allows(scope):
            raise SigilWriteError(f"Scope '{scope}' is read-only")
        from . import config

        return config.target_path(provider_id, scope, auto=auto)


# Known scopes ordered from lowest to highest precedence
_DEFAULT_SCOPES = [
    Scope("core", writable=False),
    Scope("default", writable=False),
    Scope("project", writable=True),
    Scope("project-local", writable=True),
    Scope("user", writable=True),
    Scope("user-local", writable=True),
    Scope("env", writable=False),
]

policy = ScopePolicy(_DEFAULT_SCOPES)

__all__ = [
    "Scope",
    "ScopePolicy",
    "policy",
    "CORE_DEFAULTS",
    "PRECEDENCE_USER_WINS",
    "PRECEDENCE_PROJECT_WINS",
]
