from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Literal

try:
    import tkinter as tk
    from tkinter import messagebox, simpledialog, ttk
except Exception:  # pragma: no cover - fallback for headless tests
    tk = None  # type: ignore
    simpledialog = None  # type: ignore
    ttk = None  # type: ignore
    messagebox = None  # type: ignore

from ..config import available_providers, init_config
from ..merge_policy import KeyPath
from . import events, gui_state
from ..ui.tk.config_gui import launch as launch_config_gui
from .widgets import widget_for

if TYPE_CHECKING:
    from ..core import Sigil

logger = logging.getLogger("pysigil.gui")
if os.environ.get("SIGIL_GUI_DEBUG") and not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# Public API helpers expected by GUI
# ---------------------------------------------------------------------------

_sigil_instance: Sigil | None = None
_current_package: str | None = None


class SigilGUI:
    """Legacy wrapper used in tests to ensure GUI can be instantiated."""

    def __init__(self, sigil: Sigil) -> None:
        if tk is None or ttk is None:  # pragma: no cover - tkinter missing
            raise RuntimeError("tkinter is required for GUI mode")
        self.sigil = sigil
        try:
            self.root = tk.Tk()
        except Exception as exc:  # pragma: no cover - no display
            raise RuntimeError(str(exc)) from exc


def open_package(package: str, include_sigil: bool) -> None:
    """Instantiate a Sigil object for *package* and set globals.

    The GUI allows switching between packages at runtime.  Previously this
    created a bare :class:`Sigil` instance which omitted any package-specific
    default or metadata paths.  Instead, resolve the package through the hub so
    that the same configuration used by ``get_preferences`` is honoured.  If
    resolution fails we fall back to a plain ``Sigil`` instance.
    """

    global _sigil_instance, _current_package
    logger.debug("opening package %s include_sigil=%s", package, include_sigil)
    try:
        from . import hub

        get_pref, _, sig = hub.get_preferences(package)
        # Force instantiation of the package-specific Sigil by performing a
        # harmless lookup.  ``get_preferences`` creates the instance lazily, so
        # without this call ``hub._instances`` would remain empty and the GUI
        # would show no values for newly selected packages.
        get_pref("__sigil_gui_init__", default=None)
        _sigil_instance = sig
        logger.debug("loaded instance for %s via hub", sig.app_name)
    except Exception as exc:
        logger.debug("hub resolution failed for %s: %s", package, exc)
        from ..core import Sigil

        _sigil_instance = Sigil(package)
    _current_package = _sigil_instance.app_name
    # ``include_sigil`` is currently unused but kept for API compatibility.


def current_keys(scope: str) -> list[KeyPath]:
    if _sigil_instance is None:
        return []
    return _sigil_instance.list_keys(scope)


def effective_scope_for(key: KeyPath) -> str:
    if _sigil_instance is None:
        raise RuntimeError("No package opened")
    return _sigil_instance.effective_scope_for(key)


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


def _on_pref_changed(widgets: dict, key: str, new_val: str | None, scope: str) -> None:
    """Update simple tree/label structures when a preference changes."""
    logger.debug("pref_changed %s=%s scope=%s", key, new_val, scope)
    tree = widgets.get("trees", {}).get(scope)
    empty = widgets.get("empty_labels", {}).get(scope)
    if tree is None or empty is None:
        return
    if new_val is None:
        if tree.exists(key):
            tree.delete(key)
    else:
        if tree.exists(key):
            tree.item(key, values=(key, new_val))
        else:
            tree.insert("", "end", iid=key, values=(key, new_val))
    if tree.get_children():
        empty.pack_forget()
        tree.pack(fill="both", expand=True)
    else:
        tree.pack_forget()
        empty.pack(fill="both", expand=True)


# ---------------------------------------------------------------------------
# GUI launcher with package selection + state persistence
# ---------------------------------------------------------------------------


class _HeadlessGUI:
    """Simple stand-in object used for tests when no real Tk GUI is needed."""

    def __init__(
        self, state: dict, remember: bool, state_path: Path | None, packages: list[str]
    ) -> None:
        self._state = state
        self._remember = remember
        self._state_path = state_path
        self.packages = packages
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
    packages = packages or []
    packages = list(dict.fromkeys([*packages, *available_providers()]))
    if "pysigil" not in packages:
        packages.append("pysigil")
    state = gui_state.read_state(state_path)

    if sigil is not None:
        pkg = sigil.app_name
        global _sigil_instance, _current_package
        _sigil_instance = sigil
        _current_package = pkg
    else:
        pkg = package or state.get("last_package") or "pysigil"
        open_package(pkg, include_sigil)
        pkg = _current_package or pkg
    packages = [pkg, *[p for p in packages if p != pkg]]
    state = {"last_package": pkg, "last_tab": "User", "include_sigil": include_sigil}

    if not run_mainloop:
        return _HeadlessGUI(state, remember_state, state_path, packages)

    if tk is None or ttk is None:  # pragma: no cover - no tkinter available
        raise RuntimeError("tkinter is required for GUI mode")

    root = tk.Tk()
    root.title(f"Sigil Preferences — {pkg}")

    header = ttk.Frame(root)
    header.pack(fill="x", padx=4, pady=4)
    pkg_var = tk.StringVar(value=pkg)
    combo = ttk.Combobox(header, textvariable=pkg_var, values=packages, state="readonly")
    combo.pack(side="left")


    search_var = tk.StringVar()
    ttk.Entry(header, textvariable=search_var, width=20).pack(side="left", padx=6)

    scope_var = tk.StringVar(value=_sigil_instance.default_scope if _sigil_instance else "user")
    scope_frame = ttk.Frame(header)
    scope_frame.pack(side="left", padx=6)

    scope_labels = [
        ("User", "user"),
        ("Machine", "user-local"),
        ("Project", "project"),
        ("Project·Machine", "project-local"),
    ]

    def _on_scope_change() -> None:
        if _sigil_instance is None:
            return
        _sigil_instance.set_default_scope(scope_var.get())
        _update_path()

    for text, val in scope_labels:
        ttk.Radiobutton(scope_frame, text=text, variable=scope_var, value=val, command=_on_scope_change).pack(side="left")


    path_label = ttk.Label(header, text="")
    path_label.pack(side="left", padx=6)

    def _update_path() -> None:
        if _sigil_instance is None:
            path_label.config(text="")
            return
        path_label.config(text=f"Will write to: {_sigil_instance.path_for_scope(scope_var.get())}")

    _update_path()

    ttk.Button(header, text="New setting", command=lambda: _on_add()).pack(side="right")
    ttk.Button(header, text="Init", command=lambda: _on_init()).pack(side="right", padx=2)

    tree = ttk.Treeview(root, columns=("key", "value", "source", "actions"), show="headings")
    tree.heading("key", text="Key")
    tree.heading("value", text="Value")
    tree.heading("source", text="Source")
    tree.heading("actions", text="Actions")
    tree.column("actions", width=200, anchor="w")
    tree.pack(fill="both", expand=True)

    source_map: dict[str, str] = {}
    key_scopes: dict[str, set[str]] = {}


    def _refresh() -> None:
        if _sigil_instance is None:
            return
        tree.delete(*tree.get_children())
        search = search_var.get().lower()
        scoped = _sigil_instance.scoped_values()
        all_keys = set().union(*(d.keys() for d in scoped.values()))
        label_map = {val: text for text, val in scope_labels}
        key_scopes.clear()
        editable = {val for _, val in scope_labels}
        for sc, mapping in scoped.items():
            if sc in editable:
                for k in mapping:
                    key_scopes.setdefault(k, set()).add(sc)
        for key in sorted(all_keys):
            if search and search not in key.lower():
                continue
            val = _sigil_instance.get_pref(key)
            src = _sigil_instance.effective_scope_for(key)
            source_map[key] = src
            tree.insert(
                "",
                "end",
                iid=key,
                values=(
                    key,
                    "" if val is None else str(val),
                    label_map.get(src, src),
                    "Override \u25BE   Reset \u25BE",
                ),
            )


    def _validate(key: str, val: str) -> bool:
        if _sigil_instance is None:
            return False
        current = _sigil_instance.get_pref(key)
        try:
            if isinstance(current, bool):
                if val.lower() not in {"true", "false", "1", "0"}:
                    raise ValueError(f"Expected true/false or 1/0 for {key}")
            elif isinstance(current, int) and not isinstance(current, bool):
                int(val)
            elif isinstance(current, float):
                float(val)
            elif isinstance(current, list | dict):
                data = json.loads(val)
                if not isinstance(data, type(current)):
                    raise ValueError(f"Expected {type(current).__name__} for {key}")
        except Exception as exc:
            logger.error("invalid value %r for %s: %s", val, key, exc)
            if messagebox is not None:
                messagebox.showerror("Invalid value", str(exc), parent=root)
            return False
        return True


    def _on_add() -> None:
        res = _open_value_dialog("add", scope_var.get())
        if res is None or _sigil_instance is None:
            return
        key, value = res
        if _validate(key, value):
            _sigil_instance.set_pref(key, value, scope=scope_var.get())
            _refresh()


    def _on_init() -> None:
        init_config(pkg_var.get(), scope_var.get())
        _refresh()

    def _on_override(key: str, scope: str) -> None:
        if _sigil_instance is None:
            return
        current = _sigil_instance.get_pref(key)
        res = _open_value_dialog(
            "edit", scope, key=key, value="" if current is None else str(current)
        )

        if res is None:
            return
        new_key, new_val = res
        if not _validate(new_key, new_val):
            return
        if new_key != key:
            _sigil_instance.set_pref(key, None, scope=scope)
            key = new_key
        _sigil_instance.set_pref(key, new_val, scope=scope)
        _refresh()

    def _on_reset(key: str, scope: str) -> None:
        if _sigil_instance is None:
            return
        _sigil_instance.set_pref(key, None, scope=scope)
        _refresh()

    def _show_override_menu(event, key: str) -> None:
        menu = tk.Menu(tree, tearoff=0)
        for text, val in scope_labels:
            menu.add_command(label=text, command=lambda sc=val: _on_override(key, sc))
        menu.post(event.x_root, event.y_root)

    def _show_reset_menu(event, key: str) -> None:
        menu = tk.Menu(tree, tearoff=0)
        scopes = key_scopes.get(key, set())
        for text, val in scope_labels:
            state = "normal" if val in scopes else "disabled"
            menu.add_command(
                label=text, command=lambda sc=val: _on_reset(key, sc), state=state
            )
        menu.post(event.x_root, event.y_root)

    def _on_tree_click(event) -> None:
        item = tree.identify_row(event.y)
        if not item:
            return
        column = tree.identify_column(event.x)
        if column != "#4":
            return
        bbox = tree.bbox(item, "actions")
        if not bbox:
            return
        rel_x = event.x - bbox[0]
        if rel_x < bbox[2] * 0.5:
            _show_override_menu(event, item)
        else:
            _show_reset_menu(event, item)

    tree.bind("<Button-1>", _on_tree_click)

    search_var.trace_add("write", lambda *args: _refresh())


    def _on_pkg_change(event=None):
        new_pkg = pkg_var.get()
        open_package(new_pkg, False)
        _update_path()
        _refresh()

    combo.bind("<<ComboboxSelected>>", _on_pkg_change)

    events.on("pref_changed", lambda *args: _refresh())

    _refresh()

    def _on_close() -> None:
        if remember_state:
            state["last_package"] = pkg_var.get()
            gui_state.write_state(state, state_path)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()


__all__ = [
    "SigilGUI",
    "open_package",
    "current_keys",
    "effective_scope_for",
    "launch_gui",
    "launch_config_gui",
    "_open_value_dialog",
    "_on_pref_changed",
]
