import pytest

from pysigil.settings_metadata import FieldSpec, ProviderManager, ProviderSpec


def test_fieldspec_validates_unknown_type():
    with pytest.raises(ValueError):
        FieldSpec(key="foo", type="unknown")


class DummyBackend:
    def __init__(self):
        self.writes = []
        self.removes = []
        self.sections = []

    def read_merged(self, provider_id):
        return {"retries": "3"}, {"retries": "project"}

    def write_key(self, provider_id, key, raw_value, *, scope, target_kind):
        self.writes.append((provider_id, key, raw_value, scope, target_kind))

    def remove_key(self, provider_id, key, *, scope, target_kind):
        self.removes.append((provider_id, key, scope, target_kind))

    def ensure_section(self, provider_id, *, scope, target_kind):
        self.sections.append((provider_id, scope, target_kind))

    def write_target_for(self, provider_id):
        return "settings.ini"


def test_provider_manager_roundtrip():
    spec = ProviderSpec(
        provider_id="demo",
        schema_version="0.1",
        fields=[FieldSpec(key="retries", type="integer", label="Retries")],
    )
    backend = DummyBackend()
    mgr = ProviderManager(spec, backend)

    state = mgr.effective()
    assert state["retries"].value == 3
    assert state["retries"].source == "project"

    mgr.set("retries", 5)
    assert backend.writes == [("demo", "retries", "5", "user", "settings.ini")]

    mgr.clear("retries")
    assert backend.removes == [("demo", "retries", "user", "settings.ini")]

    mgr.init("user")
    assert backend.sections == [("demo", "user", "settings.ini")]


