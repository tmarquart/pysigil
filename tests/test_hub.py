from __future__ import annotations

from pathlib import Path

from sigilcraft.core import Sigil
from sigilcraft.hub import get_preferences


def test_get_preferences_launch_gui(tmp_path, monkeypatch):
    # Prepare a prefs directory with a defaults file
    prefs_dir = tmp_path / "prefs"
    prefs_dir.mkdir()
    (prefs_dir / "settings.ini").write_text("[__root__]\ncolor = red\n")

    called: dict[str, object] = {}

    def fake_launch(*, package=None, allow_default_write=True, sigil=None):
        called["sigil"] = sigil

    monkeypatch.setattr("sigilcraft.gui.launch_gui", fake_launch)

    get_pref, set_pref, launch_gui = get_preferences(
        "sigilcraft", default_pref_directory=str(prefs_dir)
    )

    assert get_pref("color") == "red"

    launch_gui()

    assert isinstance(called["sigil"], Sigil)
    assert called["sigil"].app_name == "sigilcraft"
