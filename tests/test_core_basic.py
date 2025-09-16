import os
from pathlib import Path

import pytest

from pysigil import Sigil
from pysigil.policy import policy
from pysigil.errors import ReadOnlyScopeError


def test_roundtrip(tmp_path: Path) -> None:
    s = Sigil("demo", user_scope=tmp_path, policy=policy)
    s.set_pref("foo.bar", "baz", scope="user")
    assert s.get_pref("foo.bar") == "baz"
    content = (tmp_path / "settings.ini").read_text()
    assert "[demo]" in content
    assert "foo_bar = baz" in content
def test_package_defaults_read_only(tmp_path: Path, monkeypatch) -> None:
    pkg = tmp_path / "pkgdefaults"
    (pkg / ".sigil").mkdir(parents=True)
    (pkg / ".sigil" / "settings.ini").write_text("[pkgdefaults]\nfoo = 7\n")
    (pkg / "__init__.py").write_text("")
    monkeypatch.syspath_prepend(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    user_dir = tmp_path / "user"
    s = Sigil("pkgdefaults", user_scope=user_dir, policy=policy)
    # assert s.get_pref("foo") == 7
    with pytest.raises(ReadOnlyScopeError):
        s.set_pref("foo", "8", scope="default")


def test_dev_link_defaults_writable(tmp_path: Path, monkeypatch) -> None:
    pkg = tmp_path / "pkgdefaults"
    (pkg / ".sigil").mkdir(parents=True)
    settings = pkg / ".sigil" / "settings.ini"
    settings.write_text("[pkgdefaults]\nfoo = 7\n")
    (pkg / "__init__.py").write_text("")
    monkeypatch.syspath_prepend(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    from pysigil.authoring import link

    link("pkgdefaults", settings)
    user_dir = tmp_path / "user"
    s = Sigil("pkgdefaults", user_scope=user_dir, policy=policy)
    s.set_pref("foo", "8", scope="default")
    assert s.get_pref("foo") == 8
    assert "foo = 8" in settings.read_text()


def test_explicit_default_path_writable(tmp_path: Path) -> None:
    default_dir = tmp_path / "defaults"
    s = Sigil("demo", user_scope=tmp_path / "user.ini", default_path=default_dir, policy=policy)
    s.set_pref("foo", "bar", scope="default")
    assert s.get_pref("foo") == "bar"

    settings_file = default_dir / ".sigil" / "settings.ini"

    assert "foo = bar" in settings_file.read_text()
    s2 = Sigil("demo", user_scope=tmp_path / "user2.ini", default_path=default_dir, policy=policy)
    assert s2.get_pref("foo") == "bar"


def test_environment_scope_updates_environ(monkeypatch, tmp_path: Path) -> None:
    sigil = Sigil("demo", user_scope=tmp_path / "user", policy=policy)
    env_key = "SIGIL_DEMO_SECTION_VALUE"
    monkeypatch.delenv(env_key, raising=False)

    try:
        sigil.set_pref("section.value", "123", scope="env")
        assert os.environ[env_key] == "123"
        assert sigil.get_pref("section.value") == 123
    finally:
        sigil.set_pref("section.value", None, scope="env")
    assert env_key not in os.environ
    assert sigil.get_pref("section.value") is None

