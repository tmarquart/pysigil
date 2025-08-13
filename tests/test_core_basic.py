from pathlib import Path

from pysigil import Sigil


def test_roundtrip(tmp_path: Path) -> None:
    user = tmp_path / "user.ini"
    s = Sigil("demo", user_scope=user)
    s.set_pref("foo.bar", "baz", scope="user")
    assert s.get_pref("foo.bar") == "baz"
