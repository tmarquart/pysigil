"""Utilities for resolving configuration file locations and project roots."""

from importlib import resources
from pathlib import Path

from appdirs import user_config_dir
from pyprojroot import here

DEFAULT_FILENAME = "settings.ini"
DEFAULT_DEFAULTS_FILENAME = "defaults.ini"


class ProjectRootNotFoundError(RuntimeError):
    """Raised when no project root can be located."""


def find_project_root(start: Path | None = None) -> Path:
    """Locate the nearest project root using :func:`pyprojroot.here`.

    Parameters
    ----------
    start:
        Starting directory.  If ``None`` the current working directory is used.

    Raises
    ------
    ProjectRootNotFoundError
        If no project root can be determined.
    """

    try:
        if start is None:
            return Path(here()).resolve()
        return Path(here(start_path=Path(start))).resolve()
    except Exception as exc:  # pragma: no cover - defensive
        raise ProjectRootNotFoundError("No project root found") from exc


def project_settings_file(
    explicit_file: Path | None = None,
    start: Path | None = None,
    filename: str = DEFAULT_FILENAME,
) -> Path:
    """Resolve the project-level settings file path.

    If ``explicit_file`` is supplied, its absolute path is returned. Otherwise
    :func:`find_project_root` is used to locate the project root and
    ``<root>/.pysigil/<filename>`` is returned.  The ``.pysigil`` directory is
    created if necessary.
    """

    if explicit_file is not None:
        return Path(explicit_file).expanduser().resolve()
    root = find_project_root(start)
    cfg_dir = root / ".pysigil"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return (cfg_dir / filename).resolve()


def user_settings_file(app_name: str, filename: str = DEFAULT_FILENAME) -> Path:
    """Return the user-level settings file for ``app_name``.

    The file lives under ``<user_config_dir>/sigil/<app_name>/<filename>`` and
    parent directories are created as needed.
    """

    base = Path(user_config_dir("sigil")) / app_name
    base.mkdir(parents=True, exist_ok=True)
    return (base / filename).resolve()


def package_defaults_file(
    package: str, filename: str = DEFAULT_DEFAULTS_FILENAME
) -> Path | None:
    """Return path to a package's bundled defaults file.

    The path points to ``prefs/<filename>`` within the installed package.  If
    the package itself cannot be located ``None`` is returned.  The defaults
    file does not need to exist yet; callers may create it to enable writes to
    the ``"default"`` scope.
    """

    try:
        pkg_root = resources.files(package)
    except ModuleNotFoundError:  # pragma: no cover - defensive
        return None
    candidate = pkg_root / "prefs" / filename
    return Path(candidate).resolve()

