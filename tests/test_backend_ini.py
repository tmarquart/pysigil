from __future__ import annotations

from pathlib import Path

from pysigil.backends.ini_backend import IniBackend


def test_ini_backend_roundtrip(tmp_path: Path):
    path = tmp_path / "cfg.ini"
    backend = IniBackend()
    data = {("api", "v2", "timeout"): "30"}
    backend.save(path, data)
    text = path.read_text()
    assert "v2_timeout = 30" in text
    loaded = backend.load(path)
    assert loaded == data


def test_ini_backend_legacy_read(tmp_path: Path):
    path = tmp_path / "cfg.ini"
    path.write_text("[api]\nv2.timeout = 30\n")
    backend = IniBackend()
    loaded = backend.load(path)
    assert loaded == {("api", "v2", "timeout"): "30"}
    backend.save(path, loaded)
    assert "v2_timeout = 30" in path.read_text()
