from __future__ import annotations

"""Aurelia ttk theme helpers.

This module defines the colour palette used by the tkinter interface and
provides helpers for applying the palette to a ``tkinter`` application.
External callers can access the palette via :func:`get_palette` and
register scope specific button styles with :func:`register_scope_styles`.
"""

try:  # pragma: no cover - importing tkinter is environment dependent
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore
    ttk = None  # type: ignore

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

_AURELIA_PALETTE: dict[str, object] = {
    "bg": "#2B313B",
    "card": "#EEF3FA",
    "card_edge": "#D4DEEE",
    "hdr_fg": "#F4F8FF",
    #"hdr_fg": "#f1d48e",
    "hdr_muted": "#C3CFE4",
    "ink": "#0E1724",
    "ink_muted": "#586A84",
    "field": "#FFFFFF",
    "field_bd": "#C8D3E6",
    "gold": "#D4B76A",
    "gold_hi":"#f1d48e",
    "title_accent":"#f1d48e",
    "primary": "#365DC6",
    "primary_hover": "#587BE2",
    "on_primary": "#F7FAFF",
    "tooltip_bg": "#0E1724",
    "tooltip_fg": "#F7FAFF",
    "scopes": {
        "Env": "#1f9d66",  # green-700
        "User": "#1e40af",  # blue-900
        "Machine": "#1c6e7d",  # emerald-900
        "Project": "#D4B76A",  # violet-700
        "ProjectMachine": "#c25e0c",  # orange-700
        "Def": "#334155",  # slate-700
    },
}

_ACTIVE_PALETTE: dict[str, object] = _AURELIA_PALETTE.copy()

SCOPE_COLORS = _AURELIA_PALETTE["scopes"]  # type: ignore[index]

# ---------------------------------------------------------------------------
# Palette helpers
# ---------------------------------------------------------------------------


def get_palette() -> dict[str, object]:
    """Return the currently active palette."""

    return _ACTIVE_PALETTE


# ---------------------------------------------------------------------------
# Style registration
# ---------------------------------------------------------------------------


def register_scope_styles(
    style: ttk.Style, scope_colors: dict[str, str]
) -> None:  # pragma: no cover - thin wrapper over ttk
    """Register per-scope button styles on *style*.

    For each ``scope`` and ``color`` pair in *scope_colors* two styles are
    created: ``"Scope.<scope>.TButton"`` (filled) and
    ``"Scope.<scope>.Outline.TButton"`` (outline variant).
    """

    palette = get_palette()

    for scope, color in scope_colors.items():
        filled = f"Scope.{scope}.TButton"
        outline = f"Scope.{scope}.Outline.TButton"

        style.configure(
            filled,
            background=color,
            foreground=palette["on_primary"],
        )
        style.map(
            filled,
            background=[("active", color)],
            foreground=[("active", palette["on_primary"])],
        )

        style.configure(
            outline,
            background=palette["card"],
            foreground=color,
            bordercolor=color,
            relief="solid",
            borderwidth=1,
        )
        style.map(
            outline,
            background=[("active", palette["card"])],
            foreground=[("active", color)],
        )


# ---------------------------------------------------------------------------
# Theme application
# ---------------------------------------------------------------------------


def use(root: tk.Misc, *, palette: dict[str, object] | None = None) -> None:
    """Apply the Aurelia palette to *root*.

    ``palette`` can be provided to override the default palette; this also
    updates the palette returned by :func:`get_palette`.
    """

    global _ACTIVE_PALETTE
    colors = palette or _AURELIA_PALETTE
    _ACTIVE_PALETTE = colors

    if ttk is None:
        return

    style = ttk.Style(root)

    root.configure(bg=colors["bg"])  # type: ignore[call-arg]

    style.configure("TFrame", background=colors["bg"])
    style.configure("TLabel", background=colors["bg"], foreground=colors["hdr_fg"])

    style.configure(
        "Card.TFrame",
        background=colors["card"],
        bordercolor=colors["card_edge"],
        borderwidth=1,
        relief="solid",
    )

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

    register_scope_styles(style, colors["scopes"])


__all__ = ["use", "get_palette", "register_scope_styles", "SCOPE_COLORS"]
