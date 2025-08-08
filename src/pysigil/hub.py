from __future__ import annotations

import inspect
import threading
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Protocol, runtime_checkable
#from pyprojroot import here

from .core import Sigil
from .keys import KeyPath, parse_key

__all__ = ["get_preferences", "parse_key"]

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


@runtime_checkable
class LaunchGui(Protocol):
    def __call__(self) -> None: ...

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
    # Determine defaults directory and optional metadata sidecar.
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
    defaults_dir = prefs_dir

    # Allow optional metadata sidecar (JSON or CSV) but don't require it.
    meta_json = prefs_dir / "metadata.json"
    meta_csv = prefs_dir / "metadata.csv"
    meta_path = meta_json if meta_json.exists() else (meta_csv if meta_csv.exists() else None)

    return defaults_dir, meta_path


# ---------------------------------------------------------------------------
# 3.  Public factory
# ---------------------------------------------------------------------------

def get_preferences(
    package: str | None = None,
    *,
    default_pref_directory: str | None = None,
    settings_filename: str = "settings.ini",
) -> tuple[GetPref, SetPref, LaunchGui]:
    """
    Resolve and cache a Sigil instance for *package* and return three thin
    wrappers: `get_pref`, `set_pref`, and `launch_gui`.

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
                    defaults_dir, meta_path = _load_config(
                        package, default_pref_directory, settings_filename
                    )
                    _instances[package] = Sigil(  # type: ignore[name-defined]
                        app_name=package,
                        default_path=defaults_dir,
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

    def effective_scope_for(key: str | KeyPath) -> str:
        return _lazy().effective_scope_for(key)

    def launch_gui() -> None:
        """Launch a preferences GUI configured for this package."""
        from .gui import launch_gui as _launch

        sigil = _lazy()
        # Pass the resolved Sigil instance so that the editor reflects the
        # caller's package-specific defaults and metadata.
        _launch(sigil=sigil)

    return get_pref, set_pref, effective_scope_for, launch_gui
