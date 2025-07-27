"""ttk-based Preferences GUI."""

from __future__ import annotations

from .model import PrefModel
from .tk_view import run


def launch_gui(app_name: str) -> None:
    """Entry point used by the ``sigil-gui`` console script."""
    from ..core import Sigil
    from ..helpers import load_meta

    sigil = Sigil(app_name)
    meta_path = sigil.user_path.parent / "defaults.meta.csv"
    try:
        meta = load_meta(meta_path)
    except Exception:
        meta = {}
    run(PrefModel(sigil, meta), f"Sigil Preferences — {app_name}")

__all__ = ["launch_gui", "PrefModel", "run"]
