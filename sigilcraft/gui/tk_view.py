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
    close_btn = ttk.Button(frame, text="Close", command=root.destroy)
    close_btn.pack(pady=10)
    root.mainloop()
