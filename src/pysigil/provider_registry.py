"""Simple persistence helpers for :class:`~pysigil.settings_metadata.ProviderSpec`.

These helpers allow package authors to create a provider specification,
augment it with field specifications and store everything on disk as JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .settings_metadata import FieldSpec, ProviderSpec


def save_provider_spec(path: Path, spec: ProviderSpec) -> None:
    """Persist *spec* as JSON at *path*.

    The file is written atomically by using a temporary file which is
    then moved into place.
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
    """Create and persist a :class:`ProviderSpec`.

    Returns the created spec.
    """
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


__all__ = [
    "add_field_spec",
    "load_provider_spec",
    "register_provider",
    "save_provider_spec",
]
