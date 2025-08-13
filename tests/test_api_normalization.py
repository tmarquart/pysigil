from pathlib import Path

from pysigil import api, backend_ini

def test_set_creates_project_file_and_normalizes_provider(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='x'\n")
    monkeypatch.chdir(root)

    api.set_project_value("My.Package", "ui.theme", "forest")

    cfg = root / ".pysigil" / "settings.ini"
    data = backend_ini.read_sections(cfg)
    assert data == {"provider:my-package": {"ui.theme": "forest"}}
    assert api.get_value("My.Package", "ui.theme") == "forest"
