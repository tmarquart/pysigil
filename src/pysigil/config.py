from __future__ import annotations

import configparser
import socket
from pathlib import Path
from typing import Any

from appdirs import user_config_dir

from .authoring import normalize_provider_id
from .resolver import ProjectRootNotFoundError, find_project_root


# ---------------------------------------------------------------------------
# Host and provider helpers
# ---------------------------------------------------------------------------

def host_id() -> str:
    """Return the normalised hostname."""
    raw = socket.gethostname()
    return normalize_provider_id(raw).strip("-")


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def user_files(host: str) -> list[Path]:
    base = Path(user_config_dir("sigil"))
    files = [base / "settings.ini", base / f"settings-local-{host}.ini"]
    return [f for f in files if f.exists()]


def _project_dir(auto: bool) -> Path | None:
    if auto:
        try:
            return find_project_root()
        except ProjectRootNotFoundError:
            return None
    return Path.cwd()


def project_files(host: str, *, auto: bool = True) -> list[Path]:
    root = _project_dir(auto)
    if root is None:
        return []
    base = root / ".sigil"
    files = [base / "settings.ini", base / f"settings-local-{host}.ini"]
    return [f for f in files if f.exists()]


# ---------------------------------------------------------------------------
# Reading helpers
# ---------------------------------------------------------------------------

def merge_ini_section(acc: dict[str, Any], ini_path: Path, *, section: str) -> dict[str, Any]:
    parser = configparser.ConfigParser()
    try:
        parser.read(ini_path)
    except Exception:
        return acc
    if parser.has_section(section):
        for k, v in parser.items(section):
            acc[k] = v
    return acc


def load(provider_id: str, *, auto: bool = True) -> dict[str, Any]:
    pid = normalize_provider_id(provider_id)
    h = host_id()
    acc: dict[str, Any] = {}
    for f in user_files(h):
        acc = merge_ini_section(acc, f, section=pid)
    for f in project_files(h, auto=auto):
        acc = merge_ini_section(acc, f, section=pid)
    return acc


# ---------------------------------------------------------------------------
# Writing helpers used by CLI and GUI
# ---------------------------------------------------------------------------

def _scope_dir(scope: str, *, auto: bool) -> Path:
    if scope == "user":
        base = Path(user_config_dir("sigil"))
    else:
        root = _project_dir(auto)
        if root is None:
            raise ProjectRootNotFoundError("No project root found")
        base = root / ".sigil"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _seed_section(path: Path, section: str, comment: str) -> None:
    if path.exists():
        parser = configparser.ConfigParser()
        try:
            parser.read(path)
        except Exception:
            parser = None
        if parser and parser.has_section(section):
            return
        with path.open("a") as fh:
            fh.write(f"\n[{section}]\n{comment}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"[{section}]\n{comment}")


def init_config(provider_id: str, scope: str, *, auto: bool = False) -> Path:
    pid = normalize_provider_id(provider_id)
    h = host_id()
    base = _scope_dir(scope, auto=auto)
    if pid == "user-custom":
        path = base / f"settings-local-{h}.ini"
        comment = "# per-machine user-custom settings\n"
    else:
        path = base / "settings.ini"
        comment = "# add keys here\n"
    _seed_section(path, pid, comment)
    return path


def open_scope(scope: str, *, auto: bool = False) -> Path:
    return _scope_dir(scope, auto=auto)


def host_file(provider_id: str, scope: str, *, auto: bool = False) -> Path:
    pid = normalize_provider_id(provider_id)
    if pid != "user-custom":
        raise ValueError("host command is only valid for provider 'user-custom'")
    return init_config(pid, scope, auto=auto)


def ensure_gitignore(*, auto: bool = False) -> Path:
    root = _project_dir(auto)
    if root is None:
        raise ProjectRootNotFoundError("No project root found")
    gi = root / ".gitignore"
    rule = ".sigil/settings-local*"
    lines: list[str] = []
    if gi.exists():
        lines = gi.read_text().splitlines()
    if rule not in lines:
        lines.append(rule)
        gi.write_text("\n".join(lines) + "\n")
    return gi
