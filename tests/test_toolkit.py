from __future__ import annotations

import os
from pathlib import Path


from pysigil import get_project_directory, get_user_directory, helpers_for
from pysigil.discovery import pep503_name


def test_helpers_for_isolated_apps(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.delenv("SIGIL_DEMO_SECTION_VALUE", raising=False)

    get_a, set_a = helpers_for("demo")
    set_a("section.value", "1")
    assert get_a("section.value", cast=int) == 1

    get_b, set_b = helpers_for("other")
    assert get_b("section.value") is None
    set_b("section.value", "2")
    assert get_b("section.value", cast=int) == 2

    # original demo settings remain unchanged
    assert get_a("section.value", cast=int) == 1


def test_helpers_environment_scope(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    get_setting, set_setting = helpers_for("demo-env")
    env_key = "SIGIL_DEMO_ENV_SECTION_VALUE"
    monkeypatch.delenv(env_key, raising=False)

    try:
        set_setting("section.value", "7", scope="environment")
        assert os.environ[env_key] == "7"
        assert get_setting("section.value") == 7
    finally:
        set_setting("section.value", None, scope="env")
    assert env_key not in os.environ
    assert get_setting("section.value") is None


def test_directory_helpers_return_expected_paths(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SIGIL_ROOT", str(tmp_path / "project"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("SIGIL_APP_NAME", raising=False)

    app_name = "Demo_App"
    expected = pep503_name(app_name)

    project_dir = get_project_directory()
    user_dir = get_user_directory(app_name)

    assert project_dir.is_absolute()
    assert user_dir.is_absolute()

    assert project_dir == (tmp_path / "project" / ".sigil" / "data").resolve()
    assert project_dir.is_dir()

    assert user_dir.name == expected
    assert user_dir.parent == (tmp_path / "xdg").resolve()
    assert user_dir.is_dir()

