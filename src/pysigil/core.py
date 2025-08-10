from __future__ import annotations

import json
import logging
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path
from threading import RLock
from typing import Any

try:
    from appdirs import user_config_dir
except ModuleNotFoundError:
    from ._appdirs_stub import user_config_dir

from . import events, metadata
from .backends import get_backend_for_path
from .constants import KEY_JOIN_CHAR
from .env import read_env
from .errors import ReadOnlyScopeError, SigilWriteError, UnknownScopeError
from .keys import KeyPath, parse_key
from .secrets import (
    EncryptedFileProvider,
    EnvSecretProvider,
    KeyringProvider,
    SecretChain,
    SecretProvider,
)

logger = logging.getLogger("pysigil")


_core_cache: MutableMapping[KeyPath, str] | None = None


PRECEDENCE_USER_WINS = ("env", "user", "project", "default", "core")
PRECEDENCE_PROJECT_WINS = ("env", "project", "user", "default", "core")


class LockedPreferenceError(RuntimeError):
    """Raised when attempting to modify a locked preference."""


def _load_core_defaults() -> MutableMapping[KeyPath, str]:
    global _core_cache
    if _core_cache is not None:
        return _core_cache
    try:
        path = files("pysigil.resources") / "core_defaults.ini"
        backend = get_backend_for_path(Path(path))
        _core_cache = backend.load(Path(path))
    except Exception as exc:  # pragma: no cover - missing or malformed file
        logger.warning("Failed to load core defaults: %s", exc)
        _core_cache = {}
    return _core_cache


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
        meta_path: Path | None = None,
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

        self.project_path = Path(project_scope) if project_scope else Path.cwd()
        if self.project_path.suffix == "" or self.project_path.name != self.settings_filename:
            self.project_path = self.project_path / self.settings_filename

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
        mpath = meta_path or self.user_path.parent / "defaults.meta.csv"
        try:
            metadata.load(mpath if mpath.exists() else None)
        except Exception as exc:  # pragma: no cover - malformed meta
            logger.error("Failed to load metadata: %s", exc)
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
        self._core = _load_core_defaults()
        self.invalidate_cache()
        # Patch helpers to access preferences at runtime (no-op currently)

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
            user_backend = get_backend_for_path(self.user_path)
            project_backend = get_backend_for_path(self.project_path)
            self._user = user_backend.load(self.user_path)
            self._project = project_backend.load(self.project_path)
            if self.default_path is not None:
                default_backend = get_backend_for_path(self.default_path)
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
        meta = metadata.get_meta_for(keypath)
        return (
            PRECEDENCE_USER_WINS
            if meta.get("policy") == "user_over_project"
            else PRECEDENCE_PROJECT_WINS
        )

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

    def _meta_secret(self, key: KeyPath) -> bool:
        return bool(metadata.get_meta_for(key).get("secret"))

    def get_pref(self, key: str | KeyPath, *, default: Any = None, cast: Callable[[str], Any] | None = None) -> Any:
        path = parse_key(key)
        dotted = ".".join(path)
        if dotted.startswith("secret.") or self._meta_secret(path):
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
            if dotted.startswith("secret.") or self._meta_secret(path):
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
        meta = metadata.get_meta_for(path)
        if (
            target_scope == "user"
            and meta.get("locked")
            and meta.get("policy") != "user_over_project"
        ):
            raise LockedPreferenceError(
                f"{KEY_JOIN_CHAR.join(path)} is project-controlled and locked."
            )
        dotted = ".".join(path)
        event_key = KEY_JOIN_CHAR.join(path)
        if dotted.startswith("secret.") or self._meta_secret(path):
            if not self._secrets.can_write():
                raise SigilWriteError("Secrets backend is read-only or locked")
            self._secrets.set(dotted, str(value))
            events.emit("pref_changed", event_key, value, scope or self._default_scope)
            return
        data, path_file = self._get_scope_storage(target_scope)
        with self._lock:
            if value is None:
                data.pop(path, None)
            else:
                data[path] = str(value)
            backend = get_backend_for_path(path_file)
            backend.save(path_file, data)
            self.invalidate_cache()
        events.emit("pref_changed", event_key, value, target_scope)

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
