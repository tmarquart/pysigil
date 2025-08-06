"""Widget dispatcher stub for Sigil GUI."""
from __future__ import annotations

from tkinter import StringVar, ttk


def widget_for(key: str, meta: dict | None, master):
    """Return a ready-to-grid Tk widget for editing *key*.

    For version 2 this always returns :class:`ttk.Entry` bound to a
    :class:`tkinter.StringVar`. The widget exposes ``get()`` and ``set()``
    methods for retrieving and updating the value.
    """

    var = StringVar(master)
    entry = ttk.Entry(master, textvariable=var)

    def set_value(value: str) -> None:
        var.set(value)

    entry.set = set_value  # type: ignore[attr-defined]
    return entry
