from __future__ import annotations

from pathlib import Path

import pytest

from sigil.backend.json_backend import JsonBackend
from sigil.errors import SigilLoadError


def test_json_backend_roundtrip(tmp_path: Path):
    flat = {"x.y": 1, "x.z": True, "name": "Sigil"}
    path = tmp_path / "t.json"
    JsonBackend().save(path, flat)
    assert JsonBackend().load(path) == flat


def test_empty_file(tmp_path: Path):
    path = tmp_path / "empty.json"
    path.write_text("", encoding="utf-8")
    assert JsonBackend().load(path) == {}


def test_deep_nesting(tmp_path: Path):
    flat = {"a.b.c.d": 2}
    path = tmp_path / "deep.json"
    JsonBackend().save(path, flat)
    assert JsonBackend().load(path) == flat


def test_invalid_json(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("{ invalid", encoding="utf-8")
    with pytest.raises(SigilLoadError):
        JsonBackend().load(path)


def test_json5_relaxed(tmp_path: Path):
    try:
        import pyjson5  # type: ignore
    except ModuleNotFoundError:
        pytest.skip("pyjson5 not installed")
    path = tmp_path / "relaxed.json5"
    path.write_text("//c\n{a:1,}\n", encoding="utf-8")
    assert JsonBackend().load(path) == {"a": 1}

