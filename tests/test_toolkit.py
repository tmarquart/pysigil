from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


from pysigil import (
    get_project_directory,
    get_user_directory,
    helpers_for,
)


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


def test_get_user_directory_is_app_specific(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SIGIL_APP_NAME", raising=False)

    calls: list[str] = []

    def fake_user_data_dir(*, appname: str) -> Path:
        calls.append(appname)
        return tmp_path / f"data-{appname}"

    monkeypatch.setattr("pysigil.paths._ud", fake_user_data_dir)

    first = get_user_directory("alpha-app")
    second = get_user_directory("beta-app")

    assert first == (tmp_path / "data-alpha-app").resolve()
    assert second == (tmp_path / "data-beta-app").resolve()
    assert first.is_absolute()
    assert second.is_absolute()
    assert calls == ["alpha-app", "beta-app"]


def test_get_project_directory_returns_package_root(
    monkeypatch, tmp_path: Path
) -> None:
    names = ("toolkit_pkg_alpha", "toolkit_pkg_beta")
    roots = {}
    for name in names:
        root = tmp_path / name
        pkg_dir = root / name
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
        monkeypatch.syspath_prepend(str(root))
        roots[name] = root.resolve()

    importlib.invalidate_caches()

    try:
        resolved = {name: get_project_directory(name) for name in names}
    finally:
        for name in names:
            sys.modules.pop(name, None)

    assert resolved["toolkit_pkg_alpha"].is_absolute()
    assert resolved["toolkit_pkg_beta"].is_absolute()
    assert resolved["toolkit_pkg_alpha"] == roots["toolkit_pkg_alpha"]
    assert resolved["toolkit_pkg_beta"] == roots["toolkit_pkg_beta"]
    assert resolved["toolkit_pkg_alpha"] != resolved["toolkit_pkg_beta"]

