from dataclasses import dataclass

import pytest

from pysigil.settings_metadata import FieldType, TYPE_REGISTRY
from pysigil.ui.options_form import OptionsForm

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover - environment dependent
    tk = None  # type: ignore
    ttk = None  # type: ignore


@dataclass
class DemoOptions:
    text: str
    count: int
    ratio: float
    flag: bool
    tags: list[str]


@dataclass
class IntOptOptional:
    minimum: int | None = None


def _make_form(root):
    ft = FieldType(TYPE_REGISTRY["string"].adapter, option_model=DemoOptions)
    return OptionsForm(root, ft)


@pytest.mark.skipif(tk is None, reason="tkinter not available")
def test_basic_get_set_validate():
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("no display available")
    form = _make_form(root)
    form.set_values(DemoOptions("hello", 3, 0.5, True, ["a", "b"]))
    assert form.get_values() == {
        "text": "hello",
        "count": 3,
        "ratio": 0.5,
        "flag": True,
        "tags": ["a", "b"],
    }
    errs = form.validate()
    assert all(v is None for v in errs.values())
    root.destroy()


@pytest.mark.skipif(tk is None, reason="tkinter not available")
def test_validation_errors():
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("no display available")
    form = _make_form(root)
    form.set_values({"count": "bad"})
    errs = form.validate()
    assert errs["count"]
    root.destroy()


class DummyWidget(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.entry = ttk.Entry(self)
        self.entry.pack()

    def get_value(self):
        v = self.entry.get()
        return {"value": v} if v else {}

    def set_value(self, value):
        self.entry.delete(0, tk.END)
        if value and "value" in value:
            self.entry.insert(0, value["value"])

    def set_error(self, msg):  # pragma: no cover - placeholder
        pass


def _custom_widget(master):
    return DummyWidget(master)


@pytest.mark.skipif(tk is None, reason="tkinter not available")
def test_custom_option_widget():
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("no display available")
    ft = FieldType(TYPE_REGISTRY["string"].adapter, option_widget=_custom_widget)
    form = OptionsForm(root, ft)
    form.set_values({"value": "foo"})
    assert form.get_values()["value"] == "foo"
    root.destroy()


@pytest.mark.skipif(tk is None, reason="tkinter not available")
def test_optional_field_type():
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("no display available")
    ft = FieldType(TYPE_REGISTRY["integer"].adapter, option_model=IntOptOptional)
    form = OptionsForm(root, ft)
    form.set_values(IntOptOptional(7))
    assert form.get_values()["minimum"] == 7
    form.set_values(IntOptOptional())
    assert form.get_values()["minimum"] is None
    root.destroy()
