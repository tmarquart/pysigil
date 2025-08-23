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
    from tkinter import messagebox, simpledialog, ttk
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore
    messagebox = None  # type: ignore
    simpledialog = None  # type: ignore
    ttk = None  # type: ignore

from .. import api
from ..core import AppCore, AppState
from ..widgets import FIELD_WIDGETS


class ViewAdapter(Protocol):
    """Minimal protocol expected by :class:`AppCore` front-ends."""

    def bind_state(self, callback: Callable[[AppState], None]) -> None: ...
    def show_toast(self, msg: str, level: Literal["info", "warn", "error"]) -> None: ...
    def confirm(self, title: str, msg: str) -> bool: ...
    def prompt_new_field(self): ...


class FieldRow:
    """Representation of a single editable field row."""

    def __init__(
        self,
        master: tk.Widget,
        field: api.FieldInfo,
        core: AppCore,
        scope_var: tk.StringVar,
    ) -> None:
        self.key = field.key
        self.core = core
        self._scope_var = scope_var
        self.frame = ttk.Frame(master)
        self.frame.pack(fill="x", padx=5, pady=2)
        self._label = ttk.Label(self.frame, text=field.label or field.key, anchor="w", width=20)
        self._label.pack(side="left")
        factory = FIELD_WIDGETS.get(field.type, FIELD_WIDGETS["string"])
        self.editor = factory(self.frame)
        self.editor.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(
            self.frame,
            text="Save",
            command=self.on_save,
        ).pack(side="left", padx=2)
        ttk.Button(
            self.frame,
            text="Clear",
            command=self.on_clear,
        ).pack(side="left", padx=2)

    def update_label(self, text: str) -> None:
        self._label.configure(text=text)

    def set_from_valueinfo(self, v: api.ValueInfo | None) -> None:
        if v is None:
            self.editor.set_value(None)
            self.editor.set_source_badge(None)
        else:
            self.editor.set_value(v.value)
            self.editor.set_source_badge(v.source)

    def on_save(self) -> None:
        self.core.save_value(
            self.key, self.editor.get_value(), scope=self._scope_var.get()
        )

    def on_clear(self) -> None:
        self.core.clear_value(self.key, scope=self._scope_var.get())

    def focus(self) -> None:
        try:
            self.editor.focus_set()
        except Exception:
            children = getattr(self.editor, "winfo_children", lambda: [])()
            if children:
                try:
                    children[0].focus_set()
                except Exception:
                    pass


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

        # provider selector and context header ----------------------------
        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=5, pady=5)
        providers = self.core.service.list_providers()
        self._provider_var = tk.StringVar()
        self._provider_box = ttk.Combobox(
            header, textvariable=self._provider_var, state="readonly"
        )
        self._provider_box["values"] = providers
        self._provider_box.bind("<<ComboboxSelected>>", self._on_provider_selected)
        self._provider_box.pack(side="left")

        self._scope_var = tk.StringVar(value=self.core.state.active_scope)
        ttk.Radiobutton(
            header,
            text="User",
            variable=self._scope_var,
            value="user",
            command=self._on_scope_changed,
        ).pack(side="left", padx=4)
        ttk.Radiobutton(
            header,
            text="Project",
            variable=self._scope_var,
            value="project",
            command=self._on_scope_changed,
        ).pack(side="left", padx=4)

        self._host_label = ttk.Label(header, text=f"Host: {self.core.state.host_id}")
        self._host_label.pack(side="left", padx=4)
        self._proj_label = ttk.Label(header, text="No project detected")
        self._proj_label.pack(side="left", padx=4)

        btns = ttk.Frame(header)
        btns.pack(side="right")
        ttk.Button(
            btns,
            text="New setting",
            command=self.prompt_new_field,
        ).pack(side="left", padx=2)
        ttk.Button(
            btns,
            text="Init",
            command=lambda: self.core.init_scope(self._scope_var.get()),
        ).pack(side="left", padx=2)
        ttk.Button(
            btns,
            text="Open folder",
            command=lambda: self.core.open_folder(self._scope_var.get()),
        ).pack(side="left", padx=2)
        ttk.Button(
            btns,
            text="Open file",
            command=lambda: self.core.open_file(self._scope_var.get()),
        ).pack(side="left", padx=2)
        ttk.Button(
            btns,
            text="Add .gitignore",
            command=self.core.add_gitignore,
        ).pack(side="left", padx=2)

        # container for field editors and read-only view -------------------
        self._rows: dict[str, FieldRow] = {}
        self._focus_key: str | None = None
        self._notebook = ttk.Notebook(self.root)
        self._fields_frame = ttk.Frame(self._notebook)
        self._default_frame = ttk.Frame(self._notebook)
        self._notebook.add(self._fields_frame, text="Settings")
        self._notebook.add(self._default_frame, text="Default")
        self._notebook.pack(fill="both", expand=True, padx=5, pady=5)
        self._default_tree = ttk.Treeview(
            self._default_frame,
            columns=("key", "value", "source"),
            show="headings",
        )
        for col in ("key", "value", "source"):
            self._default_tree.heading(col, text=col.title())
        self._default_tree.pack(fill="both", expand=True)

        # forward state changes to bound callback and local UI
        self.core.events.on_state_changed.append(self._dispatch_state)
        self.core.events.on_state_changed.append(self._on_state)
        self.core.events.on_toast.append(self._on_toast)
        self.core.events.on_error.append(lambda msg: self._on_toast(msg, "error"))

        # keyboard shortcuts ----------------------------------------------
        self.root.bind("/", lambda e: self._provider_box.focus_set())
        self.root.bind("<F5>", lambda e: self.core.refresh())
        self.root.bind("<Control-n>", lambda e: self.prompt_new_field())
        self.root.bind("<Control-s>", lambda e: self.core.refresh())

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

    def prompt_new_field(self):  # pragma: no cover - interactive dialog
        if simpledialog is None or ttk is None:
            return None

        class _Dialog(simpledialog.Dialog):
            def body(self, master):  # type: ignore[override]
                ttk.Label(master, text="Key:").grid(row=0, column=0, sticky="w")
                self.key = ttk.Entry(master)
                self.key.grid(row=0, column=1, padx=4, pady=4)
                ttk.Label(master, text="Type:").grid(row=1, column=0, sticky="w")
                self.typ = ttk.Combobox(
                    master, state="readonly", values=list(FIELD_WIDGETS.keys())
                )
                self.typ.grid(row=1, column=1, padx=4, pady=4)
                ttk.Label(master, text="Label:").grid(row=2, column=0, sticky="w")
                self.lab = ttk.Entry(master)
                self.lab.grid(row=2, column=1, padx=4, pady=4)
                ttk.Label(master, text="Description:").grid(row=3, column=0, sticky="w")
                self.desc = ttk.Entry(master)
                self.desc.grid(row=3, column=1, padx=4, pady=4)
                return self.key

            def apply(self):  # type: ignore[override]
                self.result = {
                    "key": self.key.get().strip(),
                    "type": self.typ.get().strip() or "string",
                    "label": self.lab.get().strip() or None,
                    "description": self.desc.get().strip() or None,
                }

        dlg = _Dialog(self.root, "New setting")
        data = dlg.result
        if not data or not data.get("key"):
            return None
        self._focus_key = data["key"]
        self.core.add_field(
            data["key"],
            data["type"],
            label=data.get("label"),
            description=data.get("description"),
            init_scope=self._scope_var.get(),
        )
        return data

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
        self._scope_var.set(state.active_scope)
        if state.project_root is not None:
            self._proj_label.configure(text=str(state.project_root))
        else:
            self._proj_label.configure(text="No project detected")
        self._host_label.configure(text=f"Host: {state.host_id}")

        # --- sync rows -------------------------------------------------
        current = set(self._rows.keys())
        incoming = {f.key for f in state.fields}
        for key in current - incoming:
            self._rows[key].frame.destroy()
            del self._rows[key]
        for field in state.fields:
            row = self._rows.get(field.key)
            if row is None:
                row = FieldRow(self._fields_frame, field, self.core, self._scope_var)
                self._rows[field.key] = row
            else:
                row.update_label(field.label or field.key)
        for field in state.fields:
            val = state.values.get(field.key)
            self._rows[field.key].set_from_valueinfo(val)

        # --- refresh default view -------------------------------------
        tree = self._default_tree
        tree.delete(*tree.get_children())
        for field in state.fields:
            val = state.values.get(field.key)
            value = "" if val is None else str(val.value)
            src = "" if val is None else (val.source or "")
            tree.insert("", "end", iid=field.key, values=(field.key, value, src))

        if self._focus_key and self._focus_key in self._rows:
            self._rows[self._focus_key].focus()
            self._focus_key = None

    def _on_scope_changed(self) -> None:
        self.core.set_active_scope(self._scope_var.get())

    def _on_toast(self, msg: str, level: str) -> None:
        self.show_toast(msg, level)


__all__ = ["TkApp", "ViewAdapter"]
