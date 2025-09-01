import pytest

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover - tkinter missing
    tk = None  # type: ignore
    ttk = None  # type: ignore

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
