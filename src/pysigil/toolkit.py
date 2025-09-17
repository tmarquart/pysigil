from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .authoring import normalize_provider_id
from .core import Sigil
from .discovery import pep503_name
from .paths import project_data_dir, user_data_dir

__all__ = ["helpers_for", "get_project_directory", "get_user_directory"]


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


def _normalise_app_name(app_name: str) -> str:
    try:
        normalize_provider_id(app_name)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"invalid application name: {app_name!r}") from exc
    return pep503_name(app_name)


def get_project_directory(

    *, start: str | Path | None = None, **kwargs: Any
) -> Path:
    """Return the shared project data directory.

    The directory lives under ``<project-root>/.sigil/data`` and is created if
    necessary. ``start`` and ``**kwargs`` are forwarded to
    :func:`pysigil.paths.project_data_dir` for custom root resolution.
    """

    path = project_data_dir(start=start, **kwargs).resolve()

    path.mkdir(parents=True, exist_ok=True)
    return path


def get_user_directory(app_name: str) -> Path:
    """Return the user data directory for ``app_name``.

    The directory lives under the platform-specific user data root and is
    created if necessary.
    """

    app = _normalise_app_name(app_name)
    path = user_data_dir(app)
    path.mkdir(parents=True, exist_ok=True)
    return path
