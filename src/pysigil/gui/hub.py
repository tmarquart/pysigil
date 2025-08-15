from __future__ import annotations

from collections.abc import Callable

from ..core import Sigil
from ..discovery import pep503_name

_instances: dict[str, Sigil] = {}


def get_preferences(package: str) -> tuple[Callable[..., object], Callable[..., object], Sigil]:
    provider = pep503_name(package)
    sig = _instances.get(provider)
    if sig is None:
        sig = Sigil(provider)
        _instances[provider] = sig
    return sig.get_pref, sig.set_pref, sig


__all__ = ["get_preferences", "_instances"]
