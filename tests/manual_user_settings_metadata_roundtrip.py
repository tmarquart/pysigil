from pysigil.settings_metadata import (
    FieldSpec,
    add_field_spec,
    load_provider_spec,
    register_provider,
    remove_field_spec,
    update_field_spec,
)
from pysigil.paths import user_config_dir

def manual_register_add_update_remove():
    #path = tmp_path / "user" / "my-pkg.json"
    path = user_config_dir('my-pkg') / "user" / "my-pkg.json"

    # Register a provider and ensure package-level metadata is saved
    register_provider(path, "my-pkg", "1.0", title="my-pkg")
    spec = load_provider_spec(path)
    assert spec.provider_id == "my-pkg"
    assert spec.title == "my-pkg"
    assert spec.fields == ()

    # Add a field and verify it is persisted
    field = FieldSpec(key="alpha", type="string", label="Alpha")
    add_field_spec(path, field)
    spec = load_provider_spec(path)
    assert [f.label for f in spec.fields] == ["Alpha"]

    # Update the field and verify changes are persisted
    updated = FieldSpec(key="alpha", type="string", label="Alpha 2")
    update_field_spec(path, updated)
    spec = load_provider_spec(path)
    assert [f.label for f in spec.fields] == ["Alpha 2"]

    # Remove the field and ensure file reflects the deletion
    remove_field_spec(path, "alpha")
    spec = load_provider_spec(path)
    assert spec.fields == ()

if __name__=='__main__':
    manual_register_add_update_remove()