from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk

from .model import PrefModel

logger = logging.getLogger("sigil.gui")


def run(model: PrefModel, app_title: str | None = None) -> None:
    logger.info("Starting Tk preferences window")
    root = tk.Tk()
    if app_title:
        root.title(app_title)
    frame = ttk.Frame(root, padding=10)
    frame.pack(fill="both", expand=True)
    label = ttk.Label(frame, text="Preferences for " + model.sigil.app_name)
    label.pack()

    notebook = ttk.Notebook(frame)
    notebook.pack(fill="both", expand=True, padx=5, pady=5)

    scope_colors = {
        "default": "lightgrey",
        "user": "lightblue",
        "project": "lightgreen",
    }
    scoped = model.scoped_values()
    for scope in ("default", "user", "project"):
        prefs = scoped.get(scope, {})
        tab = tk.Frame(notebook, bg=scope_colors[scope])
        notebook.add(tab, text=scope.capitalize())
        for row, (key, value) in enumerate(sorted(prefs.items())):
            tk.Label(tab, text=key, bg=scope_colors[scope], anchor="w").grid(
                row=row, column=0, sticky="w", padx=5, pady=2
            )
            tk.Label(tab, text=value, bg=scope_colors[scope], anchor="w").grid(
                row=row, column=1, sticky="w", padx=5, pady=2
            )

    close_btn = ttk.Button(frame, text="Close", command=root.destroy)
    close_btn.pack(pady=10)
    root.mainloop()
