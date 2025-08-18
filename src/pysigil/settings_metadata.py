"""Lightweight object graph for Sigil GUI/CLI interaction.

This module defines a small set of immutable data structures used to
describe configuration providers and their fields.  It deliberately keeps
runtime policy such as file locations behind a simple backend interface so
that higher layers (GUI, CLI) never touch the file system directly.

The implementation follows the design described in the user request and is
intended to be a stable, extendable base for future GUI work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Dict, Iterable, Literal, Mapping, Protocol


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
        if not isinstance(value, (int, float)):
            raise TypeError("expected number")
        return str(value)

    def validate(self, value: Any, spec: "FieldSpec") -> None:
        if value is not None and not isinstance(value, (int, float)):
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


@dataclass(frozen=True)
class ProviderSpec:
    """Specification for a provider's GUI/CLI visible fields."""

    provider_id: str
    schema_version: str
    title: str | None = None
    description: str | None = None
    fields: Iterable[FieldSpec] = field(default_factory=tuple)

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


__all__ = [
    "BooleanAdapter",
    "FieldSpec",
    "FieldValue",
    "IntegerAdapter",
    "NumberAdapter",
    "ProviderManager",
    "ProviderSpec",
    "SigilBackend",
    "StringAdapter",
    "TYPE_REGISTRY",
    "TypeAdapter",
]

