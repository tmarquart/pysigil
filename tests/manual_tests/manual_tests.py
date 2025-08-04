# ruff: noqa

from __future__ import annotations

from requests_toolbelt.adapters.appengine import monkeypatch

from sigilcraft.backend.ini_backend import IniBackend

from sigilcraft import cli, core

from sigilcraft.backend.yaml_backend import YamlBackend
import shutil
import sys
from pathlib import Path

from sigilcraft.helpers import make_package_prefs

def manual_ini_backend_roundtrip():
    path = Path("artifacts/cfg.ini")
    backend = IniBackend()
    data = {"global": {"a": "1"}, "sec": {"b": "2"}}
    backend.save(path, data)
    loaded = backend.load(path)
    assert loaded == data

def manual_yaml_backend_roundtrip(tmp_path: Path):
    flat = {"x.y": 1, "x.z": True, "name": "Sigil"}
    path = tmp_path / "t.yaml"
    YamlBackend().save(path, flat)
    assert YamlBackend().load(path) == flat

def manual_make_package_prefs_explicit(tmp_path: Path):
    pkg = tmp_path / "pkgexp"
    pkg.mkdir(exist_ok=True)
    (pkg / "__init__.py").write_text("")
    prefs = pkg / "prefs"
    prefs.mkdir(exist_ok=True)
    (prefs / "defaults.yaml").write_text("[ui]\ntheme=light\n")
    sys.path.insert(0, str(tmp_path))
    config_dir = Path.home() / ".config" / "myapp_explicit"
    if config_dir.exists():
        shutil.rmtree(config_dir)
    try:
        get_pref, set_pref = make_package_prefs(app_name="myapp_explicit", package="pkgexp")
        assert get_pref("ui.theme") == "light"
        set_pref("ui.theme", "dark")
        assert get_pref("ui.theme") == "dark"
    finally:
        sys.path.pop(0)
        if config_dir.exists():
            shutil.rmtree(config_dir)

    set_pref()

if __name__=='__main__':
    manual_ini_backend_roundtrip()
    #manual_yaml_backend_roundtrip(Path('artifacts'))
    #manual_make_package_prefs_explicit(Path('artifacts'))
