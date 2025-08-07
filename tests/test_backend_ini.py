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
