"""Lightweight object graph for Sigil GUI/CLI interaction.

This module defines a small set of immutable data structures used to
describe configuration providers and their fields.  It deliberately keeps
runtime policy such as file locations behind a simple backend interface so
that higher layers (GUI, CLI) never touch the file system directly.

The implementation follows the design described in the user request and is
intended to be a stable, extendable base for future GUI work.
"""

from __future__ import annotations

import json
import configparser
from dataclasses import dataclass, field as dataclass_field
from pathlib import Path
import re
from typing import Any, Dict, Iterable, Literal, Mapping, Protocol
from uuid import uuid4

from .config import host_id
from .io_config import read_sections, write_sections
from .paths import user_config_dir
from .root import ProjectRootNotFoundError, find_project_root


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

    def validate(self, value: Any, spec: "FieldSpec") -> None:
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

    def validate(self, value: Any, spec: "FieldSpec") -> None:
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

    def validate(self, value: Any, spec: "FieldSpec") -> None:
        if value is not None and not isinstance(value, int):
            raise TypeError("expected int")


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

    def validate(self, value: Any, spec: "FieldSpec") -> None:
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

    def validate(self, value: Any, spec: "FieldSpec") -> None:
        if value is not None and not isinstance(value, bool):
            raise TypeError("expected bool")


TYPE_REGISTRY: Dict[str, TypeAdapter] = {
    "string": StringAdapter(),
    "integer": IntegerAdapter(),
    "number": NumberAdapter(),
    "boolean": BooleanAdapter(),
}

_PEP503_RE = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")

######################
##### FIELD SPEC #####
######################

@dataclass(frozen=True)
class FieldSpec:
    """Specification for a single configuration field."""

    key: str
    type: str
    label: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        if self.type not in TYPE_REGISTRY:
            raise ValueError(f"unknown type: {self.type!r}")

    def to_gui_v0(self) -> Dict[str, Any]:
        """Return a minimal GUI representation."""

        return {
            "key": self.key,
            "type": self.type,
            "label": self.label,
            "description": self.description,
        }


@dataclass
class FieldValue:
    """Parsed field value along with provenance information."""

    value: Any | None
    source: Literal["user", "user-local", "project", "project-local"] | None = None
    raw: str | None = None

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

    def __post_init__(self) -> None:
        if not _PEP503_RE.fullmatch(self.provider_id):
            raise ValueError(
                f"provider_id {self.provider_id!r} is not PEP-503 normalised"
            )
        # Freeze iterable of fields into a tuple for immutability
        object.__setattr__(self, "fields", tuple(self.fields))

    def to_gui_doc_v0(self) -> Dict[str, Any]:
        """Return a dict representation for GUI consumption."""

        return {
            "schema_version": self.schema_version,
            "provider_id": self.provider_id,
            "title": self.title,
            "description": self.description,
            "fields": [f.to_gui_v0() for f in self.fields],
        }

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


class SpecBackendError(Exception):
    """Base class for errors raised by :class:`SpecBackend` implementations."""


class UnknownProviderError(SpecBackendError):
    """Raised when a provider is requested that does not exist."""


class DuplicateProviderError(SpecBackendError):
    """Raised when attempting to create a provider that already exists."""


class ConflictError(SpecBackendError):
    """Raised when concurrent spec modifications conflict."""


class InMemorySpecBackend:
    """Simple :class:`SpecBackend` storing data in memory.

    The backend assigns a random *etag* to every stored specification so
    that concurrent modification can be detected by higher layers.
    """

    def __init__(self) -> None:
        self._specs: Dict[str, ProviderSpec] = {}
        self._etags: Dict[str, str] = {}

    def get_provider_ids(self) -> list[str]:  # pragma: no cover - trivial
        return sorted(self._specs)

    def get_spec(self, provider_id: str) -> ProviderSpec:
        try:
            return self._specs[provider_id]
        except KeyError as exc:  # pragma: no cover - defensive
            raise UnknownProviderError(provider_id) from exc


class IniSpecBackend:
    """Persist provider specifications in simple INI files.

    Provider metadata is stored in ``<base>/<provider_id>.ini`` where the
    ``__meta__`` section holds package level information and each field is
    represented by a ``field:<key>`` section with ``type``, ``label`` and
    ``description`` keys.  An in-memory ``etag`` is maintained for conflict
    detection in the same manner as :class:`InMemorySpecBackend`.

    Parameters
    ----------
    base_dir:
        Directory in which specification files are stored.  Defaults to the
        current user's configuration directory for ``sigil``.
    """

    def __init__(self, *, base_dir: Path | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else Path(user_config_dir("sigil"))
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._etags: Dict[str, str] = {}

    # ------------------------------------------------------------ helpers
    def _path(self, provider_id: str) -> Path:
        return self.base_dir / f"{provider_id}.ini"

    def _write(self, path: Path, spec: ProviderSpec) -> None:
        parser = configparser.ConfigParser()
        meta: Dict[str, str] = {"schema_version": spec.schema_version}
        if spec.title is not None:
            meta["title"] = spec.title
        if spec.description is not None:
            meta["description"] = spec.description
        parser["__meta__"] = meta
        for field in spec.fields:
            section = f"field:{field.key}"
            parser.add_section(section)
            parser.set(section, "type", field.type)
            if field.label is not None:
                parser.set(section, "label", field.label)
            if field.description is not None:
                parser.set(section, "description", field.description)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w") as fh:
            parser.write(fh)
        tmp.replace(path)

    def _read(self, path: Path, provider_id: str) -> ProviderSpec:
        parser = configparser.ConfigParser()
        if not path.exists():
            raise UnknownProviderError(provider_id)
        parser.read(path)
        meta = parser["__meta__"]
        fields: list[FieldSpec] = []
        for section in parser.sections():
            if not section.startswith("field:"):
                continue
            key = section.split(":", 1)[1]
            data = parser[section]
            fields.append(
                FieldSpec(
                    key=key,
                    type=data.get("type", "string"),
                    label=data.get("label"),
                    description=data.get("description"),
                )
            )
        return ProviderSpec(
            provider_id=provider_id,
            schema_version=meta.get("schema_version", "0"),
            title=meta.get("title"),
            description=meta.get("description"),
            fields=fields,
        )

    # -------------------------------------------------------------- API
    def get_provider_ids(self) -> list[str]:  # pragma: no cover - trivial
        return sorted(p.stem for p in self.base_dir.glob("*.ini"))

    def get_spec(self, provider_id: str) -> ProviderSpec:
        path = self._path(provider_id)
        return self._read(path, provider_id)

    def save_spec(self, spec: ProviderSpec, *, expected_etag: str | None = None) -> str:
        current = self._etags.get(spec.provider_id)
        if expected_etag is not None and current is not None and expected_etag != current:
            raise ConflictError(spec.provider_id)
        path = self._path(spec.provider_id)
        self._write(path, spec)
        etag = uuid4().hex
        self._etags[spec.provider_id] = etag
        return etag

    def create_spec(self, spec: ProviderSpec) -> str:
        path = self._path(spec.provider_id)
        if path.exists():
            raise DuplicateProviderError(spec.provider_id)
        self._write(path, spec)
        etag = uuid4().hex
        self._etags[spec.provider_id] = etag
        return etag

    def delete_spec(self, provider_id: str) -> None:
        path = self._path(provider_id)
        if path.exists():
            path.unlink()
        self._etags.pop(provider_id, None)

    def etag(self, provider_id: str) -> str:
        if provider_id not in self._etags:
            if not self._path(provider_id).exists():
                raise UnknownProviderError(provider_id)
            self._etags[provider_id] = uuid4().hex
        return self._etags[provider_id]


# ---- configuration storage ----

class SigilBackend(Protocol):
    """Minimal interface that hides IO/policy details from the manager."""

    def read_merged(self, provider_id: str) -> tuple[Mapping[str, str], Mapping[str, str]]:
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


class IniFileBackend:
    """Store provider settings in INI files on the filesystem.

    The backend mirrors the layout used by the existing command line tools::

        ~/.config/sigil/<provider>/settings.ini
        ~/.config/sigil/<provider>/settings-local-<host>.ini
        <project>/.sigil/<provider>/settings.ini
        <project>/.sigil/<provider>/settings-local-<host>.ini

    Parameters
    ----------
    user_dir:
        Base directory for user-level configuration.  Defaults to the current
        user's configuration directory for ``sigil``.
    project_dir:
        Base directory for project-level configuration.  If not supplied an
        attempt is made to locate the current project root.  When no project
        root can be found, project configuration is ignored.
    host:
        Hostname used for local overrides.  When omitted the normalized current
        host name is used.
    """

    def __init__(
        self,
        *,
        user_dir: Path | None = None,
        project_dir: Path | None = None,
        host: str | None = None,
    ) -> None:
        self.user_dir = Path(user_dir) if user_dir else Path(user_config_dir("sigil"))
        if project_dir is None:
            try:
                root = find_project_root()
            except ProjectRootNotFoundError:
                root = None
            self.project_dir = root / ".sigil" if root is not None else None
        else:
            self.project_dir = Path(project_dir)
        self.host = host or host_id()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _scope_path(self, provider_id: str, scope: str, target_kind: str) -> Path:
        if scope == "user":
            base = self.user_dir / provider_id
        elif scope == "project":
            if self.project_dir is None:
                raise ProjectRootNotFoundError("No project directory configured")
            base = self.project_dir / provider_id
        else:  # pragma: no cover - defensive
            raise ValueError(f"unknown scope {scope!r}")
        base.mkdir(parents=True, exist_ok=True)
        return base / target_kind

    def _iter_read_paths(self, provider_id: str) -> Iterable[tuple[str, Path]]:
        yield "user", self.user_dir / provider_id / "settings.ini"
        yield "user-local", self.user_dir / provider_id / f"settings-local-{self.host}.ini"
        if self.project_dir is not None:
            yield "project", self.project_dir / provider_id / "settings.ini"
            yield (
                "project-local",
                self.project_dir / provider_id / f"settings-local-{self.host}.ini",
            )

    # ------------------------------------------------------------------
    # SigilBackend API
    # ------------------------------------------------------------------
    def read_merged(self, provider_id: str) -> tuple[Mapping[str, str], Mapping[str, str]]:
        raw: Dict[str, str] = {}
        source: Dict[str, str] = {}
        for scope, path in self._iter_read_paths(provider_id):
            data = read_sections(path).get(provider_id, {})
            for k, v in data.items():
                raw[k] = v
                source[k] = scope
        return raw, source

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
        data = read_sections(path)
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
        data = read_sections(path)
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
        data = read_sections(path)
        data.setdefault(provider_id, {})
        write_sections(path, data)

    def write_target_for(self, provider_id: str) -> str:
        if provider_id == "user-custom":
            return f"settings-local-{self.host}.ini"
        return "settings.ini"

class ProviderManager:
    """Orchestrates access to provider settings through a backend."""

    def __init__(self, spec: ProviderSpec, backend: SigilBackend):
        self.spec = spec
        self.backend = backend
        self._fields: Dict[str, FieldSpec] = {f.key: f for f in spec.fields}

    def _field_for(self, key: str) -> FieldSpec:
        try:
            return self._fields[key]
        except KeyError as exc:  # pragma: no cover - defensive
            raise KeyError(f"unknown key {key!r}") from exc

    def effective(self) -> Dict[str, FieldValue]:
        raw_map, source_map = self.backend.read_merged(self.spec.provider_id)
        result: Dict[str, FieldValue] = {}
        for field in self.spec.fields:
            raw = raw_map.get(field.key)
            adapter = TYPE_REGISTRY[field.type]
            value = adapter.parse(raw)
            result[field.key] = FieldValue(
                value=value, source=source_map.get(field.key), raw=raw
            )
        return result

    def set(self, key: str, python_value: Any, *, scope: str = "user") -> None:
        field = self._field_for(key)
        adapter = TYPE_REGISTRY[field.type]
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
    )


def register_provider(
    path: Path,
    provider_id: str,
    schema_version: str,
    *,
    title: str | None = None,
    description: str | None = None,
    fields: Iterable[FieldSpec] = (),
) -> ProviderSpec:
    """Create and persist a :class:`ProviderSpec` and return it."""
    spec = ProviderSpec(
        provider_id=provider_id,
        schema_version=schema_version,
        title=title,
        description=description,
        fields=fields,
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
    )
    save_provider_spec(path, spec)
    return spec


__all__ = [
    "BooleanAdapter",
    "FieldSpec",
    "FieldValue",
    "IntegerAdapter",
    "IniFileBackend",
    "NumberAdapter",
    "ProviderManager",
    "ProviderSpec",
    "SigilBackend",
    "SpecBackend",
    "SpecBackendError",
    "InMemorySpecBackend",
    "IniSpecBackend",
    "UnknownProviderError",
    "DuplicateProviderError",
    "ConflictError",
    "StringAdapter",
    "TYPE_REGISTRY",
    "TypeAdapter",
    "add_field_spec",
    "update_field_spec",
    "remove_field_spec",
    "load_provider_spec",
    "register_provider",
    "save_provider_spec",
]

