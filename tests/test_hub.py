from __future__ import annotations

from pathlib import Path

from pysigil.core import Sigil
from pysigil.hub import get_preferences


def test_get_preferences_launch_gui(tmp_path, monkeypatch):
    # Prepare a prefs directory with a defaults file
    prefs_dir = tmp_path / "prefs"
    prefs_dir.mkdir()
    (prefs_dir / "settings.ini").write_text("[__root__]\ncolor = red\n")

    called: dict[str, object] = {}

    def fake_launch(*, sigil=None, **kwargs):
        called["sigil"] = sigil

    monkeypatch.setattr("pysigil.gui.launch_gui", fake_launch)

    get_pref, set_pref, effective_scope_for, launch_gui = get_preferences(
        "pysigil", default_pref_directory=str(prefs_dir)
    )

    assert get_pref("color") == "red"

    launch_gui()

    assert isinstance(called["sigil"], Sigil)
    assert called["sigil"].app_name == "pysigil"
