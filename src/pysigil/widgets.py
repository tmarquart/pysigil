from __future__ import annotations

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore
    ttk = None  # type: ignore


def widget_for(key: str, value: str | None, master):
    if ttk is None or tk is None:  # pragma: no cover - no tkinter available
        raise RuntimeError("tkinter is required for widgets")
    entry = ttk.Entry(master)

    def _set(val: str | None) -> None:
        entry.delete(0, tk.END)
        if val is not None:
            entry.insert(0, val)

    entry.set = _set  # type: ignore[attr-defined]
    return entry


__all__ = ["widget_for"]
