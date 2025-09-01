"""Widget registry for basic field editors.

The registry maps a field ``type`` as reported by :mod:`pysigil.api` to a
callable returning an editor widget.  Editors follow a very small
protocol which makes it straightforward to provide alternative
implementations for other GUI toolkits.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Callable, Protocol, Dict, Any

from ..settings_metadata import TYPE_REGISTRY

try:  # pragma: no cover - importing tkinter is environment dependent
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore
    ttk = None  # type: ignore


class EditorWidget(Protocol):
    """Protocol all editor widgets must implement."""

    def get_value(self) -> object | None: ...
    def set_value(self, value: object | None) -> None: ...
    def set_error(self, msg: str | None) -> None: ...
    def set_source_badge(self, source: str | None) -> None: ...


# -- concrete editor implementations ---------------------------------------


def _simple_entry(master) -> EditorWidget:
    if tk is None or ttk is None:  # pragma: no cover - tkinter missing
        raise RuntimeError("tkinter is required for widgets")
    frame = ttk.Frame(master)
    entry = ttk.Entry(frame)
    entry.pack(side="left", fill="x", expand=True)
    badge = ttk.Label(frame, text="")
    badge.pack(side="left", padx=4)

    def get_value() -> object | None:
        text = entry.get()
        return text if text != "" else None

    def set_value(value: object | None) -> None:
        entry.delete(0, tk.END)
        if value is not None:
            entry.insert(0, str(value))

    def set_error(msg: str | None) -> None:
        if msg:
            entry.configure(foreground="red")
        else:
            entry.configure(foreground="black")

    def set_source_badge(src: str | None) -> None:
        badge.configure(text=src or "")

    frame.get_value = get_value  # type: ignore[attr-defined]
    frame.set_value = set_value  # type: ignore[attr-defined]
    frame.set_error = set_error  # type: ignore[attr-defined]
    frame.set_source_badge = set_source_badge  # type: ignore[attr-defined]
    return frame  # type: ignore[return-value]


def _boolean_check(master) -> EditorWidget:
    if tk is None or ttk is None:  # pragma: no cover - tkinter missing
        raise RuntimeError("tkinter is required for widgets")
    frame = ttk.Frame(master)
    var = tk.BooleanVar()
    widget = ttk.Checkbutton(frame, variable=var)
    widget.pack(side="left")
    badge = ttk.Label(frame, text="")
    badge.pack(side="left", padx=4)

    def get_value() -> object | None:
        return var.get()

    def set_value(value: object | None) -> None:
        var.set(bool(value))

    def set_error(_msg: str | None) -> None:  # pragma: no cover - placeholder
        pass

    def set_source_badge(src: str | None) -> None:
        badge.configure(text=src or "")

    frame.get_value = get_value  # type: ignore[attr-defined]
    frame.set_value = set_value  # type: ignore[attr-defined]
    frame.set_error = set_error  # type: ignore[attr-defined]
    frame.set_source_badge = set_source_badge  # type: ignore[attr-defined]
    return frame  # type: ignore[return-value]


# Register widget implementations with the type registry
TYPE_REGISTRY["string"] = replace(TYPE_REGISTRY["string"], value_widget=_simple_entry)
TYPE_REGISTRY["integer"] = replace(TYPE_REGISTRY["integer"], value_widget=_simple_entry)
TYPE_REGISTRY["number"] = replace(TYPE_REGISTRY["number"], value_widget=_simple_entry)
TYPE_REGISTRY["boolean"] = replace(TYPE_REGISTRY["boolean"], value_widget=_boolean_check)
TYPE_REGISTRY["string_list"] = replace(TYPE_REGISTRY["string_list"], value_widget=_simple_entry)


FIELD_WIDGETS: Dict[str, Callable[[Any], EditorWidget]] = {
    key: ft.value_widget  # type: ignore[assignment]
    for key, ft in TYPE_REGISTRY.items()
    if ft.value_widget is not None
}


__all__ = ["EditorWidget", "FIELD_WIDGETS"]
