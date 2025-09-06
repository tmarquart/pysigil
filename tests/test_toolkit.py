from __future__ import annotations

from pathlib import Path

from pysigil import get_setting, init, set_setting


def test_cached_instances(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    sig1 = init("demo")
    set_setting("section.value", "1")
    assert get_setting("section.value") == 1

    sig2 = init("demo")
    assert sig1 is sig2

    init("other")
    assert get_setting("section.value") is None
    set_setting("section.value", "2")
    assert get_setting("section.value") == 2

    init("demo")
    assert get_setting("section.value", cast=int) == 1
