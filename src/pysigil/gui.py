from __future__ import annotations

import argparse
import logging
from pathlib import Path

try:  # pragma: no cover - tkinter may be missing
    import tkinter as tk
except Exception:  # pragma: no cover - fallback for headless envs
    tk = None  # type: ignore

from .core import Sigil

logger = logging.getLogger(__name__)


class SigilGUI:
    """Tiny Tk-based editor for user preferences."""

    def __init__(self, sigil: Sigil) -> None:
        if tk is None:  # pragma: no cover - depends on platform
            raise RuntimeError("tkinter is required for GUI mode")
        try:
            self.root = tk.Tk()
        except Exception as exc:  # pragma: no cover - headless display
            raise RuntimeError("tkinter failed to initialize") from exc
        self.root.title(f"Sigil Preferences — {sigil.app_name}")
        self.sigil = sigil
        self._vars: dict[str, tk.StringVar] = {}
        prefs = sigil.scoped_values().get("user", {})
        for row, (key, value) in enumerate(sorted(prefs.items())):
            tk.Label(self.root, text=key).grid(row=row, column=0, sticky="w", padx=4, pady=2)
            var = tk.StringVar(value=value)
            tk.Entry(self.root, textvariable=var).grid(row=row, column=1, sticky="ew", padx=4, pady=2)
            self._vars[key] = var
        tk.Button(self.root, text="Save", command=self._save).grid(
            row=len(prefs), column=0, columnspan=2, pady=4
        )

    def _save(self) -> None:
        for key, var in self._vars.items():
            self.sigil.set_pref(key, var.get(), scope="user")
        self.root.destroy()

    def run(self) -> None:
        """Start the Tk mainloop."""
        self.root.mainloop()


def launch_gui(argv: list[str] | None = None) -> None:
    """Entry point for ``sigil-gui`` script."""
    parser = argparse.ArgumentParser(description="Launch Sigil preferences GUI")
    parser.add_argument("--app", required=True, help="Application name")
    parser.add_argument(
        "--user-path",
        type=Path,
        help="Optional path to the user settings file (default: platform standard)",
    )
    args = parser.parse_args(argv)
    sigil = Sigil(args.app, user_scope=args.user_path)
    gui = SigilGUI(sigil)
    gui.run()


__all__ = ["SigilGUI", "launch_gui"]
