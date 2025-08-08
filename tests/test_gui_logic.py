from __future__ import annotations

from pathlib import Path

from sigilcraft import events, gui
from sigilcraft.core import Sigil


class DummyTree:
    def __init__(self) -> None:
        self.rows: dict[str, tuple[str, str]] = {}
        self._selection: list[str] = []

    def insert(self, parent, index, iid, values):
        self.rows[iid] = values

    def item(self, iid, option=None, **kwargs):
        if kwargs:
            self.rows[iid] = kwargs.get("values", self.rows[iid])
            return
        if option == "values":
            return self.rows[iid]
        return {"values": self.rows[iid]}

    def delete(self, *iids):
        for iid in iids:
            self.rows.pop(iid, None)

    def exists(self, iid):
        return iid in self.rows

    def selection(self):
        return tuple(self._selection)

    def selection_set(self, iid):
        self._selection = [iid]

    def get_children(self):
        return list(self.rows)


class DummyNotebook:
    def __init__(self, current: str) -> None:
        self._current = current

    def select(self, tab=None):
        if tab is None:
            return self._current
        self._current = tab

    def tab(self, tab_id, option=None):
        if option == "text":
            return tab_id.capitalize()
        return ""


def make_widgets(current_scope: str):
    nb = DummyNotebook(current_scope)
    trees = {scope: DummyTree() for scope in ("default", "user", "project")}
    return {"notebook": nb, "trees": trees}


def setup_func(tmp_path: Path) -> tuple[Sigil, dict]:
    events._callbacks.clear()  # type: ignore[attr-defined]
    sig = Sigil(
        "app",
        user_scope=tmp_path / "u.ini",
        project_scope=tmp_path / "p.ini",
    )
    gui._sigil_instance = sig
    widgets = make_widgets("user")
    events.on("pref_changed", lambda k, v, s: gui._on_pref_changed(widgets, k, v, s))
    return sig, widgets


def test_add(monkeypatch, tmp_path):
    sig, widgets = setup_func(tmp_path)
    monkeypatch.setattr(gui, "_open_value_dialog", lambda *a, **k: ("color", "blue"))
    gui._on_add(widgets)
    assert sig.get_pref("color") == "blue"
    assert widgets["trees"]["user"].rows["color"][1] == "blue"


def test_add_with_underscore(monkeypatch, tmp_path):
    sig, widgets = setup_func(tmp_path)
    monkeypatch.setattr(gui, "_open_value_dialog", lambda *a, **k: ("foo_bar", "baz"))
    gui._on_add(widgets)
    assert sig.get_pref("foo_bar") == "baz"
    assert "foo_bar" in widgets["trees"]["user"].rows
    assert "foo.bar" not in widgets["trees"]["user"].rows


def test_edit(monkeypatch, tmp_path):
    sig, widgets = setup_func(tmp_path)
    sig.set_pref("color", "blue", scope="user")
    gui._populate_tree(widgets["trees"]["user"], "user")
    widgets["trees"]["user"].selection_set("color")
    monkeypatch.setattr(gui, "_open_value_dialog", lambda *a, **k: ("color", "green"))
    gui._on_edit(widgets)
    assert sig.get_pref("color") == "green"
    assert widgets["trees"]["user"].rows["color"][1] == "green"


def test_delete(tmp_path):
    sig, widgets = setup_func(tmp_path)
    sig.set_pref("color", "blue", scope="user")
    gui._populate_tree(widgets["trees"]["user"], "user")
    widgets["trees"]["user"].selection_set("color")
    gui._on_delete(widgets)
    assert sig.get_pref("color") is None
    assert "color" not in widgets["trees"]["user"].rows
