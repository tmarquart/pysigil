from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

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
