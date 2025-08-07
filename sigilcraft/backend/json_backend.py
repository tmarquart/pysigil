from __future__ import annotations

import json
from collections.abc import Mapping, MutableMapping
from pathlib import Path

from ..errors import SigilLoadError
from ..keys import KeyPath
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

    def load(self, path: Path) -> MutableMapping[KeyPath, str]:
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
        return _collect(data)

    def save(self, path: Path, data: Mapping[KeyPath, str]) -> None:
        path = Path(path)
        nested = _build(data)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(nested, fh, indent=2, sort_keys=True, ensure_ascii=False)
        tmp.replace(path)
