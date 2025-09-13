import importlib
import pytest
import types

try:
    import tkinter as tk
except Exception:  # pragma: no cover - tkinter missing
    tk = None  # type: ignore

import pysigil.ui.tk.rows as tk_rows
from pysigil.ui.tk.rows import FieldRow
from pysigil.ui.tk.widgets import PillButton
from pysigil.ui.provider_adapter import ValueInfo


class DummyAdapter:
    def scopes(self):
        return ["env", "user", "user-local", "project", "project-local", "default"]

    def scope_label(self, scope_id, short=False):
        short_labels = {
            "env": "Env",
            "user": "User",
            "user-local": "Machine",
            "project": "Project",
            "project-local": "Project·Machine",
            "default": "Default",
        }
        long_labels = {
            "env": "Environment",
            "user": "User",
            "user-local": "Machine",
            "project": "Project",
            "project-local": "Project on this Machine",
            "default": "Default",
        }
        return (short_labels if short else long_labels)[scope_id]

    def can_write(self, scope_id):
        return scope_id not in {"env", "project", "default"}

    def is_overlay(self, scope_id):
        return scope_id == "env"

    def values_for_key(self, key):
        return {
            "env": ValueInfo("e"),
            "user": ValueInfo("u"),
            "project-local": ValueInfo("pl"),
            "default": ValueInfo("d"),
        }

    def effective_for_key(self, key):
        return "u", "user"

    def default_for_key(self, key):
        return "d"


def _collect_pills(row):
    return [w for w in row.pills.winfo_children() if isinstance(w, PillButton)]


def test_field_row_full_mode(monkeypatch):
    if tk is None:
        pytest.skip("tkinter not available")
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("no display available")
    clicks = []
    row = FieldRow(root, DummyAdapter(), "alpha", lambda k, s: clicks.append((k, s)), compact=False)
    pills = _collect_pills(row)
    states = {p.text: p.state for p in pills}
    assert states == {
        "Env": "present",
        "User": "effective",
        "Machine": "empty",
        "Project": "disabled",
        "Project·Machine": "present",
        "Default": "present",
    }
    default_pill = next(p for p in pills if p.text == "Default")
    assert default_pill.locked
    env_pill = next(p for p in pills if p.text == "Env")
    assert env_pill.locked
    for p in _collect_pills(row):
        if p.text == "User":
            p.on_click()
            break
    assert clicks == [("alpha", "user")]
    lock_txt = row.var_eff.get()
    assert lock_txt.startswith("u")
    assert "(User)" in lock_txt
    root.destroy()


def test_field_row_compact_mode():
    if tk is None:
        pytest.skip("tkinter not available")
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("no display available")
    row = FieldRow(root, DummyAdapter(), "alpha", lambda k, s: None, compact=True)
    pills = _collect_pills(row)
    assert [p.text for p in pills] == ["Env", "User", "Project·Machine", "Default"]
    root.destroy()


def test_locked_pill_shows_hint(monkeypatch):
    if tk is None:
        pytest.skip("tkinter not available")
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("no display available")
    calls = []
    dummy_box = types.SimpleNamespace(showinfo=lambda *a, **k: calls.append(a))
    monkeypatch.setattr(tk_rows, "messagebox", dummy_box)
    row = FieldRow(root, DummyAdapter(), "alpha", lambda k, s: None, compact=False)
    env_pill = next(p for p in _collect_pills(row) if p.text == "Env")
    env_pill.on_click()
    assert calls and "Author" in calls[0][1]
    root.destroy()


class NoDefaultAdapter(DummyAdapter):
    def values_for_key(self, key):
        return {"env": ValueInfo("e")}

    def effective_for_key(self, key):
        return "e", "env"

    def default_for_key(self, key):
        return None


def test_field_row_hides_default_when_missing():
    if tk is None:
        pytest.skip("tkinter not available")
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("no display available")
    row = FieldRow(root, NoDefaultAdapter(), "alpha", lambda k, s: None, compact=True)
    pills = [p.text for p in _collect_pills(row)]
    assert "Default" not in pills
    root.destroy()


def test_field_row_shows_default_when_missing_in_full_mode():
    if tk is None:
        pytest.skip("tkinter not available")
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("no display available")
    row = FieldRow(root, NoDefaultAdapter(), "alpha", lambda k, s: None, compact=False)
    pills = {p.text: p.state for p in _collect_pills(row)}
    assert pills["Default"] == "empty"
    root.destroy()



class DefaultOnlyAdapter(DummyAdapter):
    def scopes(self):
        return ["default"]

    def values_for_key(self, key):
        return {"default": ValueInfo("d")}

    def effective_for_key(self, key):
        return "d", "default"


def test_field_row_default_effective():
    if tk is None:
        pytest.skip("tkinter not available")
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("no display available")
    row = FieldRow(root, DefaultOnlyAdapter(), "alpha", lambda k, s: None, compact=True)
    pills = _collect_pills(row)
    assert len(pills) == 1
    pill = pills[0]
    assert pill.text == "Default"
    assert pill.state == "effective"
    assert pill.color == "#000000"
    assert pill.locked
    root.destroy()


def test_debug_columns_env_var_after_import(monkeypatch):
    if tk is None:
        pytest.skip("tkinter not available")
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("no display available")

    monkeypatch.delenv("PYSGIL_DEBUG_COLUMNS", raising=False)
    importlib.reload(tk_rows)

    monkeypatch.setenv("PYSGIL_DEBUG_COLUMNS", "1")
    row = tk_rows.FieldRow(root, DummyAdapter(), "alpha", lambda k, s: None, compact=False)
    assert hasattr(row, "_debug_canvas")
    root.destroy()

