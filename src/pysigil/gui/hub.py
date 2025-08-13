from __future__ import annotations

from collections.abc import Callable

from ..core import Sigil

_instances: dict[str, Sigil] = {}


def get_preferences(package: str) -> tuple[Callable[..., object], Callable[..., object], Sigil]:
    sig = _instances.get(package)
    if sig is None:
        sig = Sigil(package)
        _instances[package] = sig
    return sig.get_pref, sig.set_pref, sig


__all__ = ["get_preferences", "_instances"]
