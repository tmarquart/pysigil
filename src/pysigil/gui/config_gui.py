from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from ..config import host_id, init_config, open_scope


def launch() -> None:  # pragma: no cover - GUI interactions
    root = tk.Tk()
    root.title("Sigil Config")
    ttk.Label(root, text=f"Host: {host_id()}").pack(padx=10, pady=10)

    def do_open() -> None:
        path = open_scope("user-custom", "user")
        try:
            import click

            click.launch(str(path))
        except Exception:
            try:
                messagebox.showerror("Sigil Config", f"Could not open {path}")
            except Exception:
                pass

    def do_init() -> None:
        path = init_config("user-custom", "user")
        try:
            messagebox.showinfo("Sigil Config", f"Initialized user-custom at {path}")
        except Exception:
            pass
        do_open()

    ttk.Button(root, text="Initialize User Custom", command=do_init).pack(pady=5)
    ttk.Button(root, text="Open user config folder", command=do_open).pack(pady=5)

    root.mainloop()
