"""Widget registry for basic field editors.

The registry maps a field ``type`` as reported by :mod:`pysigil.api` to a
callable returning an editor widget.  Editors follow a very small
protocol which makes it straightforward to provide alternative
implementations for other GUI toolkits.
"""

from __future__ import annotations

from typing import Callable, Protocol, Dict, Any

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
    entry = ttk.Entry(master)

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

    def set_source_badge(_src: str | None) -> None:  # pragma: no cover - placeholder
        pass

    entry.get_value = get_value  # type: ignore[attr-defined]
    entry.set_value = set_value  # type: ignore[attr-defined]
    entry.set_error = set_error  # type: ignore[attr-defined]
    entry.set_source_badge = set_source_badge  # type: ignore[attr-defined]
    return entry  # type: ignore[return-value]


def _boolean_check(master) -> EditorWidget:
    if tk is None or ttk is None:  # pragma: no cover - tkinter missing
        raise RuntimeError("tkinter is required for widgets")
    var = tk.BooleanVar()
    widget = ttk.Checkbutton(master, variable=var)

    def get_value() -> object | None:
        return var.get()

    def set_value(value: object | None) -> None:
        var.set(bool(value))

    def set_error(_msg: str | None) -> None:  # pragma: no cover - placeholder
        pass

    def set_source_badge(_src: str | None) -> None:  # pragma: no cover - placeholder
        pass

    widget.get_value = get_value  # type: ignore[attr-defined]
    widget.set_value = set_value  # type: ignore[attr-defined]
    widget.set_error = set_error  # type: ignore[attr-defined]
    widget.set_source_badge = set_source_badge  # type: ignore[attr-defined]
    return widget  # type: ignore[return-value]


FIELD_WIDGETS: Dict[str, Callable[[Any], EditorWidget]] = {
    "string": _simple_entry,
    "integer": _simple_entry,
    "number": _simple_entry,
    "boolean": _boolean_check,
}

__all__ = ["EditorWidget", "FIELD_WIDGETS"]
