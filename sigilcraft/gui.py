"""Tk GUI for editing Sigil preferences."""
from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog, ttk
from typing import Literal

from sigilcraft.core import Sigil

from . import events
from .widgets import widget_for

_sigil_instance: Sigil | None = None


def edit_preferences(package: str | None = None, *, allow_default_write: bool = True) -> None:
    """Launch the preference editor for *package*.

    This function blocks until the window is closed.
    """
    global _sigil_instance
    app = package or "app"
    _sigil_instance = Sigil(app)
    root = tk.Tk()
    root.title(f"Sigil Preferences — {_sigil_instance.app_name}")
    widgets = _build_main_window(root)
    for scope, tree in widgets["trees"].items():
        _populate_tree(tree, scope)
    events.on("pref_changed", lambda k, v, s: _on_pref_changed(widgets, k, v, s))
    root.mainloop()


def launch_gui() -> None:
    """Console entry point."""
    edit_preferences()


# ----- helpers -----

def _current_scope(widgets: dict) -> str:
    nb: ttk.Notebook = widgets["notebook"]
    tab_id = nb.select()
    return nb.tab(tab_id, "text").lower()


def _build_main_window(root: tk.Tk) -> dict:
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)
    trees: dict[str, ttk.Treeview] = {}
    for scope in ("default", "user", "project"):
        frame = ttk.Frame(notebook)
        tree = ttk.Treeview(frame, columns=("key", "value"), show="headings")
        tree.heading("key", text="key")
        tree.heading("value", text="value")
        tree.pack(fill="both", expand=True)
        notebook.add(frame, text=scope.title())
        trees[scope] = tree
    btn_frame = ttk.Frame(root)
    btn_frame.pack(fill="x", pady=4)
    add_btn = ttk.Button(btn_frame, text="Add")
    edit_btn = ttk.Button(btn_frame, text="Edit")
    del_btn = ttk.Button(btn_frame, text="Delete")
    close_btn = ttk.Button(btn_frame, text="Close", command=root.destroy)
    for btn in (add_btn, edit_btn, del_btn, close_btn):
        btn.pack(side="left", padx=2)
    widgets = {
        "root": root,
        "notebook": notebook,
        "trees": trees,
        "add": add_btn,
        "edit": edit_btn,
        "delete": del_btn,
    }
    add_btn.configure(command=lambda: _on_add(widgets))
    edit_btn.configure(command=lambda: _on_edit(widgets))
    del_btn.configure(command=lambda: _on_delete(widgets))
    return widgets


def _populate_tree(tree: ttk.Treeview, scope: str) -> None:
    assert _sigil_instance is not None
    tree.delete(*tree.get_children())
    values = _sigil_instance.scoped_values().get(scope, {})
    for key, value in sorted(values.items()):
        tree.insert("", "end", iid=key, values=(key, value))


def _open_value_dialog(
    mode: Literal["add", "edit"],
    scope: str,
    *,
    key: str = "",
    value: str = "",
):
    parent = tk._get_default_root()
    title = "Add preference" if mode == "add" else "Edit preference"

    class _Dialog(simpledialog.Dialog):
        def body(self, master):  # type: ignore[override]
            ttk.Label(master, text="Key:").grid(row=0, column=0, sticky="w")
            self.key_w = widget_for("key", None, master)
            self.key_w.grid(row=0, column=1, padx=5, pady=5)
            self.key_w.set(key)
            ttk.Label(master, text="Value:").grid(row=1, column=0, sticky="w")
            self.val_w = widget_for(key, None, master)
            self.val_w.grid(row=1, column=1, padx=5, pady=5)
            self.val_w.set(value)
            return self.key_w

        def apply(self):  # type: ignore[override]
            self.result = (self.key_w.get(), self.val_w.get())

    dlg = _Dialog(parent, title)
    return dlg.result


def _on_add(widgets: dict) -> None:
    scope = _current_scope(widgets)
    res = _open_value_dialog("add", scope)
    if not res:
        return
    key, value = res
    assert _sigil_instance is not None
    _sigil_instance.set_pref(key, value, scope=scope)


def _on_edit(widgets: dict) -> None:
    scope = _current_scope(widgets)
    tree: ttk.Treeview = widgets["trees"][scope]
    sel = tree.selection()
    if not sel:
        return
    key = sel[0]
    current = tree.item(key, "values")[1]
    res = _open_value_dialog("edit", scope, key=key, value=current)
    if not res:
        return
    new_key, new_val = res
    assert _sigil_instance is not None
    if new_key != key:
        _sigil_instance.set_pref(key, None, scope=scope)
        key = new_key
    _sigil_instance.set_pref(key, new_val, scope=scope)


def _on_delete(widgets: dict) -> None:
    scope = _current_scope(widgets)
    tree: ttk.Treeview = widgets["trees"][scope]
    sel = tree.selection()
    if not sel:
        return
    key = sel[0]
    assert _sigil_instance is not None
    _sigil_instance.set_pref(key, None, scope=scope)


def _on_pref_changed(widgets: dict, key: str, new_val: str | None, scope: str) -> None:
    tree: ttk.Treeview = widgets["trees"].get(scope)
    if tree is None:
        return
    if new_val is None:
        if tree.exists(key):
            tree.delete(key)
    else:
        if tree.exists(key):
            tree.item(key, values=(key, new_val))
        else:
            tree.insert("", "end", iid=key, values=(key, new_val))
