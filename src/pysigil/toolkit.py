from __future__ import annotations

from typing import Any, Callable

from .core import Sigil

__all__ = ["helpers_for"]


def helpers_for(app_name: str) -> tuple[Callable[..., Any], Callable[..., None]]:
    """Return setting helpers bound to *app_name*.

    The returned ``get_setting`` and ``set_setting`` functions operate on a
    dedicated :class:`Sigil` instance for the provided application name.
    """

    sigil = Sigil(app_name)

    def get_setting(
        key: str,
        *,
        cast: Callable[[str], Any] | None = None,
        default: Any | None = None,
    ) -> Any:
        return sigil.get_pref(key, cast=cast, default=default)

    def set_setting(
        key: str,
        value: Any,
        *,
        scope: str | None = None,
    ) -> None:
        sigil.set_pref(key, value, scope=scope)

    return get_setting, set_setting
