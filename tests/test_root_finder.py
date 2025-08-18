from pathlib import Path

import pytest

from pysigil.root import (
    Candidate,
    ProjectRootNotFoundError,
    ProjectRootNotFoundWithSuggestionsError,
    find_project_root,
    suggest_candidates,
)

# ---------- helpers ----------

def mkfile(base: Path, rel: str, content: str = "x") -> Path:
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p

def mkdir(base: Path, rel: str) -> Path:
    p = base / rel
    p.mkdir(parents=True, exist_ok=True)
    return p

# ---------- core: Tier 0/1/2/3 detection ----------

def test_sentinel_file_detected(tmp_path: Path):
    # /proj/app/.sigil-root (wins immediately at that dir)
    app = tmp_path / "proj" / "app"
    mkdir(app, ".")
    mkfile(app, ".sigil-root", "pinned")
    # Even if a parent has other markers, nearest sentinel in walk wins at that level
    root = find_project_root(start=app / "sub" / "dir")
    assert root == app

def test_tier1_pyproject_detected(tmp_path: Path):
    pkg = tmp_path / "pkg"
    mkfile(pkg, "pyproject.toml", "[project]\nname='x'")
    # Start deeper; should return the dir with pyproject
    start = pkg / "src" / "x" / "deeper"
    mkdir(start, ".")
    root = find_project_root(start=start)
    assert root == pkg

def test_tier1_setup_cfg_detected(tmp_path: Path):
    d = tmp_path / "a" / "b" / "c"
    mkfile(tmp_path / "a" / "b", "setup.cfg", "")
    mkdir(d, ".")
    assert find_project_root(start=d) == tmp_path / "a" / "b"

def test_tier1_git_dir_detected(tmp_path: Path):
    repo = tmp_path / "repo"
    mkdir(repo, ".git")  # directory marker
    start = repo / "x" / "y"
    mkdir(start, ".")
    assert find_project_root(start=start) == repo

def test_tier1_git_file_worktree_detected(tmp_path: Path):
    repo = tmp_path / "repo"
    mkfile(repo, ".git", "gitdir: /worktrees/main")
    mkdir(repo / "src" / "pkg", ".")
    assert find_project_root(start=repo / "src" / "pkg") == repo

def test_nearest_within_tier_wins(tmp_path: Path):
    # pyproject at /proj and at /proj/app; starting at /proj/app/sub should pick /proj/app
    proj = tmp_path / "proj"
    app = proj / "app"
    mkfile(proj, "pyproject.toml", "")
    mkfile(app, "pyproject.toml", "")
    start = app / "sub"
    mkdir(start, ".")
    assert find_project_root(start=start) == app

def test_tier2_tox_when_no_tier1(tmp_path: Path):
    tool = tmp_path / "tooling"
    mkfile(tool, "tox.ini", "")
    start = tool / "src" / "pkg"
    mkdir(start, ".")
    assert find_project_root(start=start) == tool

@pytest.mark.parametrize(
    "fname",
    [
        "WORKSPACE",
        "WORKSPACE.bazel",
        "MODULE.bazel",
        "CMakeLists.txt",
        "package.json",
        "pnpm-workspace.yaml",
        "lerna.json",
        "turbo.json",
        "nx.json",
        "go.mod",
        "Cargo.toml",
        "pom.xml",
        "settings.gradle",
        "settings.gradle.kts",
    ],
)
def test_tier3_other_ecosystems_detected(tmp_path: Path, fname: str):
    root = tmp_path / "mono" / "svc"
    mkfile(root, fname, "")
    start = root / "sub" / "deep"
    mkdir(start, ".")
    assert find_project_root(start=start) == root

def test_tier_precedence_python_over_repo_root(tmp_path: Path):
    # monorepo root has .git; subdir has pyproject → Python (Tier1) should win from within subdir
    mono = tmp_path / "mono"
    mkdir(mono, ".git")
    py = mono / "services" / "py-svc"
    mkfile(py, "pyproject.toml", "")
    start = py / "src" / "x"
    mkdir(start, ".")
    assert find_project_root(start=start) == py

# ---------- IDE (guarded) behavior ----------

def test_ide_guard_accepts_vscode_core_files(tmp_path: Path):
    proj = tmp_path / "quick"
    mkfile(proj, ".vscode/settings.json", "{}")
    # No stronger markers; guarded IDE should pass
    start = proj / "sub"
    mkdir(start, ".")
    assert find_project_root(start=start) == proj

def test_ide_guard_accepts_idea_core_files(tmp_path: Path):
    proj = tmp_path / "quick2"
    mkfile(proj, ".idea/workspace.xml", "<project/>")
    start = proj / "x"
    mkdir(start, ".")
    assert find_project_root(start=start) == proj

def test_ide_guard_accepts_with_co_signals(tmp_path: Path):
    proj = tmp_path / "quick3"
    mkdir(proj, ".vscode")  # empty IDE dir
    mkfile(proj, "README.md", "# hi")  # co-signal
    start = proj / "z"
    mkdir(start, ".")
    assert find_project_root(start=start) == proj

def test_ide_guard_rejects_empty_ide_dir(tmp_path: Path):
    proj = tmp_path / "maybe"
    mkdir(proj, ".vscode")  # empty, no co-signal
    start = proj / "k"
    mkdir(start, ".")
    # Should not auto-select; should raise with suggestions
    with pytest.raises(ProjectRootNotFoundWithSuggestionsError) as e:
        find_project_root(start=start)
    # suggestions should include our dir because .vscode is a weak hint
    cands = e.value.candidates
    assert any(c.path == proj for c in cands)

def test_stronger_marker_trumps_ide(tmp_path: Path):
    proj = tmp_path / "both"
    mkfile(proj, ".vscode/settings.json", "{}")
    mkfile(proj, "pyproject.toml", "")
    # Tier1 should win over IDE
    assert find_project_root(start=proj / "deep") == proj

# ---------- failure / strict / suggestions ----------

def test_strict_false_returns_start(tmp_path: Path):
    nowhere = tmp_path / "nowhere" / "deep"
    mkdir(nowhere, ".")
    assert find_project_root(start=nowhere, strict=False) == nowhere.resolve()

def test_no_markers_raises_with_suggestions(tmp_path: Path):
    # But place some weak hints upward so suggestions are non-empty
    leaf = tmp_path / "a" / "b" / "c"
    mkdir(leaf, ".")
    mkfile(tmp_path / "a", "README.md", "# readme")
    mkfile(tmp_path, "Dockerfile", "FROM scratch")
    with pytest.raises(ProjectRootNotFoundWithSuggestionsError) as e:
        find_project_root(start=leaf)
    cands = e.value.candidates
    assert isinstance(cands, list) and len(cands) > 0
    # top candidate should be either tmp_path (Dockerfile+README at ancestor) or a/ (README)
    assert cands[0].path in {tmp_path, tmp_path / "a"}

# ---------- suggestions ranking & limits ----------

def test_suggestions_rank_by_score_then_proximity(tmp_path: Path):
    # Build a chain: leaf (README), parent (README+Makefile+Dockerfile), top (README)
    leaf = tmp_path / "x" / "y" / "z"
    mkdir(leaf, ".")
    mkfile(leaf, "README.md", "# leaf")
    mid = tmp_path / "x" / "y"
    mkfile(mid, "README.md", "# mid")
    mkfile(mid, "Makefile", "")
    mkfile(mid, "Dockerfile", "")
    top = tmp_path / "x"
    mkfile(top, "README", "top")
    # Mid should score highest and appear first
    cands = suggest_candidates(start=leaf, max_up=5, top_k=5)
    assert cands[0].path == mid
    assert "Dockerfile" in cands[0].hits and "Makefile" in cands[0].hits

def test_suggestions_respect_top_k_and_max_up(tmp_path: Path):
    base = tmp_path / "deep" / "a" / "b" / "c" / "d"
    mkdir(base, ".")
    # sprinkle weak hints across many ancestors
    mkfile(tmp_path / "deep", "README.md", "")
    mkfile(tmp_path / "deep" / "a", "Dockerfile", "")
    mkfile(tmp_path / "deep" / "a" / "b", "Makefile", "")
    mkfile(tmp_path / "deep" / "a" / "b" / "c", ".gitignore", "")
    cands = suggest_candidates(start=base, max_up=3, top_k=2)
    assert len(cands) == 2  # limited by top_k
    # max_up=3 means we only consider c, b, a (not the top 'deep')
    considered_paths = {c.path for c in cands}
    assert tmp_path / "deep" not in considered_paths

# ---------- edge/nuance tests ----------

def test_tier1_vs_tier2_precedence_same_dir(tmp_path: Path):
    d = tmp_path / "mix"
    mkfile(d, "tox.ini", "")
    mkfile(d, "pyproject.toml", "")
    # Same dir: pyproject (Tier1) should win over tox (Tier2), but since nearest dir is the same,
    # the chosen root is d regardless — this just ensures no crash and immediate return.
    assert find_project_root(start=d / "sub") == d

def test_tier3_github_dir_counts_as_root(tmp_path: Path):
    d = tmp_path / "infra"
    mkdir(d, ".github")
    assert find_project_root(start=d / "sub") == d

def test_candidate_model_fields(tmp_path: Path):
    # ensure dataclass is used and hits non-empty when a weak marker exists
    d = tmp_path / "w"
    mkfile(d, "README.md", "")
    cands = suggest_candidates(start=d)
    assert isinstance(cands[0], Candidate)
    assert cands[0].hits and isinstance(cands[0].score, int)

def test_error_types_and_message(tmp_path: Path):
    leaf = tmp_path / "leaf"
    mkdir(leaf, ".")
    with pytest.raises(ProjectRootNotFoundWithSuggestionsError) as e:
        find_project_root(start=leaf)
    err = e.value
    assert isinstance(err, ProjectRootNotFoundError)
    assert str(leaf) in str(err)
