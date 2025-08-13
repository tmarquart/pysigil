from __future__ import annotations

from pysigil.core import KEY_JOIN_CHAR, Sigil
from pysigil.gui import _on_pref_changed, events


class DummyTree:
    def __init__(self) -> None:
        self.items: dict[str, tuple[str, str]] = {}
        self.packed = False

    def exists(self, iid: str) -> bool:
        return iid in self.items

    def item(self, iid: str, values: tuple[str, str] | None = None):
        if values is not None:
            self.items[iid] = values
        return self.items.get(iid)

    def insert(self, parent: str, index: str, iid: str, values: tuple[str, str]):
        self.items[iid] = values

    def delete(self, iid: str) -> None:
        self.items.pop(iid, None)

    def get_children(self) -> list[str]:
        return list(self.items.keys())

    def pack(self, **_kwargs) -> None:
        self.packed = True

    def pack_forget(self) -> None:
        self.packed = False


class DummyLabel:
    def __init__(self) -> None:
        self.packed = False

    def pack(self, **_kwargs) -> None:
        self.packed = True

    def pack_forget(self) -> None:
        self.packed = False


def test_pref_changed_event_uses_join_char(tmp_path):
    events._handlers.clear()
    sigil = Sigil("demo", user_scope=tmp_path)
    received: list[str] = []

    def _cb(k, _v, _s):
        received.append(k)

    events.on("pref_changed", _cb)
    sigil.set_pref("foo.bar", "baz", scope="user")
    assert received == [f"foo{KEY_JOIN_CHAR}bar"]


def test_on_pref_changed_updates_empty_label():
    tree = DummyTree()
    label = DummyLabel()
    widgets = {"trees": {"user": tree}, "empty_labels": {"user": label}}

    _on_pref_changed(widgets, "foo", "bar", "user")
    assert tree.packed is True
    assert label.packed is False

    _on_pref_changed(widgets, "foo", None, "user")
    assert tree.packed is False
    assert label.packed is True

