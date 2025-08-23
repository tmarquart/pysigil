"""Manual round trip test for user settings metadata persistence.

This script exercises the public API for working with provider metadata and
ensures that changes are reflected on disk.  It is intentionally not part of
the automated test suite; run it manually to inspect the created JSON file.
"""

from __future__ import annotations

from pysigil.paths import user_config_dir
from pysigil.settings_metadata import (
    FieldSpec,
    add_field_spec,
    load_provider_spec,
    register_provider,
    remove_field_spec,
    update_field_spec,
)


def manual_round_trip() -> None:
    """Exercise registering, updating and removing field specs."""

    path = user_config_dir("my-pkg") / "user" / "my-pkg.json"

    if path.exists():
        path.unlink()

    # Register a provider and ensure package-level metadata is saved
    register_provider(path, "my-pkg", "1.0", title="my-pkg")
    spec = load_provider_spec(path)
    assert spec.provider_id == "my-pkg"
    assert spec.title == "my-pkg"
    assert spec.fields == ()

    # Add three fields and verify they are persisted
    fields = [
        FieldSpec(key="alpha", type="string", label="Alpha"),
        FieldSpec(key="beta", type="integer", label="Beta"),
        FieldSpec(key="gamma", type="boolean", label="Gamma"),
    ]
    for f in fields:
        add_field_spec(path, f)
    spec = load_provider_spec(path)
    assert [f.label for f in spec.fields] == ["Alpha", "Beta", "Gamma"]

    # Update one field and verify the change is persisted
    update_field_spec(path, FieldSpec(key="beta", type="integer", label="Beta 2"))
    spec = load_provider_spec(path)
    assert [f.label for f in spec.fields] == ["Alpha", "Beta 2", "Gamma"]

    # Remove a field and ensure the file reflects the deletion
    remove_field_spec(path, "gamma")
    spec = load_provider_spec(path)
    assert [f.label for f in spec.fields] == ["Alpha", "Beta 2"]

    # Display the final contents for manual inspection
    print(path.read_text())


if __name__ == "__main__":
    manual_round_trip()

