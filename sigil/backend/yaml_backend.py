from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from pathlib import Path

from ..errors import SigilLoadError
from . import register_backend
from .base import BaseBackend


def _flatten(src: Mapping[str, object], prefix: str = "") -> MutableMapping[str, object]:
    out: MutableMapping[str, object] = {}
    for k, v in src.items():
        key = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, key))
        else:
            out[key] = v
    return out


def _unflatten(flat: Mapping[str, object]) -> dict:
    root: dict = {}
    for dotted, val in flat.items():
        parts = dotted.split(".")
        node = root
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = val
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

    def load(self, path: Path) -> MutableMapping[str, object]:
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
        return _flatten(data)

    def save(self, path: Path, data: Mapping[str, object]) -> None:
        yaml = self._require_yaml()
        path = Path(path)
        nested = _unflatten(data)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(nested, fh, sort_keys=True, allow_unicode=True)
        tmp.replace(path)
