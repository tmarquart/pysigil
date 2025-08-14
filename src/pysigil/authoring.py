from __future__ import annotations

import configparser
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import tomlkit
from appdirs import user_config_dir

# ---------------------------------------------------------------------------
# Dev links registry
# ---------------------------------------------------------------------------


class DevLinkError(Exception):
    """Raised when development link operations fail."""


@dataclass
class DevLink:
    provider_id: str
    defaults_path: Path
    link_path: Path


_PEP503_RE = re.compile(r"[-_.]+")


def normalize_provider_id(name: str) -> str:
    """PEP 503 normalize ``name``."""
    return _PEP503_RE.sub("-", name).lower()


def _dev_dir() -> Path:
    return Path(user_config_dir("sigil")) / "dev"


def link(provider: str, defaults_path: Path, *, validate: bool = True) -> DevLink:
    pid = normalize_provider_id(provider)
    defaults_path = Path(defaults_path).expanduser().resolve()
    if not defaults_path.is_file():
        raise DevLinkError(f"Defaults file not found: {defaults_path}")
    if defaults_path.name != "settings.ini" or defaults_path.parent.name != ".sigil":
        raise DevLinkError("Defaults file must be inside a '.sigil' directory")
    if validate:
        validate_defaults_file(defaults_path, pid)
    dir_ = _dev_dir()
    dir_.mkdir(parents=True, exist_ok=True)
    link_path = dir_ / f"{pid}.ini"
    cfg = configparser.ConfigParser()
    cfg["link"] = {"defaults": str(defaults_path)}
    with link_path.open("w") as f:
        cfg.write(f)
    return DevLink(pid, defaults_path, link_path)


def unlink(provider: str) -> bool:
    pid = normalize_provider_id(provider)
    link_path = _dev_dir() / f"{pid}.ini"
    if link_path.exists():
        link_path.unlink()
        return True
    return False


def get(provider: str) -> DevLink | None:
    pid = normalize_provider_id(provider)
    link_path = _dev_dir() / f"{pid}.ini"
    if not link_path.is_file():
        return None
    cfg = configparser.ConfigParser()
    try:
        cfg.read(link_path)
    except Exception:
        return None
    defaults = cfg.get("link", "defaults", fallback=None)
    if not defaults:
        return None
    return DevLink(pid, Path(defaults), link_path)


def list_links(must_exist_on_disk: bool = False) -> dict[str, Path]:
    dir_ = _dev_dir()
    if not dir_.is_dir():
        return {}
    result: dict[str, Path] = {}
    for file in dir_.glob("*.ini"):
        dl = get(file.stem)
        if dl is None:
            continue
        if must_exist_on_disk and not dl.defaults_path.exists():
            continue
        result[dl.provider_id] = dl.defaults_path
    return result


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
