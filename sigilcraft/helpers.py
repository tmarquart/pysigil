from __future__ import annotations

import csv
import inspect
import json
import logging
from collections.abc import Callable, Mapping
from importlib import resources
from pathlib import Path
from threading import Lock

try:
    from distutils.util import strtobool  # type: ignore
except Exception:  # pragma: no cover - fallback for Python >=3.12
    def strtobool(val: str) -> int:
        val = val.lower()
        if val in {"y", "yes", "t", "true", "on", "1"}:
            return 1
        if val in {"n", "no", "f", "false", "off", "0"}:
            return 0
        raise ValueError(f"invalid truth value {val!r}")

from .core import Sigil
from .errors import SigilMetaError


def make_package_prefs(
    *,
    app_name: str,
    package: str | None = None,
    defaults_rel: str = "prefs/defaults.ini",
) -> tuple[Callable, Callable]:
    """Return (get_pref, set_pref) callables wired to package defaults.

    If ``package`` is omitted, the caller's module name is used.
    """

    if package is None:
        frame = inspect.stack()[1].frame
        package = frame.f_globals.get("__name__")
        del frame
        if not isinstance(package, str) or not package:
            raise ValueError("Could not determine caller package; pass 'package'")
    lock = Lock()
    sigil_obj: Sigil | None = None
    defaults_path: Path = resources.files(package).joinpath(defaults_rel)
    defaults_dir = defaults_path.parent
    settings_file = defaults_path.name

    def _lazy() -> Sigil:
        nonlocal sigil_obj
        if sigil_obj is None:
            with lock:
                if sigil_obj is None:
                    sigil_obj = Sigil(
                        app_name,
                        default_path=defaults_dir,
                        settings_filename=settings_file,
                    )
        return sigil_obj

    def _get(key: str, *, default=None, cast=None):
        return _lazy().get_pref(key, default=default, cast=cast)

    def _set(key: str, value, *, scope="user"):
        return _lazy().set_pref(key, value, scope=scope)

    return _get, _set


def _parse_json(path: Path) -> dict[str, dict]:
    """Parse JSON metadata file into a mapping."""
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:  # pragma: no cover - delegated to json
        raise SigilMetaError(str(exc)) from exc
    if not isinstance(data, Mapping):
        raise SigilMetaError("Metadata root must be a JSON object")
    meta: dict[str, dict] = {}
    for key, val in data.items():
        if key in meta:
            raise SigilMetaError(f"duplicate key '{key}'")
        if not isinstance(val, Mapping):
            raise SigilMetaError(f"entry for '{key}' must be an object")
        meta[key] = dict(val)
    return meta


def _parse_csv(path: Path) -> dict[str, dict]:
    """Parse CSV metadata following the spec."""

    logger = logging.getLogger("sigil")

    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise SigilMetaError(f"{path}: missing header row")
        fieldnames = [name.lower() for name in reader.fieldnames]
        reader.fieldnames = fieldnames

        meta: dict[str, dict] = {}

        def parse_bool(val: str) -> bool:
            try:
                return strtobool(val.strip().lower()) == 1
            except Exception as exc:
                raise SigilMetaError(f"{path} invalid boolean '{val}'") from exc

        def parse_num(val: str):
            val = val.strip()
            if val == "":
                return None
            try:
                return int(val)
            except ValueError:
                try:
                    return float(val)
                except ValueError as exc:
                    raise SigilMetaError(
                        f"{path} invalid numeric value '{val}'"
                    ) from exc

        known = {
            "key",
            "title",
            "tooltip",
            "secret",
            "type",
            "choices",
            "min",
            "max",
            "order",
            "advanced",
        }

        for lineno, row in enumerate(reader, start=2):
            row = {k.lower(): (v or "") for k, v in row.items()}

            key = row.get("key", "").strip()
            if not key:
                raise SigilMetaError(f"{path}:{lineno} missing 'key' value")
            if key in meta:
                raise SigilMetaError(f"duplicate key '{key}'")

            entry: dict[str, object] = {}

            if row.get("title"):
                entry["title"] = row["title"].strip()
            if row.get("tooltip"):
                entry["tooltip"] = row["tooltip"].strip()
            if row.get("secret"):
                entry["secret"] = parse_bool(row["secret"])
            if row.get("type"):
                entry["type"] = row["type"].strip().lower()
                allowed_types = {
                    "str",
                    "int",
                    "float",
                    "bool",
                    "choice",
                    "path",
                    "json",
                    "yaml",
                }
                if entry["type"] not in allowed_types:
                    logger.warning("unknown type value '%s'", entry["type"])
            if row.get("choices"):
                choices = [p.strip() for p in row["choices"].split("|")]
                if not isinstance(choices, list):
                    raise SigilMetaError("choices split did not produce a list")
                entry["choices"] = choices
                if entry.get("type") != "choice":
                    logger.warning("choices present but type != choice")
            num = parse_num(row.get("min", ""))
            if num is not None:
                entry["min"] = num
            num = parse_num(row.get("max", ""))
            if num is not None:
                entry["max"] = num
            num = parse_num(row.get("order", ""))
            if num is not None:
                entry["order"] = num
            if row.get("advanced"):
                entry["advanced"] = parse_bool(row["advanced"])

            if (
                "min" in entry
                and "max" in entry
                and isinstance(entry["min"], int | float)
                and isinstance(entry["max"], int | float)
                and entry["min"] > entry["max"]
            ):
                raise SigilMetaError(f"{path}:{lineno} min > max")

            # preserve any unknown columns
            for col, val in row.items():
                if col not in known and val.strip() != "":
                    entry[col] = val.strip()

            meta[key] = entry

    return meta


def load_meta(path: Path) -> dict[str, dict]:
    """Load preference metadata from a JSON or CSV file."""

    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".csv":
        return _parse_csv(path)
    elif ext == ".json":
        return _parse_json(path)
    raise SigilMetaError(f"unsupported metadata format: {path}")
