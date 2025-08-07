from __future__ import annotations

import configparser
from collections.abc import Mapping, MutableMapping
from pathlib import Path

from ..constants import BOOT_KEY_JOIN_CHAR
from ..keys import KeyPath
from . import register_backend
from .base import BaseBackend


def get_pref(key: str, default: str | None = None) -> str | None:  # pragma: no cover - patched in tests
    return default


@register_backend
class IniBackend(BaseBackend):
    suffixes = (".ini",)

    def load(self, path: Path) -> MutableMapping[KeyPath, str]:
        parser = configparser.ConfigParser()
        if path.exists():
            parser.read(path)
        joiner = get_pref("sigil.key_join_char", BOOT_KEY_JOIN_CHAR) or BOOT_KEY_JOIN_CHAR
        data: MutableMapping[KeyPath, str] = {}
        for section in parser.sections():
            for key, value in parser.items(section):
                if section == "__root__":
                    kp = (key,)
                else:
                    kp = (section, *key.split(joiner))
                data[kp] = value
        return data

    def save(self, path: Path, data: Mapping[KeyPath, str]) -> None:
        parser = configparser.ConfigParser()
        joiner = get_pref("sigil.key_join_char", BOOT_KEY_JOIN_CHAR) or BOOT_KEY_JOIN_CHAR
        for kp, value in data.items():
            if len(kp) == 1:
                section = "__root__"
                key_name = kp[0]
            else:
                section = kp[0]
                key_name = joiner.join(kp[1:])
            if not parser.has_section(section):
                parser.add_section(section)
            parser.set(section, key_name, str(value))
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w") as f:
            parser.write(f)
        tmp.replace(path)
