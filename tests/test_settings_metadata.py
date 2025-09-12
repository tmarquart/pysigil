import pytest
from pathlib import PurePosixPath
import pysigil.settings_metadata as settings_metadata
from pysigil.errors import ConflictError
from pysigil.settings_metadata import (
    FieldSpec,
    IniFileBackend,
    IniSpecBackend,
    ProviderManager,
    ProviderSpec,
)
from pysigil.io_config import read_sections, write_sections
from tests.utils import DummyPolicy


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
        fields=[
            FieldSpec(
                key="retries",
                type="integer",
                label="Retries",
                options={"minimum": 0},
            )
        ],
    )
    backend = DummyBackend()
    mgr = ProviderManager(spec, backend)

    state = mgr.effective()
    assert state["retries"].value == 3
    assert state["retries"].source == "project"
    assert mgr.spec.fields[0].options == {"minimum": 0}

    mgr.set("retries", 5)
    assert backend.writes == [("demo", "retries", "5", "user", "settings.ini")]

    mgr.clear("retries")
    assert backend.removes == [("demo", "retries", "user", "settings.ini")]

    mgr.init("user")
    assert backend.sections == [("demo", "user", "settings.ini")]


def test_integer_minimum_enforced():
    spec = ProviderSpec(
        provider_id="demo",
        schema_version="0.1",
        fields=[FieldSpec(key="count", type="integer", options={"minimum": 1})],
    )
    backend = DummyBackend()
    mgr = ProviderManager(spec, backend)
    with pytest.raises(ValueError):
        mgr.set("count", 0)


def test_ini_spec_backend_persists_options(tmp_path):
    backend = IniSpecBackend(user_dir=tmp_path)
    spec = ProviderSpec(
        provider_id="demo",
        schema_version="1",
        fields=[
            FieldSpec(key="mode", type="string", options={"choices": ["a", "b"]})
        ],
    )
    backend.create_spec(spec)
    loaded = backend.get_spec("demo")
    assert loaded.fields[0].options == {"choices": ["a", "b"]}


def test_ini_file_backend(tmp_path):
    user_dir = tmp_path / "user"
    project_dir = tmp_path / "proj"
    policy = DummyPolicy(user_dir, project_dir, host="host")
    backend = IniFileBackend(policy=policy)

    write_sections(user_dir / "demo" / "settings.ini", {"demo": {"alpha": "u"}})
    write_sections(project_dir / "settings.ini", {"demo": {"alpha": "p", "beta": "p"}})
    write_sections(
        project_dir / "settings-local-host.ini", {"demo": {"beta": "pl"}}
    )

    raw, src = backend.read_merged("demo")
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


def test_short_description_length_limit():
    with pytest.raises(ValueError):
        FieldSpec(key="k", type="string", description_short="x" * 121)


def test_fieldspec_serialization_omits_empty_descriptions():
    spec = FieldSpec(key="k", type="string")
    gui = spec.to_gui_v0()
    assert "description" not in gui
    assert "description_short" not in gui
    spec = FieldSpec(key="k", type="string", description="long")
    gui = spec.to_gui_v0()
    assert gui["description"] == "long"
    assert "description_short" not in gui


def test_spec_backend_detects_external_change(tmp_path):
    backend = IniSpecBackend(user_dir=tmp_path)
    spec = ProviderSpec(provider_id="demo", schema_version="1")
    backend.create_spec(spec)
    loaded = backend.get_spec("demo")
    path = tmp_path / "demo" / "metadata.ini"
    path.write_text(path.read_text() + "\n# external\n")
    with pytest.raises(ConflictError):
        backend.save_spec(loaded)


def test_ini_spec_backend_get_provider_ids_installed(monkeypatch):
    backend = IniSpecBackend()
    monkeypatch.setattr(settings_metadata, "list_links", lambda **kw: {})

    class DummyDist:
        def __init__(self, name, files, meta_name=None):
            self.name = name
            self._files = [PurePosixPath(p) for p in files]
            if meta_name is None:
                self.metadata = {}
            else:
                self.metadata = {"Name": meta_name}

        @property
        def files(self):  # pragma: no cover - simple
            return self._files

    dists = [
        DummyDist("pkg_a", [".sigil/metadata.ini"], "Foo"),
        DummyDist("pkg_b", ["other.txt"], "Bar"),
    ]
    monkeypatch.setattr(settings_metadata, "distributions", lambda: dists)

    ids = backend.get_provider_ids()
    assert ids == ["foo"]


def test_ini_spec_backend_prefers_dev_link(monkeypatch, tmp_path):
    defaults = tmp_path / "foo" / "defaults.ini"
    defaults.parent.mkdir(parents=True)
    defaults.write_text("")
    (defaults.parent / "metadata.ini").write_text("[__meta__]\nschema_version=1\n")

    monkeypatch.setattr(settings_metadata, "list_links", lambda **kw: {"foo": defaults})

    class DummyDist:
        def __init__(self, name):
            self.name = name
            self._files = [PurePosixPath(".sigil/metadata.ini")]
            self.metadata = {"Name": name}

        @property
        def files(self):  # pragma: no cover - simple
            return self._files

    dists = [DummyDist("Foo"), DummyDist("Bar")]
    monkeypatch.setattr(settings_metadata, "distributions", lambda: dists)

    backend = IniSpecBackend()
    ids = backend.get_provider_ids()
    assert ids == ["bar", "foo"]


