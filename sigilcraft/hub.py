from __future__ import annotations

import inspect
import importlib
import tomllib
import threading
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Protocol, runtime_checkable
#from pyprojroot import here

from .core import Sigil

__all__ = ["get_preferences"]

_configs: dict[str, tuple[Path, Path | None]] = {}
_instances: dict[str, Sigil] = {}
_lock = Lock()

# ---------------------------------------------------------------------------
# 1.  Types that preserve the signatures of the callables we return
# ---------------------------------------------------------------------------

@runtime_checkable
class GetPref(Protocol):
    def __call__(
        self,
        key: str,
        *,
        default: Any | None = None,
        cast: Callable[[Any], Any] | None = None,
    ) -> Any: ...

@runtime_checkable
class SetPref(Protocol):
    def __call__(self, key: str, value: Any, *, scope: str = "user") -> Any: ...

# ---------------------------------------------------------------------------
# 2.  Internal helpers
# ---------------------------------------------------------------------------

_lock: threading.Lock = threading.Lock()
_instances: dict[str | None, "Sigil"] = {}


def _find_project_root(start: Path) -> Path:
    """Walk up from *start* until a directory with pyproject.toml or setup.py is found."""
    for parent in (start, *start.parents):
        if (parent / "pyproject.toml").is_file() or (parent / "setup.py").is_file():
            return parent
    raise FileNotFoundError(
        "Could not locate project root containing pyproject.toml or setup.py"
    )


def _load_config(
    package: str | None,
    default_pref_directory: str | None,
    settings_filename: str,
) -> tuple[Path, Path | None]:
    # ------------------------------------------------------------------
    # Determine defaults_path (= prefs folder) and metadata path.
    # ------------------------------------------------------------------
    if package:
        # Import the package and look at its __file__.
        mod = __import__(package)
        caller_path = Path(mod.__file__).resolve()
    else:
        # Use the frame of the caller two levels up (user code → wrapper → here).
        caller_path = Path(inspect.stack()[2].filename).resolve()

    project_root = _find_project_root(caller_path)
    prefs_dir = (
        Path(default_pref_directory)
        if default_pref_directory is not None
        else project_root / "prefs"
    )
    defaults_path = prefs_dir / settings_filename

    # Allow optional metadata sidecar (JSON or CSV) but don't require it.
    meta_json = prefs_dir / "metadata.json"
    meta_csv = prefs_dir / "metadata.csv"
    meta_path = meta_json if meta_json.exists() else (meta_csv if meta_csv.exists() else None)

    return defaults_path, meta_path


# ---------------------------------------------------------------------------
# 3.  Public factory
# ---------------------------------------------------------------------------

def get_preferences(
    package: str | None = None,
    *,
    default_pref_directory: str | None = None,
    settings_filename: str = "settings.ini",
) -> tuple[GetPref, SetPref]:
    """
    Resolve and cache a Sigil instance for *package* and return two thin
    wrappers: `get_pref` and `set_pref`.

    Parameters
    ----------
    package
        Import-name of the package that owns the preferences, or None to infer
        from the caller’s file location.
    default_pref_directory
        Override for the directory that contains defaults + metadata.  If None,
        we use <project-root>/prefs.
    settings_filename
        Name of the defaults file inside *default_pref_directory*.  Default: 'settings.ini'.
    """

    def _lazy() -> "Sigil":
        if package not in _instances:
            with _lock:
                if package not in _instances:
                    defaults_path, meta_path = _load_config(
                        package, default_pref_directory, settings_filename
                    )
                    _instances[package] = Sigil(  # type: ignore[name-defined]
                        app_name=package,
                        default_path=defaults_path,
                        meta_path=meta_path,
                        settings_filename=settings_filename,
                    )
        return _instances[package]

    # --- Thin, type-safe wrappers ------------------------------------
    def get_pref(
        key: str,
        *,
        default: Any | None = None,
        cast: Callable[[Any], Any] | None = None,
    ) -> Any:
        return _lazy().get_pref(key, default=default, cast=cast)

    def set_pref(key: str, value: Any, *, scope: str = "user") -> Any:
        return _lazy().set_pref(key, value, scope=scope)

    return get_pref, set_pref


# def _find_pyproject(start: Path) -> Path | None:
#     path = start
#     while True:
#         candidate = path / "pyproject.toml"
#         if candidate.exists():
#             return candidate
#         if path.parent == path:
#             return None
#         path = path.parent
#
#
# def _load_config(package: str) -> tuple[Path, Path | None]:
#     if package in _configs:
#         return _configs[package]
#     module = importlib.import_module(package)
#     start = Path(module.__file__).resolve().parent
#     pyproject = _find_pyproject(start)
#     defaults_rel = Path("prefs/defaults.ini")
#     meta_rel: Path | None = None
#     base = start
#     if pyproject:
#         base = pyproject.parent
#         try:
#             with pyproject.open("rb") as fh:
#                 data = tomllib.load(fh)
#             section = data.get("tool", {}).get("sigil", {})
#             if isinstance(section, dict):
#                 if "defaults" in section:
#                     defaults_rel = Path(section["defaults"])
#                 if "meta" in section:
#                     meta_rel = Path(section["meta"])
#         except Exception:
#             pass
#     defaults_path = defaults_rel if defaults_rel.is_absolute() else base / defaults_rel
#     meta_path = None
#     if meta_rel is not None:
#         meta_path = meta_rel if meta_rel.is_absolute() else base / meta_rel
#     _configs[package] = (defaults_path, meta_path)
#     return defaults_path, meta_path
#
# def package_setup(package_name,default_pref_directory='prefs',pref_file_name='settings.ini'):
#     def get_pref(key: str, *, default=None, cast=None):
#         return get_pref(key, default=default, cast=cast)
#
#     def set_pref(key: str, value, *, scope="user"):
#         return set_pref(key, value, scope=scope)
#
#     return get_pref, set_pref
#
# def get_preferences(package: str | None = None,default_pref_directory=None,settings_filename='settings.ini') -> tuple[Callable, Callable]:
#
#     # if package is None:
#     #     frame = inspect.stack()[1]
#     #     mod = inspect.getmodule(frame[0])
#     #     if not mod or not mod.__package__:
#     #         raise RuntimeError("Cannot infer package name automatically, please define.")
#     #     package  = mod.__package__
#
#     # if package is None:
#     #     print(inspect.stack())
#     #     frame = inspect.stack()[1].frame
#     #     package = frame.f_globals.get("__name__")
#     #     del frame
#     #     if not isinstance(package, str) or not package:
#     #         raise ValueError("Could not determine caller package; pass package")
#
#     def _lazy() -> Sigil:
#         if package not in _instances:
#             with _lock:
#                 if package not in _instances:
#                     defaults_path, meta_path = _load_config(package)
#                     _instances[package] = Sigil(
#                         package, default_path=default_pref_directory, meta_path=meta_path,settings_filename=settings_filename
#                     )
#         return _instances[package]
#
#     def get_pref(key: str, *, default=None, cast=None):
#         return _lazy().get_pref(key, default=default, cast=cast)
#
#     def set_pref(key: str, value, *, scope="user"):
#         return _lazy().set_pref(key, value, scope=scope)
#
#     return get_pref, set_pref
#
# # hub.py
# _registry = {}            # filled during discovery
#
# def get_manifest(pkg_name: str) -> dict | None:
#     """Return the raw manifest dict Sigil stored for a package."""
#     return _registry.get(pkg_name)
