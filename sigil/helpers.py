from __future__ import annotations

from importlib import resources
import inspect
from pathlib import Path
from threading import Lock
from typing import Callable

from .core import Sigil


def make_package_prefs(
    *,
    app_name: str,
    package: str | None = None,
    defaults_rel: str = "prefs/defaults.ini",
) -> tuple[Callable, Callable]:
    """Return (get_pref, set_pref) callables wired to package defaults.

    If ``package`` is omitted, the caller's module name is used.
    """

    if package is None:
        frame = inspect.stack()[1].frame
        package = frame.f_globals.get("__name__")
        del frame
        if not isinstance(package, str) or not package:
            raise ValueError("Could not determine caller package; pass 'package'")
    lock = Lock()
    sigil_obj: Sigil | None = None
    defaults_path: Path = resources.files(package).joinpath(defaults_rel)

    def _lazy() -> Sigil:
        nonlocal sigil_obj
        if sigil_obj is None:
            with lock:
                if sigil_obj is None:
                    sigil_obj = Sigil(app_name, default_path=defaults_path)
        return sigil_obj

    def _get(key: str, *, default=None, cast=None):
        return _lazy().get_pref(key, default=default, cast=cast)

    def _set(key: str, value, *, scope="user"):
        return _lazy().set_pref(key, value, scope=scope)

    return _get, _set
