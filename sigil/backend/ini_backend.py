from __future__ import annotations

import configparser
from pathlib import Path
from typing import Mapping, MutableMapping

from .base import BaseBackend


class IniBackend(BaseBackend):
    suffixes = (".ini",)

    def load(self, path: Path) -> MutableMapping[str, MutableMapping[str, str]]:
        parser = configparser.ConfigParser()
        if path.exists():
            parser.read(path)
        data: MutableMapping[str, MutableMapping[str, str]] = {}
        for section in parser.sections():
            # use private _sections to avoid mixing defaults
            sec = dict(parser._sections.get(section, {}))
            sec.pop("__name__", None)
            data[section] = sec
        if parser.defaults():
            data.setdefault("global", {}).update(parser.defaults())
        return data

    def save(self, path: Path, data: Mapping[str, Mapping[str, str]]) -> None:
        parser = configparser.ConfigParser()
        for section, values in data.items():
            if section == "global":
                parser.defaults().update(values)
            else:
                parser[section] = dict(values)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w") as f:
            parser.write(f)
        tmp.replace(path)
