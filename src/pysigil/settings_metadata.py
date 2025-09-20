"""Lightweight object graph for Sigil GUI/CLI interaction.

This module defines a small set of immutable data structures used to
describe configuration providers and their fields.  It deliberately keeps
runtime policy such as file locations behind a simple backend interface so
that higher layers (GUI, CLI) never touch the file system directly.

The implementation follows the design described in the user request and is
intended to be a stable, extendable base for future GUI work.
"""

from __future__ import annotations

import configparser
import json
import os
import re
from importlib.metadata import distributions

from contextlib import contextmanager
from dataclasses import dataclass, field as dataclass_field
from pathlib import Path

if os.name == "nt":  # pragma: no cover - platform specific
    import msvcrt
else:  # pragma: no cover - platform specific
    import fcntl

from collections.abc import Iterable, Mapping, MutableMapping

from types import SimpleNamespace
from typing import Any, Callable, Iterator, Literal, Protocol
from uuid import uuid4


from .authoring import get as get_dev_link, list_links
from .config import host_id
from .errors import (
    ConflictError,
    DuplicateProviderError,
    SigilLoadError,
    UnknownFieldError,
    UnknownProviderError,
)
from .io_config import IniIOError, read_sections, write_sections
from .policy import ScopePolicy, policy as default_policy
from .resolver import resolve_defaults
from .root import ProjectRootNotFoundError
from .discovery import pep503_name

# Maximum length for short descriptions in field specs
SHORT_DESC_MAX = 80

####################
##### ADAPTERS #####
####################

class TypeAdapter(Protocol):
    """Adapter for a primitive field type.

    Adapters are responsible for parsing raw string values, validating Python
    values and serialising them back to strings for storage.
    """

    def parse(self, raw: str | None) -> Any:
        """Parse *raw* text into a Python value."""

    def serialize(self, value: Any) -> str:
        """Serialise *value* into text for storage."""

    def validate(self, value: Any, spec: FieldSpec) -> None:
        """Validate *value* against *spec*.

        Implementations should raise :class:`TypeError` or :class:`ValueError`
        if validation fails.
        """


class StringAdapter:
    """Adapter for plain string values."""

    def parse(self, raw: str | None) -> str | None:  # pragma: no cover - trivial
        return raw

    def serialize(self, value: Any) -> str:
        if not isinstance(value, str):
            raise TypeError("expected str")
        return value

    def validate(self, value: Any, spec: FieldSpec) -> None:
        if value is not None and not isinstance(value, str):
            raise TypeError("expected str")


class IntegerAdapter:
    """Adapter for integer values."""

    def parse(self, raw: str | None) -> int | None:
        if raw is None:
            return None
        return int(raw)

    def serialize(self, value: Any) -> str:
        if not isinstance(value, int):
            raise TypeError("expected int")
        return str(value)

    def validate(self, value: Any, spec: FieldSpec) -> None:
        if value is not None and not isinstance(value, int):
            raise TypeError("expected int")
        if value is None:
            return
        minimum = spec.options.get("minimum")
        if minimum is not None:
            if not isinstance(minimum, int):
                raise TypeError("minimum option must be int")
            if value < minimum:
                raise ValueError(f"value {value} < minimum {minimum}")


class NumberAdapter:
    """Adapter for floating point numbers."""

    def parse(self, raw: str | None) -> float | None:
        if raw is None:
            return None
        return float(raw)

    def serialize(self, value: Any) -> str:
        if not isinstance(value, int | float):
            raise TypeError("expected number")
        return str(value)

    def validate(self, value: Any, spec: FieldSpec) -> None:
        if value is not None and not isinstance(value, int | float):
            raise TypeError("expected number")


class BooleanAdapter:
    """Adapter for boolean values."""

    def parse(self, raw: str | None) -> bool | None:
        if raw is None:
            return None
        lowered = raw.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        raise ValueError(f"invalid boolean: {raw!r}")

    def serialize(self, value: Any) -> str:
        if not isinstance(value, bool):
            raise TypeError("expected bool")
        return "true" if value else "false"

    def validate(self, value: Any, spec: FieldSpec) -> None:
        if value is not None and not isinstance(value, bool):
            raise TypeError("expected bool")


class StringListAdapter:
    """Adapter for lists of strings."""

    def parse(self, raw: str | None) -> list[str]:
        if not raw:
            return []
        return [p.strip() for p in raw.split(",") if p.strip()]

    def serialize(self, value: Any) -> str:
        if not isinstance(value, list) or not all(isinstance(p, str) for p in value):
            raise TypeError("expected list[str]")
        return ", ".join(value)

    def validate(self, value: Any, spec: FieldSpec) -> None:
        if value is not None and (
            not isinstance(value, list) or not all(isinstance(p, str) for p in value)
        ):
            raise TypeError("expected list[str]")


@dataclass
class IntegerOptions:
    """Configuration options for integer fields."""

    minimum: int | None = None


@dataclass(frozen=True)
class FieldType:
    """Metadata describing a supported field type."""

    adapter: TypeAdapter
    option_model: type | None = None
    value_widget: Callable[[Any], Any] | None = None
    option_widget: Callable[[Any], Any] | None = None


TYPE_REGISTRY: dict[str, FieldType] = {
    "string": FieldType(StringAdapter()),
    "integer": FieldType(IntegerAdapter(), option_model=IntegerOptions),
    "number": FieldType(NumberAdapter()),
    "boolean": FieldType(BooleanAdapter()),
    "string_list": FieldType(StringListAdapter()),
}

_PEP503_RE = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")


def _stat_etag(st: os.stat_result) -> str:
    """Return a simple ETag from ``os.stat`` results."""

    return f"{st.st_mtime_ns}-{st.st_size}"


def _path_etag(path: Path) -> str:
    return _stat_etag(path.stat())


@contextmanager
def _locked(path: Path, exclusive: bool):
    """Context manager acquiring an advisory lock for *path*."""

    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a") as fh:
        if os.name == "nt":  # pragma: no cover - platform specific
            fh.seek(0)
            mode = msvcrt.LK_LOCK if exclusive else msvcrt.LK_RLCK
            msvcrt.locking(fh.fileno(), mode, 1)
        else:  # pragma: no cover - platform specific
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        try:
            yield
        finally:
            if os.name == "nt":  # pragma: no cover - platform specific
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:  # pragma: no cover - platform specific
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

######################
##### FIELD SPEC #####
######################

@dataclass(frozen=True)
class FieldSpec:
    """Specification for a single configuration field."""

    key: str
    type: str
    label: str | None = None
    description_short: str | None = None
    description: str | None = None
    options: dict[str, Any] = dataclass_field(default_factory=dict)
    section: str | None = None
    order: int | None = None

    def __post_init__(self) -> None:
        if self.type not in TYPE_REGISTRY:
            raise ValueError(f"unknown type: {self.type!r}")
        if (
            self.description_short is not None
            and len(self.description_short) > SHORT_DESC_MAX
        ):
            raise ValueError(
                f"description_short too long ({len(self.description_short)}>{SHORT_DESC_MAX})"
            )

    def to_gui_v0(self) -> dict[str, Any]:
        """Return a minimal GUI representation."""

        data = {
            "key": self.key,
            "type": self.type,
        }
        if self.label is not None:
            data["label"] = self.label
        if self.description_short is not None:
            data["description_short"] = self.description_short
        if self.description is not None:
            data["description"] = self.description
        if self.options:
            data["options"] = self.options
        if self.section is not None:
            data["section"] = self.section
        if self.order is not None:
            data["order"] = self.order
        return data


@dataclass
class FieldValue:
    """Parsed field value along with provenance information."""

    value: Any | None
    source: Literal[
        "user",
        "user-local",
        "project",
        "project-local",
        "default",
        "env",
    ] | None = None
    raw: str | None = None
    error: str | None = None

##########################
###### PROVIDER SPEC #####
##########################

@dataclass(frozen=True)
class ProviderSpec:
    """Specification for a provider's GUI/CLI visible fields."""

    provider_id: str
    schema_version: str
    title: str | None = None
    description: str | None = None
    fields: Iterable[FieldSpec] = dataclass_field(default_factory=tuple)
    sections_order: Iterable[str] | None = None
    sections_collapsed: Iterable[str] | None = None

    def __post_init__(self) -> None:
        if not _PEP503_RE.fullmatch(self.provider_id):
            raise ValueError(
                f"provider_id {self.provider_id!r} is not PEP-503 normalised"
            )
        # Freeze iterable of fields into a tuple for immutability
        object.__setattr__(self, "fields", tuple(self.fields))
        if self.sections_order is not None:
            object.__setattr__(self, "sections_order", tuple(self.sections_order))
        if self.sections_collapsed is not None:
            object.__setattr__(self, "sections_collapsed", tuple(self.sections_collapsed))

    def to_gui_doc_v0(self) -> dict[str, Any]:
        """Return a dict representation for GUI consumption."""

        data = {
            "schema_version": self.schema_version,
            "provider_id": self.provider_id,
            "title": self.title,
            "description": self.description,
            "fields": [f.to_gui_v0() for f in self.fields],
        }
        if self.sections_order is not None:
            data["sections_order"] = list(self.sections_order)
        if self.sections_collapsed is not None:
            data["sections_collapsed"] = list(self.sections_collapsed)
        return data

####################
##### BACKENDS #####
####################

# ---- specification storage ----

class SpecBackend(Protocol):
    """Protocol describing the provider specification backend."""

    def get_provider_ids(self) -> list[str]:
        ...

    def get_spec(self, provider_id: str) -> ProviderSpec:
        ...

    def save_spec(self, spec: ProviderSpec, *, expected_etag: str | None = None) -> str:
        ...

    def create_spec(self, spec: ProviderSpec) -> str:
        ...

    def delete_spec(self, provider_id: str) -> None:
        ...

    def etag(self, provider_id: str) -> str:
        ...

    def exists(self, provider_id: str) -> bool:
        ...


class InMemorySpecBackend:
    """Simple :class:`SpecBackend` storing data in memory.

    The backend assigns a random *etag* to every stored specification so
    that concurrent modification can be detected by higher layers.
    """

    def __init__(self) -> None:
        self._specs: dict[str, ProviderSpec] = {}
        self._etags: dict[str, str] = {}

    def get_provider_ids(self) -> list[str]:  # pragma: no cover - trivial
        return sorted(self._specs)

    def get_spec(self, provider_id: str) -> ProviderSpec:
        try:
            return self._specs[provider_id]
        except KeyError as exc:  # pragma: no cover - defensive
            raise UnknownProviderError(provider_id) from exc

    def exists(self, provider_id: str) -> bool:  # pragma: no cover - trivial
        return provider_id in self._specs


class IniSpecBackend:
    """Persist provider specifications in simple INI files.

    Metadata primarily lives alongside a package's defaults file (the
    ``default`` scope).  When a development link exists for a provider, the
    metadata is read from and written to ``<defaults_dir>/metadata.ini``.  For
    convenience and testing purposes a secondary user-level directory can be
    supplied where metadata files are also consulted.

    Parameters
    ----------
    user_dir:
        Optional directory for user-level metadata storage.  When provided this
        location is used as a fallback when no development link (and thus no
        default location) exists for a provider.
    """

    def __init__(self, *, user_dir: Path | None = None) -> None:
        self.user_dir = Path(user_dir) if user_dir else None
        if self.user_dir is not None:
            self.user_dir.mkdir(parents=True, exist_ok=True)
        self._etags: dict[str, str] = {}

    # ------------------------------------------------------------ helpers
    def _user_path(self, provider_id: str) -> Path:
        assert self.user_dir is not None
        return self.user_dir / provider_id / "metadata.ini"

    def _read_path(self, provider_id: str) -> Path:
        dl = get_dev_link(provider_id)
        if dl is not None:
            path = dl.defaults_path.parent / "metadata.ini"
            if path.is_file():
                return path
        else:
            path, _src = resolve_defaults(provider_id, "metadata.ini")
            if path is not None and path.is_file():
                return path
        if self.user_dir is not None:
            return self._user_path(provider_id)
        raise UnknownProviderError(provider_id)

    def _write_path(self, provider_id: str) -> Path:
        dl = get_dev_link(provider_id)
        if dl is not None:
            path = dl.defaults_path.parent / "metadata.ini"
            path.parent.mkdir(parents=True, exist_ok=True)
            return path
        if self.user_dir is not None:
            path = self._user_path(provider_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            return path
        raise ProjectRootNotFoundError("No development link configured")

    def _write_locked(self, path: Path, spec: ProviderSpec) -> str:
        parser = configparser.ConfigParser()
        meta: dict[str, str] = {"schema_version": spec.schema_version}
        if spec.title is not None:
            meta["title"] = spec.title
        if spec.description is not None:
            meta["description"] = spec.description
        if spec.sections_order is not None:
            meta["sections_order"] = json.dumps(list(spec.sections_order))
        if spec.sections_collapsed is not None:
            meta["sections_collapsed"] = json.dumps(list(spec.sections_collapsed))
        parser["__meta__"] = meta
        for field in spec.fields:
            section = f"field:{field.key}"
            parser.add_section(section)
            parser.set(section, "type", field.type)
            if field.label is not None:
                parser.set(section, "label", field.label)
            if field.description_short is not None:
                parser.set(section, "description_short", field.description_short)
            if field.description is not None:
                parser.set(section, "description", field.description)
            if field.options:
                parser.set(section, "options", json.dumps(field.options, sort_keys=True))
            if field.section is not None:
                parser.set(section, "section", field.section)
            if field.order is not None:
                parser.set(section, "order", str(field.order))
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w") as fh:
            parser.write(fh)
        tmp.replace(path)
        return _path_etag(path)

    def _read(self, path: Path, provider_id: str) -> ProviderSpec:
        parser = configparser.ConfigParser()
        with _locked(path, exclusive=False):
            if not path.exists():
                raise UnknownProviderError(provider_id)
            with path.open("r") as fh:
                parser.read_file(fh)
                st = os.fstat(fh.fileno())
        meta = parser["__meta__"]
        fields: list[FieldSpec] = []
        for section in parser.sections():
            if not section.startswith("field:"):
                continue
            key = section.split(":", 1)[1]
            data = parser[section]
            order_val = data.get("order")
            fields.append(
                FieldSpec(
                    key=key,
                    type=data.get("type", "string"),
                    label=data.get("label"),
                    description_short=data.get("description_short"),
                    description=data.get("description"),
                    options=json.loads(data.get("options", "{}")),
                    section=data.get("section"),
                    order=int(order_val) if order_val is not None else None,
                )
            )
        so_raw = meta.get("sections_order")
        sc_raw = meta.get("sections_collapsed")
        spec = ProviderSpec(
            provider_id=provider_id,
            schema_version=meta.get("schema_version", "0"),
            title=meta.get("title"),
            description=meta.get("description"),
            fields=fields,
            sections_order=json.loads(so_raw) if so_raw else None,
            sections_collapsed=json.loads(sc_raw) if sc_raw else None,
        )
        self._etags[provider_id] = _stat_etag(st)
        return spec

    def exists(self, provider_id: str) -> bool:
        dl = get_dev_link(provider_id)
        if dl is not None:
            if (dl.defaults_path.parent / "metadata.ini").is_file():
                return True
        else:
            path, _src = resolve_defaults(provider_id, "metadata.ini")
            if path is not None and path.is_file():
                return True
        if self.user_dir is not None:
            return (self.user_dir / provider_id / "metadata.ini").is_file()
        return False

    # -------------------------------------------------------------- API
    def get_provider_ids(self) -> list[str]:
        ids: dict[str, str] = {}
        if self.user_dir is not None and self.user_dir.exists():
            for p in self.user_dir.iterdir():
                if (p / "metadata.ini").exists():
                    ids.setdefault(p.name, "user")
        for pid, defaults in list_links(must_exist_on_disk=True).items():
            if (defaults.parent / "metadata.ini").exists():
                ids[pid] = "dev"
        for dist in distributions():
            files = getattr(dist, "files", None)
            if not files:
                continue
            if not any(f.parts[-2:] == (".sigil", "metadata.ini") for f in files):
                continue
            meta = getattr(dist, "metadata", None)
            name = meta.get("Name") if meta is not None else dist.name
            if not name:
                continue
            provider_id = pep503_name(name)
            ids.setdefault(provider_id, "dist")
        return sorted(ids)

    def get_spec(self, provider_id: str) -> ProviderSpec:
        path = self._read_path(provider_id)
        return self._read(path, provider_id)

    def save_spec(self, spec: ProviderSpec, *, expected_etag: str | None = None) -> str:
        path = self._write_path(spec.provider_id)
        with _locked(path, exclusive=True):
            on_disk = _path_etag(path) if path.exists() else None
            current = self._etags.get(spec.provider_id)
            if current is not None and on_disk is not None and current != on_disk:
                raise ConflictError(spec.provider_id)
            if expected_etag is not None and current is not None and expected_etag != current:
                raise ConflictError(spec.provider_id)
            etag = self._write_locked(path, spec)
        self._etags[spec.provider_id] = etag
        return etag

    def create_spec(self, spec: ProviderSpec) -> str:
        path = self._write_path(spec.provider_id)
        with _locked(path, exclusive=True):
            if path.exists():
                raise DuplicateProviderError(spec.provider_id)
            etag = self._write_locked(path, spec)
        self._etags[spec.provider_id] = etag
        return etag

    def delete_spec(self, provider_id: str) -> None:
        path = self._write_path(provider_id)
        with _locked(path, exclusive=True):
            if path.exists():
                path.unlink()
        self._etags.pop(provider_id, None)

    def etag(self, provider_id: str) -> str:
        path = self._read_path(provider_id)
        with _locked(path, exclusive=False):
            if not path.exists():
                raise UnknownProviderError(provider_id)
            etag = _path_etag(path)
        self._etags[provider_id] = etag
        return etag


# ---- configuration storage ----

class SigilBackend(Protocol):
    """Minimal interface that hides IO/policy details from the manager."""

    def read_merged(self, provider_id: str) -> tuple[Mapping[str, str], Mapping[str, str]]:
        ...

    def read_layers(self, provider_id: str) -> Mapping[str, Mapping[str, str]]:
        """Return raw values for all scopes for *provider_id*.

        The returned mapping uses scope names (e.g. ``"user"`` or
        ``"project-local"``) as keys and maps them to dictionaries of raw
        key/value pairs.  Scopes missing on disk are omitted from the result.
        """
        ...

    def write_key(
        self,
        provider_id: str,
        key: str,
        raw_value: str,
        *,
        scope: str,
        target_kind: str,
    ) -> None:
        ...

    def remove_key(
        self,
        provider_id: str,
        key: str,
        *,
        scope: str,
        target_kind: str,
    ) -> None:
        ...

    def ensure_section(
        self,
        provider_id: str,
        *,
        scope: str,
        target_kind: str,
    ) -> None:
        ...

    def write_target_for(self, provider_id: str) -> str:
        ...

    @contextmanager
    def transaction(
        self,
        provider_id: str,
        *,
        scope: str,
        target_kind: str,
    ) -> Iterator[MutableMapping[str, str]]:
        """Stage updates to a provider section and commit on success."""
        ...


class IniFileBackend:
    """Store provider settings in INI files on the filesystem.

    The backend mirrors the layout used by the existing command line tools::

        ~/.config/sigil/<provider>/settings.ini
        ~/.config/sigil/<provider>/settings-local-<host>.ini
        <project>/.sigil/settings.ini
        <project>/.sigil/settings-local-<host>.ini

    Unlike the original implementation the backend no longer performs its own
    path calculations.  Instead a :class:`~pysigil.policy.ScopePolicy` instance
    is injected which provides file locations and precedence information.
    """

    def __init__(self, *, policy: ScopePolicy | None = None) -> None:
        self.policy = policy or default_policy

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _scope_path(self, provider_id: str, scope: str, target_kind: str) -> Path:
        if scope == "default":
            dl = get_dev_link(provider_id)
            if dl is None:
                raise ProjectRootNotFoundError("No development link configured")
            path = dl.defaults_path
            path.parent.mkdir(parents=True, exist_ok=True)
            return path
        return self.policy.path(scope, provider_id)

    def _iter_read_paths(self, provider_id: str) -> Iterable[tuple[str, Path]]:
        defaults_path, _source = resolve_defaults(provider_id, "settings.ini")
        for scope in reversed(self.policy.precedence(read=True)):
            if scope in {"env", "core"}:
                continue
            if scope == "default":
                if defaults_path is not None:
                    yield "default", defaults_path
                continue
            try:
                yield scope, self.policy.path(scope, provider_id)
            except ProjectRootNotFoundError:
                continue

    def _read_sections(self, path: Path) -> dict[str, dict[str, str]]:
        try:
            return read_sections(path)
        except IniIOError as exc:  # pragma: no cover - defensive
            raise SigilLoadError(str(exc)) from exc


    # ------------------------------------------------------------------
    # SigilBackend API
    # ------------------------------------------------------------------
    def read_merged(self, provider_id: str) -> tuple[Mapping[str, str], Mapping[str, str]]:
        raw: dict[str, str] = {}
        source: dict[str, str] = {}
        for scope, path in self._iter_read_paths(provider_id):
            data = self._read_sections(path).get(provider_id, {})
            for k, v in data.items():
                raw[k] = v
                source[k] = scope
        prefix = f"SIGIL_{provider_id.upper().replace('-', '_')}_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                raw_key = key[len(prefix):].lower()
                raw[raw_key] = value
                source[raw_key] = "env"
        return raw, source

    def read_layers(self, provider_id: str) -> Mapping[str, Mapping[str, str]]:
        layers: dict[str, Mapping[str, str]] = {}
        for scope, path in self._iter_read_paths(provider_id):
            data = self._read_sections(path).get(provider_id, {})
            layers[scope] = data
        env_map: dict[str, str] = {}
        prefix = f"SIGIL_{provider_id.upper().replace('-', '_')}_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                raw_key = key[len(prefix):].lower()
                env_map[raw_key] = value
        if env_map:
            layers["env"] = env_map
        return layers

    def write_key(
        self,
        provider_id: str,
        key: str,
        raw_value: str,
        *,
        scope: str,
        target_kind: str,
    ) -> None:
        path = self._scope_path(provider_id, scope, target_kind)
        data = self._read_sections(path)
        section = data.setdefault(provider_id, {})
        section[key] = raw_value
        write_sections(path, data)

    def remove_key(
        self,
        provider_id: str,
        key: str,
        *,
        scope: str,
        target_kind: str,
    ) -> None:
        path = self._scope_path(provider_id, scope, target_kind)
        data = self._read_sections(path)
        section = data.get(provider_id, {})
        if key in section:
            del section[key]
        if section:
            data[provider_id] = section
        elif provider_id in data:
            del data[provider_id]
        write_sections(path, data)

    def ensure_section(
        self,
        provider_id: str,
        *,
        scope: str,
        target_kind: str,
    ) -> None:
        path = self._scope_path(provider_id, scope, target_kind)
        data = self._read_sections(path)
        data.setdefault(provider_id, {})
        write_sections(path, data)

    def write_target_for(self, provider_id: str) -> str:
        return self.policy.path("user", provider_id).name

    @contextmanager
    def transaction(
        self,
        provider_id: str,
        *,
        scope: str,
        target_kind: str,
    ) -> Iterator[MutableMapping[str, str]]:
        path = self._scope_path(provider_id, scope, target_kind)
        data = read_sections(path)
        section = dict(data.get(provider_id, {}))
        try:
            yield section
        except Exception:  # pragma: no cover - passthrough
            raise
        else:
            if section:
                data[provider_id] = section
            elif provider_id in data:
                del data[provider_id]
            write_sections(path, data)

class ProviderManager:
    """Orchestrates access to provider settings through a backend."""

    def __init__(self, spec: ProviderSpec, backend: SigilBackend):
        self.spec = spec
        self.backend = backend
        self._fields: dict[str, FieldSpec] = {f.key: f for f in spec.fields}

    def _field_for(self, key: str) -> FieldSpec:
        try:
            return self._fields[key]
        except KeyError as exc:  # pragma: no cover - defensive
            raise UnknownFieldError(key) from exc

    def effective(self) -> dict[str, FieldValue]:
        raw_map, source_map = self.backend.read_merged(self.spec.provider_id)
        result: dict[str, FieldValue] = {}
        for field in self.spec.fields:
            raw = raw_map.get(field.key)
            adapter = TYPE_REGISTRY[field.type].adapter
            try:
                value = adapter.parse(raw)
            except (TypeError, ValueError) as exc:
                value = None
                error = str(exc)
            else:
                error = None
            result[field.key] = FieldValue(
                value=value,
                source=source_map.get(field.key),
                raw=raw,
                error=error,
            )
        return result

    def layers(self) -> dict[str, dict[str, FieldValue | None]]:
        """Return raw and parsed values for each scope."""
        raw_layers = self.backend.read_layers(self.spec.provider_id)
        result: dict[str, dict[str, FieldValue | None]] = {}
        for field in self.spec.fields:
            per_scope: dict[str, FieldValue | None] = {}
            for scope, mapping in raw_layers.items():
                raw = mapping.get(field.key)
                if raw is None:
                    per_scope[scope] = None
                else:
                    adapter = TYPE_REGISTRY[field.type].adapter
                    try:
                        value = adapter.parse(raw)
                    except (TypeError, ValueError) as exc:
                        value = None
                        error = str(exc)
                    else:
                        error = None
                    per_scope[scope] = FieldValue(
                        value=value,
                        source=scope,
                        raw=raw,
                        error=error,
                    )
            result[field.key] = per_scope
        return result

    @contextmanager
    def transaction(self, *, scope: str = "user") -> Iterator[SimpleNamespace]:
        target = self.backend.write_target_for(self.spec.provider_id)
        with self.backend.transaction(
            self.spec.provider_id, scope=scope, target_kind=target
        ) as section:
            def set_value(key: str, python_value: Any) -> None:
                field = self._field_for(key)
                adapter = TYPE_REGISTRY[field.type].adapter
                adapter.validate(python_value, field)
                section[key] = adapter.serialize(python_value)

            def clear_value(key: str) -> None:
                self._field_for(key)
                section.pop(key, None)

            yield SimpleNamespace(set=set_value, clear=clear_value)

    def set(self, key: str, python_value: Any, *, scope: str = "user") -> None:
        field = self._field_for(key)
        adapter = TYPE_REGISTRY[field.type].adapter
        adapter.validate(python_value, field)
        raw_value = adapter.serialize(python_value)
        target = self.backend.write_target_for(self.spec.provider_id)
        self.backend.write_key(
            self.spec.provider_id,
            key,
            raw_value,
            scope=scope,
            target_kind=target,
        )

    def clear(self, key: str, *, scope: str = "user") -> None:
        self._field_for(key)  # validate existence
        target = self.backend.write_target_for(self.spec.provider_id)
        self.backend.remove_key(
            self.spec.provider_id,
            key,
            scope=scope,
            target_kind=target,
        )

    def init(self, scope: str) -> None:
        target = self.backend.write_target_for(self.spec.provider_id)
        self.backend.ensure_section(
            self.spec.provider_id, scope=scope, target_kind=target
        )


# ---------------------------------------------------------------------------
# Provider specification persistence helpers
# ---------------------------------------------------------------------------

def save_provider_spec(path: Path, spec: ProviderSpec) -> None:
    """Persist provider metadata and field definitions at *path*.

    The provider's package-level information (such as ``provider_id`` and
    ``schema_version``) along with its field specifications are written to
    disk in a deterministic JSON format.  The file is written atomically by
    using a temporary file which is then moved into place.  Parent directories
    are created as needed so callers can provide paths in yet-to-exist
    configuration roots.
    """

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(spec.to_gui_doc_v0(), fh, indent=2, sort_keys=True)
    tmp.replace(path)


def load_provider_spec(path: Path) -> ProviderSpec:
    """Load a :class:`ProviderSpec` from *path*.

    The file must contain JSON previously written by :func:`save_provider_spec`.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    fields = [FieldSpec(**f) for f in data.get("fields", [])]
    return ProviderSpec(
        provider_id=data["provider_id"],
        schema_version=data["schema_version"],
        title=data.get("title"),
        description=data.get("description"),
        fields=fields,
        sections_order=data.get("sections_order"),
        sections_collapsed=data.get("sections_collapsed"),
    )


def register_provider(
    path: Path,
    provider_id: str,
    schema_version: str,
    *,
    title: str | None = None,
    description: str | None = None,
    fields: Iterable[FieldSpec] = (),
    sections_order: Iterable[str] | None = None,
    sections_collapsed: Iterable[str] | None = None,
) -> ProviderSpec:
    """Create and persist a :class:`ProviderSpec` and return it."""
    spec = ProviderSpec(
        provider_id=provider_id,
        schema_version=schema_version,
        title=title,
        description=description,
        fields=fields,
        sections_order=sections_order,
        sections_collapsed=sections_collapsed,
    )
    save_provider_spec(path, spec)
    return spec


def add_field_spec(path: Path, field: FieldSpec) -> ProviderSpec:
    """Append *field* to the provider spec stored at *path* and re-save."""
    spec = load_provider_spec(path)
    spec = ProviderSpec(
        provider_id=spec.provider_id,
        schema_version=spec.schema_version,
        title=spec.title,
        description=spec.description,
        fields=list(spec.fields) + [field],
        sections_order=spec.sections_order,
        sections_collapsed=spec.sections_collapsed,
    )
    save_provider_spec(path, spec)
    return spec


def update_field_spec(path: Path, field: FieldSpec) -> ProviderSpec:
    """Replace an existing *field* in the provider spec stored at *path*."""

    spec = load_provider_spec(path)
    fields = list(spec.fields)
    for idx, existing in enumerate(fields):
        if existing.key == field.key:
            fields[idx] = field
            break
    else:  # pragma: no cover - defensive
        raise KeyError(f"unknown field {field.key!r}")
    spec = ProviderSpec(
        provider_id=spec.provider_id,
        schema_version=spec.schema_version,
        title=spec.title,
        description=spec.description,
        fields=fields,
        sections_order=spec.sections_order,
        sections_collapsed=spec.sections_collapsed,
    )
    save_provider_spec(path, spec)
    return spec


def remove_field_spec(path: Path, key: str) -> ProviderSpec:
    """Remove the field identified by *key* from the provider spec at *path*."""

    spec = load_provider_spec(path)
    fields = [f for f in spec.fields if f.key != key]
    if len(fields) == len(spec.fields):  # pragma: no cover - defensive
        raise KeyError(f"unknown field {key!r}")
    spec = ProviderSpec(
        provider_id=spec.provider_id,
        schema_version=spec.schema_version,
        title=spec.title,
        description=spec.description,
        fields=fields,
        sections_order=spec.sections_order,
        sections_collapsed=spec.sections_collapsed,
    )
    save_provider_spec(path, spec)
    return spec


__all__ = [
    "BooleanAdapter",
    "FieldSpec",
    "FieldValue",
    "FieldType",
    "IntegerAdapter",
    "IntegerOptions",
    "IniFileBackend",
    "NumberAdapter",
    "ProviderManager",
    "ProviderSpec",
    "SigilBackend",
    "SpecBackend",
    "InMemorySpecBackend",
    "IniSpecBackend",
    "UnknownProviderError",
    "DuplicateProviderError",
    "ConflictError",
    "StringAdapter",
    "StringListAdapter",
    "TYPE_REGISTRY",
    "TypeAdapter",
    "add_field_spec",
    "update_field_spec",
    "remove_field_spec",
    "load_provider_spec",
    "register_provider",
    "save_provider_spec",
    "SHORT_DESC_MAX",
]

