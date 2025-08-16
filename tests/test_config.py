from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from pysigil import config as cfg
from pysigil.cli import cli


def _fake_user_dir(tmp_path: Path) -> Path:
    d = tmp_path / "user"
    d.mkdir()
    return d


def _fake_project_root(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / ".sigil").mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='demo'\n")
    return root


def _patch_env(monkeypatch, tmp_path: Path, host: str = "host") -> tuple[Path, Path]:
    user_dir = _fake_user_dir(tmp_path)
    project_root = _fake_project_root(tmp_path)
    monkeypatch.setattr(cfg, "user_config_dir", lambda app: str(user_dir))
    monkeypatch.setattr(cfg, "find_project_root", lambda: project_root)
    monkeypatch.setattr(cfg.socket, "gethostname", lambda: host)
    return user_dir, project_root


def test_precedence(monkeypatch, tmp_path: Path) -> None:
    user_dir, project_root = _patch_env(monkeypatch, tmp_path)
    (user_dir / "pkg").mkdir()
    (user_dir / "pkg" / "settings.ini").write_text("[pkg]\na=1\n")
    (user_dir / "pkg" / "settings-local-host.ini").write_text("[pkg]\na=2\n")
    proj_dir = project_root / ".sigil" / "pkg"
    proj_dir.mkdir(parents=True)
    (proj_dir / "settings.ini").write_text("[pkg]\na=3\n")
    (proj_dir / "settings-local-host.ini").write_text("[pkg]\na=4\n")
    data = cfg.load("pkg")
    assert data == {"a": "4"}


def test_write_policy(monkeypatch, tmp_path: Path) -> None:
    user_dir, _ = _patch_env(monkeypatch, tmp_path)
    runner = CliRunner()
    res = runner.invoke(cli, ["config", "init", "--provider", "user-custom", "--scope", "user"])
    assert res.exit_code == 0
    assert (user_dir / "user-custom" / "settings-local-host.ini").exists()
    assert not (user_dir / "user-custom" / "settings.ini").exists()
    res = runner.invoke(cli, ["config", "init", "--provider", "mypkg", "--scope", "user"])
    assert res.exit_code == 0
    assert (user_dir / "mypkg" / "settings.ini").exists()
    res = runner.invoke(cli, ["config", "host", "--provider", "mypkg"])
    assert res.exit_code != 0


def test_host_filtering(monkeypatch, tmp_path: Path) -> None:
    user_dir, project_root = _patch_env(monkeypatch, tmp_path)
    (user_dir / "pkg").mkdir()
    (user_dir / "pkg" / "settings-local-host.ini").write_text("[pkg]\nx=1\n")
    (user_dir / "pkg" / "settings-local-other.ini").write_text("[pkg]\nx=2\n")
    proj_dir = project_root / ".sigil" / "pkg"
    proj_dir.mkdir(parents=True)
    (proj_dir / "settings-local-host.ini").write_text("[pkg]\ny=3\n")
    (proj_dir / "settings-local-other.ini").write_text("[pkg]\ny=4\n")
    data = cfg.load("pkg")
    assert data == {"x": "1", "y": "3"}


def test_gitignore_idempotent(monkeypatch, tmp_path: Path) -> None:
    _, project_root = _patch_env(monkeypatch, tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["config", "gitignore", "--init", "--auto"])
    runner.invoke(cli, ["config", "gitignore", "--init", "--auto"])
    content = (project_root / ".gitignore").read_text().splitlines()
    assert content == [".sigil/*/settings-local*"]


def test_cli_roundtrip(monkeypatch, tmp_path: Path) -> None:
    user_dir, project_root = _patch_env(monkeypatch, tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["config", "init", "--provider", "pkg", "--scope", "user"])
    runner.invoke(
        cli,
        ["config", "init", "--provider", "pkg", "--scope", "project", "--auto"],
    )
    (user_dir / "pkg" / "settings.ini").write_text("[pkg]\nkey=user\n")
    proj_dir = project_root / ".sigil" / "pkg"
    (proj_dir / "settings.ini").write_text("[pkg]\nkey=project\n")
    res = runner.invoke(
        cli,
        ["config", "show", "--provider", "pkg", "--as", "json", "--auto"],
    )
    assert res.exit_code == 0
    assert json.loads(res.output) == {"key": "project"}


def test_gui_lists_user_custom(monkeypatch, tmp_path: Path) -> None:
    user_dir, _ = _patch_env(monkeypatch, tmp_path)
    (user_dir / "user-custom").mkdir()
    (user_dir / "user-custom" / "settings-local-host.ini").write_text(
        "[user-custom]\nfoo=bar\n"
    )
    from pysigil.gui import launch_gui

    gui = launch_gui(run_mainloop=False, state_path=tmp_path / "state.json")
    assert "user-custom" in gui.packages
