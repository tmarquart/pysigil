from __future__ import annotations

import sys
from pathlib import Path

import importlib

from sigil import core
from sigil.hub import get_preferences


def test_get_preferences(tmp_path: Path, monkeypatch):
    root = tmp_path / "proj"
    pkg = root / "mypkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    prefs = pkg / "prefs"
    prefs.mkdir()
    (prefs / "defaults.ini").write_text("[db]\nhost=localhost\n")
    (root / "pyproject.toml").write_text(
        "[tool.sigil]\ndefaults = 'mypkg/prefs/defaults.ini'\n"
    )

    monkeypatch.setattr(core, "user_config_dir", lambda app: str(tmp_path / app))
    sys.path.insert(0, str(root))
    try:
        get_pref, set_pref = get_preferences("mypkg")
        assert get_pref("db.host") == "localhost"
        set_pref("db.host", "remote")
        assert get_pref("db.host") == "remote"
    finally:
        sys.path.pop(0)
