from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, MutableMapping, Tuple

from .errors import SigilWriteError, UnknownScopeError
from .root import ProjectRootNotFoundError

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
    machine: bool = False


class ScopePolicy:
    """Manager providing policy information for configuration scopes."""

    def __init__(self, scopes: Iterable[Scope]):
        self._scopes: List[Scope] = list(scopes)
        self._by_name = {s.name: s for s in self._scopes}
        self._stores: dict[str, MutableMapping] = {}
        self._machine = {s.name for s in self._scopes if s.machine}

    @property
    def scopes(self) -> List[str]:
        """Ordered list of known scope names."""
        return [s.name for s in self._scopes]

    def precedence(self, *, read: bool = False) -> Tuple[str, ...]:
        """Return the precedence order.

        When ``read`` is ``True`` the current policy is looked up from the
        stored configuration.  If no policy is configured the project-over-user
        order is assumed.
        """

        if not read:
            return PRECEDENCE_PROJECT_WINS

        key = ("pysigil", "policy")
        for scope in PRECEDENCE_PROJECT_WINS:
            store = self._stores.get(scope)
            if store is None:
                continue
            mode = store.get(key)
            if mode == "user_over_project":
                return PRECEDENCE_USER_WINS
            if mode == "project_over_user":
                return PRECEDENCE_PROJECT_WINS
        return PRECEDENCE_PROJECT_WINS

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

    def machine_scopes(self) -> List[str]:
        """Return scopes that are machine-specific."""

        return list(self._machine)

    def path(self, scope: str, provider_id: str, *, auto: bool = False) -> Path:
        """Return configuration path for *scope* and *provider_id*.

        Directories are created as needed and writes are only permitted for
        scopes marked writable in the policy.
        """

        if not self.allows(scope):
            raise SigilWriteError(f"Scope '{scope}' is read-only")

        from . import config
        from .authoring import normalize_provider_id

        pid = normalize_provider_id(provider_id)
        if scope in {"user", "user-local"}:
            base = Path(config.user_config_dir("sigil")) / pid
        else:
            root = config._project_dir(auto)
            if root is None:
                raise ProjectRootNotFoundError("No project root found")
            base = root / ".sigil"
        base.mkdir(parents=True, exist_ok=True)
        if scope in self._machine or pid == "user-custom":
            return base / f"settings-local-{config.host_id()}.ini"
        return base / "settings.ini"


# Known scopes ordered from lowest to highest precedence
_DEFAULT_SCOPES = [
    Scope("core", writable=False),
    Scope("default", writable=False),
    Scope("project", writable=True),
    Scope("project-local", writable=True, machine=True),
    Scope("user", writable=True),
    Scope("user-local", writable=True, machine=True),
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
