import pytest

from pysigil.settings_metadata import (
    FieldSpec,
    IniFileBackend,
    ProviderManager,
    ProviderSpec,
)
from pysigil.io_config import read_sections, write_sections


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


def test_ini_file_backend(tmp_path):
    user_dir = tmp_path / "user"
    project_dir = tmp_path / "proj"
    backend = IniFileBackend(user_dir=user_dir, project_dir=project_dir, host="host")

    write_sections(user_dir / "demo" / "settings.ini", {"demo": {"alpha": "u"}})
    write_sections(project_dir / "settings.ini", {"demo": {"alpha": "p", "beta": "p"}})
    write_sections(
        project_dir / "settings-local-host.ini", {"demo": {"beta": "pl"}}
    )

    raw, src = backend.read_merged("demo")
    print(raw)
    assert raw == {"alpha": "p", "beta": "pl"}
    assert src == {"alpha": "project", "beta": "project-local"}

    backend.ensure_section("demo", scope="user", target_kind="settings.ini")
    backend.write_key("demo", "gamma", "42", scope="user", target_kind="settings.ini")
    data = read_sections(user_dir / "demo" / "settings.ini")
    assert data["demo"]["gamma"] == "42"

    backend.remove_key("demo", "gamma", scope="user", target_kind="settings.ini")
    data = read_sections(user_dir / "demo" / "settings.ini")
    assert "gamma" not in data["demo"]

    assert backend.write_target_for("user-custom") == "settings-local-host.ini"
    assert backend.write_target_for("demo") == "settings.ini"


