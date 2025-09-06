from __future__ import annotations

from pathlib import Path

from pysigil import helpers_for


def test_helpers_for_isolated_apps(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    get_a, set_a = helpers_for("demo")
    set_a("section.value", "1")
    assert get_a("section.value", cast=int) == 1

    get_b, set_b = helpers_for("other")
    assert get_b("section.value") is None
    set_b("section.value", "2")
    assert get_b("section.value", cast=int) == 2

    # original demo settings remain unchanged
    assert get_a("section.value", cast=int) == 1
