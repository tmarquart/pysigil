from __future__ import annotations

import os
import sys
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..authoring import DevLinkError, _dev_dir, link, normalize_provider_id

APP_TITLE = "Sigil – Register Package Defaults"


def _find_package_dir(chosen: Path) -> Path | None:
    """Locate the package directory from ``chosen``.

    Accepts either a directory that directly contains ``__init__.py`` or a
    repository root with a ``src`` layout containing exactly one package.
    Returns the resolved package directory or ``None`` if ambiguous.
    """

    chosen = chosen.resolve()

    if (chosen / "__init__.py").exists():
        return chosen

    src = chosen / "src"
    if src.is_dir():
        candidates = [p for p in src.iterdir() if p.is_dir() and (p / "__init__.py").exists()]
        if len(candidates) == 1:
            return candidates[0]

    return None


def _pep503_default_provider(package_dir: Path) -> str:
    """Best-effort provider id using pyproject ``project.name`` or dir name."""

    cur = package_dir
    while cur and cur != cur.parent:
        ppt = cur / "pyproject.toml"
        if ppt.exists():
            try:  # pragma: no cover - best effort
                import tomllib

                data = tomllib.loads(ppt.read_text(encoding="utf-8"))
                name = data.get("project", {}).get("name")
                if name:
                    return normalize_provider_id(name)
            except Exception:  # pragma: no cover - defensive
                pass
        cur = cur.parent

    return normalize_provider_id(package_dir.name)


def _ensure_defaults_file(package_dir: Path, provider_id: str) -> Path:
    """Ensure ``.sigil/settings.ini`` exists in ``package_dir``.

    If missing, create a minimal template. Returns the path to ``settings.ini``.
    """

    sigil_dir = package_dir / ".sigil"
    sigil_dir.mkdir(exist_ok=True)
    ini = sigil_dir / "settings.ini"
    if not ini.exists():
        template = (
            f"[provider:{provider_id}]\n"
            "# Add your package defaults here.\n"
            "# key = value\n"
        )
        ini.write_text(template, encoding="utf-8")
    return ini


class RegisterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("640x320")
        self.minsize(520, 280)

        self.defaults_path: tk.StringVar = tk.StringVar(value="")
        self.provider_id: tk.StringVar = tk.StringVar(value="")
        self.message_var: tk.StringVar = tk.StringVar(
            value="Pick your package folder (contains __init__.py). Provider ID is pre-filled; edit if needed."
        )

        self._build()

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
        )
        if not folder:
            return

        chosen = Path(folder)
        pkg = _find_package_dir(chosen)
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
        self.provider_id.set(_pep503_default_provider(pkg))
        self.message_var.set(f"Package folder: {pkg}")

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
        pkg = _find_package_dir(pkg_dir)
        if not pkg:
            messagebox.showerror(
                "Invalid folder",
                "That folder doesn’t look like a package. Pick the folder that contains __init__.py.",
            )
            return

        provider_norm = normalize_provider_id(provider)
        try:
            settings_path = _ensure_defaults_file(pkg, provider_norm)
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
