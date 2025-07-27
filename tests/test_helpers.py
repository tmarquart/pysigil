from __future__ import annotations

import importlib
import sys
import shutil
from pathlib import Path

from sigil.helpers import make_package_prefs


def test_make_package_prefs_explicit(tmp_path: Path):
    pkg = tmp_path / "pkgexp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    prefs = pkg / "prefs"
    prefs.mkdir()
    (prefs / "defaults.ini").write_text("[ui]\ntheme=light\n")
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


def test_make_package_prefs_infer(tmp_path: Path):
    pkg = tmp_path / "pkginf"
    pkg.mkdir()
    prefs = pkg / "prefs"
    prefs.mkdir()
    (prefs / "defaults.ini").write_text("[ui]\ntheme=light\n")
    (pkg / "__init__.py").write_text(
        "from sigil.helpers import make_package_prefs\n"
        "get_pref, set_pref = make_package_prefs(app_name='myapp_infer')\n"
    )
    sys.path.insert(0, str(tmp_path))
    config_dir = Path.home() / ".config" / "myapp_infer"
    if config_dir.exists():
        shutil.rmtree(config_dir)
    try:
        mod = importlib.import_module("pkginf")
        assert mod.get_pref("ui.theme") == "light"
        mod.set_pref("ui.theme", "dark")
        assert mod.get_pref("ui.theme") == "dark"
    finally:
        sys.path.pop(0)
        sys.modules.pop("pkginf", None)
        if config_dir.exists():
            shutil.rmtree(config_dir)

