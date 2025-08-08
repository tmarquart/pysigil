"""Simple pub-sub event helper for Sigil GUI."""
from __future__ import annotations

from collections.abc import Callable

_callbacks: dict[str, list[Callable]] = {}


def on(event: str, fn: Callable) -> None:
    """Register *fn* to be called when *event* is emitted."""
    _callbacks.setdefault(event, []).append(fn)


def emit(event: str, *args, **kwargs) -> None:
    """Emit *event*, calling all subscribed callbacks."""
    for fn in _callbacks.get(event, []):
        fn(*args, **kwargs)
