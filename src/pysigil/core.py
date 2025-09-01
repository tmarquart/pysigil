from __future__ import annotations

import json
import logging
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any

from .authoring import normalize_provider_id
from .discovery import pep503_name
from .errors import (
    ReadOnlyScopeError,
    SigilError,  # noqa: F401 - re-exported for compatibility
    SigilWriteError,
    UnknownScopeError,
)
from .merge_policy import KeyPath, parse_key, read_env
from .policy import CORE_DEFAULTS, ScopePolicy, policy as default_policy
from .root import ProjectRootNotFoundError
from .resolver import (
    project_settings_file,
    resolve_defaults,
    user_settings_file,
)
from .secrets import (
    EncryptedFileProvider,
    EnvSecretProvider,
    KeyringProvider,
    SecretChain,
    SecretProvider,
)
from .config import host_id


def _backend_for(path: Path):
    from .backends import get_backend_for_path

    return get_backend_for_path(path)

logger = logging.getLogger("pysigil")

KEY_JOIN_CHAR = "_"


class Sigil:
    def __init__(
        self,
        app_name: str,
        *,
        user_scope: Path | None = None,
        project_scope: Path | None = None,
        defaults: Mapping[str | KeyPath, Any] | None = None,
        default_path: Path | None = None,
        env_reader: Callable[[str], Mapping[KeyPath, str]] = read_env,
        secrets: Sequence[SecretProvider] | None = None,
        settings_filename='settings.ini',
        policy: ScopePolicy | None = None,
    ) -> None:
        # Normalise the application name so that underscores and hyphens are
        # treated equivalently across all scopes.  This mirrors the
        # normalisation used for provider discovery (PEP 503) and ensures that
        # configuration files using either convention are correctly recognised.
        try:
            normalize_provider_id(app_name)
            self.app_name = pep503_name(app_name)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError(f"invalid application name: {app_name!r}") from exc
        self.settings_filename = settings_filename

        self._host = host_id()

        if user_scope is not None:
            self.user_path = Path(user_scope)
            if (
                self.user_path.suffix == ""
                or self.user_path.name != self.settings_filename
            ):
                self.user_path = self.user_path / self.settings_filename
        else:
            self.user_path = user_settings_file(
                self.app_name, filename=self.settings_filename
            )

        if project_scope is not None:
            self.project_path = Path(project_scope)
            if (
                self.project_path.suffix == ""
                or self.project_path.name != self.settings_filename
            ):
                self.project_path = self.project_path / self.settings_filename
        else:
            try:
                self.project_path = project_settings_file(
                    filename=self.settings_filename
                )
            except ProjectRootNotFoundError:
                self.project_path = Path.cwd() / self.settings_filename

        self.user_local_path = self.user_path.parent / f"settings-local-{self._host}.ini"
        self.project_local_path = self.project_path.parent / f"settings-local-{self._host}.ini"

        if default_path is not None:
            self.default_path = Path(default_path)
            if (
                self.default_path.suffix == ""
                or self.default_path.name != self.settings_filename
            ):
                self.default_path = self.default_path / ".sigil" / self.settings_filename
            self._default_source = "explicit"
            self._defaults_writable = True
        else:
            self.default_path, self._default_source = resolve_defaults(
                self.app_name, filename=self.settings_filename
            )
            self._defaults_writable = self._default_source == "dev-link"

        # Mapping from scope names to backing paths
        self._paths: dict[str, Path] = {
            "user": self.user_path,
            "user-local": self.user_local_path,
            "project": self.project_path,
            "project-local": self.project_local_path,
        }
        if self.default_path is not None:
            self._paths["default"] = self.default_path

        self.policy = (policy or default_policy).clone(
            default_writable=self._defaults_writable
        )

        self._defaults: MutableMapping[KeyPath, str] = {}
        if defaults:
            for k, v in defaults.items():
                self._defaults[(self.app_name, *parse_key(k))] = str(v)
        self._env_reader = env_reader
        self._lock = RLock()
        self._default_scope = "user"
        enc_path = self.default_path.with_suffix(".enc.json") if self.default_path else None
        if secrets is None:
            providers = [
                KeyringProvider(),
                EncryptedFileProvider(enc_path, prompt=False, required=False),
                EnvSecretProvider(self.app_name),
            ]
            self._secrets = SecretChain(providers)
        else:
            self._secrets = SecretChain(secrets)
        self._core: MutableMapping[KeyPath, str] = {}
        for section, mapping in CORE_DEFAULTS.items():
            for k, v in mapping.items():
                self._core[parse_key(f"{section}.{k}")] = str(v)

        # Stores for each scope
        self._user: MutableMapping[KeyPath, str] = {}
        self._user_local: MutableMapping[KeyPath, str] = {}
        self._project: MutableMapping[KeyPath, str] = {}
        self._project_local: MutableMapping[KeyPath, str] = {}
        self._env: MutableMapping[KeyPath, str] = {}

        for name, store in {
            "core": self._core,
            "default": self._defaults,
            "user": self._user,
            "user-local": self._user_local,
            "project": self._project,
            "project-local": self._project_local,
            "env": self._env,
        }.items():
            try:
                self.policy.set_store(name, store)
            except UnknownScopeError:
                pass

        self.invalidate_cache()

    @property
    def default_scope(self) -> str:
        """Return the current default scope for writes."""
        return self._default_scope

    def set_default_scope(self, scope: str) -> None:
        """Set the default scope for writes.

        Only writable scopes are supported.  The ``"default"`` scope is only
        available when defaults were loaded via a development link or explicit
        path.
        """
        if not self.policy.allows(scope):
            raise ReadOnlyScopeError("Default scope is read-only")
        self._default_scope = scope

    def invalidate_cache(self) -> None:
        with self._lock:
            raw_env = self._env_reader(self.app_name)
            self._env.clear()
            for k, v in raw_env.items():
                self._env[(self.app_name, *k)] = v

            user_backend = _backend_for(self.user_path)
            project_backend = _backend_for(self.project_path)
            user_local_backend = _backend_for(self.user_local_path)
            project_local_backend = _backend_for(self.project_local_path)
            self._user.clear()
            for k, v in user_backend.load(self.user_path).items():
                nk = self._normalize_key(k)
                if nk:
                    self._user[nk] = v
            self._user_local.clear()
            for k, v in user_local_backend.load(self.user_local_path).items():
                nk = self._normalize_key(k)
                if nk:
                    self._user_local[nk] = v
            self._project.clear()
            for k, v in project_backend.load(self.project_path).items():
                nk = self._normalize_key(k)
                if nk:
                    self._project[nk] = v
            self._project_local.clear()
            for k, v in project_local_backend.load(self.project_local_path).items():
                nk = self._normalize_key(k)
                if nk:
                    self._project_local[nk] = v
            if self.default_path is not None:
                default_backend = _backend_for(self.default_path)
                for k, v in default_backend.load(self.default_path).items():
                    nk = self._normalize_key(k)
                    if nk:
                        self._defaults[nk] = v
            self._merge_cache()

    def _merge_cache(self) -> None:
        self._merged = {}
        for scope in self.policy.iter_scopes(read=True):
            self._merged.update(self.policy.get_store(scope))

    def _normalize_key(self, path: KeyPath) -> KeyPath | None:
        """Return *path* with normalised prefix if it belongs to us.

        Configuration files may use either ``-`` or ``_`` in the provider
        section name.  This helper converts the first path element to the
        canonical :attr:`app_name` and returns ``None`` for unrelated keys.
        """

        if len(path) == 0:
            return None
        if pep503_name(path[0]) != self.app_name:
            return None
        return (self.app_name, *path[1:])

    def _is_ours(self, path: KeyPath) -> bool:
        return self._normalize_key(path) is not None

    def _strip_prefix(self, path: KeyPath) -> KeyPath:
        return path[1:] if self._is_ours(path) else path

    def _value_from_scope(self, scope: str, key: KeyPath) -> str | None:
        return self.policy.get_store(scope).get(key)

    def scoped_values(self) -> Mapping[str, MutableMapping[str, str]]:
        """Return all known preferences grouped by scope.

        The returned mapping contains ``"default"``, ``"user"``, ``"user-local"``,
        ``"project"`` and ``"project-local"`` keys, each mapping to a flat
        dictionary of preference keys to values.
        """
        with self._lock:
            out: dict[str, MutableMapping[str, str]] = {}
            for scope in self.policy.iter_scopes(read=True):
                if scope == "env":
                    continue
                out[scope] = self._flatten(self.policy.get_store(scope))
            return out

    def _flatten(self, data: Mapping[KeyPath, str]) -> MutableMapping[str, str]:
        flat: MutableMapping[str, str] = {}
        for path, val in data.items():
            path = self._strip_prefix(path)
            if len(path) == 1:
                flat[path[0]] = val
            else:
                flat[f"{path[0]}{KEY_JOIN_CHAR}{KEY_JOIN_CHAR.join(path[1:])}"] = val
        return flat

    def list_keys(self, scope: str) -> list[KeyPath]:
        """Return all preference keys defined in *scope* sorted alphabetically."""
        data = self.policy.get_store(scope)
        return sorted(
            self._strip_prefix(k) for k in data if self._is_ours(k)
        )

    def get_pref(self, key: str | KeyPath, *, default: Any = None, cast: Callable[[str], Any] | None = None) -> Any:
        raw_path = parse_key(key)
        dotted = ".".join(raw_path)
        if dotted.startswith("secret."):
            val = self._secrets.get(dotted)
            if val is not None:
                return self._cast(val, cast)
        full_path = (self.app_name, *raw_path)
        with self._lock:
            order = self.policy.precedence(read=True)
            for scope in order:
                val = self._value_from_scope(scope, full_path)
                if val is not None:
                    return self._cast(val, cast)
        return default

    def _cast(self, value: str, cast: Callable[[str], Any] | None) -> Any:
        if cast is not None:
            return cast(value)
        lower = value.lower()
        if lower in {"true", "false"}:
            return lower == "true"
        for func in (int, float):
            try:
                return func(value)
            except ValueError:
                pass
        if value.startswith("[") or value.startswith("{"):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        return value

    # ----- typed helper getters -----

    def get_int(self, key: str, *, default: int | None = None) -> int | None:
        """Return an int preference or ``default``.

        ``TypeError`` is raised if the stored value cannot be interpreted as an
        integer.
        """
        val = self.get_pref(key)
        if val is None:
            return default
        if isinstance(val, int):
            return val
        if isinstance(val, float) and val.is_integer():
            return int(val)
        if isinstance(val, str):
            try:
                return int(float(val)) if "." in val else int(val)
            except ValueError:
                pass
        raise TypeError(f"Expected int for {key}")

    def get_float(self, key: str, *, default: float | None = None) -> float | None:
        """Return a float preference or ``default``."""
        val = self.get_pref(key)
        if val is None:
            return default
        if isinstance(val, int | float):
            return float(val)
        if isinstance(val, str):
            try:
                return float(val)
            except ValueError:
                pass
        raise TypeError(f"Expected float for {key}")

    def get_bool(self, key: str, *, default: bool | None = None) -> bool | None:
        """Return a boolean preference or ``default``."""
        val = self.get_pref(key)
        if val is None:
            return default
        if isinstance(val, bool):
            return val
        if isinstance(val, int) and val in {0, 1}:
            return bool(val)
        if isinstance(val, str):
            lower = val.lower()
            if lower in {"true", "1"}:
                return True
            if lower in {"false", "0"}:
                return False
        raise TypeError(f"Expected bool for {key}")

    # ----- export helpers -----

    def export_env(
        self,
        *,
        prefix: str = "SIGIL_",
        uppercase: bool = True,
        include_secrets: bool = False,
    ) -> dict[str, str]:
        """Return a mapping of environment variable names to values."""
        base = f"{prefix}{self.app_name.upper()}_"
        out: dict[str, str] = {}
        for path in sorted(self._merged):
            dotted = ".".join(path)
            if dotted.startswith("secret."):
                if not include_secrets:
                    continue
            val = self.get_pref(path)
            if val is None:
                continue
            env_key = base + KEY_JOIN_CHAR.join(path)
            if uppercase:
                env_key = env_key.upper()
            out[env_key] = str(val)
        return out

    def effective_scope_for(self, key: str | KeyPath) -> str:
        kp = parse_key(key)
        order = self.policy.precedence(read=True)
        with self._lock:
            for scope in order:
                if self._value_from_scope(scope, kp) is not None:
                    return scope
        return "none"

    def path_for_scope(self, scope: str) -> Path:
        """Return the path backing *scope*.

        This helper exposes the location that will be written to when a value
        is saved in the given *scope*.  It is primarily intended for user
        interfaces that need to communicate the write target clearly.
        """
        if scope not in self.policy.scopes:
            raise UnknownScopeError(scope)
        try:
            return self._paths[scope]
        except KeyError as exc:
            raise UnknownScopeError(scope) from exc

    def set_pref(self, key: str | KeyPath, value: Any, *, scope: str | None = None) -> None:
        target_scope = scope or self._default_scope
        if target_scope == "core":
            raise ReadOnlyScopeError("Core defaults are read-only")
        if target_scope == "default" and not self._defaults_writable:
            raise ReadOnlyScopeError("Default scope is read-only")
        raw_path = parse_key(key)
        if raw_path and raw_path[0] == "secret":
            if not self._secrets.can_write():
                raise SigilWriteError("Secrets backend is read-only or locked")
            self._secrets.set(".".join(raw_path), str(value))
            return
        full_path = (self.app_name, *raw_path)
        data, path_file = self._get_scope_storage(target_scope)
        with self._lock:
            if value is None:
                data.pop(full_path, None)
            else:
                data[full_path] = str(value)
            backend = _backend_for(path_file)
            backend.save(path_file, data)
            self.invalidate_cache()

    def _get_scope_storage(self, scope: str) -> tuple[MutableMapping[KeyPath, str], Path]:
        if scope == "user":
            return self._user, self.user_path
        if scope == "user-local":
            return self._user_local, self.user_local_path
        if scope == "project":
            return self._project, self.project_path
        if scope == "project-local":
            return self._project_local, self.project_local_path
        if scope == "default" and self._defaults_writable and self.default_path is not None:
            return self._defaults, self.default_path
        raise UnknownScopeError(scope)

    @contextmanager
    def project(self, path: Path):
        new_path = Path(path)
        if new_path.suffix == "" or new_path.name != self.settings_filename:
            new_path = new_path / self.settings_filename

        old_project = self.project_path
        old_project_local = self.project_local_path
        old_default = self._default_scope

        self.project_path = new_path
        self.project_local_path = new_path.parent / f"settings-local-{self._host}.ini"
        self._paths["project"] = self.project_path
        self._paths["project-local"] = self.project_local_path
        self._default_scope = "project"
        self.invalidate_cache()
        try:
            yield self
        finally:
            self.project_path = old_project
            self.project_local_path = old_project_local
            self._paths["project"] = self.project_path
            self._paths["project-local"] = self.project_local_path
            self._default_scope = old_default
            self.invalidate_cache()
