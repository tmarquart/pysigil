"""Backend registry and factory."""
from __future__ import annotations

from pathlib import Path

from .base import BaseBackend

_REGISTRY: dict[str, type[BaseBackend]] = {}

def register_backend(backend: type[BaseBackend]) -> type[BaseBackend]:
    """Register a backend class and return it for decorator use."""
    for suf in backend.suffixes:
        _REGISTRY[suf] = backend
    return backend

def get_backend_for_path(path: Path) -> BaseBackend:
    backend_cls = _REGISTRY.get(path.suffix.lower())
    if backend_cls is None:
        raise ValueError(f"No backend for {path.suffix}")
    return backend_cls()

# register default backends
from . import ini_backend, json_backend, yaml_backend  # noqa: F401,E402
