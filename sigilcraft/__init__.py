"""Sigil preference manager."""
from __future__ import annotations

from .core import Sigil
from .helpers import make_package_prefs
from .keys import KeyPath, parse_key

__all__ = [
    "Sigil",
    "make_package_prefs",
    "get_int",
    "get_float",
    "get_bool",
    "parse_key",
    "KeyPath",
]
__version__ = "0.1.1"


def get_int(key: str, *, app: str, default: int | None = None) -> int | None:
    """Return typed integer preference for ``app``."""
    return Sigil(app).get_int(key, default=default)


def get_float(key: str, *, app: str, default: float | None = None) -> float | None:
    """Return typed float preference for ``app``."""
    return Sigil(app).get_float(key, default=default)


def get_bool(key: str, *, app: str, default: bool | None = None) -> bool | None:
    """Return typed boolean preference for ``app``."""
    return Sigil(app).get_bool(key, default=default)
