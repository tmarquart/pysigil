from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class Tooltip:
    """Simple tooltip for a widget."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tipwindow: tk.Toplevel | None = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None) -> None:  # type: ignore[override]
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 1
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(tw, text=self.text, relief="solid", borderwidth=1,
                          background="yellow", padding=(4, 2))
        label.pack()

    def hide(self, event=None) -> None:  # type: ignore[override]
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


def numeric_validator(min_val: float | None = None, max_val: float | None = None):
    """Return a Tk validation function for numeric entry."""

    def _validate(P: str) -> bool:
        if P == "":
            return True
        try:
            num = float(P)
        except ValueError:
            return False
        if min_val is not None and num < min_val:
            return False
        if max_val is not None and num > max_val:
            return False
        return True

    return _validate
