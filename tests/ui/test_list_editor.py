import pytest

try:
    import tkinter as tk
except Exception:  # pragma: no cover - tkinter missing
    tk = None  # type: ignore

import pysigil.ui.tk.list_editor as le
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


def test_list_editor_import_bom(tmp_path, monkeypatch):
    if tk is None:
        pytest.skip("tkinter not available")
    try:
        root = _make_root()
    except Exception:
        pytest.skip("no display available")
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("\ufeffitem1\nitem2\n", encoding="utf-8")
    monkeypatch.setattr(le.filedialog, "askopenfilename", lambda **kwargs: str(csv_path))
    editor = ListEditor(root, value=[])
    editor._on_import()
    assert editor.get_list() == ["item1", "item2"]
    root.destroy()


def test_list_editor_move_preserves_selection():
    if tk is None:
        pytest.skip("tkinter not available")
    try:
        root = _make_root()
    except Exception:
        pytest.skip("no display available")
    editor = ListEditor(root, value=["a", "b", "c"])
    editor._tree.selection_set("1")
    editor._move(-1)
    assert editor.get_list() == ["b", "a", "c"]
    assert editor._tree.selection() == ("0",)
    root.destroy()
