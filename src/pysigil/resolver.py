"""Utilities for resolving configuration file locations and project roots."""

from importlib import resources
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

from appdirs import user_config_dir
from pyprojroot import here

from .authoring import load_links

DEFAULT_FILENAME = "settings.ini"


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
    ``<root>/.sigil/<filename>`` is returned.  The ``.sigil`` directory is
    created if necessary.
    """

    if explicit_file is not None:
        return Path(explicit_file).expanduser().resolve()
    root = find_project_root(start)
    cfg_dir = root / ".sigil"
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
    package: str, filename: str = DEFAULT_FILENAME
) -> Path | None:
    """Return path to a package's bundled defaults file.

    The path points to ``.sigil/<filename>`` within the installed package.  If
    the package itself cannot be located ``None`` is returned.  The resulting
    file is considered read-only and should not be modified at runtime.
    """

    try:
        pkg_root = resources.files(package)
    except ModuleNotFoundError:  # pragma: no cover - defensive
        return None
    candidate = pkg_root / ".sigil" / filename
    return Path(candidate).resolve()


def _installed_defaults(provider_id: str, filename: str = DEFAULT_FILENAME) -> Path | None:
    """Locate bundled defaults for an installed distribution."""

    try:
        dist = distribution(provider_id)
    except PackageNotFoundError:
        return None
    files = dist.files or []
    for file in files:
        if len(file.parts) >= 2 and file.parts[-2] == ".sigil" and file.name == filename:
            return Path(dist.locate_file(file)).resolve()
    return None


def resolve_defaults(provider_id: str, filename: str = DEFAULT_FILENAME) -> tuple[Path | None, str]:
    """Resolve defaults for ``provider_id`` according to precedence rules.

    Returns ``(path, source)`` where ``source`` is one of ``"installed"``,
    ``"dev-link"`` or ``"none"``.
    """

    path = _installed_defaults(provider_id, filename)
    if path is not None and path.is_file():
        return path, "installed"
    links = load_links()
    link_path = links.get(provider_id)
    if link_path and link_path.is_file():
        return link_path, "dev-link"
    # Fallback to importable package for legacy/dev usage
    pkg_path = package_defaults_file(provider_id, filename)
    if pkg_path is not None and pkg_path.is_file():
        return pkg_path, "installed"
    return None, "none"

