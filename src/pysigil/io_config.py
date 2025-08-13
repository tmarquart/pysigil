from __future__ import annotations

import configparser
from importlib.metadata import Distribution
from pathlib import Path

try:
    from appdirs import user_config_dir  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback
    def user_config_dir(appname: str) -> str:
        return str(Path.home() / ".config" / appname)


class IniIOError(Exception):
    """Raised when an INI file cannot be read or written."""


def read_sections(path: Path) -> dict[str, dict[str, str]]:
    parser = configparser.ConfigParser(strict=False)
    data: dict[str, dict[str, str]] = {}
    if path.exists():
        try:
            parser.read(path)
        except Exception as exc:  # pragma: no cover - defensive
            raise IniIOError(str(exc)) from exc
        for section in parser.sections():
            data[section] = dict(parser.items(section))
    return data


def write_sections(path: Path, data: dict[str, dict[str, str]]) -> None:
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


class DefaultsFormatError(Exception):
    pass


def load_provider_defaults(provider_id: str, dist: Distribution) -> dict[str, dict[str, str]]:
    cfg_path = Path(dist.locate_file("pysigil/defaults.ini"))
    if not cfg_path.is_file():
        return {}
    data = read_sections(cfg_path)
    expected_section = f"provider:{provider_id}"
    for section in data:
        if section.startswith("provider:") and section != expected_section:
            raise DefaultsFormatError("provider section name mismatch")
    if expected_section not in data:
        raise DefaultsFormatError("missing provider section")
    result: dict[str, dict[str, str]] = {expected_section: data[expected_section]}
    if "pysigil" in data:
        result["pysigil"] = data["pysigil"]
    return result
