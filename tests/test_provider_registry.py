from pathlib import Path

from pysigil.provider_registry import (
    add_field_spec,
    load_provider_spec,
    register_provider,
)
from pysigil.settings_metadata import FieldSpec


def test_register_and_add_field(tmp_path):
    path = tmp_path / "demo.json"
    register_provider(path, "demo", "1.0", title="Demo")
    spec = load_provider_spec(path)
    assert spec.provider_id == "demo"
    assert spec.schema_version == "1.0"
    assert spec.title == "Demo"
    assert spec.fields == ()

    field = FieldSpec(key="retries", type="integer", label="Retries")
    add_field_spec(path, field)
    spec2 = load_provider_spec(path)
    assert len(spec2.fields) == 1
    assert spec2.fields[0].key == "retries"
    assert spec2.fields[0].type == "integer"
