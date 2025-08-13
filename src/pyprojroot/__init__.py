"""Minimal subset of :mod:`pyprojroot` used for test purposes.

This is a lightweight stand-in providing only the :func:`here` function used by
``pysigil``.  It searches parent directories for common project markers such as
``pyproject.toml`` or ``.git`` and returns the matching directory.
"""

from collections.abc import Iterable
from pathlib import Path


def here(
    *path: str | Path,
    start_path: Path | None = None,
    project_files: Iterable[str] | None = None,
    root_marker_files: Iterable[str] | None = None,
) -> Path:
    """Return the project root or a path relative to it.

    Parameters
    ----------
    start_path:
        Directory to start searching from.  If ``None`` the current working
        directory is used.
    project_files, root_marker_files:
        Names of files or directories that signal the project root.
    """

    markers = list(project_files or ["pyproject.toml"]) + list(
        root_marker_files or [".git", ".here"]
    )
    start = Path(start_path or Path.cwd())
    for candidate in (start, *start.parents):
        if any((candidate / m).exists() for m in markers):
            return candidate.joinpath(*path)
    raise RuntimeError("Project root not found")

