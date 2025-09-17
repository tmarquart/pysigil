from __future__ import annotations

import importlib
import os
from importlib import resources as ilr
from pathlib import Path

from platformdirs import (
    user_cache_dir as _ucache,
    user_config_dir as _uc,
    user_data_dir as _ud,
)

from .root import ProjectRootNotFoundError, find_project_root

# ---------------------------------------------------------------------------
# User directories
# ---------------------------------------------------------------------------

def _app_name(default: str) -> str:
    return os.getenv("SIGIL_APP_NAME", default)

def user_config_dir(app_name: str = "pysigil") -> Path:
    app = _app_name(app_name)
    return Path(_uc(appname=app)).resolve()

def user_data_dir(app_name: str = "pysigil") -> Path:
    app = _app_name(app_name)
    return Path(_ud(appname=app)).resolve()

def user_cache_dir(app_name: str = "pysigil") -> Path:
    app = _app_name(app_name)
    return Path(_ucache(appname=app)).resolve()

# ---------------------------------------------------------------------------
# Project directories
# ---------------------------------------------------------------------------
def project_dir(package: str) -> Path:
    """Return the project root directory for an importable *package*."""

    module = importlib.import_module(package)
    file_attr = getattr(module, "__file__", None)
    if file_attr is not None:
        pkg_root = Path(file_attr).resolve().parent
    else:  # pragma: no cover - namespace package fallback
        pkg_root = Path(str(ilr.files(package))).resolve()
    try:
        root = find_project_root(start=pkg_root)
    except ProjectRootNotFoundError:
        root = pkg_root
    return root.resolve()


def project_root(start: str | Path | None = None, **kw) -> Path:
    env = os.getenv("SIGIL_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return find_project_root(start=start, **kw)

def project_config_dir(start: str | Path | None = None, **kw) -> Path:
    return project_root(start, **kw) / ".sigil"

def project_data_dir(start: str | Path | None = None, **kw) -> Path:
    return project_config_dir(start, **kw) / "data"

def project_cache_dir(start: str | Path | None = None, **kw) -> Path:
    return project_config_dir(start, **kw) / "cache"

# ---------------------------------------------------------------------------
# Package-installed defaults
# ---------------------------------------------------------------------------

def default_config_dir(package: str = "pysigil") -> Path:
    return Path(ilr.files(package)) / ".sigil"

def default_data_dir(package: str = "pysigil") -> Path:
    return default_config_dir(package) / "data"
