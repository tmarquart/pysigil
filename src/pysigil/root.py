from __future__ import annotations

from pathlib import Path
from typing import Iterable

try:  # pragma: no cover - optional dependency
    from pyprojroot import here
except Exception:  # pragma: no cover - fallback
    here = None  # type: ignore[assignment]


class ProjectRootNotFoundError(RuntimeError):
    """Raised when no project root can be located."""


def _scan_for_markers(start: Path, markers: Iterable[str]) -> Path | None:
    for path in [start, *start.parents]:
        for marker in markers:
            if (path / marker).exists():
                return path
    return None


def find_project_root(
    start: str | Path | None = None,
    *,
    strict: bool = True,
    allow_ide: bool = False,  # reserved for future use
) -> Path:
    """Return the nearest project root.

    The search prefers :mod:`pyprojroot` when available and falls back to
    scanning upwards from ``start`` for a ``pyproject.toml`` file or ``.git``
    directory.  ``strict=False`` returns the starting path when no root is
    found instead of raising :class:`ProjectRootNotFoundError`.
    """

    if start is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start).expanduser().resolve()

    # Try pyprojroot if present when no start is given
    if start is None and here is not None:  # pragma: no branch - simple guard
        try:
            return Path(here()).resolve()
        except Exception:
            pass

    markers = ["pyproject.toml", ".git"]
    root = _scan_for_markers(start_path, markers)
    if root is not None:
        return root

    if strict:
        raise ProjectRootNotFoundError("No project root found")
    return start_path
