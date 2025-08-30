from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .errors import (
    ConflictError,
    DuplicateFieldError,
    DuplicateProviderError,
    IOFailureError,
    PolicyError,
    SigilError,
    UnknownFieldError,
    UnknownProviderError,
    ValidationError,
)
from .orchestrator import Orchestrator
from .policy import policy
from .settings_metadata import FieldSpec, FieldValue, ProviderSpec

__all__ = [
    "SigilError",
    "UnknownProviderError",
    "UnknownFieldError",
    "DuplicateFieldError",
    "ValidationError",
    "PolicyError",
    "ConflictError",
    "IOFailureError",
    "FieldInfo",
    "ValueInfo",
    "ProviderInfo",
    "providers",
    "get_provider",
    "handle",
    "register_provider",
    "ProviderHandle",
]


# ---------------------------------------------------------------------------
# dataclasses returned to callers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldInfo:
    key: str
    type: str
    label: str | None
    description: str | None


@dataclass(frozen=True)
class ValueInfo:
    value: Any | None
    source: Literal["user", "user-local", "project", "project-local"] | None
    raw: str | None


@dataclass(frozen=True)
class ProviderInfo:
    provider_id: str
    title: str | None
    description: str | None
    fields: list[FieldInfo]


def _field_info(spec: FieldSpec) -> FieldInfo:
    return FieldInfo(
        key=spec.key,
        type=spec.type,
        label=spec.label,
        description=spec.description,
    )


def _provider_info(spec: ProviderSpec) -> ProviderInfo:
    return ProviderInfo(
        provider_id=spec.provider_id,
        title=spec.title,
        description=spec.description,
        fields=[_field_info(f) for f in spec.fields],
    )


def _value_info(val: FieldValue) -> ValueInfo:
    return ValueInfo(value=val.value, source=val.source, raw=val.raw)


# ---------------------------------------------------------------------------
# orchestrator wiring
# ---------------------------------------------------------------------------

_ORCH = Orchestrator()


# ---------------------------------------------------------------------------
# top level API
# ---------------------------------------------------------------------------

def providers() -> list[str]:
    """List all registered provider ids."""
    return _ORCH.list_providers()


def get_provider(provider_id: str) -> ProviderInfo:
    spec = _ORCH.reload_spec(provider_id)
    return _provider_info(spec)


def handle(provider_id: str) -> ProviderHandle:
    get_provider(provider_id)  # ensure existence
    return ProviderHandle(provider_id)


def register_provider(
    provider_id: str,
    *,
    title: str | None = None,
    description: str | None = None,
) -> ProviderInfo:
    try:
        spec = _ORCH.register_provider(
            provider_id, title=title, description=description
        )
    except DuplicateProviderError:
        spec = _ORCH.reload_spec(provider_id)
    return _provider_info(spec)


# ---------------------------------------------------------------------------
# provider bound façade
# ---------------------------------------------------------------------------


class ProviderHandle:
    provider_id: str

    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id

    def _manager(self):  # pragma: no cover - simple wrapper
        return _ORCH._manager(self.provider_id)  # type: ignore[attr-defined]

    # -------- Metadata (field catalog) --------
    def info(self) -> ProviderInfo:
        return get_provider(self.provider_id)

    def fields(self) -> list[FieldInfo]:
        return self.info().fields

    def add_field(
        self,
        key: str,
        type: str,
        *,
        label: str | None = None,
        description: str | None = None,
        init_scope: Literal[
            "user", "user-local", "project", "project-local"
        ] | None = "user",
    ) -> FieldInfo:
        try:
            field = _ORCH.add_field(
                self.provider_id,
                key=key,
                type=type,
                label=label,
                description=description,
            )
        except DuplicateFieldError as exc:
            raise DuplicateFieldError(key) from exc
        except PolicyError as exc:
            raise PolicyError(str(exc)) from exc
        if init_scope is not None:
            try:
                self._manager().init(init_scope)
            except PolicyError as exc:  # pragma: no cover - defensive
                raise PolicyError(str(exc)) from exc
        return _field_info(field)

    def edit_field(
        self,
        key: str,
        *,
        new_key: str | None = None,
        new_type: str | None = None,
        label: str | None = None,
        description: str | None = None,
        on_type_change: Literal["convert", "clear"] = "convert",
        migrate_scopes: tuple[
            Literal["user", "user-local", "project", "project-local"], ...
        ] = ("user",),
    ) -> FieldInfo:
        try:
            field = _ORCH.edit_field(
                self.provider_id,
                key,
                new_key=new_key,
                new_type=new_type,
                label=label,
                description=description,
                on_type_change=on_type_change,
            )
        except UnknownFieldError as exc:
            raise UnknownFieldError(key) from exc
        except DuplicateFieldError as exc:
            raise DuplicateFieldError(str(exc)) from exc
        except PolicyError as exc:
            raise PolicyError(str(exc)) from exc
        return _field_info(field)

    def delete_field(
        self,
        key: str,
        *,
        remove_values: bool = False,
        scopes: tuple[
            Literal["user", "user-local", "project", "project-local"], ...
        ] = ("user", "project"),
    ) -> None:
        try:
            _ORCH.delete_field(
                self.provider_id,
                key,
                remove_values=remove_values,
                scopes=scopes,
            )
        except UnknownFieldError as exc:
            raise UnknownFieldError(key) from exc
        except PolicyError as exc:
            raise PolicyError(str(exc)) from exc

    # Untracked (manual INI edits)
    def untracked_keys(self) -> list[str]:
        return _ORCH.find_untracked_keys(self.provider_id)

    def adopt_untracked(self, mapping: Mapping[str, str]) -> list[FieldInfo]:
        specs = _ORCH.adopt_untracked(self.provider_id, dict(mapping))
        return [_field_info(s) for s in specs]

    # -------- Values (typed + scope aware) --------
    def effective(self) -> dict[str, ValueInfo]:
        values = _ORCH.get_effective(self.provider_id)
        return {k: _value_info(v) for k, v in values.items()}

    def layers(self) -> dict[str, dict[str, ValueInfo | None]]:
        """Return values for all scopes for this provider."""
        layers = _ORCH.get_layers(self.provider_id)
        result: dict[str, dict[str, ValueInfo | None]] = {}
        for key, per_scope in layers.items():
            result[key] = {
                scope: (_value_info(v) if v is not None else None)
                for scope, v in per_scope.items()
            }
        return result

    def get(self, key: str) -> ValueInfo:
        eff = self.effective()
        if key not in eff:
            raise UnknownFieldError(key)
        return eff[key]

    def set(
        self,
        key: str,
        value: object,
        *,
        scope: Literal["user", "user-local", "project", "project-local"] = "user",
    ) -> None:
        try:
            _ORCH.set_value(self.provider_id, key, value, scope=scope)
        except ValidationError as exc:
            raise ValidationError(str(exc)) from exc
        except PolicyError as exc:
            raise PolicyError(str(exc)) from exc
        except KeyError as exc:  # propagated by provider manager
            raise UnknownFieldError(key) from exc

    def clear(
        self,
        key: str,
        *,
        scope: Literal["user", "user-local", "project", "project-local"] = "user",
    ) -> None:
        try:
            _ORCH.clear_value(self.provider_id, key, scope=scope)
        except PolicyError as exc:
            raise PolicyError(str(exc)) from exc
        except KeyError as exc:
            raise UnknownFieldError(key) from exc

    def set_many(
        self,
        updates: Mapping[str, object],
        *,
        scope: Literal["user", "user-local", "project", "project-local"] = "user",
        atomic: bool = True,
    ) -> None:
        """Set multiple configuration values.

        With ``atomic=True`` (the default) updates are staged and committed
        only if all validations and writes succeed.
        """
        try:
            _ORCH.set_many(
                self.provider_id, dict(updates), scope=scope, atomic=atomic
            )
        except ValidationError as exc:
            raise ValidationError(str(exc)) from exc
        except UnknownFieldError as exc:
            raise UnknownFieldError(str(exc)) from exc
        except PolicyError as exc:
            raise PolicyError(str(exc)) from exc
        except KeyError as exc:
            raise UnknownFieldError(str(exc)) from exc

    # -------- Utilities / ergonomics --------
    def init(
        self, *, scope: Literal["user", "user-local", "project", "project-local"] = "user"
    ) -> None:
        try:
            self._manager().init(scope)
        except PolicyError as exc:
            raise PolicyError(str(exc)) from exc

    def export_spec(self, dest: str | Path | None = None) -> Path:
        if dest is None:
            dest = Path(f"{self.provider_id}-spec.json")
        try:
            return _ORCH.export_spec(self.provider_id, dest)
        except PolicyError as exc:
            raise PolicyError(str(exc)) from exc

    def reload_spec(self) -> ProviderInfo:
        spec = _ORCH.reload_spec(self.provider_id)
        return _provider_info(spec)


    def target_path(
        self, scope: Literal["user", "user-local", "project", "project-local"] = "user"
    ) -> Path:

        """Return the file path used for *scope* writes."""
        return policy.path(scope, self.provider_id)
