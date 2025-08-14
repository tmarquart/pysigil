from __future__ import annotations

import os
import sys
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..authoring import DevLinkError, _dev_dir, link, normalize_provider_id

APP_TITLE = "Sigil – Register Package Defaults"


class RegisterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("640x320")
        self.minsize(520, 280)

        self.defaults_path: tk.StringVar = tk.StringVar(value="")
        self.provider_id: tk.StringVar = tk.StringVar(value="")
        self.message_var: tk.StringVar = tk.StringVar(
            value="Pick your .sigil/settings.ini and confirm the provider id."
        )

        self._build()

    def _build(self) -> None:
        pad = {"padx": 12, "pady": 8}

        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True)

        row1 = ttk.Frame(frm)
        row1.pack(fill=tk.X, **pad)
        ttk.Label(row1, text="1) Defaults file (.sigil/settings.ini):").pack(anchor=tk.W)

        pick = ttk.Frame(row1)
        pick.pack(fill=tk.X)
        entry = ttk.Entry(pick, textvariable=self.defaults_path)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(pick, text="Browse…", command=self.on_browse).pack(side=tk.LEFT, padx=6)

        row2 = ttk.Frame(frm)
        row2.pack(fill=tk.X, **pad)
        ttk.Label(row2, text="2) Provider ID (PEP 503 normalized):").pack(anchor=tk.W)
        prov = ttk.Entry(row2, textvariable=self.provider_id)
        prov.pack(fill=tk.X)

        actions = ttk.Frame(frm)
        actions.pack(fill=tk.X, **pad)
        ttk.Button(actions, text="Register", command=self.on_register).pack(side=tk.LEFT)
        ttk.Button(actions, text="Open dev-links folder", command=self.on_open_folder).pack(
            side=tk.LEFT, padx=8
        )
        ttk.Button(actions, text="Quit", command=self.destroy).pack(side=tk.RIGHT)

        status = ttk.Frame(self)
        status.pack(fill=tk.X)
        ttk.Label(status, textvariable=self.message_var).pack(anchor=tk.W, padx=10, pady=6)

    def on_browse(self) -> None:
        fn = filedialog.askopenfilename(
            title="Select .sigil/settings.ini",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")],
        )
        if not fn:
            return
        p = Path(fn)
        self.defaults_path.set(str(p))
        try:
            pkg_dir = p.parent.parent.name
            self.provider_id.set(normalize_provider_id(pkg_dir))
        except Exception:
            self.provider_id.set(normalize_provider_id(p.stem))

    def on_register(self) -> None:
        defaults = Path(self.defaults_path.get().strip())
        provider = self.provider_id.get().strip()

        if not defaults:
            messagebox.showerror("Missing file", "Please choose your .sigil/settings.ini file.")
            return
        if not provider:
            messagebox.showerror("Missing provider id", "Please enter a provider id.")
            return

        try:
            dl = link(provider, defaults, validate=True)
            self.message_var.set(f"Linked {dl.provider_id} -> {dl.defaults_path}")
            messagebox.showinfo(
                "Success", f"Registered defaults for {dl.provider_id}.\n\n{dl.defaults_path}"
            )
        except DevLinkError as e:
            self.message_var.set(str(e))
            messagebox.showerror("Error", str(e))

    def on_open_folder(self) -> None:
        folder = _dev_dir()
        folder.mkdir(parents=True, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(folder)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f"open '{folder}'")
        else:
            try:
                os.system(f"xdg-open '{folder}'")
            except Exception:
                webbrowser.open(str(folder))


def main() -> None:
    app = RegisterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
