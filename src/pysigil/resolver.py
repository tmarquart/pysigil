"""Utilities for resolving configuration file locations and project roots."""

import re
import sys, os
from importlib import resources
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

try:  # pragma: no cover - Python <3.11
    import tomllib  # type: ignore
except Exception:  # pragma: no cover - fallback
    import tomli as tomllib  # type: ignore

from .authoring import get as get_dev_link, normalize_provider_id
from .paths import project_config_dir, user_config_dir

DEFAULT_FILENAME = "settings.ini"


def project_settings_file(
    explicit_file: Path | None = None,
    start: Path | None = None,
    filename: str = DEFAULT_FILENAME,
) -> Path:
    """Resolve the project-level settings file path.

    If ``explicit_file`` is supplied, its absolute path is returned.
    Otherwise ``<root>/.sigil/<filename>`` under the detected project root is
    returned. The ``.sigil`` directory is created if necessary.
    """

    if explicit_file is not None:
        return Path(explicit_file).expanduser().resolve()
    cfg_dir = project_config_dir(start)
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

    candidates = [package, *_candidate_module_names(package)]
    seen: set[str] = set()
    fallback: Path | None = None
    for cand in candidates:
        if not cand or cand in seen:
            continue
        seen.add(cand)
        try:
            pkg_root = resources.files(cand)
        except ModuleNotFoundError:  # pragma: no cover - defensive
            continue
        candidate = pkg_root / ".sigil" / filename
        path = Path(candidate).resolve()
        if path.exists():
            return path
        if fallback is None:
            fallback = path
    return fallback


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
    dl = get_dev_link(provider_id)
    if dl and dl.defaults_path.is_file():
        return dl.defaults_path, "dev-link"
    # Fallback to importable package for legacy/dev usage
    pkg_path = package_defaults_file(provider_id, filename)
    if pkg_path is not None and pkg_path.is_file():
        return pkg_path, "installed"
    return None, "none"


def read_dist_name_from_pyproject(root: Path) -> str | None:
    """Return ``project.name`` from ``pyproject.toml`` if present."""

    ppt = root / "pyproject.toml"
    if not ppt.exists():
        return None
    try:  # pragma: no cover - best effort
        data = tomllib.loads(ppt.read_text(encoding="utf-8"))
        name = data.get("project", {}).get("name")
        return name if isinstance(name, str) and name.strip() else None
    except Exception:  # pragma: no cover - defensive
        return None


def _candidate_module_names(dist_name: str) -> list[str]:
    base = dist_name.lower()
    cands = set()
    cands.add(base.replace("-", "_").replace(".", "_"))
    cands.add(base.replace("-", "").replace(".", ""))
    parts = [p for p in re.split(r"[-.]+", base) if p]
    cands.update(parts)
    return [c for c in cands if c]


try:  # pragma: no cover - fallback when setuptools is missing
    from setuptools import PackageFinder  # type: ignore
except Exception:  # pragma: no cover - defensive
    PackageFinder = None  # type: ignore[assignment]


def _setuptools_pkg_map(root: Path) -> dict[str, Path]:
    """Return mapping of package name to directory using ``setuptools``."""

    if PackageFinder is None:  # pragma: no cover - setuptools not installed
        return {}

    mapping: dict[str, Path] = {}
    for base in [root / "src", root]:
        if not base.is_dir():
            continue
        for pkg in PackageFinder.find(where=[str(base)]):
            mapping[pkg] = base / Path(pkg.replace(".", "/"))
    return mapping


def find_package_dir(root: Path, dist_name: str | None) -> Path | None:
    """Deterministically locate a package directory under ``root``."""

    root = Path(root).resolve()
    pkg_map = _setuptools_pkg_map(root)
    if pkg_map:
        if dist_name:
            for cand in _candidate_module_names(dist_name):
                if cand in pkg_map:
                    return pkg_map[cand]
        if len(pkg_map) == 1:
            return next(iter(pkg_map.values()))
        return None

    # Fallback heuristic when setuptools isn't available
    def _probe(parent: Path, names: list[str]) -> Path | None:
        for n in names:
            cand = parent / n
            if (cand / "__init__.py").exists():
                return cand
        return None

    if dist_name:
        names = _candidate_module_names(dist_name)
        src = root / "src"
        if src.is_dir():
            p = _probe(src, names)
            if p:
                return p
        p = _probe(root, names)
        if p:
            return p

    def _one_pkg(parent: Path) -> Path | None:
        pkgs = [p for p in parent.iterdir() if p.is_dir() and (p / "__init__.py").exists()]
        return pkgs[0] if len(pkgs) == 1 else None

    src = root / "src"
    maybe = _one_pkg(src) if src.is_dir() else None
    if maybe:
        return maybe
    maybe = _one_pkg(root)
    if maybe:
        return maybe
    return None


def default_provider_id(package_dir: Path, dist_name: str | None) -> str:
    """Return default provider id using ``dist_name`` or ``package_dir.name``."""

    if dist_name:
        return normalize_provider_id(dist_name)
    return normalize_provider_id(package_dir.name)


def ensure_defaults_file(package_dir: Path, provider_id: str) -> Path:
    """Ensure ``.sigil/settings.ini`` exists under ``package_dir``."""

    sigil_dir = package_dir / ".sigil"
    sigil_dir.mkdir(exist_ok=True)
    ini = sigil_dir / "settings.ini"
    if not ini.exists():
        template = (
            f"[{provider_id}]\n"
            "# Add your package defaults here.\n"
            "# key = value\n"
        )
        ini.write_text(template, encoding="utf-8")
    return ini

