from __future__ import annotations

import inspect
import importlib
import tomllib
from pathlib import Path
from threading import Lock
from typing import Callable

from .core import Sigil

__all__ = ["get_preferences"]

_configs: dict[str, tuple[Path, Path | None]] = {}
_instances: dict[str, Sigil] = {}
_lock = Lock()


def _find_pyproject(start: Path) -> Path | None:
    path = start
    while True:
        candidate = path / "pyproject.toml"
        if candidate.exists():
            return candidate
        if path.parent == path:
            return None
        path = path.parent


def _load_config(package: str) -> tuple[Path, Path | None]:
    if package in _configs:
        return _configs[package]
    module = importlib.import_module(package)
    start = Path(module.__file__).resolve().parent
    pyproject = _find_pyproject(start)
    defaults_rel = Path("prefs/defaults.ini")
    meta_rel: Path | None = None
    base = start
    if pyproject:
        base = pyproject.parent
        try:
            with pyproject.open("rb") as fh:
                data = tomllib.load(fh)
            section = data.get("tool", {}).get("sigil", {})
            if isinstance(section, dict):
                if "defaults" in section:
                    defaults_rel = Path(section["defaults"])
                if "meta" in section:
                    meta_rel = Path(section["meta"])
        except Exception:
            pass
    defaults_path = defaults_rel if defaults_rel.is_absolute() else base / defaults_rel
    meta_path = None
    if meta_rel is not None:
        meta_path = meta_rel if meta_rel.is_absolute() else base / meta_rel
    _configs[package] = (defaults_path, meta_path)
    return defaults_path, meta_path


def get_preferences(package: str | None = None) -> tuple[Callable, Callable]:
    if package is None:
        frame = inspect.stack()[1].frame
        package = frame.f_globals.get("__name__")
        del frame
        if not isinstance(package, str) or not package:
            raise ValueError("Could not determine caller package; pass package")

    def _lazy() -> Sigil:
        if package not in _instances:
            with _lock:
                if package not in _instances:
                    defaults_path, meta_path = _load_config(package)
                    _instances[package] = Sigil(
                        package, default_path=defaults_path, meta_path=meta_path
                    )
        return _instances[package]

    def get_pref(key: str, *, default=None, cast=None):
        return _lazy().get_pref(key, default=default, cast=cast)

    def set_pref(key: str, value, *, scope="user"):
        return _lazy().set_pref(key, value, scope=scope)

    return get_pref, set_pref
