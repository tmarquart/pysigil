from __future__ import annotations

import configparser
import json
import re
import shutil
from pathlib import Path

import tomlkit

from appdirs import user_config_dir

# ---------------------------------------------------------------------------
# Dev links registry
# ---------------------------------------------------------------------------

_DEV_LINKS_FILE = Path(user_config_dir("sigil")) / "dev-links.json"


def _ensure_parent() -> None:
    _DEV_LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_links() -> dict[str, Path]:
    """Load the development defaults links registry."""

    if not _DEV_LINKS_FILE.is_file():
        return {}
    try:
        data = json.loads(_DEV_LINKS_FILE.read_text())
    except Exception:
        return {}
    if data.get("version") != 1:
        return {}
    result: dict[str, Path] = {}
    links = data.get("links", {})
    if isinstance(links, dict):
        for key, value in links.items():
            p = Path(value)
            if p.is_file():
                result[str(key)] = p
    return result


def save_links(links: dict[str, Path]) -> None:
    """Persist ``links`` to disk."""

    _ensure_parent()
    serialised = {k: str(v) for k, v in links.items()}
    data = {"version": 1, "links": serialised}
    _DEV_LINKS_FILE.write_text(json.dumps(data, indent=2))


def link(provider_id: str, path: Path) -> None:
    """Add or update a development link for ``provider_id``."""

    path = Path(path).expanduser().resolve()
    if not path.is_absolute():
        raise ValueError("path must be absolute")
    if not path.is_file():
        raise FileNotFoundError(path)
    links = load_links()
    links[provider_id] = path
    save_links(links)


def unlink(provider_id: str) -> bool:
    """Remove a development link.  Returns ``True`` if removed."""

    links = load_links()
    if provider_id in links:
        del links[provider_id]
        save_links(links)
        return True
    return False

# ---------------------------------------------------------------------------
# Defaults validation
# ---------------------------------------------------------------------------


class DefaultsValidationError(Exception):
    """Raised when a defaults file is invalid."""


_KEY_RE = re.compile(r"^[a-z0-9]+(\.[a-z0-9_]+)*$")


def validate_defaults_file(path: Path, provider_id: str) -> None:
    """Validate ``path`` for ``provider_id``.

    The file must contain a ``[provider:<provider_id>]`` section and all keys in
    that section must be dotted names using lowercase letters, digits and
    underscores after the first segment.
    """

    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise DefaultsValidationError("defaults file not found")

    parser = configparser.ConfigParser()
    try:
        parser.read(path)
    except Exception as exc:  # pragma: no cover - defensive
        raise DefaultsValidationError(str(exc)) from exc

    section = f"provider:{provider_id}"
    if section not in parser:
        raise DefaultsValidationError("missing provider section")
    for key in parser[section]:
        if not _KEY_RE.match(key):
            raise DefaultsValidationError(f"invalid key: {key}")


# ---------------------------------------------------------------------------
# pyproject.toml helpers
# ---------------------------------------------------------------------------


def import_package_from(ini_path: Path) -> str:
    """Infer the import package name from ``ini_path``.

    The defaults file is expected at ``<pkg>/.sigil/settings.ini``; the package
    name is derived from the parent directory of ``.sigil``.
    """

    ini_path = Path(ini_path).resolve()
    return ini_path.parent.parent.name


def patch_pyproject_package_data(pyproject: Path, import_package: str) -> None:
    """Ensure ``.sigil/settings.ini`` is included as package data."""

    pyproject = Path(pyproject).resolve()
    if not pyproject.is_file():
        return
    text = pyproject.read_text()
    data = tomlkit.parse(text)
    tool = data.setdefault("tool", tomlkit.table())
    setuptools = tool.setdefault("setuptools", tomlkit.table())
    pkg_data = setuptools.setdefault("package-data", tomlkit.table())
    entry = pkg_data.setdefault(import_package, tomlkit.array())
    if ".sigil/settings.ini" not in [str(x) for x in entry]:
        entry.append(".sigil/settings.ini")
    backup = pyproject.with_suffix(pyproject.suffix + ".sigil.bak")
    if not backup.exists():
        shutil.copy2(pyproject, backup)
    pyproject.write_text(tomlkit.dumps(data))
