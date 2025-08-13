from pathlib import Path

from pysigil.core import Sigil


def test_default_project_scope_uses_pysigil_dir(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='x'\n")
    monkeypatch.chdir(root)

    s = Sigil("app")
    s.set_pref("ui.theme", "dark", scope="project")

    cfg = root / ".pysigil" / "settings.ini"
    assert cfg.exists()
    contents = cfg.read_text().strip()
    assert "[ui]" in contents
