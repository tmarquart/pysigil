"""Backend registry and factory."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Type

from .base import BaseBackend
from .ini_backend import IniBackend

_REGISTRY: Dict[str, Type[BaseBackend]] = {}

def register_backend(backend: Type[BaseBackend]) -> None:
    for suf in backend.suffixes:
        _REGISTRY[suf] = backend

def get_backend_for_path(path: Path) -> BaseBackend:
    backend_cls = _REGISTRY.get(path.suffix.lower())
    if backend_cls is None:
        raise ValueError(f"No backend for {path.suffix}")
    return backend_cls()

# register default ini backend
register_backend(IniBackend)
