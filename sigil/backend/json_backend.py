from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, MutableMapping

from .base import BaseBackend
from . import register_backend
from ..errors import SigilLoadError


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
class JsonBackend(BaseBackend):
    """JSON file backend."""

    suffixes = (".json", ".JSON", ".json5")

    def _parse(self, text: str, path: Path) -> Mapping[str, object]:
        if path.suffix.lower() == ".json5":
            try:
                import pyjson5
                return pyjson5.decode(text)
            except ModuleNotFoundError:
                pass
        return json.loads(text)

    def load(self, path: Path) -> MutableMapping[str, object]:
        path = Path(path)
        if not path.exists():
            return {}
        raw = path.read_text(encoding="utf-8")
        if raw.strip() == "":
            raw = "{}"
        try:
            data = self._parse(raw, path)
        except Exception as exc:  # JSON or JSON5 decoding errors
            raise SigilLoadError(str(exc)) from exc
        if not isinstance(data, dict):
            raise SigilLoadError("Root of JSON prefs must be an object")
        return _flatten(data)

    def save(self, path: Path, data: Mapping[str, object]) -> None:
        path = Path(path)
        nested = _unflatten(data)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(nested, fh, indent=2, sort_keys=True, ensure_ascii=False)
        tmp.replace(path)
