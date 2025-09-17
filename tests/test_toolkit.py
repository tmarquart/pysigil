from __future__ import annotations

import os
from pathlib import Path


from pysigil import helpers_for


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

