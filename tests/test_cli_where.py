from __future__ import annotations

from pysigil import cli, core


def test_cli_where(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(core, "user_config_dir", lambda app: str(tmp_path))
    # Seed values
    assert cli.main(["set", "color", "red", "--app", "myapp", "--scope", "project"]) == 0
    capsys.readouterr()
    assert cli.main(["set", "color", "blue", "--app", "myapp"]) == 0
    capsys.readouterr()
    assert cli.main(["where", "color", "--app", "myapp"]) == 0
    out = capsys.readouterr().out
    assert "Policy: project_over_user" in out
    assert "(locked: false)" in out.lower()
    assert "project:" in out and "\u2190 effective" in out
