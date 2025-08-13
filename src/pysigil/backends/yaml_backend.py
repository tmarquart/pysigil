from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from pathlib import Path

from ..errors import SigilLoadError
from ..merge_policy import KeyPath
from . import register_backend
from .base import BaseBackend


def _collect(src: Mapping[str, object], prefix: tuple[str, ...] = ()) -> MutableMapping[KeyPath, str]:
    out: MutableMapping[KeyPath, str] = {}
    for k, v in src.items():
        if isinstance(v, dict):
            out.update(_collect(v, prefix + (k,)))
        else:
            out[prefix + (k,)] = str(v)
    return out


def _build(flat: Mapping[KeyPath, str]) -> dict:
    root: dict = {}
    for path, val in flat.items():
        node = root
        for p in path[:-1]:
            node = node.setdefault(p, {})
        node[path[-1]] = val
    return root


@register_backend
class YamlBackend(BaseBackend):
    """YAML file backend."""

    suffixes = (".yaml", ".yml")

    def _require_yaml(self):
        try:
            import yaml  # type: ignore
        except ModuleNotFoundError as exc:
            raise SigilLoadError("PyYAML is required for YAML backend") from exc
        return yaml

    def load(self, path: Path) -> MutableMapping[KeyPath, str]:
        yaml = self._require_yaml()
        path = Path(path)
        if not path.exists():
            return {}
        raw = path.read_text(encoding="utf-8")
        if raw.strip() == "":
            return {}
        try:
            data = yaml.safe_load(raw) or {}
        except Exception as exc:
            raise SigilLoadError(str(exc)) from exc
        if not isinstance(data, dict):
            raise SigilLoadError("Root of YAML prefs must be a mapping")
        return _collect(data)

    def save(self, path: Path, data: Mapping[KeyPath, str]) -> None:
        yaml = self._require_yaml()
        path = Path(path)
        nested = _build(data)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(nested, fh, sort_keys=True, allow_unicode=True)
        tmp.replace(path)
