from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, MutableMapping
from pathlib import Path


class BaseBackend(ABC):
    """Abstract base backend."""

    suffixes: tuple[str, ...] = ()

    @abstractmethod
    def load(self, path: Path) -> MutableMapping[str, MutableMapping[str, str]]:
        pass

    @abstractmethod
    def save(self, path: Path, data: Mapping[str, Mapping[str, str]]) -> None:
        pass
