from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Mapping, MutableMapping, Sequence

try:
    from appdirs import user_config_dir
except ModuleNotFoundError:
    from ._appdirs_stub import user_config_dir

from .backend import get_backend_for_path
from .env import read_env
from .errors import UnknownScopeError, SigilWriteError
from .secrets import (
    SecretChain,
    SecretProvider,
    KeyringProvider,
    EncryptedFileProvider,
    EnvSecretProvider,
)

logger = logging.getLogger("sigil")


class Sigil:
    def __init__(
        self,
        app_name: str,
        *,
        user_scope: Path | None = None,
        project_scope: Path | None = None,
        defaults: Mapping[str, Any] | None = None,
        default_path: Path | None = None,
        env_reader: Callable[[str], Mapping[str, str]] = read_env,
        secrets: Sequence[SecretProvider] | None = None,
        meta_path: Path | None = None,
    ) -> None:
        self.app_name = app_name
        self.user_path = Path(user_scope) if user_scope else Path(user_config_dir(app_name)) / "settings.ini"
        self.project_path = Path(project_scope) if project_scope else Path.cwd() / "settings.ini"
        defaults_map: MutableMapping[str, Any] = {}
        if default_path is not None:
            backend = get_backend_for_path(Path(default_path))
            loaded = backend.load(Path(default_path))
            for section, values in loaded.items():
                for key, value in values.items():
                    if section == "global":
                        defaults_map[key] = value
                    else:
                        defaults_map[f"{section}.{key}"] = value
        if defaults:
            defaults_map.update(defaults)
        self._defaults_flat = self._ensure_flat(defaults_map)
        self._env_reader = env_reader
        self._lock = RLock()
        self._default_scope = "user"
        self._meta = {}
        mpath = meta_path or self.user_path.parent / "defaults.meta.csv"
        try:
            from .helpers import load_meta

            if mpath.exists():
                self._meta = load_meta(mpath)
        except Exception as exc:  # pragma: no cover - malformed meta
            logger.error("Failed to load metadata: %s", exc)
        enc_path = default_path.with_suffix(".enc.json") if default_path else None
        if secrets is None:
            providers = [
                KeyringProvider(),
                EncryptedFileProvider(enc_path, prompt=False, required=False),
                EnvSecretProvider(app_name),
            ]
            self._secrets = SecretChain(providers)
        else:
            self._secrets = SecretChain(secrets)
        self.invalidate_cache()

    def _ensure_flat(self, data: Mapping[str, Any]) -> MutableMapping[str, str]:
        flat: MutableMapping[str, str] = {}
        for key, value in data.items():
            flat[key] = str(value)
        return flat

    def invalidate_cache(self) -> None:
        with self._lock:
            self._env = dict(self._env_reader(self.app_name))
            user_backend = get_backend_for_path(self.user_path)
            project_backend = get_backend_for_path(self.project_path)
            self._user = user_backend.load(self.user_path)
            self._project = project_backend.load(self.project_path)
            self._merge_cache()

    def _merge_cache(self) -> None:
        self._merged = {}
        self._merged.update(self._defaults_flat)
        self._merged.update(self._flatten(self._user))
        self._merged.update(self._flatten(self._project))
        self._merged.update(self._env)

    def _flatten(self, data: Mapping[str, Mapping[str, str]]) -> MutableMapping[str, str]:
        flat: MutableMapping[str, str] = {}
        for section, values in data.items():
            for key, value in values.items():
                if section == "global":
                    flat[key] = value
                else:
                    flat[f"{section}.{key}"] = value
        return flat

    def _split(self, key: str) -> tuple[str, str]:
        if "." in key:
            section, k = key.split(".", 1)
        else:
            section, k = "global", key
        return section, k

    def _meta_secret(self, key: str) -> bool:
        return bool(self._meta.get(key, {}).get("secret"))

    def get_pref(self, key: str, *, default: Any = None, cast: Callable[[str], Any] | None = None) -> Any:
        if key.startswith("secret.") or self._meta_secret(key):
            val = self._secrets.get(key)
            if val is not None:
                return self._cast(val, cast)
        with self._lock:
            value = self._merged.get(key)
        if value is None:
            return default
        return self._cast(value, cast)

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

    def set_pref(self, key: str, value: Any, *, scope: str | None = None) -> None:
        if key.startswith("secret.") or self._meta_secret(key):
            if not self._secrets.can_write():
                raise SigilWriteError("Secrets backend is read-only or locked")
            self._secrets.set(key, str(value))
            return
        target_scope = scope or self._default_scope
        if target_scope not in {"user", "project"}:
            raise UnknownScopeError(target_scope)
        section, k = self._split(key)
        with self._lock:
            data = getattr(self, f"_{target_scope}")
            sec = data.setdefault(section, {})
            sec[k] = str(value)
            path = getattr(self, f"{target_scope}_path")
            backend = get_backend_for_path(path)
            backend.save(path, data)
            self.invalidate_cache()

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
