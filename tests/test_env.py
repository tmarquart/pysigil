from __future__ import annotations

from sigil.env import read_env


def test_read_env(monkeypatch):
    monkeypatch.setenv("SIGIL_MYAPP_FOO_BAR", "baz")
    result = read_env("myapp")
    assert result == {"foo.bar": "baz"}
