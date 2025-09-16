from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

import pysigil.authoring as authoring
from pysigil import cli
from pysigil.authoring import ensure_sigil_package_data


def _write_pyproject(root: Path, name: str) -> None:
    content = f"[project]\nname = \"{name}\"\n"
    (root / "pyproject.toml").write_text(content, encoding="utf-8")


def test_ensure_sigil_package_data(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, "demo")
    ensure_sigil_package_data(tmp_path, "demo_pkg")
    data = tomllib.loads((tmp_path / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["tool"]["setuptools"]["package-data"]["demo_pkg"] == [".sigil/*"]
    # idempotent
    ensure_sigil_package_data(tmp_path, "demo_pkg")
    data = tomllib.loads((tmp_path / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["tool"]["setuptools"]["package-data"]["demo_pkg"] == [".sigil/*"]


def test_author_register_adds_package_data(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path
    _write_pyproject(root, "demo-pkg")
    pkg = root / "src" / "demo_pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").touch()

    monkeypatch.setattr(authoring, "_dev_dir", lambda: tmp_path / "dev")
    monkeypatch.chdir(root)

    ns = argparse.Namespace(
        auto=True,
        package_dir=None,
        defaults=None,
        provider=None,
        no_validate=True,
    )
    assert cli.author_register(ns) == 0
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["tool"]["setuptools"]["package-data"]["demo_pkg"] == [".sigil/*"]

