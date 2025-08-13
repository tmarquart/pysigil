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
    assert path == tmp_path / ".pysigil" / "settings.ini"
    assert path.parent.is_dir()


def test_package_defaults_file(tmp_path: Path, monkeypatch) -> None:
    pkg = tmp_path / "pkg"
    (pkg / "prefs").mkdir(parents=True)
    (pkg / "prefs" / "settings.ini").write_text("[pkg]\nfoo=bar\n")
    (pkg / "__init__.py").write_text("")
    monkeypatch.syspath_prepend(tmp_path)
    path = package_defaults_file("pkg", filename="settings.ini")
    assert path == pkg / "prefs" / "settings.ini"


def test_package_defaults_file_missing(tmp_path: Path, monkeypatch) -> None:
    pkg = tmp_path / "pkg_missing"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    monkeypatch.syspath_prepend(tmp_path)
    path = package_defaults_file("pkg_missing", filename="settings.ini")
    assert path == pkg / "prefs" / "settings.ini"
    assert not path.exists()
