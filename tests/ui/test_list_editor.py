import pytest

try:
    import tkinter as tk
except Exception:  # pragma: no cover - tkinter missing
    tk = None  # type: ignore

from pysigil.ui.tk.list_editor import ListEditor, ListEditDialog


def _make_root():
    root = tk.Tk()
    root.withdraw()
    return root


def test_list_editor_dedupe_sort():
    if tk is None:
        pytest.skip("tkinter not available")
    try:
        root = _make_root()
    except Exception:
        pytest.skip("no display available")
    editor = ListEditor(root, value=["b", "a", "b"], unique=False)
    assert editor.get_list() == ["b", "a", "b"]
    editor.dedupe()
    assert editor.get_list() == ["b", "a"]
    editor.sort_items()
    assert editor.get_list() == ["a", "b"]
    root.destroy()


def test_list_edit_dialog_result():
    if tk is None:
        pytest.skip("tkinter not available")
    try:
        root = _make_root()
    except Exception:
        pytest.skip("no display available")
    dlg = ListEditDialog(root, value=["x"])
    dlg._on_ok()
    assert dlg.result == ["x"]
    root.destroy()
