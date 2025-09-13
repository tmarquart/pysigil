import pytest

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover - tkinter missing
    tk = None  # type: ignore
    ttk = None  # type: ignore

from pysigil.api import FieldInfo
from pysigil.ui.tk.dialogs import EditDialog
from pysigil.ui.provider_adapter import ValueInfo


class DummyAdapter:
    def scopes(self):
        return ["user", "default"]

    def scope_label(self, scope, short=False):
        return scope.title() if short else scope.title()

    def values_for_key(self, key):
        return {"default": ValueInfo("d")}

    def can_write(self, scope):
        return scope != "default"

    def is_overlay(self, scope):
        return False

    def field_info(self, key):
        return FieldInfo(
            key=key,
            type="string",
            label="Alpha Label",
            description_short="Short description",
            description="Long description",
        )


def test_edit_dialog_default_readonly():
    if tk is None:
        pytest.skip("tkinter not available")
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("no display available")
    dlg = EditDialog(root, DummyAdapter(), "alpha")
    entry = dlg.entries["default"]
    assert entry.instate(["readonly"])  # default is read-only
    row = entry.grid_info()["row"]
    body = entry.master
    btn_save = body.grid_slaves(row=row, column=2)[0]
    btn_remove = body.grid_slaves(row=row, column=3)[0]
    assert btn_save.instate(["disabled"])
    assert btn_remove.instate(["disabled"])
    dlg.destroy()
    root.destroy()


def test_edit_dialog_shows_metadata():
    if tk is None:
        pytest.skip("tkinter not available")
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("no display available")
    dlg = EditDialog(root, DummyAdapter(), "alpha")
    assert dlg.title() == "Edit — Alpha Label"
    children = dlg.winfo_children()
    texts = [w.cget("text") for w in children if isinstance(w, ttk.Label)]
    assert "Alpha Label" in texts
    assert "alpha" in texts
    body = next(w for w in children if isinstance(w, ttk.Frame))
    body_texts = [w.cget("text") for w in body.winfo_children() if isinstance(w, ttk.Label)]
    assert "Short description" in body_texts
    assert "Long description" in body_texts
    dlg.destroy()
    root.destroy()
