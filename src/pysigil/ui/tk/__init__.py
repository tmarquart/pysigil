"""Tkinter based view layer for :mod:`pysigil.ui`.

The classes in this module provide a very small concrete implementation of
:class:`pysigil.ui.core.AppCore` using tkinter.  The goal of the module is
not to offer a feature complete GUI but rather to demonstrate how a view
layer can be wired to the framework agnostic core.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, Protocol

try:  # pragma: no cover - importing tkinter is environment dependent
    import tkinter as tk
    from tkinter import messagebox, ttk
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore
    messagebox = None  # type: ignore
    ttk = None  # type: ignore

from ..core import AppCore, AppState
from ..widgets import FIELD_WIDGETS


class ViewAdapter(Protocol):
    """Minimal protocol expected by :class:`AppCore` front-ends."""

    def bind_state(self, callback: Callable[[AppState], None]) -> None: ...
    def show_toast(self, msg: str, level: Literal["info", "warn", "error"]) -> None: ...
    def confirm(self, title: str, msg: str) -> bool: ...
    def prompt_new_field(self): ...


class TkApp:
    """Very small tkinter application shell.

    The application only exposes enough functionality for unit tests and
    for developers experimenting with the new architecture.  A more
    full-featured GUI can be built incrementally on top of this skeleton.
    """

    def __init__(self, core: AppCore | None = None) -> None:
        if tk is None:  # pragma: no cover - tkinter not available
            raise RuntimeError("tkinter is required for TkApp")
        self.core = core or AppCore()
        self.root = tk.Tk()
        self.root.title("pysigil")
        self._state_cb: Callable[[AppState], None] | None = None

        # provider selector -------------------------------------------------
        providers = self.core.service.list_providers()
        self._provider_var = tk.StringVar()
        self._provider_box = ttk.Combobox(
            self.root, textvariable=self._provider_var, state="readonly"
        )
        self._provider_box["values"] = providers
        self._provider_box.bind("<<ComboboxSelected>>", self._on_provider_selected)
        self._provider_box.pack(fill="x", padx=5, pady=5)

        # container for field editors --------------------------------------
        self._fields_frame = ttk.Frame(self.root)
        self._fields_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # forward state changes to bound callback and local UI
        self.core.events.on_state_changed.append(self._dispatch_state)
        self.core.events.on_state_changed.append(self._on_state)

    # -- view adapter protocol ---------------------------------------
    def bind_state(self, callback: Callable[[AppState], None]) -> None:
        self._state_cb = callback

    def show_toast(self, msg: str, level: Literal["info", "warn", "error"] = "info") -> None:
        if messagebox is None:  # pragma: no cover - tkinter missing
            return
        if level == "error":
            messagebox.showerror("pysigil", msg)
        elif level == "warn":
            messagebox.showwarning("pysigil", msg)
        else:
            messagebox.showinfo("pysigil", msg)

    def confirm(self, title: str, msg: str) -> bool:
        if messagebox is None:  # pragma: no cover
            return False
        return bool(messagebox.askyesno(title, msg))

    def prompt_new_field(self):  # pragma: no cover - placeholder dialog
        return None

    # -- internal helpers --------------------------------------------
    def _dispatch_state(self, state: AppState) -> None:
        if self._state_cb is not None:
            self._state_cb(state)

    # -- callbacks ---------------------------------------------------
    def _on_provider_selected(self, _event=None) -> None:
        pid = self._provider_var.get()
        if pid:
            self.core.select_provider(pid)

    def _on_state(self, state: AppState) -> None:
        if ttk is None:  # pragma: no cover - tkinter missing
            return
        for child in self._fields_frame.winfo_children():
            child.destroy()
        for field in state.fields:
            label = ttk.Label(
                self._fields_frame, text=field.label or field.key, anchor="w"
            )
            label.pack(fill="x", padx=5, pady=2)
            factory = FIELD_WIDGETS.get(field.type, FIELD_WIDGETS["string"])
            editor = factory(self._fields_frame)
            val = state.values.get(field.key)
            if val is not None:
                editor.set_value(val.value)
            editor.pack(fill="x", padx=5, pady=2)


__all__ = ["TkApp", "ViewAdapter"]
