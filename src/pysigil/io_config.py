from __future__ import annotations

import configparser
from importlib import resources
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


def load_provider_defaults(
    provider_id: str, package: str
) -> dict[str, dict[str, str]]:
    """Load bundled defaults for a provider from ``package``.

    Defaults are stored in ``.sigil/settings.ini`` within the package and use
    the same structure as project-level settings.  The returned mapping contains
    the section matching ``provider_id`` and optionally a ``"pysigil"`` section.
    The file is considered read-only; if it does not exist an empty mapping is
    returned.
    """

    try:
        cfg_res = resources.files(package) / ".sigil" / "settings.ini"
    except ModuleNotFoundError:
        return {}
    cfg_path = Path(cfg_res)
    if not cfg_path.is_file():
        return {}
    data = read_sections(cfg_path)
    if provider_id not in data:
        raise DefaultsFormatError("missing provider section")
    result: dict[str, dict[str, str]] = {provider_id: data[provider_id]}
    if "pysigil" in data:
        result["pysigil"] = data["pysigil"]
    return result
