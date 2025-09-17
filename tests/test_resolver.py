from pathlib import Path

from pysigil.resolver import (
    package_defaults_file,
    project_settings_file,
    user_settings_file,
)


def test_user_settings_file(monkeypatch, tmp_path: Path) -> None:
    def fake_user_config_dir(appname: str) -> str:
        assert appname == "sigil"
        return str(tmp_path)

    monkeypatch.setattr(
        "pysigil.resolver.user_config_dir", fake_user_config_dir
    )
    path = user_settings_file("demo")
    assert path == tmp_path / "demo" / "settings.ini"


def test_project_settings_file(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("")
    sub = tmp_path / "src"
    sub.mkdir()
    path = project_settings_file(start=sub)
    assert path == tmp_path / ".sigil" / "settings.ini"
    assert path.parent.is_dir()


def test_package_defaults_file(tmp_path: Path, monkeypatch) -> None:
    pkg = tmp_path / "pkg"
    (pkg / ".sigil").mkdir(parents=True)
    (pkg / ".sigil" / "settings.ini").write_text("[pkg]\nfoo=bar\n")
    (pkg / "__init__.py").write_text("")
    monkeypatch.syspath_prepend(tmp_path)
    path = package_defaults_file("pkg", filename="settings.ini")
    assert path == pkg / ".sigil" / "settings.ini"


def test_package_defaults_file_missing(tmp_path: Path, monkeypatch) -> None:
    pkg = tmp_path / "pkg_missing"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    monkeypatch.syspath_prepend(tmp_path)
    path = package_defaults_file("pkg_missing", filename="settings.ini")
    assert path == pkg / ".sigil" / "settings.ini"
    assert not path.exists()


def test_resolve_defaults_handles_provider_id_variants(
    tmp_path: Path, monkeypatch
) -> None:
    import importlib
    import sys

    provider_id = "sigil-dummy"
    package_name = "sigil_dummy"
    pkg = tmp_path / package_name
    (pkg / ".sigil").mkdir(parents=True)
    defaults = pkg / ".sigil" / "settings.ini"
    defaults.write_text("[pkg]\nfoo=bar\n")
    (pkg / "__init__.py").write_text("")

    sys.modules.pop(package_name, None)
    monkeypatch.syspath_prepend(tmp_path)
    importlib.invalidate_caches()

    from pysigil import resolver

    monkeypatch.setattr(resolver, "_installed_defaults", lambda *_: None)
    monkeypatch.setattr(resolver, "get_dev_link", lambda *_: None)

    path, source = resolver.resolve_defaults(provider_id)
    assert path == defaults
    assert source == "installed"

    sys.modules.pop(package_name, None)

def test_resolve_defaults_precedence(monkeypatch, tmp_path: Path) -> None:
    import types
    from pysigil import resolver

    installed = tmp_path / "installed.ini"
    dev = tmp_path / "dev.ini"
    installed.write_text("")
    dev.write_text("")

    monkeypatch.setattr(resolver, "_installed_defaults", lambda pid, fn: installed)
    monkeypatch.setattr(resolver, "get_dev_link", lambda pid: types.SimpleNamespace(defaults_path=dev))

    path, source = resolver.resolve_defaults("prov")
    assert path == installed and source == "installed"

    installed.unlink()
    path, source = resolver.resolve_defaults("prov")
    assert path == dev and source == "dev-link"

    dev.unlink()
    monkeypatch.setattr(resolver, "get_dev_link", lambda pid: None)
    path, source = resolver.resolve_defaults("prov")
    assert path is None and source == "none"
