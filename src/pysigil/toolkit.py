from __future__ import annotations

from typing import Any, Callable

from .core import Sigil
from .discovery import pep503_name

__all__ = ["init", "get_setting", "set_setting"]

_cache: dict[str, Sigil] = {}
_current: str | None = None


def init(app_name: str) -> Sigil:
    """Initialise and cache a :class:`Sigil` instance for *app_name*.

    Repeated calls for the same application return the cached instance and
    switch the active application used by :func:`get_setting` and
    :func:`set_setting`.
    """
    global _current
    name = pep503_name(app_name)
    _current = name
    try:
        return _cache[name]
    except KeyError:
        sigil = Sigil(app_name)
        _cache[name] = sigil
        return sigil


def _current_sigil() -> Sigil:
    if _current is None:
        raise RuntimeError("call init(app_name) before accessing settings")
    return _cache[_current]


def get_setting(
    key: str,
    *,
    cast: Callable[[str], Any] | None = None,
    default: Any | None = None,
) -> Any:
    """Return the value for *key* from the active application."""
    return _current_sigil().get_pref(key, cast=cast, default=default)


def set_setting(
    key: str,
    value: Any,
    *,
    scope: str | None = None,
) -> None:
    """Set *key* to *value* in the active application."""
    _current_sigil().set_pref(key, value, scope=scope)
