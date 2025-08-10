"""Project root and settings file resolution utilities."""

from pathlib import Path

DEFAULT_FILENAME = "settings.ini"


class ProjectRootNotFoundError(RuntimeError):
    """Raised when no ``pyproject.toml`` can be found in parent directories."""
    pass


def find_project_root(start: Path | None = None) -> Path:
    """Return absolute path to nearest ancestor containing ``pyproject.toml``.

    Parameters
    ----------
    start:
        Starting directory.  If ``None`` the current working directory is used.

    Raises
    ------
    ProjectRootNotFoundError
        If no ``pyproject.toml`` is found when walking up to the filesystem
        root.
    """
    start_path = Path.cwd() if start is None else Path(start)
    for candidate in (start_path, *start_path.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate.resolve()
    raise ProjectRootNotFoundError(
        "No pyproject.toml found; provide --project-file or run inside a project"
    )


def project_settings_file(
    explicit_file: Path | None = None,
    start: Path | None = None,
    filename: str = DEFAULT_FILENAME,
) -> Path:
    """Resolve the project settings file path.

    If ``explicit_file`` is supplied, its absolute path is returned. Otherwise
    ``find_project_root`` is used to locate the project root and
    ``<root>/.pysigil/<filename>`` is returned.  The ``.pysigil`` directory is
    created if necessary.
    """
    if explicit_file is not None:
        return Path(explicit_file).expanduser().resolve()
    root = find_project_root(start)
    cfg_dir = root / ".pysigil"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return (cfg_dir / filename).resolve()
