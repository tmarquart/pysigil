from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from pysigil.io_config import DefaultsFormatError, IniIOError, load_provider_defaults


@pytest.fixture
def package_builder(tmp_path, monkeypatch):
    created: list[str] = []

    def build(
        name: str,
        *,
        ini_content: str | None = None,
        create_sigil_dir: bool = False,
    ) -> tuple[str, Path]:
        pkg_dir = tmp_path / name
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
        if create_sigil_dir:
            (pkg_dir / ".sigil").mkdir()
        if ini_content is not None:
            sigil_dir = pkg_dir / ".sigil"
            sigil_dir.mkdir(exist_ok=True)
            (sigil_dir / "settings.ini").write_text(ini_content, encoding="utf-8")
        monkeypatch.syspath_prepend(str(tmp_path))
        importlib.invalidate_caches()
        sys.modules.pop(name, None)
        created.append(name)
        return name, pkg_dir

    yield build

    for name in created:
        sys.modules.pop(name, None)


def test_load_provider_defaults_missing_package() -> None:
    result = load_provider_defaults("provider", "pkg_does_not_exist")
    assert result == {}


def test_load_provider_defaults_without_settings(package_builder) -> None:
    name, _ = package_builder("pkg_without_defaults")
    result = load_provider_defaults("provider", name)
    assert result == {}


def test_load_provider_defaults_empty_directory(package_builder) -> None:
    name, _ = package_builder("pkg_with_empty_dir", create_sigil_dir=True)
    result = load_provider_defaults("provider", name)
    assert result == {}


def test_load_provider_defaults_missing_provider_section(package_builder) -> None:
    name, _ = package_builder(
        "pkg_missing_provider",
        ini_content="[other]\nvalue = 1\n",
    )
    with pytest.raises(DefaultsFormatError):
        load_provider_defaults("provider", name)


def test_load_provider_defaults_with_pysigil_section(package_builder) -> None:
    name, _ = package_builder(
        "pkg_with_pysigil",
        ini_content=(
            "[provider]\n"
            "alpha = one\n"
            "beta = two\n"
            "\n"
            "[pysigil]\n"
            "scope = project\n"
        ),
    )
    result = load_provider_defaults("provider", name)
    assert result == {
        "provider": {"alpha": "one", "beta": "two"},
        "pysigil": {"scope": "project"},
    }


def test_load_provider_defaults_provider_only(package_builder) -> None:
    name, _ = package_builder(
        "pkg_provider_only",
        ini_content="[provider]\nvalue = test\n",
    )
    result = load_provider_defaults("provider", name)
    assert result == {"provider": {"value": "test"}}


def test_load_provider_defaults_malformed_content(package_builder) -> None:
    name, _ = package_builder(
        "pkg_malformed",
        ini_content="not a valid ini file",
    )
    with pytest.raises(IniIOError):
        load_provider_defaults("provider", name)
