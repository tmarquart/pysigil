from __future__ import annotations

import configparser
from collections.abc import Mapping, MutableMapping
from pathlib import Path

from ..keys import KeyPath
from . import register_backend
from .base import BaseBackend


@register_backend
class IniBackend(BaseBackend):
    suffixes = (".ini",)

    def load(self, path: Path) -> MutableMapping[KeyPath, str]:
        parser = configparser.ConfigParser()
        if path.exists():
            parser.read(path)
        data: MutableMapping[KeyPath, str] = {}
        for section in parser.sections():
            for key, value in parser.items(section):
                if section == "__root__":
                    kp = (key,)
                else:
                    kp = (section, *key.split("."))
                data[kp] = value
        return data

    def save(self, path: Path, data: Mapping[KeyPath, str]) -> None:
        parser = configparser.ConfigParser()
        for kp, value in data.items():
            if len(kp) == 1:
                sec = "__root__"
                if not parser.has_section(sec):
                    parser.add_section(sec)
                parser.set(sec, kp[0], str(value))
            else:
                sec = kp[0]
                if not parser.has_section(sec):
                    parser.add_section(sec)
                parser.set(sec, ".".join(kp[1:]), str(value))
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w") as f:
            parser.write(f)
        tmp.replace(path)
