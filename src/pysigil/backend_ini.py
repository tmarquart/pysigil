from __future__ import annotations

import configparser
from pathlib import Path
from typing import Dict


class IniIOError(Exception):
    """Raised when an INI file cannot be read or written."""


# Returns mapping: section -> mapping(key -> value)
def read_sections(path: Path) -> Dict[str, Dict[str, str]]:
    parser = configparser.ConfigParser(strict=False)
    data: Dict[str, Dict[str, str]] = {}
    if path.exists():
        try:
            parser.read(path)
        except Exception as exc:  # pragma: no cover - defensive
            raise IniIOError(str(exc)) from exc
        for section in parser.sections():
            data[section] = dict(parser.items(section))
    return data


def write_sections(path: Path, data: Dict[str, Dict[str, str]]) -> None:
    parser = configparser.ConfigParser()
    for section in sorted(data):
        parser.add_section(section)
        for key, value in sorted(data[section].items()):
            parser.set(section, key, str(value))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as fh:
        parser.write(fh)
    tmp.replace(path)
