from pathlib import Path

from pysigil import Sigil


def test_roundtrip(tmp_path: Path) -> None:
    s = Sigil("demo", user_scope=tmp_path)
    s.set_pref("foo.bar", "baz", scope="user")
    assert s.get_pref("foo.bar") == "baz"
    content = (tmp_path / "settings.ini").read_text()
    assert "[demo]" in content
    assert "foo_bar = baz" in content


def test_default_roundtrip(tmp_path: Path) -> None:
    user_dir = tmp_path / "user"
    default_file = tmp_path / "defaults.ini"
    s = Sigil(
        "demo",
        user_scope=user_dir,
        default_path=default_file,
        settings_filename="defaults.ini",
    )
    s.set_pref("foo.bar", "baz", scope="default")
    assert s.get_pref("foo.bar") == "baz"
    content = default_file.read_text()
    assert "[demo]" in content
    assert "foo_bar = baz" in content
