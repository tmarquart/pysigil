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
from typing import Literal, Mapping

from .authoring import normalize_provider_id
from .errors import (
    DuplicateFieldError,
    PolicyError,
    SigilLoadError,
    UnknownFieldError,
    UnknownProviderError,
    ValidationError,
)
from .root import ProjectRootNotFoundError
from .settings_metadata import (
    TYPE_REGISTRY,
    FieldSpec,
    FieldValue,
    IniFileBackend,
    IniSpecBackend,
    ProviderManager,
    ProviderSpec,
    SigilBackend,
    SpecBackend,
    save_provider_spec,
)

# ---------------------------------------------------------------------------
# orchestrator implementation
# ---------------------------------------------------------------------------


class Orchestrator:
    """High level façade coordinating spec and config backends."""

    def __init__(
        self,
        spec_backend: SpecBackend | None = None,
        config_backend: SigilBackend | None = None,
    ) -> None:
        if spec_backend is None:
            spec_backend = IniSpecBackend()
        if config_backend is None:
            config_backend = IniFileBackend()
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
        """Create and store a new provider specification.

        Raises
        ------
        DuplicateProviderError
            If the provider already exists.
        PolicyError
            If the provider metadata cannot be written due to project
            configuration.
        """
        pid = normalize_provider_id(provider_id)
        spec = ProviderSpec(
            provider_id=pid,
            schema_version="0",
            title=title,
            description=description,
        )
        try:
            self.spec_backend.create_spec(spec)
        except ProjectRootNotFoundError as exc:
            raise PolicyError(str(exc)) from exc
        return spec

    def edit_provider(
        self,
        provider_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
    ) -> ProviderSpec:
        """Modify metadata for an existing provider.

        Raises
        ------
        UnknownProviderError
            If the provider is not registered.
        PolicyError
            If the provider metadata cannot be written due to project
            configuration.
        """
        pid = normalize_provider_id(provider_id)
        spec = self.spec_backend.get_spec(pid)
        etag = self.spec_backend.etag(pid)
        updated = replace(
            spec,
            title=spec.title if title is None else title,
            description=spec.description if description is None else description,
        )
        try:
            self.spec_backend.save_spec(updated, expected_etag=etag)
        except ProjectRootNotFoundError as exc:
            raise PolicyError(str(exc)) from exc
        return updated

    def delete_provider(self, provider_id: str) -> None:
        """Delete a provider specification.

        Raises
        ------
        PolicyError
            If the provider metadata cannot be removed due to project
            configuration.
        """
        pid = normalize_provider_id(provider_id)
        try:
            self.spec_backend.delete_spec(pid)
        except ProjectRootNotFoundError as exc:
            raise PolicyError(str(exc)) from exc

    # ---- Field metadata ----
    def add_field(
        self,
        provider_id: str,
        *,
        key: str,
        type: str,
        label: str | None = None,
        description: str | None = None,
        options: Mapping[str, object] | None = None,
    ) -> FieldSpec:
        """Add a new field to a provider specification.

        Raises
        ------
        UnknownProviderError
            If the provider is not registered.
        DuplicateFieldError
            If a field with *key* already exists.
        PolicyError
            If the provider metadata cannot be written due to project
            configuration.
        """
        pid = normalize_provider_id(provider_id)
        spec = self.spec_backend.get_spec(pid)
        if key in {f.key for f in spec.fields}:
            raise DuplicateFieldError(key)
        field = FieldSpec(
            key=key,
            type=type,
            label=label,
            description=description,
            options=dict(options) if options is not None else {},
        )
        new_spec = replace(spec, fields=tuple(spec.fields) + (field,))
        etag = self.spec_backend.etag(pid)
        try:
            self.spec_backend.save_spec(new_spec, expected_etag=etag)
        except ProjectRootNotFoundError as exc:
            raise PolicyError(str(exc)) from exc
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
        options: Mapping[str, object] | None = None,
        on_type_change: Literal["convert", "clear"] = "convert",
    ) -> FieldSpec:
        """Modify an existing field definition.

        Raises
        ------
        UnknownProviderError
            If the provider is not registered.
        UnknownFieldError
            If *key* does not exist.
        DuplicateFieldError
            If *new_key* conflicts with another field.
        PolicyError
            If metadata or configuration cannot be written.
        SigilLoadError
            If existing configuration values cannot be read.
        """
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
            options=old_field.options if options is None else dict(options),
        )

        raw_map, source_map = self.config_backend.read_merged(pid)
        raw = raw_map.get(key)
        source = source_map.get(key)
        if raw is not None and source is not None:
            scope = source.split("-")[0]
            target = self.config_backend.write_target_for(pid)
            new_raw = raw
            if nt != old_field.type:
                if on_type_change == "convert":
                    adapter = TYPE_REGISTRY[nt].adapter
                    try:
                        value = adapter.parse(raw)
                        new_raw = adapter.serialize(value)
                    except Exception as exc:
                        raise ValidationError(str(exc)) from exc
                elif on_type_change == "clear":
                    new_raw = None
            if nk != key:
                if new_raw is not None:
                    self.config_backend.write_key(
                        pid, nk, new_raw, scope=scope, target_kind=target
                    )
                else:
                    self.config_backend.remove_key(
                        pid, nk, scope=scope, target_kind=target
                    )
                self.config_backend.remove_key(
                    pid, key, scope=scope, target_kind=target
                )
            else:
                if new_raw is None:
                    self.config_backend.remove_key(
                        pid, nk, scope=scope, target_kind=target
                    )
                elif new_raw != raw:
                    self.config_backend.write_key(
                        pid, nk, new_raw, scope=scope, target_kind=target
                    )

        new_spec = replace(spec, fields=tuple(fields))
        etag = self.spec_backend.etag(pid)
        try:
            self.spec_backend.save_spec(new_spec, expected_etag=etag)
        except ProjectRootNotFoundError as exc:
            raise PolicyError(str(exc)) from exc

        return fields[index]

    def delete_field(
        self,
        provider_id: str,
        key: str,
        *,
        remove_values: bool = False,
        scopes: tuple[str, ...] = ("user", "project"),
    ) -> None:
        """Remove a field from a provider specification.

        Raises
        ------
        UnknownProviderError
            If the provider is not registered.
        UnknownFieldError
            If *key* does not exist.
        PolicyError
            If metadata or configuration cannot be written.
        SigilLoadError
            If existing configuration values cannot be read when
            removing stored values.
        """
        pid = normalize_provider_id(provider_id)
        spec = self.spec_backend.get_spec(pid)
        fields = [f for f in spec.fields if f.key != key]
        if len(fields) == len(spec.fields):
            raise UnknownFieldError(key)
        new_spec = replace(spec, fields=tuple(fields))
        etag = self.spec_backend.etag(pid)
        try:
            self.spec_backend.save_spec(new_spec, expected_etag=etag)
        except ProjectRootNotFoundError as exc:
            raise PolicyError(str(exc)) from exc

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
        """Return identifiers for all registered providers."""
        return self.spec_backend.get_provider_ids()

    def list_fields(self, provider_id: str) -> list[FieldSpec]:
        """List field specifications for *provider_id*.

        Raises
        ------
        UnknownProviderError
            If the provider is not registered.
        """
        pid = normalize_provider_id(provider_id)
        spec = self.spec_backend.get_spec(pid)
        return list(spec.fields)

    def find_untracked_keys(self, provider_id: str) -> list[str]:
        """Return config keys not described in provider metadata.

        Raises
        ------
        UnknownProviderError
            If the provider is not registered.
        SigilLoadError
            If configuration values cannot be read.
        """
        pid = normalize_provider_id(provider_id)
        spec = self.spec_backend.get_spec(pid)
        raw_map, _ = self.config_backend.read_merged(pid)
        tracked = {f.key for f in spec.fields}
        return sorted(set(raw_map) - tracked)

    def adopt_untracked(self, provider_id: str, mapping: dict[str, str]) -> list[FieldSpec]:
        """Create field specs for previously untracked keys.

        Raises
        ------
        UnknownProviderError
            If the provider is not registered.
        DuplicateFieldError
            If any key already exists.
        PolicyError
            If metadata cannot be written.
        """
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
        """Return effective configuration values for *provider_id*.

        Raises
        ------
        UnknownProviderError
            If the provider is not registered.
        SigilLoadError
            If configuration values cannot be read.
        """
        return self._manager(provider_id).effective()

    def get_layers(self, provider_id: str) -> dict[str, dict[str, FieldValue | None]]:
        """Return values for all scopes for *provider_id*."""
        return self._manager(provider_id).layers()

    def set_value(
        self,
        provider_id: str,
        key: str,
        value: object,
        *,
        scope: Literal["user", "project", "default"] = "user",
    ) -> None:
        """Persist *value* for *key*.

        Raises
        ------
        UnknownProviderError
            If the provider is not registered.
        UnknownFieldError
            If *key* is not defined.
        ValidationError
            If *value* fails validation.
        PolicyError
            If configuration cannot be written due to project settings.
        SigilLoadError
            If configuration values cannot be read.
        """
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
        scope: Literal["user", "project", "default"] = "user",
    ) -> None:
        """Remove the stored value for *key*.

        Raises
        ------
        UnknownProviderError
            If the provider is not registered.
        UnknownFieldError
            If *key* is not defined.
        PolicyError
            If configuration cannot be written.
        SigilLoadError
            If configuration values cannot be read.
        """
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
        scope: Literal["user", "project", "default"] = "user",
        atomic: bool = True,
    ) -> None:

        """Set multiple configuration values.

        Raises
        ------
        UnknownProviderError
            If the provider is not registered.
        UnknownFieldError
            If any key is not defined.
        ValidationError
            If any value fails validation.
        PolicyError
            If configuration cannot be written.
        SigilLoadError
            If configuration values cannot be read.
Set multiple values for *provider_id* at once.

        When ``atomic`` is true (the default) all updates are validated and
        written as a single transaction.  If validation or writing fails no
        changes are persisted.

        """
        mgr = self._manager(provider_id)
        if atomic:
            fields = mgr._fields  # pylint: disable=protected-access
            for key, value in updates.items():
                field = fields.get(key)
                if field is None:
                    raise UnknownFieldError(key)
                adapter = TYPE_REGISTRY[field.type].adapter
                try:
                    adapter.validate(value, field)
                except (TypeError, ValueError) as exc:
                    raise ValidationError(str(exc)) from exc
            with mgr.transaction(scope=scope) as tx:
                for key, value in updates.items():
                    tx.set(key, value)
        else:
            for key, value in updates.items():
                mgr.set(key, value, scope=scope)

    def validate_value(self, provider_id: str, key: str, value: object) -> None:
        """Validate *value* for *key* without persisting it.

        Raises
        ------
        UnknownProviderError
            If the provider is not registered.
        UnknownFieldError
            If *key* is not defined.
        ValidationError
            If *value* is invalid.
        """
        mgr = self._manager(provider_id)
        field = mgr._field_for(key)  # pylint: disable=protected-access
        adapter = TYPE_REGISTRY[field.type].adapter
        try:
            adapter.validate(value, field)
        except (TypeError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc

    def validate_all(self, provider_id: str) -> dict[str, str | None]:
        """Validate all stored values for *provider_id*.

        Raises
        ------
        UnknownProviderError
            If the provider is not registered.
        SigilLoadError
            If configuration values cannot be read.
        """
        pid = normalize_provider_id(provider_id)
        spec = self.spec_backend.get_spec(pid)
        raw_map, _ = self.config_backend.read_merged(pid)
        result: dict[str, str | None] = {}
        for field in spec.fields:
            adapter = TYPE_REGISTRY[field.type].adapter
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
        """Export the provider specification to *dest*.

        Raises
        ------
        UnknownProviderError
            If the provider is not registered.
        """
        pid = normalize_provider_id(provider_id)
        spec = self.spec_backend.get_spec(pid)
        path = Path(dest)
        save_provider_spec(path, spec)
        return path

    def reload_spec(self, provider_id: str) -> ProviderSpec:
        """Reload and return the specification for *provider_id*.

        Raises
        ------
        UnknownProviderError
            If the provider is not registered.
        """
        pid = normalize_provider_id(provider_id)
        return self.spec_backend.get_spec(pid)


__all__ = [
    "Orchestrator",
    # errors
    "UnknownProviderError",
    "UnknownFieldError",
    "DuplicateFieldError",
    "ValidationError",
    "PolicyError",
    "SigilLoadError",
]

