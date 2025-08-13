from __future__ import annotations

import json
import logging
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any

from .errors import (
    ReadOnlyScopeError,
    SigilError,
    SigilLoadError,
    SigilMetaError,
    SigilSecretsError,
    SigilWriteError,
    UnknownScopeError,
)
from .io_config import user_config_dir
from .merge_policy import CORE_DEFAULTS, KeyPath, parse_key, read_env
from .resolver import ProjectRootNotFoundError, project_settings_file
from .secrets import (
    EncryptedFileProvider,
    EnvSecretProvider,
    KeyringProvider,
    SecretChain,
    SecretProvider,
)


def _backend_for(path: Path):
    from .backends import get_backend_for_path

    return get_backend_for_path(path)

logger = logging.getLogger("pysigil")

KEY_JOIN_CHAR = "_"


PRECEDENCE_USER_WINS = ("env", "user", "project", "default", "core")
PRECEDENCE_PROJECT_WINS = ("env", "project", "user", "default", "core")


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
        settings_filename='settings.ini'
    ) -> None:
        self.app_name = app_name
        self.settings_filename = settings_filename

        self.user_path = (
            Path(user_scope)
            if user_scope
            else Path(user_config_dir("sigil"), self.app_name)
        )
        if self.user_path.suffix == "" or self.user_path.name != self.settings_filename:
            self.user_path = self.user_path / self.settings_filename

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

        self.default_path = Path(default_path) if default_path else None
        if self.default_path is not None:
            if self.default_path.suffix == "" or self.default_path.name != self.settings_filename:
                self.default_path = self.default_path / self.settings_filename

        self._defaults: MutableMapping[KeyPath, str] = {}
        if defaults:
            for k, v in defaults.items():
                self._defaults[parse_key(k)] = str(v)
        self._env_reader = env_reader
        self._lock = RLock()
        self._default_scope = "user"
        enc_path = self.default_path.with_suffix(".enc.json") if self.default_path else None
        if secrets is None:
            providers = [
                KeyringProvider(),
                EncryptedFileProvider(enc_path, prompt=False, required=False),
                EnvSecretProvider(app_name),
            ]
            self._secrets = SecretChain(providers)
        else:
            self._secrets = SecretChain(secrets)
        self._core: MutableMapping[KeyPath, str] = {}
        for section, mapping in CORE_DEFAULTS.items():
            for k, v in mapping.items():
                self._core[parse_key(f"{section}.{k}")] = str(v)
        self.invalidate_cache()

    @property
    def default_scope(self) -> str:
        """Return the current default scope for writes."""
        return self._default_scope

    def set_default_scope(self, scope: str) -> None:
        """Set the default scope for writes.

        Only ``"user"``, ``"project"`` and ``"default"`` scopes are supported.
        ``"default"`` requires ``default_path`` to be configured.
        """
        if scope == "default" and self.default_path is None:
            raise UnknownScopeError(scope)
        if scope not in {"user", "project", "default"}:
            raise UnknownScopeError(scope)
        self._default_scope = scope

    def invalidate_cache(self) -> None:
        with self._lock:
            self._env = dict(self._env_reader(self.app_name))
            user_backend = _backend_for(self.user_path)
            project_backend = _backend_for(self.project_path)
            self._user = user_backend.load(self.user_path)
            self._project = project_backend.load(self.project_path)
            if self.default_path is not None:
                default_backend = _backend_for(self.default_path)
                self._defaults = default_backend.load(self.default_path)
            self._merge_cache()

    def _merge_cache(self) -> None:
        self._merged = {}
        self._merged.update(self._core)
        self._merged.update(self._defaults)
        self._merged.update(self._user)
        self._merged.update(self._project)
        self._merged.update(self._env)

    def _order_for(self, keypath: KeyPath) -> tuple[str, ...]:
        return PRECEDENCE_PROJECT_WINS

    def _value_from_scope(self, scope: str, key: KeyPath) -> str | None:
        if scope == "env":
            return self._env.get(key)
        return self._get_scope_dict(scope).get(key)

    def scoped_values(self) -> Mapping[str, MutableMapping[str, str]]:
        """Return all known preferences grouped by scope.

        The returned mapping contains ``"default"``, ``"user"`` and ``"project"``
        keys, each mapping to a flat dictionary of preference keys to values.
        """
        with self._lock:
            core_flat = self._flatten(self._core)
            default_flat = self._flatten(self._defaults)
            user_flat = self._flatten(self._user)
            project_flat = self._flatten(self._project)
            return {
                "core": core_flat,
                "default": default_flat,
                "user": user_flat,
                "project": project_flat,
            }

    def _flatten(self, data: Mapping[KeyPath, str]) -> MutableMapping[str, str]:
        flat: MutableMapping[str, str] = {}
        for path, val in data.items():
            if len(path) == 1:
                flat[path[0]] = val
            else:
                flat[f"{path[0]}{KEY_JOIN_CHAR}{KEY_JOIN_CHAR.join(path[1:])}"] = val
        return flat

    def list_keys(self, scope: str) -> list[KeyPath]:
        """Return all preference keys defined in *scope* sorted alphabetically."""
        data = self._get_scope_dict(scope)
        return sorted(data)

    def _get_scope_dict(self, scope: str) -> MutableMapping[KeyPath, str]:
        if scope == "user":
            return self._user
        if scope == "project":
            return self._project
        if scope == "default":
            return self._defaults
        if scope == "core":
            return self._core
        raise UnknownScopeError(scope)

    def get_pref(self, key: str | KeyPath, *, default: Any = None, cast: Callable[[str], Any] | None = None) -> Any:
        path = parse_key(key)
        dotted = ".".join(path)
        if dotted.startswith("secret."):
            val = self._secrets.get(dotted)
            if val is not None:
                return self._cast(val, cast)
        with self._lock:
            order = self._order_for(path)
            for scope in order:
                val = self._value_from_scope(scope, path)
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
        order = self._order_for(kp)
        with self._lock:
            for scope in order:
                if self._value_from_scope(scope, kp) is not None:
                    return scope
        return "none"

    def set_pref(self, key: str | KeyPath, value: Any, *, scope: str | None = None) -> None:
        target_scope = scope or self._default_scope
        if target_scope == "core":
            raise ReadOnlyScopeError("Core defaults are read-only")
        path = parse_key(key)
        dotted = ".".join(path)
        if dotted.startswith("secret."):
            if not self._secrets.can_write():
                raise SigilWriteError("Secrets backend is read-only or locked")
            self._secrets.set(dotted, str(value))
            return
        data, path_file = self._get_scope_storage(target_scope)
        with self._lock:
            if value is None:
                data.pop(path, None)
            else:
                data[path] = str(value)
            backend = _backend_for(path_file)
            backend.save(path_file, data)
            self.invalidate_cache()

    def _get_scope_storage(self, scope: str) -> tuple[MutableMapping[KeyPath, str], Path]:
        if scope == "user":
            return self._user, self.user_path
        if scope == "project":
            return self._project, self.project_path
        if scope == "default" and self.default_path is not None:
            return self._defaults, self.default_path
        raise UnknownScopeError(scope)

    @contextmanager
    def project(self, path: Path):
        old_path = self.project_path
        old_default = self._default_scope
        self.project_path = path
        self._default_scope = "project"
        try:
            yield self
        finally:
            self.project_path = old_path
            self._default_scope = old_default
            self.invalidate_cache()
