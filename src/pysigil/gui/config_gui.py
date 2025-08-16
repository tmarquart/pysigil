from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..config import host_id, init_config, open_scope


def launch() -> None:  # pragma: no cover - GUI interactions
    root = tk.Tk()
    root.title("Sigil Config")
    ttk.Label(root, text=f"Host: {host_id()}").pack(padx=10, pady=10)

    def do_init() -> None:
        init_config("user-custom", "user")

    ttk.Button(root, text="Initialize User Custom", command=do_init).pack(pady=5)

    def do_open() -> None:
        path = open_scope("user")
        try:
            import click

            click.launch(str(path))
        except Exception:
            pass

    ttk.Button(root, text="Open user config folder", command=do_open).pack(pady=5)

    root.mainloop()
