"""High level orchestration layer for Sigil configuration.

This module exposes a thin façade that ties together a specification
backend (storing provider metadata) and the existing configuration
backend.  It offers a small, UI agnostic API for managing provider
metadata and reading/writing typed configuration values.  The
implementation is deliberately compact but mirrors the design proposed in
the accompanying user request so that it can grow organically.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Literal

from .authoring import normalize_provider_id
from .settings_metadata import (
    FieldSpec,
    FieldValue,
    IniFileBackend,
    IniSpecBackend,
    ProviderManager,
    ProviderSpec,
    SigilBackend,
    SpecBackend,
    TYPE_REGISTRY,
    save_provider_spec,
)
from .root import ProjectRootNotFoundError


# ---------------------------------------------------------------------------
# errors
# ---------------------------------------------------------------------------


class OrchestratorError(Exception):
    """Base class for orchestrator specific errors."""


class UnknownFieldError(OrchestratorError):
    """Raised when a field key is unknown."""


class DuplicateFieldError(OrchestratorError):
    """Raised when attempting to add a field that already exists."""


class ValidationError(OrchestratorError):
    """Raised when value validation fails."""


class PolicyError(OrchestratorError):
    """Raised when the configuration policy prevents an operation."""


# ---------------------------------------------------------------------------
# orchestrator implementation
# ---------------------------------------------------------------------------


class Orchestrator:
    """High level façade coordinating spec and config backends."""

    def __init__(
        self,
        spec_backend: SpecBackend | None = None,
        config_backend: SigilBackend | None = None,
        *,
        user_dir: Path | None = None,
        project_dir: Path | None = None,
        host: str | None = None,
    ) -> None:
        if spec_backend is None:
            spec_backend = IniSpecBackend(base_dir=user_dir)
        if config_backend is None:
            config_backend = IniFileBackend(
                user_dir=user_dir, project_dir=project_dir, host=host
            )
        self.spec_backend = spec_backend
        self.config_backend = config_backend

    # ---- Provider / package metadata ----
    def register_provider(
        self,
        provider_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
    ) -> ProviderSpec:
        pid = normalize_provider_id(provider_id)
        spec = ProviderSpec(
            provider_id=pid,
            schema_version="0",
            title=title,
            description=description,
        )
        self.spec_backend.create_spec(spec)
        return spec

    def edit_provider(
        self,
        provider_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
    ) -> ProviderSpec:
        pid = normalize_provider_id(provider_id)
        spec = self.spec_backend.get_spec(pid)
        etag = self.spec_backend.etag(pid)
        updated = replace(
            spec,
            title=spec.title if title is None else title,
            description=spec.description if description is None else description,
        )
        self.spec_backend.save_spec(updated, expected_etag=etag)
        return updated

    def delete_provider(self, provider_id: str) -> None:
        pid = normalize_provider_id(provider_id)
        self.spec_backend.delete_spec(pid)

    # ---- Field metadata ----
    def add_field(
        self,
        provider_id: str,
        *,
        key: str,
        type: str,
        label: str | None = None,
        description: str | None = None,
    ) -> FieldSpec:
        pid = normalize_provider_id(provider_id)
        spec = self.spec_backend.get_spec(pid)
        if key in {f.key for f in spec.fields}:
            raise DuplicateFieldError(key)
        field = FieldSpec(key=key, type=type, label=label, description=description)
        new_spec = replace(spec, fields=tuple(spec.fields) + (field,))
        etag = self.spec_backend.etag(pid)
        self.spec_backend.save_spec(new_spec, expected_etag=etag)
        mgr = ProviderManager(new_spec, self.config_backend)
        try:  # ensure default section exists for user scope
            mgr.init("user")
        except ProjectRootNotFoundError as exc:  # pragma: no cover - defensive
            raise PolicyError(str(exc)) from exc
        return field

    def edit_field(
        self,
        provider_id: str,
        key: str,
        *,
        new_key: str | None = None,
        new_type: str | None = None,
        label: str | None = None,
        description: str | None = None,
        on_type_change: Literal["convert", "clear"] = "convert",
    ) -> FieldSpec:
        pid = normalize_provider_id(provider_id)
        spec = self.spec_backend.get_spec(pid)
        fields = list(spec.fields)
        try:
            index = next(i for i, f in enumerate(fields) if f.key == key)
        except StopIteration as exc:
            raise UnknownFieldError(key) from exc

        old_field = fields[index]
        nk = new_key or key
        nt = new_type or old_field.type

        if nk != key and nk in {f.key for f in fields}:
            raise DuplicateFieldError(nk)

        fields[index] = FieldSpec(
            key=nk,
            type=nt,
            label=old_field.label if label is None else label,
            description=old_field.description if description is None else description,
        )

        new_spec = replace(spec, fields=tuple(fields))
        etag = self.spec_backend.etag(pid)
        self.spec_backend.save_spec(new_spec, expected_etag=etag)

        raw_map, source_map = self.config_backend.read_merged(pid)
        raw = raw_map.get(key)
        source = source_map.get(key)
        if raw is not None and source is not None:
            scope = source.split("-")[0]
            target = self.config_backend.write_target_for(pid)
            if nk != key:
                self.config_backend.write_key(pid, nk, raw, scope=scope, target_kind=target)
                self.config_backend.remove_key(pid, key, scope=scope, target_kind=target)
                raw_map[nk] = raw
                raw = raw_map.get(nk)
            if nt != old_field.type:
                if on_type_change == "convert":
                    adapter = TYPE_REGISTRY[nt]
                    value = adapter.parse(raw)
                    raw_new = adapter.serialize(value)
                    self.config_backend.write_key(
                        pid, nk, raw_new, scope=scope, target_kind=target
                    )
                elif on_type_change == "clear":
                    self.config_backend.remove_key(pid, nk, scope=scope, target_kind=target)

        return fields[index]

    def delete_field(
        self,
        provider_id: str,
        key: str,
        *,
        remove_values: bool = False,
        scopes: tuple[str, ...] = ("user", "project"),
    ) -> None:
        pid = normalize_provider_id(provider_id)
        spec = self.spec_backend.get_spec(pid)
        fields = [f for f in spec.fields if f.key != key]
        if len(fields) == len(spec.fields):
            raise UnknownFieldError(key)
        new_spec = replace(spec, fields=tuple(fields))
        etag = self.spec_backend.etag(pid)
        self.spec_backend.save_spec(new_spec, expected_etag=etag)

        if remove_values:
            target = self.config_backend.write_target_for(pid)
            for scope in scopes:
                try:
                    self.config_backend.remove_key(
                        pid, key, scope=scope, target_kind=target
                    )
                except ProjectRootNotFoundError as exc:  # pragma: no cover - defensive
                    raise PolicyError(str(exc)) from exc

    # ---- Discovery ----
    def list_providers(self) -> list[str]:
        return self.spec_backend.get_provider_ids()

    def list_fields(self, provider_id: str) -> list[FieldSpec]:
        pid = normalize_provider_id(provider_id)
        spec = self.spec_backend.get_spec(pid)
        return list(spec.fields)

    def find_untracked_keys(self, provider_id: str) -> list[str]:
        pid = normalize_provider_id(provider_id)
        spec = self.spec_backend.get_spec(pid)
        raw_map, _ = self.config_backend.read_merged(pid)
        tracked = {f.key for f in spec.fields}
        return sorted(set(raw_map) - tracked)

    def adopt_untracked(self, provider_id: str, mapping: dict[str, str]) -> list[FieldSpec]:
        added: list[FieldSpec] = []
        for key, type in mapping.items():
            added.append(self.add_field(provider_id, key=key, type=type))
        return added

    # ---- Values ----
    def _manager(self, provider_id: str) -> ProviderManager:
        pid = normalize_provider_id(provider_id)
        spec = self.spec_backend.get_spec(pid)
        return ProviderManager(spec, self.config_backend)

    def get_effective(self, provider_id: str) -> dict[str, FieldValue]:
        return self._manager(provider_id).effective()

    def set_value(
        self,
        provider_id: str,
        key: str,
        value: object,
        *,
        scope: Literal["user", "project"] = "user",
    ) -> None:
        mgr = self._manager(provider_id)
        try:
            mgr.set(key, value, scope=scope)
        except (TypeError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        except ProjectRootNotFoundError as exc:
            raise PolicyError(str(exc)) from exc

    def clear_value(
        self,
        provider_id: str,
        key: str,
        *,
        scope: Literal["user", "project"] = "user",
    ) -> None:
        mgr = self._manager(provider_id)
        try:
            mgr.clear(key, scope=scope)
        except ProjectRootNotFoundError as exc:
            raise PolicyError(str(exc)) from exc

    def set_many(
        self,
        provider_id: str,
        updates: dict[str, object],
        *,
        scope: Literal["user", "project"] = "user",
        atomic: bool = True,
    ) -> None:
        mgr = self._manager(provider_id)
        if atomic:
            # Validate first
            fields = mgr._fields  # pylint: disable=protected-access
            for key, value in updates.items():
                field = fields.get(key)
                if field is None:
                    raise UnknownFieldError(key)
                adapter = TYPE_REGISTRY[field.type]
                try:
                    adapter.validate(value, field)
                except (TypeError, ValueError) as exc:
                    raise ValidationError(str(exc)) from exc
        for key, value in updates.items():
            mgr.set(key, value, scope=scope)

    def validate_value(self, provider_id: str, key: str, value: object) -> None:
        mgr = self._manager(provider_id)
        field = mgr._field_for(key)  # pylint: disable=protected-access
        adapter = TYPE_REGISTRY[field.type]
        try:
            adapter.validate(value, field)
        except (TypeError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc

    def validate_all(self, provider_id: str) -> dict[str, str | None]:
        pid = normalize_provider_id(provider_id)
        spec = self.spec_backend.get_spec(pid)
        raw_map, _ = self.config_backend.read_merged(pid)
        result: dict[str, str | None] = {}
        for field in spec.fields:
            adapter = TYPE_REGISTRY[field.type]
            raw = raw_map.get(field.key)
            try:
                adapter.parse(raw)
            except Exception as exc:  # pragma: no cover - defensive
                result[field.key] = str(exc)
            else:
                result[field.key] = None
        return result

    # ---- Spec persistence ----
    def export_spec(self, provider_id: str, dest: str | Path) -> Path:
        pid = normalize_provider_id(provider_id)
        spec = self.spec_backend.get_spec(pid)
        path = Path(dest)
        save_provider_spec(path, spec)
        return path

    def reload_spec(self, provider_id: str) -> ProviderSpec:
        pid = normalize_provider_id(provider_id)
        return self.spec_backend.get_spec(pid)


__all__ = [
    "Orchestrator",
    # errors
    "OrchestratorError",
    "UnknownFieldError",
    "DuplicateFieldError",
    "ValidationError",
    "PolicyError",
]

