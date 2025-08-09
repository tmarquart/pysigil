from pathlib import Path

import pytest

from pysigil import resolver


def test_find_project_root_success(tmp_path: Path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='x'\n")
    sub = root / "sub" / "pkg"
    sub.mkdir(parents=True)
    assert resolver.find_project_root(sub) == root


def test_find_project_root_failure(tmp_path: Path):
    with pytest.raises(resolver.ProjectRootNotFound):
        resolver.find_project_root(tmp_path)


def test_project_settings_file_creation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='x'\n")
    monkeypatch.chdir(root)
    path = resolver.project_settings_file()
    assert path == root / ".pysigil" / resolver.DEFAULT_FILENAME
    assert path.parent.is_dir()
