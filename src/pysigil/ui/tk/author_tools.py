from __future__ import annotations

try:  # pragma: no cover - tkinter availability depends on environment
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore
    ttk = None  # type: ignore

from ..core import AppCore


class AuthorTools(tk.Toplevel):  # pragma: no cover - simple UI wrapper
    """Toplevel window exposing authoring tools.

    The implementation intentionally keeps the interface minimal.  It
    presents a tabbed notebook with three placeholder tabs: *Fields*,
    *Defaults* and *Untracked*.  Content is read-only for now and pulled
    from :class:`~pysigil.ui.core.AppCore`.
    """

    def __init__(self, master: tk.Misc, core: AppCore) -> None:
        super().__init__(master)
        self.title("Sigil – Author Tools")
        self.core = core
        self._build()
        self._populate_fields()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        self.geometry("640x480")
        nb = ttk.Notebook(self)
        self._tab_fields = ttk.Frame(nb)
        self._tab_defaults = ttk.Frame(nb)
        self._tab_untracked = ttk.Frame(nb)
        nb.add(self._tab_fields, text="Fields")
        nb.add(self._tab_defaults, text="Defaults")
        nb.add(self._tab_untracked, text="Untracked")
        nb.pack(fill="both", expand=True)

        self._fields_list = tk.Listbox(self._tab_fields)
        self._fields_list.pack(fill="both", expand=True, padx=6, pady=6)

    def _populate_fields(self) -> None:
        self._fields_list.delete(0, tk.END)
        for info in self.core.state.fields:
            self._fields_list.insert(tk.END, info.key)
