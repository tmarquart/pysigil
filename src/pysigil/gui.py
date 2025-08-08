from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Literal

try:
    import tkinter as tk
    from tkinter import simpledialog, ttk
except Exception:  # pragma: no cover - fallback for headless tests
    tk = None  # type: ignore
    simpledialog = None  # type: ignore
    ttk = None  # type: ignore

from . import gui_state
from .core import Sigil
from .keys import KeyPath
from .widgets import widget_for

# ---------------------------------------------------------------------------
# Public API helpers expected by GUI
# ---------------------------------------------------------------------------

_sigil_instance: Sigil | None = None
_current_package: str | None = None


def open_package(package: str, include_sigil: bool) -> None:
    """Instantiate a Sigil object for *package* and set globals."""
    global _sigil_instance, _current_package
    _sigil_instance = Sigil(package)
    _current_package = package
    # ``include_sigil`` is currently unused but kept for API compatibility.


def current_keys(scope: str) -> list[KeyPath]:
    if _sigil_instance is None:
        return []
    return _sigil_instance.list_keys(scope)


def effective_scope_for(key: KeyPath) -> str:
    if _sigil_instance is None:
        raise RuntimeError("No package opened")
    return _sigil_instance.effective_scope_for(key)


# ---------------------------------------------------------------------------
# Legacy preference editor helpers (kept for tests)
# ---------------------------------------------------------------------------


def _current_scope(widgets: dict) -> str:
    nb = widgets["notebook"]
    tab_id = nb.select()
    return nb.tab(tab_id, "text").lower()


def _populate_tree(tree, scope: str) -> None:
    if _sigil_instance is None:
        return
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
    if tk is None or simpledialog is None:
        return None
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
    if not res or _sigil_instance is None:
        return
    key, value = res
    _sigil_instance.set_pref(key, value, scope=scope)


def _on_edit(widgets: dict) -> None:
    scope = _current_scope(widgets)
    tree = widgets["trees"][scope]
    sel = tree.selection()
    if not sel:
        return
    key = sel[0]
    current = tree.item(key, "values")[1]
    res = _open_value_dialog("edit", scope, key=key, value=current)
    if not res or _sigil_instance is None:
        return
    new_key, new_val = res
    if new_key != key:
        _sigil_instance.set_pref(key, None, scope=scope)
        key = new_key
    _sigil_instance.set_pref(key, new_val, scope=scope)


def _on_delete(widgets: dict) -> None:
    scope = _current_scope(widgets)
    tree = widgets["trees"][scope]
    sel = tree.selection()
    if not sel or _sigil_instance is None:
        return
    key = sel[0]
    _sigil_instance.set_pref(key, None, scope=scope)


def _on_pref_changed(widgets: dict, key: str, new_val: str | None, scope: str) -> None:
    tree = widgets["trees"].get(scope)
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


# ---------------------------------------------------------------------------
# GUI launcher with package selection + state persistence
# ---------------------------------------------------------------------------

class _HeadlessGUI:
    """Simple stand-in object used for tests when no real Tk GUI is needed."""

    def __init__(self, state: dict, remember: bool, state_path: Path | None) -> None:
        self._state = state
        self._remember = remember
        self._state_path = state_path
        self.package = state["last_package"]
        self.tab = state["last_tab"]
        self.include_sigil = state["include_sigil"]
        self.empty = {
            scope: len(current_keys(scope.lower())) == 0
            for scope in ("Default", "User", "Project")
        }

    def select_package(self, package: str) -> None:
        self.package = package
        self._state["last_package"] = package
        open_package(package, self.include_sigil)
        self.empty = {
            scope: len(current_keys(scope.lower())) == 0
            for scope in ("Default", "User", "Project")
        }

    def select_tab(self, tab: str) -> None:
        self.tab = tab
        self._state["last_tab"] = tab

    def toggle_sigil(self, flag: bool) -> None:
        self.include_sigil = flag
        self._state["include_sigil"] = flag

    def close(self) -> None:
        if self._remember:
            gui_state.write_state(self._state, self._state_path)


def _detect_project_package() -> str | None:
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        return None
    try:
        import tomllib

        data = tomllib.loads(pyproject.read_text())
        name = data.get("project", {}).get("name")
        if isinstance(name, str) and name:
            return name
    except Exception:
        return None
    return None


def launch_gui(
    package: str | None = None,
    *,
    include_sigil: bool = False,
    remember_state: bool = True,
    packages: list[str] | None = None,
    run_mainloop: bool = True,
    refresh_callback: Callable[[], None] | None = None,
    state_path: Path | None = None,
    sigil: Sigil | None = None,
):
    """Launch the GUI.  When *run_mainloop* is False, return a headless helper."""
    packages = packages or ["pysigil"]
    state = gui_state.read_state(state_path)

    if sigil is not None:
        pkg = sigil.app_name
        # Ensure provided Sigil instance becomes the active one.
        global _sigil_instance, _current_package
        _sigil_instance = sigil
        _current_package = pkg
        if pkg not in packages:
            packages = [pkg, *packages]
    else:
        pkg = (
            package
            or _detect_project_package()
            or state.get("last_package")
            or "pysigil"
        )
        open_package(pkg, include_sigil)
        if pkg not in packages:
            packages = [pkg, *packages]

    tab = state.get("last_tab", "User")
    inc = include_sigil or state.get("include_sigil", False)
    state = {"last_package": pkg, "last_tab": tab, "include_sigil": inc}

    if not run_mainloop:
        return _HeadlessGUI(state, remember_state, state_path)

    if tk is None or ttk is None:  # pragma: no cover - no tkinter available
        raise RuntimeError("tkinter is required for GUI mode")

    root = tk.Tk()
    root.title(f"Sigil Preferences — {pkg}")

    header = ttk.Frame(root)
    header.pack(fill="x", padx=4, pady=4)
    pkg_var = tk.StringVar(value=pkg)
    combo = ttk.Combobox(header, textvariable=pkg_var, values=packages, state="readonly")
    combo.pack(side="left")
    refresh_cb = refresh_callback or (lambda: None)
    ttk.Button(header, text="Refresh", command=refresh_cb).pack(side="left", padx=4)
    sigil_var = tk.BooleanVar(value=inc)
    ttk.Checkbutton(
        header,
        text="Show Sigil settings",
        variable=sigil_var,
        command=lambda: None,
    ).pack(side="right")

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)
    trees: dict[str, ttk.Treeview] = {}
    empty_labels: dict[str, ttk.Label] = {}
    for scope in ("default", "user", "project"):
        frame = ttk.Frame(notebook)
        tree = ttk.Treeview(frame, columns=("key", "value"), show="headings")
        tree.heading("key", text="key")
        tree.heading("value", text="value")
        tree.pack(fill="both", expand=True)
        notebook.add(frame, text=scope.title())
        trees[scope] = tree
        empty_labels[scope] = ttk.Label(frame, text="No settings in this scope yet.")

    def _refresh() -> None:
        for scope, tree in trees.items():
            _populate_tree(tree, scope)
            if not tree.get_children():
                tree.pack_forget()
                empty_labels[scope].pack(fill="both", expand=True)
            else:
                empty_labels[scope].pack_forget()
                tree.pack(fill="both", expand=True)

    _refresh()

    def _on_pkg_change(event=None):
        new_pkg = pkg_var.get()
        state["last_package"] = new_pkg
        open_package(new_pkg, sigil_var.get())
        _refresh()

    combo.bind("<<ComboboxSelected>>", _on_pkg_change)

    def _on_tab_change(event=None):
        tab_name = notebook.tab(notebook.select(), "text")
        state["last_tab"] = tab_name

    notebook.bind("<<NotebookTabChanged>>", _on_tab_change)
    for i, scope in enumerate(["Default", "User", "Project"]):
        if scope == tab:
            notebook.select(i)
            break

    def _on_close() -> None:
        state["include_sigil"] = sigil_var.get()
        if remember_state:
            gui_state.write_state(state, state_path)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()


__all__ = [
    "open_package",
    "current_keys",
    "effective_scope_for",
    "launch_gui",
    "_open_value_dialog",
    "_populate_tree",
    "_on_add",
    "_on_edit",
    "_on_delete",
    "_on_pref_changed",
]
