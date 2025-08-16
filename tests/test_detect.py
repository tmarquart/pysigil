from __future__ import annotations

from pathlib import Path

from pysigil.resolver import (
    default_provider_id,
    ensure_defaults_file,
    find_package_dir,
    read_dist_name_from_pyproject,
)
from pysigil.root import find_project_root


def write_pyproject(root: Path, name: str | None = None) -> None:
    content = "[project]\n"
    if name is not None:
        content += f"name = \"{name}\"\n"
    (root / "pyproject.toml").write_text(content, encoding="utf-8")


def test_find_project_root_pyproject(tmp_path: Path) -> None:
    write_pyproject(tmp_path)
    sub = tmp_path / "sub"
    sub.mkdir()
    assert find_project_root(sub) == tmp_path


def test_provider_from_pyproject(tmp_path: Path) -> None:
    write_pyproject(tmp_path, name="My_Package.Name")
    name = read_dist_name_from_pyproject(tmp_path)
    assert name == "My_Package.Name"
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").touch()
    assert (
        default_provider_id(pkg, name) == "my-package-name"
    )


def test_find_package_src_layout(tmp_path: Path) -> None:
    write_pyproject(tmp_path, name="my-pkg")
    pkg = tmp_path / "src" / "my_pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").touch()
    found = find_package_dir(tmp_path, "my-pkg")
    assert found == pkg


def test_find_package_flat_layout(tmp_path: Path) -> None:
    write_pyproject(tmp_path, name="my-pkg")
    pkg = tmp_path / "my_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").touch()
    found = find_package_dir(tmp_path, "my-pkg")
    assert found == pkg


def test_single_package_under_src(tmp_path: Path) -> None:
    write_pyproject(tmp_path)
    pkg = tmp_path / "src" / "only_pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").touch()
    found = find_package_dir(tmp_path, None)
    assert found == pkg


def test_ambiguous_packages(tmp_path: Path) -> None:
    write_pyproject(tmp_path)
    for name in ["a", "b"]:
        pkg = tmp_path / "src" / name
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").touch()
    assert find_package_dir(tmp_path, None) is None


def test_ensure_defaults_file(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").touch()
    ini = ensure_defaults_file(pkg, "prov")
    text = ini.read_text(encoding="utf-8")
    assert "[prov]" in text
