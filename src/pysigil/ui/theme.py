"""Toolkit-agnostic theme management for tkinter UIs."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass

try:  # pragma: no cover - importing tkinter is environment dependent
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore
    ttk = None  # type: ignore


@dataclass(frozen=True)
class ThemeSpec:
    """Description of a theme that can be applied to a tkinter UI."""

    name: str
    ttk_theme: str
    palette: Mapping[str, object]

    def with_palette(self, palette: Mapping[str, object]) -> ThemeSpec:
        """Return a copy of the theme using *palette* instead of the default."""

        return ThemeSpec(name=self.name, ttk_theme=self.ttk_theme, palette=palette)


_ACTIVE_THEME: ThemeSpec | None = None
_ACTIVE_PALETTE: dict[str, object] = {}


def get_active_palette() -> dict[str, object]:
    """Return the palette from the most recently applied theme."""

    return _ACTIVE_PALETTE


def apply_theme(
    root: tk.Misc,
    theme: ThemeSpec,
    *,
    palette_override: Mapping[str, object] | None = None,
) -> None:
    """Apply *theme* to *root* with an optional palette override."""

    global _ACTIVE_THEME, _ACTIVE_PALETTE

    colors: dict[str, object] = dict(palette_override or theme.palette)
    _ACTIVE_THEME = theme.with_palette(colors)
    _ACTIVE_PALETTE = colors

    if ttk is None:  # pragma: no cover - ttk unavailable in some environments
        return

    style = ttk.Style(root)
    try:  # pragma: no branch - prefer requested ttk theme but fall back silently
        style.theme_use(theme.ttk_theme)
    except Exception:  # pragma: no cover - best effort on unsupported themes
        pass

    root.configure(bg=colors["bg"])  # type: ignore[call-arg]
    try:  # pragma: no branch - tk palette calls may fail on some platforms
        root.tk_setPalette(
            background=colors["bg"],
            foreground=colors["ink"],
            activeBackground=colors["primary_hover"],
            activeForeground=colors["on_primary"],
            highlightColor=colors["gold"],
            highlightBackground=colors["bg"],
            selectColor=colors["primary"],
        )
    except Exception:
        pass

    option_add = getattr(root, "option_add", None)
    if callable(option_add):
        option_add("*background", colors["bg"])
        option_add("*foreground", colors["ink"])
        option_add("*selectBackground", colors["primary_hover"])
        option_add("*selectForeground", colors["on_primary"])
        option_add("*insertBackground", colors["ink"])
        option_add("*troughColor", colors["card_edge"])
        option_add("*activeBackground", colors["primary_hover"])
        option_add("*activeForeground", colors["on_primary"])
        option_add("*highlightColor", colors["gold"])

    style.configure("TFrame", background=colors["bg"])
    style.configure("TLabel", background=colors["bg"], foreground=colors["hdr_fg"])

    style.configure(
        "TMenubutton",
        background=colors["card"],
        foreground=colors["ink"],
        borderwidth=1,
        relief="solid",
    )

    style.configure(
        "Card.TFrame",
        background=colors["card"],
        bordercolor=colors["card_edge"],
        borderwidth=1,
        relief="solid",
    )
    style.configure("CardBody.TFrame", background=colors["card"])
    style.configure("CardSection.TFrame", background=colors["card"])

    style.configure(
        "TButton",
        background=colors["card"],
        foreground=colors["ink"],
        bordercolor=colors["field_bd"],
        borderwidth=1,
        relief="solid",
    )
    style.map(
        "TButton",
        background=[("active", colors["card_edge"])],
        foreground=[("disabled", colors["ink_muted"])],
    )

    style.configure(
        "TCheckbutton",
        background=colors["bg"],
        foreground=colors["hdr_muted"],
        indicatorcolor=colors["card"],
        focusthickness=1,
        focuscolor=colors["primary"],
    )
    style.map(
        "TCheckbutton",
        foreground=[("disabled", colors["ink_muted"]), ("active", colors["hdr_fg"])],
        indicatorcolor=[("selected", colors["primary"]), ("!selected", colors["card_edge"])],
    )

    style.configure(
        "Card.TCheckbutton",
        background=colors["card"],
        foreground=colors["ink"],
        indicatorcolor=colors["card_edge"],
        focusthickness=1,
        focuscolor=colors["primary"],
    )
    style.map(
        "Card.TCheckbutton",
        foreground=[("disabled", colors["ink_muted"]), ("active", colors["ink"])],
        indicatorcolor=[("selected", colors["primary"]), ("!selected", colors["card_edge"])],
        background=[("active", colors["card_edge"])],
    )

    style.configure(
        "TRadiobutton",
        background=colors["bg"],
        foreground=colors["hdr_muted"],
        indicatorcolor=colors["card"],
        focusthickness=1,
        focuscolor=colors["primary"],
    )
    style.map(
        "TRadiobutton",
        foreground=[("disabled", colors["ink_muted"]), ("active", colors["hdr_fg"])],
        indicatorcolor=[("selected", colors["primary"]), ("!selected", colors["card_edge"])],
    )

    style.configure(
        "Plain.TButton",
        background=colors["card"],
        foreground=colors["ink"],
        borderwidth=0,
        relief="flat",
    )
    style.map(
        "Plain.TButton",
        background=[("active", colors["card_edge"])],
        foreground=[("disabled", colors["ink_muted"])],
    )

    style.configure(
        "Toolbutton",
        background=colors["card"],
        foreground=colors["ink"],
        bordercolor=colors["field_bd"],
        borderwidth=1,
        focusthickness=1,
        focuscolor=colors["primary"],
        relief="solid",
        padding=4,
    )
    style.map(
        "Toolbutton",
        background=[("selected", colors["primary"]), ("active", colors["card_edge"])],
        foreground=[("selected", colors["on_primary"]), ("disabled", colors["ink_muted"])],
    )

    style.configure(
        "Card.TLabel",
        background=colors["card"],
        foreground=colors["ink"],
    )
    style.configure(
        "CardKey.TLabel",
        background=colors["card"],
        foreground=colors["ink"],
        font=(None, 10, "bold"),
    )
    style.configure(
        "CardMuted.TLabel",
        background=colors["card"],
        foreground=colors["ink_muted"],
    )
    style.configure(
        "CardSection.TLabel",
        background=colors["card"],
        foreground=colors["ink"],
        font=(None, 12, "bold"),
    )
    style.configure(
        "CardToggle.TLabel",
        background=colors["card"],
        foreground=colors["ink_muted"],
    )

    style.configure(
        "TEntry",
        padding=6,
        foreground=colors["ink"],
        fieldbackground=colors["field"],
        background=colors["field"],
        insertcolor=colors["ink"],
        bordercolor=colors["field_bd"],
        lightcolor=colors["field_bd"],
        darkcolor=colors["field_bd"],
        borderwidth=1,
        relief="solid",
    )
    style.map(
        "TEntry",
        fieldbackground=[("readonly", colors["card_edge"]), ("disabled", colors["card_edge"])],
        foreground=[("disabled", colors["ink_muted"])],
        bordercolor=[("focus", colors["primary"])],
        lightcolor=[("focus", colors["primary"])],
        darkcolor=[("focus", colors["primary"])],
    )

    style.configure(
        "TCombobox",
        padding=4,
        background=colors["field"],
        foreground=colors["ink"],
        fieldbackground=colors["field"],
        arrowcolor=colors["ink"],
        bordercolor=colors["field_bd"],
        lightcolor=colors["field_bd"],
        darkcolor=colors["field_bd"],
        borderwidth=1,
        relief="solid",
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", colors["field"]), ("disabled", colors["card_edge"])],
        foreground=[("disabled", colors["ink_muted"])],
        arrowcolor=[("pressed", colors["primary"]), ("active", colors["primary"])],
        bordercolor=[("focus", colors["primary"])],
        lightcolor=[("focus", colors["primary"])],
        darkcolor=[("focus", colors["primary"])],
    )

    style.configure(
        "TSpinbox",
        padding=4,
        background=colors["field"],
        foreground=colors["ink"],
        fieldbackground=colors["field"],
        arrowcolor=colors["ink"],
        bordercolor=colors["field_bd"],
        lightcolor=colors["field_bd"],
        darkcolor=colors["field_bd"],
        borderwidth=1,
        relief="solid",
    )
    style.map(
        "TSpinbox",
        fieldbackground=[("readonly", colors["field"]), ("disabled", colors["card_edge"])],
        foreground=[("disabled", colors["ink_muted"])],
        arrowcolor=[("pressed", colors["primary"]), ("active", colors["primary"])],
        bordercolor=[("focus", colors["primary"])],
        lightcolor=[("focus", colors["primary"])],
        darkcolor=[("focus", colors["primary"])],
    )

    style.configure(
        "TLabelframe",
        background=colors["card"],
        bordercolor=colors["card_edge"],
        borderwidth=1,
        relief="solid",
        foreground=colors["ink"],
    )
    style.configure(
        "TLabelframe.Label",
        background=colors["card"],
        foreground=colors["ink_muted"],
    )

    style.configure(
        "Treeview",
        background=colors["card"],
        fieldbackground=colors["card"],
        foreground=colors["ink"],
        bordercolor=colors["card_edge"],
    )
    style.map(
        "Treeview",
        background=[("selected", colors["primary_hover"])],
        foreground=[("selected", colors["on_primary"])],
    )
    style.configure(
        "Treeview.Heading",
        background=colors["card_edge"],
        foreground=colors["ink"],
        bordercolor=colors["card_edge"],
        relief="flat",
    )
    style.map(
        "Treeview.Heading",
        background=[("active", colors["primary_hover"])],
        foreground=[("active", colors["on_primary"])],
    )

    style.configure("TSeparator", background=colors["card_edge"])

    style.configure(
        "Vertical.TScrollbar",
        background=colors["card"],
        troughcolor=colors["card_edge"],
        arrowcolor=colors["ink"],
        bordercolor=colors["card_edge"],
    )
    style.configure(
        "Horizontal.TScrollbar",
        background=colors["card"],
        troughcolor=colors["card_edge"],
        arrowcolor=colors["ink"],
        bordercolor=colors["card_edge"],
    )

    style.configure("TPanedwindow", background=colors["bg"], borderwidth=0)
    style.configure(
        "Tooltip.TLabel",
        background=colors["tooltip_bg"],
        foreground=colors["tooltip_fg"],
    )

    scope_colors = colors.get("scopes")
    if isinstance(scope_colors, Mapping):
        register_scope_styles(style, scope_colors, palette=colors)


def register_scope_styles(
    style: ttk.Style,
    scope_colors: Mapping[str, str],
    *,
    palette: MutableMapping[str, object] | None = None,
) -> None:  # pragma: no cover - thin wrapper over ttk
    """Register per-scope button styles on *style*."""

    colors = palette or get_active_palette()
    if not colors:
        return

    for scope, color in scope_colors.items():
        filled = f"Scope.{scope}.TButton"
        outline = f"Scope.{scope}.Outline.TButton"

        style.configure(
            filled,
            background=color,
            foreground=colors["on_primary"],
        )
        style.map(
            filled,
            background=[("active", color)],
            foreground=[("active", colors["on_primary"])],
        )

        style.configure(
            outline,
            background=colors["card"],
            foreground=color,
            bordercolor=color,
            relief="solid",
            borderwidth=1,
        )
        style.map(
            outline,
            background=[("active", colors["card"])],
            foreground=[("active", color)],
        )


__all__ = ["ThemeSpec", "apply_theme", "get_active_palette", "register_scope_styles"]
