from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, MutableMapping
from pathlib import Path

from ..merge_policy import KeyPath


class BaseBackend(ABC):
    """Abstract base backend."""

    suffixes: tuple[str, ...] = ()

    @abstractmethod
    def load(self, path: Path) -> MutableMapping[KeyPath, str]:
        pass

    @abstractmethod
    def save(self, path: Path, data: Mapping[KeyPath, str]) -> None:
        pass
