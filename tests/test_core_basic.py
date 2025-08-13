from pathlib import Path

from pysigil import Sigil


def test_roundtrip(tmp_path: Path) -> None:
    s = Sigil("demo", user_scope=tmp_path)
    s.set_pref("foo.bar", "baz", scope="user")
    assert s.get_pref("foo.bar") == "baz"
    content = (tmp_path / "settings.ini").read_text()
    assert "[demo]" in content
    assert "foo_bar = baz" in content
