from pysigil import authoring
from pysigil.ui.author_adapter import AuthorAdapter
import pysigil.api as api


def test_upsert_field_sets_options_and_default(tmp_path, monkeypatch):
    monkeypatch.setenv("SIGIL_APP_NAME", "sigil-test")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("SIGIL_ROOT", str(tmp_path))

    defaults_dir = tmp_path / "pkg" / ".sigil"
    defaults_dir.mkdir(parents=True)
    defaults_path = defaults_dir / "settings.ini"
    defaults_path.write_text("[demo]\n")

    authoring.link("demo", defaults_path)
    api.register_provider("demo", title="Demo")

    adapter = AuthorAdapter("demo")
    adapter.upsert_field("alpha", "integer", options={"minimum": 0}, default=5)

    fields = {f.key: f for f in adapter.list_defined()}
    assert fields["alpha"].options == {"minimum": 0}
    default_info = adapter.default_for_key("alpha")
    assert default_info is not None and default_info.value == 5


def test_adopt_untracked(tmp_path, monkeypatch):
    monkeypatch.setenv("SIGIL_APP_NAME", "sigil-test")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("SIGIL_ROOT", str(tmp_path))

    defaults_dir = tmp_path / "pkg" / ".sigil"
    defaults_dir.mkdir(parents=True)
    defaults_path = defaults_dir / "settings.ini"
    defaults_path.write_text("[demo]\nfoo = bar\n")

    authoring.link("demo", defaults_path)
    api.register_provider("demo", title="Demo")

    adapter = AuthorAdapter("demo")
    assert any(u.key == "foo" for u in adapter.list_undiscovered())

    adapter.adopt_untracked({"foo": "string"})
    defined = {f.key for f in adapter.list_defined()}
    assert "foo" in defined
    assert not any(u.key == "foo" for u in adapter.list_undiscovered())

