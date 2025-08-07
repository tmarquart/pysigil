import pytest

from sigilcraft.core import Sigil
from sigilcraft.errors import ReadOnlyScopeError
from sigilcraft.keys import parse_key


def test_core_scope_read_only(tmp_path):
    s = Sigil("app", user_scope=tmp_path / "u.ini", project_scope=tmp_path / "p.ini")
    with pytest.raises(ReadOnlyScopeError):
        s.set_pref("sigil.key_join_char", "-", scope="core")


def test_join_char_override_affects_serialization(tmp_path):
    s = Sigil("app", user_scope=tmp_path)
    s.set_pref("sigil.key_join_char", ".", scope="user")
    s.set_pref(("api", "v2", "timeout"), "30", scope="user")
    content = (tmp_path / "settings.ini").read_text()
    assert "v2.timeout = 30" in content


def test_parse_key_bootstrap_and_override(tmp_path):
    assert parse_key("a_b") == ("a", "b")
    s = Sigil("app", user_scope=tmp_path / "u.ini")
    assert parse_key("a_b") == ("a", "b")
    s.set_pref("sigil.key_delimiters", "-", scope="user")
    assert parse_key("a-b") == ("a", "b")


def test_resolution_order(tmp_path, monkeypatch):
    user_path = tmp_path / "u.ini"
    project_path = tmp_path / "p.ini"
    sig = Sigil("app", user_scope=user_path, project_scope=project_path)
    assert sig.get_pref("sigil.key_join_char") == "_"
    sig = Sigil(
        "app",
        user_scope=user_path,
        project_scope=project_path,
        defaults={"sigil.key_join_char": "."},
    )
    assert sig.get_pref("sigil.key_join_char") == "."
    sig.set_pref("sigil.key_join_char", "-", scope="user")
    assert sig.get_pref("sigil.key_join_char") == "-"
    sig.set_pref("sigil.key_join_char", "+", scope="project")
    assert sig.get_pref("sigil.key_join_char") == "+"
    monkeypatch.setenv("SIGIL_APP_SIGIL_KEY_JOIN_CHAR", "*")
    sig.invalidate_cache()
    assert sig.get_pref("sigil.key_join_char") == "*"


def test_missing_core_defaults(monkeypatch, tmp_path):
    import sigilcraft.core as core_mod

    class Dummy:
        def __truediv__(self, name):
            return tmp_path / name

    monkeypatch.setattr(core_mod, "files", lambda pkg: Dummy())
    monkeypatch.setattr(core_mod, "_core_cache", None)
    s = core_mod.Sigil("app", user_scope=tmp_path / "u.ini", project_scope=tmp_path / "p.ini")
    assert s.get_pref("sigil.key_join_char", default="_") == "_"
    assert parse_key("a_b") == ("a", "b")
