from __future__ import annotations

from pathlib import Path

from sigilcraft.core import Sigil


def test_defaults_and_env_override(monkeypatch):
    monkeypatch.setenv("SIGIL_APP_COLOR", "blue")
    s = Sigil("app", defaults={"ui.theme": "light"})
    assert s.get_pref("ui.theme") == "light"
    assert s.get_pref("color") == "blue"


def test_set_and_get_user_scope(tmp_path: Path):
    user_path = tmp_path / "user.ini"
    project_path = tmp_path / "project.ini"
    s = Sigil("app", user_scope=user_path, project_scope=project_path)
    s.set_pref("ui.theme", "dark", scope="user")
    assert s.get_pref("ui.theme") == "dark"
    # ensure value persisted
    s2 = Sigil("app", user_scope=user_path, project_scope=project_path)
    assert s2.get_pref("ui.theme") == "dark"


def test_context_manager_project(tmp_path: Path):
    user_path = tmp_path / "u.ini"
    project_a = tmp_path / "a.ini"
    project_b = tmp_path / "b.ini"
    s = Sigil("app", user_scope=user_path, project_scope=project_a)
    s.set_pref("setting", "one")
    with s.project(project_b):
        s.set_pref("setting", "two")
        assert s.get_pref("setting") == "two"
    # after context manager should revert
    assert s.get_pref("setting") == "one"


def test_defaults_from_file(tmp_path: Path):
    defaults = tmp_path / "defaults.ini"
    defaults.write_text("[ui]\ntheme=light\n")
    s = Sigil("app", default_path=defaults)
    assert s.get_pref("ui.theme") == "light"
