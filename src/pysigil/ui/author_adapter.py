"""Authoring adapter.

This module exposes a thin layer used by the authoring tools. The
implementation purposely mirrors
:class:`~pysigil.ui.provider_adapter.ProviderAdapter` but focuses on
manipulating provider specifications and defaults. Only a minimal feature set
required by the tests is implemented; the API is kept simple so additional
capabilities can be bolted on in the future without the UI reaching directly
into :mod:`pysigil.api` or :mod:`pysigil.settings_metadata`.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field as dataclass_field
from typing import Any

from .. import api
from ..settings_metadata import TYPE_REGISTRY

# ---------------------------------------------------------------------------
# Data classes exposed to the UI layer
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldInfo:
    """Metadata describing a single configuration field."""

    key: str
    type: str
    label: str | None = None
    description_short: str | None = None
    description: str | None = None
    options: dict[str, Any] = dataclass_field(default_factory=dict)
    section: str | None = None
    order: int | None = None


@dataclass(frozen=True)
class ValueInfo:
    """Raw configuration value along with its originating scope."""

    raw: str | None
    scope: str | None = None
    value: Any | None = None
    error: str | None = None


@dataclass(frozen=True)
class UntrackedInfo:
    """Information about keys present in configuration but not in metadata."""

    key: str
    raw: str | None
    guessed_type: str


@dataclass(frozen=True)
class ValidateResult:
    """Result of validating a field key."""

    normalized: str
    error: str | None = None

    @property
    def ok(self) -> bool:  # pragma: no cover - trivial
        return self.error is None


@dataclass(frozen=True)
class RenamePreview:
    """Preview information for a rename operation."""

    key: str
    new_key: str
    existing: dict[str, str]
    conflicts: dict[str, str]


@dataclass(frozen=True)
class RenamePlan:
    """Plan representing a rename operation."""

    key: str
    new_key: str
    layers: dict[str, str]


@dataclass(frozen=True)
class DeletePreview:
    """Preview information for deleting a field."""

    key: str
    layers: dict[str, str]


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_]*(\.[a-z0-9_]+)*$")


class AuthorAdapter:
    """Adapter exposing authoring related operations for the UI."""

    def __init__(self, provider_id: str | None = None) -> None:
        self._provider_id: str | None = None
        self._handle: api.ProviderHandle | None = None
        if provider_id is not None:
            self.set_provider(provider_id)

    # -- helpers ---------------------------------------------------------
    def _require_handle(self) -> api.ProviderHandle:
        if self._handle is None:
            raise RuntimeError("provider not set")
        return self._handle

    # -- provider selection ---------------------------------------------
    def set_provider(self, provider_id: str) -> None:
        self._provider_id = provider_id
        self._handle = api.handle(provider_id)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def list_defined(self) -> list[FieldInfo]:
        """Return field specifications defined for the current provider."""

        handle = self._require_handle()
        return [
            FieldInfo(
                f.key,
                f.type,
                f.label,
                f.description_short,
                f.description,
                f.options,
                f.section,
                f.order,
            )
            for f in handle.fields()
        ]

    def list_undiscovered(self) -> list[UntrackedInfo]:
        """Return keys that exist in configuration but lack field metadata."""

        handle = self._require_handle()
        assert self._provider_id is not None
        keys = handle.untracked_keys()
        raw_map, _ = api._ORCH.config_backend.read_merged(self._provider_id)  # type: ignore[attr-defined]
        infos: list[UntrackedInfo] = []
        for key in keys:
            raw = raw_map.get(key)
            guessed = self._guess_type(raw)
            infos.append(UntrackedInfo(key=key, raw=raw, guessed_type=guessed))
        return infos

    def default_for_key(self, key: str) -> ValueInfo | None:
        """Return value information from the ``default`` scope for *key*."""

        handle = self._require_handle()
        layers = handle.layers()
        per_scope = layers.get(key, {})
        val = per_scope.get("default")
        if val is None:
            return None
        return ValueInfo(raw=val.raw, scope="default", value=val.value, error=val.error)

    def get_sections_order(self) -> list[str] | None:
        handle = self._require_handle()
        return handle.get_sections_order()

    def get_sections_collapsed(self) -> list[str] | None:
        handle = self._require_handle()
        return handle.get_sections_collapsed()

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------
    def upsert_field(
        self,
        key: str,
        type: str,
        *,
        label: str | None = None,
        description_short: str | None = None,
        description: str | None = None,
        options: Mapping[str, Any] | None = None,
        section: str | None = None,
        order: int | None = None,
        default: Any | None = None,
        init_scope: str | None = "user",
        new_key: str | None = None,
    ) -> FieldInfo:
        """Create or update a field specification."""

        handle = self._require_handle()
        existing = {f.key: f for f in handle.fields()}
        if key in existing and new_key is None:
            res = handle.edit_field(
                key,
                new_type=type,
                label=label,
                description_short=description_short,
                description=description,
                 options=options,
                section=section,
                order=order,
            )
        elif key in existing and new_key is not None:
            res = handle.edit_field(
                key,
                new_key=new_key,
                new_type=type,
                label=label,
                description_short=description_short,
                description=description,
                options=options,
                section=section,
                order=order,
            )
        else:
            res = handle.add_field(
                key if new_key is None else new_key,
                type,
                label=label,
                description_short=description_short,
                description=description,
                options=options,
                section=section,
                order=order,
                init_scope=init_scope,  # type: ignore[arg-type]
            )
        info = FieldInfo(
            res.key,
            res.type,
            res.label,
            res.description_short,
            res.description,
            res.options,
            res.section,
            res.order,
        )
        if default is not None:
            api._ORCH.set_value(self._provider_id or "", res.key, default, scope="default")  # type: ignore[arg-type]
        return info

    def set_sections_order(self, seq: list[str]) -> None:
        handle = self._require_handle()
        handle.set_sections_order(seq)

    def set_sections_collapsed(self, seq: list[str]) -> None:
        handle = self._require_handle()
        handle.set_sections_collapsed(seq)

    def patch_fields(self, updates: list[dict[str, object]]) -> None:
        handle = self._require_handle()
        handle.patch_fields(updates)

    def delete_field(self, key: str, *, remove_values: bool = False, scopes: Iterable[str] = ("user", "project")) -> None:
        """Remove a field from the provider specification."""

        handle = self._require_handle()
        handle.delete_field(key, remove_values=remove_values, scopes=tuple(scopes))

    def adopt_untracked(self, mapping: Mapping[str, str]) -> list[FieldInfo]:
        """Adopt untracked configuration keys as field specifications."""

        handle = self._require_handle()
        specs = handle.adopt_untracked(mapping)
        return [
            FieldInfo(
                s.key,
                s.type,
                s.label,
                s.description_short,
                s.description,
                s.options,
            )
            for s in specs
        ]

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def validate_key(self, key: str) -> ValidateResult:
        """Validate a field key and normalise it."""

        norm = key.strip().lower()
        if not _KEY_RE.fullmatch(norm):
            return ValidateResult(norm, "invalid field key")
        return ValidateResult(norm, None)

    # ------------------------------------------------------------------
    # Preview helpers
    # ------------------------------------------------------------------
    def preview_rename(self, key: str, new_key: str) -> RenamePreview:
        """Preview changes performed when renaming *key* to *new_key*."""

        assert self._provider_id is not None
        layers = api._ORCH.config_backend.read_layers(self._provider_id)  # type: ignore[attr-defined]
        existing = {scope: vals[key] for scope, vals in layers.items() if key in vals}
        conflicts = {scope: vals[new_key] for scope, vals in layers.items() if new_key in vals}
        return RenamePreview(key=key, new_key=new_key, existing=existing, conflicts=conflicts)

    def plan_rename(self, preview: RenamePreview) -> RenamePlan:
        """Create a :class:`RenamePlan` from a :class:`RenamePreview`."""

        layers = dict(preview.existing)
        return RenamePlan(key=preview.key, new_key=preview.new_key, layers=layers)

    def apply_rename(self, plan: RenamePlan) -> FieldInfo:
        """Apply a rename plan and return updated field information."""

        handle = self._require_handle()
        res = handle.edit_field(plan.key, new_key=plan.new_key)
        return FieldInfo(
            res.key,
            res.type,
            res.label,
            res.description_short,
            res.description,
            res.options,
        )

    def preview_delete(self, key: str) -> DeletePreview:
        """Return scopes containing values for *key* prior to deletion."""

        assert self._provider_id is not None
        layers = api._ORCH.config_backend.read_layers(self._provider_id)  # type: ignore[attr-defined]
        present = {scope: vals[key] for scope, vals in layers.items() if key in vals}
        return DeletePreview(key=key, layers=present)

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------
    @staticmethod
    def _guess_type(raw: str | None) -> str:
        """Best effort type guess based on ``TYPE_REGISTRY`` adapters."""

        if raw is None:
            return "string"
        for typ, field_type in TYPE_REGISTRY.items():
            try:
                field_type.adapter.parse(raw)
                return typ
            except Exception:
                continue
        return "string"
