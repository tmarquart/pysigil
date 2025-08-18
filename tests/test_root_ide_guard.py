from pathlib import Path
import pytest
from pysigil.root import find_project_root, ProjectRootNotFoundWithSuggestions

def mkfile(base: Path, rel: str, content: str = "x") -> Path:
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p

def mkdir(base: Path, rel: str) -> Path:
    p = base / rel
    p.mkdir(parents=True, exist_ok=True)
    return p

def test_vscode_core_files_any_one_is_enough(tmp_path: Path):
    proj = tmp_path / "vs"
    mkfile(proj, ".vscode/launch.json", "{}")
    assert find_project_root(start=proj / "a") == proj

def test_idea_core_files_any_one_is_enough(tmp_path: Path):
    proj = tmp_path / "ij"
    mkfile(proj, ".idea/modules.xml", "<modules/>")
    assert find_project_root(start=proj / "a") == proj

def test_ide_guard_prefers_python_if_present(tmp_path: Path):
    proj = tmp_path / "both"
    mkfile(proj, ".vscode/settings.json", "{}")
    mkfile(proj, "pyproject.toml", "")
    # Should return immediately at proj due to Tier1; test ensures no guard interference
    assert find_project_root(start=proj / "deep") == proj

def test_empty_vscode_and_no_co_signals_gives_suggestions(tmp_path: Path):
    proj = tmp_path / "empty"
    mkdir(proj, ".vscode")
    with pytest.raises(ProjectRootNotFoundWithSuggestions):
        find_project_root(start=proj / "child")
