from __future__ import annotations

from pathlib import Path

from sigilcraft.backend.ini_backend import IniBackend
from sigilcraft.keys import KeyPath


def test_ini_backend_roundtrip(tmp_path: Path):
    path = tmp_path / "cfg.ini"
    backend = IniBackend()
    data = {("a",): "1", ("sec", "b"): "2", ("sec", "deep", "c"): "3"}
    backend.save(path, data)
    loaded = backend.load(path)
    assert loaded == data


def test_join_char_underscore(tmp_path: Path):
    path = tmp_path / "cfg.ini"
    backend = IniBackend()
    data = {("api", "v2", "timeout"): "30"}
    backend.save(path, data)
    text = path.read_text()
    assert "v2_timeout" in text
    loaded = backend.load(path)
    assert loaded == data


def test_join_char_dot(monkeypatch, tmp_path: Path):
    path = tmp_path / "cfg.ini"
    backend = IniBackend()
    monkeypatch.setattr(
        "sigilcraft.backend.ini_backend.get_pref", lambda *a, **k: "."
    )
    data = {("api", "v2", "timeout"): "30"}
    backend.save(path, data)
    text = path.read_text()
    assert "v2.timeout" in text
    loaded = backend.load(path)
    assert loaded == data
