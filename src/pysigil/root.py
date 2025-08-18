# pysigil/root.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
import re

__all__ = [
    "ProjectRootNotFoundError",
    "ProjectRootNotFoundWithSuggestions",
    "Candidate",
    "find_project_root",
    "suggest_candidates",
]

# =========================================================
# Exceptions & suggestion model
# =========================================================

class ProjectRootNotFoundError(RuntimeError):
    """Raised when no project root can be located."""

@dataclass(frozen=True)
class Candidate:
    """A ranked fallback directory that *looks* like a project root."""
    path: Path
    score: int
    hits: tuple[str, ...]  # marker names contributing to the score

class ProjectRootNotFoundWithSuggestions(ProjectRootNotFoundError):
    """
    Raised when no strong root is found; includes ranked candidates.
    Catch this to present choices and (optionally) place a sentinel.
    """
    def __init__(self, start: Path, candidates: list[Candidate]):
        super().__init__(f"No project root found from {start}")
        self.start = start
        self.candidates = candidates

# =========================================================
# Hard-coded strong tiers (auto-detect)
# =========================================================

# Tier 0 – explicit sentinel (owner intent beats all)
_SENTINEL_FILE = ".sigil-root"

# Tier 1 – Python packaging + VCS
_TIER1_FILES: tuple[str, ...] = ("pyproject.toml", "setup.cfg", "setup.py")
_TIER1_DIRS:  tuple[str, ...] = (".git", ".hg", ".svn")

# Tier 2 – Python tools
_TIER2_FILES: tuple[str, ...] = ("tox.ini", "poetry.lock", "pdm.lock")
_TIER2_DIRS:  tuple[str, ...] = (".dvc",)

# Tier 3 – other ecosystems / monorepo roots
_TIER3_FILES: tuple[str, ...] = (
    # Bazel/CMake
    "WORKSPACE", "WORKSPACE.bazel", "MODULE.bazel", "CMakeLists.txt",
    # JS/TS monorepos & tools
    "package.json", "pnpm-workspace.yaml", "lerna.json", "turbo.json", "nx.json",
    # Go / Rust / Java/Kotlin
    "go.mod", "Cargo.toml", "pom.xml", "settings.gradle", "settings.gradle.kts",
)
_TIER3_DIRS: tuple[str, ...] = (".github",)  # weak but repo-level and useful

# IDE dirs (treated as strong by default, but with guards)
_IDE_DIRS: tuple[str, ...] = (".idea", ".vscode")

# =========================================================
# Weak “massive net” (suggestions only; never auto-pick)
# =========================================================

_WEAK_FILES: tuple[str, ...] = (
    "README", "README.md", "README.rst",
    "LICENSE", "LICENSE.md",
    ".gitignore", ".gitattributes", ".editorconfig",
    ".pre-commit-config.yaml", ".ruff.toml", ".flake8",
    "requirements.txt", "requirements-dev.txt", "environment.yml",
    "Pipfile", "Pipfile.lock", ".python-version",
    "Makefile", "Dockerfile", "docker-compose.yml", "compose.yaml",
    ".gitlab-ci.yml", "azure-pipelines.yml", "Jenkinsfile",
    ".nvmrc", ".node-version", ".tool-versions", "tsconfig.json",
)
_WEAK_DIRS: tuple[str, ...] = (".github", ".github/workflows", ".idea", ".vscode")

_WEIGHTS: dict[str, int] = {
    # docs / legal
    "README": 10, "README.md": 10, "README.rst": 10,
    "LICENSE": 10, "LICENSE.md": 10,
    # git/editor hygiene
    ".gitignore": 10, ".gitattributes": 10, ".editorconfig": 8,
    # qa/tooling
    ".pre-commit-config.yaml": 8, ".ruff.toml": 8, ".flake8": 6,
    # python env
    "requirements.txt": 12, "requirements-dev.txt": 12, "environment.yml": 12,
    "Pipfile": 12, "Pipfile.lock": 12, ".python-version": 6,
    # build/devops
    "Makefile": 10, "Dockerfile": 10, "docker-compose.yml": 10, "compose.yaml": 10,
    # CI
    ".github": 10, ".github/workflows": 10, ".gitlab-ci.yml": 10,
    "azure-pipelines.yml": 10, "Jenkinsfile": 10,
    # language hints
    ".nvmrc": 6, ".node-version": 6, ".tool-versions": 6, "tsconfig.json": 6,
    # IDE dirs (weak as hints only)
    ".idea": 6, ".vscode": 6,
}

# =========================================================
# Internals
# =========================================================

_GITDIR_RE = re.compile(r"^\s*gitdir:\s*(.+)\s*$", re.IGNORECASE)

def _has_git_marker(d: Path) -> bool:
    g = d / ".git"
    if g.is_dir():
        return True
    if g.is_file():
        try:
            return bool(_GITDIR_RE.search(g.read_text(errors="ignore")))
        except Exception:
            return False
    return False

def _walk_up(start: Path) -> Iterable[Path]:
    cur = start
    while True:
        yield cur
        if cur.parent == cur:
            break
        cur = cur.parent

def _match_here(cur: Path, *, files: Sequence[str], dirs: Sequence[str]) -> str | None:
    for f in files:
        if (cur / f).is_file():
            return f
    for d in dirs:
        if d == ".git":
            if _has_git_marker(cur):
                return ".git"
        elif (cur / d).is_dir():
            return d
    return None

# ---------- IDE guard (prevents stray matches) ----------

def _is_real_vscode(cur: Path) -> bool:
    vs = cur / ".vscode"
    return any((vs / n).is_file() for n in ("settings.json", "launch.json", "tasks.json"))

def _is_real_jetbrains(cur: Path) -> bool:
    ij = cur / ".idea"
    return any((ij / n).is_file() for n in ("workspace.xml", "modules.xml", "misc.xml", "project.iml"))

_CO_SIGNALS: tuple[str, ...] = (
    "README", "README.md", "Makefile", "Dockerfile",
    "requirements.txt", "requirements-dev.txt", "environment.yml",
    ".gitignore", ".editorconfig", "package.json",
)

def _has_co_signal(cur: Path) -> bool:
    return any((cur / f).exists() for f in _CO_SIGNALS)

def _ide_guard_ok(cur: Path) -> bool:
    return _is_real_vscode(cur) or _is_real_jetbrains(cur) or _has_co_signal(cur)

# ---------- Suggestions scoring ----------

def _score_dir(cur: Path) -> Candidate | None:
    hits: list[str] = []
    score = 0
    for f in _WEAK_FILES:
        if (cur / f).is_file():
            hits.append(f)
            score += _WEIGHTS.get(f, 5)
    for d in _WEAK_DIRS:
        if (cur / d).is_dir():
            hits.append(d)
            score += _WEIGHTS.get(d, 5)
    if score == 0:
        return None
    return Candidate(path=cur, score=score, hits=tuple(hits))

# =========================================================
# Public API
# =========================================================

def suggest_candidates(
    start: str | Path | None = None,
    *,
    max_up: int = 16,
    top_k: int = 5,
) -> list[Candidate]:
    """
    Return top-k directories above `start` that *look* like project roots,
    ranked by weak-marker score (higher is better), then by proximity (nearer first).
    """
    start_path = (Path.cwd() if start is None else Path(start)).resolve(strict=False)

    # distance map for proximity tie-break
    dist_index: dict[Path, int] = {}
    for i, cur in enumerate(_walk_up(start_path)):
        dist_index[cur] = i
        if i >= max_up:
            break

    cands: list[Candidate] = []
    for cur, i in dist_index.items():
        cand = _score_dir(cur)
        if cand:
            cands.append(cand)

    cands.sort(key=lambda c: (-c.score, dist_index.get(c.path, 1_000_000)))
    return cands[:top_k]

def find_project_root(
    start: str | Path | None = None,
    *,
    strict: bool = True,
) -> Path:
    """
    Find the nearest project root above `start` using strong markers.

    Priority (two-pass, nearest within each pass wins):
      Pass A:  .sigil-root  →  Tier1 (py packaging + VCS)  →  Tier2 (py tools)
      Pass B:  Tier3 (other ecosystems)  →  IDE dirs (guarded)

    If nothing matches and `strict=True`, raises ProjectRootNotFoundWithSuggestions
    containing ranked fallback candidates (weak 'massive net').
    If `strict=False`, returns the resolved starting directory.
    """
    start_path = (Path.cwd() if start is None else Path(start)).resolve(strict=False)

    # Pass A: strongest tiers
    for cur in _walk_up(start_path):
        if (cur / _SENTINEL_FILE).is_file():
            return cur
        if _match_here(cur, files=_TIER1_FILES, dirs=_TIER1_DIRS):
            return cur
        if _match_here(cur, files=_TIER2_FILES, dirs=_TIER2_DIRS):
            return cur

    # Pass B: other ecosystems (then guarded IDE markers)
    for cur in _walk_up(start_path):
        if _match_here(cur, files=_TIER3_FILES, dirs=_TIER3_DIRS):
            return cur
        if any((cur / d).is_dir() for d in _IDE_DIRS) and _ide_guard_ok(cur):
            return cur

    # Nothing strong found → suggest candidates or fallback
    if strict:
        raise ProjectRootNotFoundWithSuggestions(start_path, suggest_candidates(start_path))
    return start_path
