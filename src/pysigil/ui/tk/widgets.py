"""Reusable tkinter widgets used by :mod:`pysigil.ui.tk`.

This module provides small standalone widgets used by the tkinter view
layer.  It ports components originally prototyped during the UI design
process, namely :class:`HoverTip` for delayed hover tooltips and
:class:`PillButton`, a rounded button displaying the value state of a
setting.

The module also exports a handful of color constants so that other parts
of the interface can match the prototype styling.
"""

from __future__ import annotations

from typing import Callable, Any, Literal

try:  # pragma: no cover - importing tkinter is environment dependent
    import tkinter as tk
    import tkinter.font as tkfont
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore
    tkfont = None  # type: ignore

# --- prototype color constants -------------------------------------------------

SCOPE_COLOR = {
    "Env": "#15803d",  # green-700
    "User": "#1e40af",  # blue-900
    "Machine": "#065f46",  # emerald-900
    "Project": "#6d28d9",  # violet-700
    "ProjectMachine": "#c2410c",  # orange-700
    "Def": "#000000",  # black
}

GREY_BG = "#f3f4f6"
GREY_TXT = "#6b7280"
GREY_BORDER = "#e5e7eb"


class HoverTip:
    """Display a tooltip when hovering over a widget."""

    def __init__(
        self,
        widget: tk.Widget,
        text_fn: Callable[[], str | None],
        *,
        delay: int = 250,
    ) -> None:
        self.widget = widget
        self.text_fn = text_fn
        self.delay = delay
        self._after: str | None = None
        self.tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add=True)
        widget.bind("<Leave>", self._hide, add=True)

    def _schedule(self, _event: tk.Event) -> None:
        self._after = self.widget.after(self.delay, self._show)

    def _show(self) -> None:
        if self.tip:
            return
        txt = self.text_fn() or ""
        if not txt:
            return
        x = self.widget.winfo_rootx() + 4
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.attributes("-topmost", True)
        self.tip.wm_geometry(f"+{x}+{y}")
        frame = tk.Frame(self.tip, bg="#111827", bd=0)
        frame.pack()
        label = tk.Label(frame, text=txt, bg="#111827", fg="#ffffff", padx=8, pady=6)
        label.pack()

    def _hide(self, _event: tk.Event) -> None:
        if self._after:
            self.widget.after_cancel(self._after)
            self._after = None
        if self.tip:
            tip = self.tip
            self.tip = None
            tip.after(120, tip.destroy)


class PillButton(tk.Canvas):
    """Rounded button indicating value state.

    ``state`` can be one of ``"effective"``, ``"present"``, ``"empty"``,
    ``"disabled"`` or ``"synthetic"``.
    """

    def __init__(
        self,
        master: tk.Widget,
        *,
        text: str,
        color: str,
        state: Literal["effective", "present", "empty", "disabled", "synthetic"],
        value_provider: Callable[[], Any],
        clickable: bool = True,
        on_click: Callable[[], None] | None = None,
        tooltip_title: str | None = None,
    ) -> None:
        super().__init__(master, height=28, highlightthickness=0, bd=0)
        self.text = text
        self.tooltip_title = tooltip_title or text
        self.color = color
        self.state = state
        self.clickable = clickable and state != "disabled"
        self.on_click = on_click
        self.font = tkfont.Font(size=9, weight="bold") if tkfont else None
        self.value_provider = value_provider
        self.pad_x = 14
        self.rad = 14
        self.bind("<Configure>", lambda e: self._draw())
        if self.clickable:
            self.bind("<Button-1>", lambda e: on_click() if on_click else None)
            self.configure(cursor="hand2")
        else:
            self.configure(cursor="arrow")
        self.configure(takefocus=1)
        self.bind("<FocusIn>", lambda e: self._draw())
        self.bind("<FocusOut>", lambda e: self._draw())
        self.bind(
            "<Key-Return>",
            lambda e: self.on_click() if self.clickable and self.on_click else None,
        )
        self.bind(
            "<Key-space>",
            lambda e: self.on_click() if self.clickable and self.on_click else None,
        )
        HoverTip(self, self._tip_text)
        self._draw(initial=True)

    # -- drawing ------------------------------------------------------------

    def _measure_width(self) -> int:
        if self.font is None:
            return 64
        text_w = self.font.measure(self.text)
        return max(64, text_w + self.pad_x * 2)

    def _draw(self, initial: bool = False) -> None:
        w = self._measure_width()
        self.configure(width=w)
        self.delete("all")
        if self.state == "effective":
            fill = outline = self.color
            fg = "#ffffff"
            border_w = 1
        elif self.state == "present":
            fill = "#ffffff"
            outline = self.color
            fg = self.color
            border_w = 2
        elif self.state == "disabled":
            fill = GREY_BG
            outline = GREY_BORDER
            fg = GREY_TXT
            border_w = 1
        elif self.state == "synthetic":
            fill = "#ffffff"
            outline = self.color
            fg = self.color
            border_w = 1
        else:  # empty
            fill = "#ffffff"
            outline = GREY_BORDER
            fg = GREY_TXT
            border_w = 1
        r = self.rad
        self._round_rect(1, 1, w - 1, 26, r, fill=fill, outline=outline, width=border_w)
        self.create_text(w / 2, 14, text=self.text, fill=fg, font=self.font)
        if self.focus_displayof() is self:
            self.create_rectangle(3, 3, w - 3, 24, outline="#111", dash=(2, 2))

    def _round_rect(self, x1: int, y1: int, x2: int, y2: int, r: int, **kw: Any) -> int:
        pts = [
            x1 + r,
            y1,
            x2 - r,
            y1,
            x2,
            y1,
            x2,
            y1 + r,
            x2,
            y2 - r,
            x2,
            y2,
            x2 - r,
            y2,
            x1 + r,
            y2,
            x1,
            y2,
            x1,
            y2 - r,
            x1,
            y1 + r,
            x1,
            y1,
        ]
        return self.create_polygon(pts, smooth=True, **kw)

    def _tip_text(self) -> str:
        val = self.value_provider()
        val_txt = str(val) if val is not None else "—"
        return f"{self.tooltip_title}: {val_txt}"


__all__ = [
    "HoverTip",
    "PillButton",
    "SCOPE_COLOR",
    "GREY_BG",
    "GREY_TXT",
    "GREY_BORDER",
]
