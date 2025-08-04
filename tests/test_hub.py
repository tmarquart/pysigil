from __future__ import annotations

from pathlib import Path

from sigilcraft.gui import PrefModel
from sigilcraft.hub import get_preferences


def test_get_preferences_launch_gui(tmp_path, monkeypatch):
    # Prepare a prefs directory with a defaults file
    prefs_dir = tmp_path / "prefs"
    prefs_dir.mkdir()
    (prefs_dir / "settings.ini").write_text("[global]\ncolor = red\n")

    called: dict[str, object] = {}

    def fake_run(model: PrefModel, title: str) -> None:  # type: ignore[override]
        called["model"] = model
        called["title"] = title

    monkeypatch.setattr("sigilcraft.gui.run", fake_run)

    get_pref, set_pref, launch_gui = get_preferences(
        "sigilcraft", default_pref_directory=str(prefs_dir)
    )

    assert get_pref("color") == "red"

    launch_gui()

    assert isinstance(called["model"], PrefModel)
    assert called["title"] == "Sigil Preferences — sigilcraft"
