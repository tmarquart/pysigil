from __future__ import annotations

import os
import sys
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ...authoring import DevLinkError, _dev_dir, link, normalize_provider_id
from ...resolver import (
    default_provider_id,
    ensure_defaults_file,
    find_package_dir,
    read_dist_name_from_pyproject,
)
from ...root import ProjectRootNotFoundError, find_project_root
from ..aurelia_theme import get_palette, use

APP_TITLE = "Sigil – Register Package Defaults"




class RegisterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        use(self)
        palette = get_palette()

        style = ttk.Style(self)
        style.configure("TLabel",font=(None, 10, "bold"))

        self.configure(bg=palette["bg"])  # type: ignore[call-arg]
        self.title(APP_TITLE)
        self.geometry("640x320")
        self.minsize(520, 280)
        self.option_add("*highlightcolor", palette["gold"])
        self.option_add("*highlightbackground", palette["bg"])
        self.option_add("*highlightthickness", 1)

        self.defaults_path: tk.StringVar = tk.StringVar(value="")
        self.provider_id: tk.StringVar = tk.StringVar(value="")
        self.message_var: tk.StringVar = tk.StringVar(
            value="Pick your package folder (contains __init__.py). Provider ID is pre-filled; edit if needed."
        )

        self._build()
        self._try_autodetect()

    def _build(self) -> None:
        pad = {"padx": 12, "pady": 8}

        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True)

        row1 = ttk.Frame(frm)
        row1.pack(fill=tk.X, **pad)
        ttk.Label(row1, text="1) Package folder (contains __init__.py):").pack(anchor=tk.W)

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
        folder = filedialog.askdirectory(
            title="Select your package folder (e.g., mypkg/ or src/mypkg/)",
            mustexist=True,
            initialdir=os.getcwd(),
        )
        if not folder:
            return

        chosen = Path(folder)
        if (chosen / "__init__.py").exists():
            pkg = chosen
        else:
            pkg = find_package_dir(chosen, None)
        if not pkg:
            messagebox.showerror(
                "Pick your package folder",
                "Please choose the **package folder** that contains __init__.py\n"
                "Examples:\n"
                "- mypkg/\n"
                "- src/mypkg/\n\n"
                "Tip: If you picked the repo root, I can auto-detect only when there is exactly one package under src/.",
            )
            return

        self.defaults_path.set(str(pkg))
        try:
            root = find_project_root(pkg)
        except ProjectRootNotFoundError:
            root = pkg
        dist_name = read_dist_name_from_pyproject(root)
        self.provider_id.set(default_provider_id(pkg, dist_name))
        self.message_var.set(f"Package folder: {pkg}")

    def _try_autodetect(self) -> None:
        cwd = Path(os.getcwd())
        try:
            root = find_project_root(cwd)
        except ProjectRootNotFoundError:
            root = cwd
        dist_name = read_dist_name_from_pyproject(root)
        pkg = find_package_dir(root, dist_name)
        if pkg:
            self.defaults_path.set(str(pkg))
            self.provider_id.set(default_provider_id(pkg, dist_name))
            self.message_var.set(f"Detected package folder: {pkg}")

    def on_register(self) -> None:
        pkg_dir_raw = self.defaults_path.get().strip()
        provider = self.provider_id.get().strip()

        if not pkg_dir_raw:
            messagebox.showerror("Missing folder", "Please choose your **package folder**.")
            return
        if not provider:
            messagebox.showerror("Missing provider id", "Please confirm or edit the provider id.")
            return

        pkg_dir = Path(pkg_dir_raw)
        if (pkg_dir / "__init__.py").exists():
            pkg = pkg_dir
        else:
            pkg = find_package_dir(pkg_dir, None)
        if not pkg or not (pkg / "__init__.py").exists():
            messagebox.showerror(
                "Invalid folder",
                "That folder doesn’t look like a package. Pick the folder that contains __init__.py.",
            )
            return

        provider_norm = normalize_provider_id(provider)
        try:
            settings_path = ensure_defaults_file(pkg, provider_norm)
            dl = link(provider_norm, settings_path, validate=True)
            self.message_var.set(f"Linked {dl.provider_id} -> {dl.defaults_path}")
            messagebox.showinfo(
                "Success",
                f"Created/verified {settings_path}\n\nRegistered dev link for {dl.provider_id}.",
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
