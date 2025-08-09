from pathlib import Path

from pathlib import Path

import pytest

from pysigil import api, backend_ini


class DummyDist:
    pass


def test_project_over_user(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    root = tmp_path / "proj"
    (root / "pyproject.toml").parent.mkdir(exist_ok=True)
    (root / "pyproject.toml").write_text("[project]\nname='x'")
    proj_file = root / ".pysigil" / "settings.ini"

    monkeypatch.setattr(api, "_find_distribution", lambda pid: DummyDist())
    monkeypatch.setattr(
        api,
        "load_provider_defaults",
        lambda pid, dist: {f"provider:{pid}": {"ui.theme": "ocean"}},
    )

    api.set_project_value("pkg", "ui.theme", "desert", project_file=proj_file)
    api.set_user_value("pkg", "ui.theme", "forest")

    assert (
        api.get_value("pkg", "ui.theme", project_file=proj_file)
        == "desert"
    )


def test_user_over_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    root = tmp_path / "proj"
    (root / "pyproject.toml").parent.mkdir(exist_ok=True)
    (root / "pyproject.toml").write_text("[project]\nname='x'")
    proj_file = root / ".pysigil" / "settings.ini"

    backend_ini.write_sections(
        proj_file,
        {
            "pysigil": {"policy": "user_over_project"},
            "provider:pkg": {"ui.theme": "desert"},
        },
    )
    api.set_user_value("pkg", "ui.theme", "forest")
    monkeypatch.setattr(api, "_find_distribution", lambda pid: None)

    assert (
        api.get_value("pkg", "ui.theme", project_file=proj_file)
        == "forest"
    )
