import pytest

try:
    import tkinter as tk
except Exception:  # pragma: no cover - tkinter missing
    tk = None  # type: ignore

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
        return scope_id not in {"env", "project"}

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
    states = {p.text: p.state for p in _collect_pills(row)}
    assert states == {
        "Env": "disabled",
        "User": "effective",
        "Machine": "empty",
        "Project": "disabled",
        "Project·Machine": "present",
        "Default": "present",
    }
    for p in _collect_pills(row):
        if p.text == "User":
            p.on_click()
            break
    assert clicks == [("alpha", "user")]
    lock_txt = row.var_eff.get()
    assert lock_txt.startswith("\U0001F512 u")
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
