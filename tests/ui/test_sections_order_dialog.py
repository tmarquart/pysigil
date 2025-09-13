try:  # pragma: no cover - tkinter availability depends on the env
    import tkinter as tk
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore

import pytest

from pysigil.ui.author_adapter import FieldInfo
from pysigil.ui.tk.dialogs import SectionOrderDialog


class DummyAdapter:
    def __init__(self) -> None:
        self.saved: list[str] | None = None

    def list_defined(self):
        return [
            FieldInfo(key="a", type="string", section="One"),
            FieldInfo(key="b", type="string", section="Two"),
        ]

    def get_sections_order(self):
        return ["One", "Two"]

    def set_sections_order(self, seq):
        self.saved = list(seq)


def test_section_order_dialog_moves_and_saves():
    if tk is None:
        pytest.skip("tkinter not available")
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("no display available")

    adapter = DummyAdapter()
    dlg = SectionOrderDialog(root, adapter)
    dlg._list.selection_set(1)
    dlg._move_up()
    dlg._save()
    assert adapter.saved == ["Two", "One"]
    root.destroy()
