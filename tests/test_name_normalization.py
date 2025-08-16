from pysigil import Sigil


def test_defaults_section_normalized(tmp_path):
    defaults_dir = tmp_path / ".sigil"
    defaults_dir.mkdir()
    defaults_file = defaults_dir / "settings.ini"
    defaults_file.write_text("[sigil_dummy]\nfoo=bar\n", encoding="utf-8")

    sig = Sigil("sigil-dummy", default_path=defaults_file, user_scope=tmp_path / "user.ini")
    assert sig.get_pref("foo") == "bar"
    assert ("foo",) in sig.list_keys("default")


def test_env_prefix_normalized(tmp_path, monkeypatch):
    monkeypatch.setenv("SIGIL_SIGIL_DUMMY_FOO", "42")
    sig = Sigil("sigil-dummy", user_scope=tmp_path / "user.ini")
    assert sig.get_pref("foo") == 42
