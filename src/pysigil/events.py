from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

_handlers: defaultdict[str, list[Callable[..., Any]]] = defaultdict(list)


def on(event: str, callback: Callable[..., Any]) -> None:
    _handlers[event].append(callback)


def emit(event: str, *args: Any, **kwargs: Any) -> None:
    for callback in list(_handlers.get(event, [])):
        callback(*args, **kwargs)


__all__ = ["on", "emit"]
