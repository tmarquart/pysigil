from pysigil.settings_metadata import (
    FieldSpec,
    add_field_spec,
    load_provider_spec,
    register_provider,
    remove_field_spec,
    update_field_spec,
)


def test_register_add_edit_delete(tmp_path):
    path = tmp_path / "user" / "my-pkg.json"
    register_provider(path, "my-pkg", "1.0", title="my-pkg")

    field = FieldSpec(key="alpha", type="string", label="Alpha")
    add_field_spec(path, field)

    updated = FieldSpec(key="alpha", type="string", label="Alpha 2")
    update_field_spec(path, updated)
    spec = load_provider_spec(path)
    assert [f.label for f in spec.fields] == ["Alpha 2"]

    remove_field_spec(path, "alpha")
    spec = load_provider_spec(path)
    assert spec.fields == ()
