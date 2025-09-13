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

_AURELIA_PALETTE: dict[str, dict[str, str]] = {
    # Neutrals ---------------------------------------------------------------
    "neutrals": {
        "0": "#ffffff",
        "50": "#f9fafb",
        "100": "#f3f4f6",
        "200": "#e5e7eb",
        "300": "#d1d5db",
        "400": "#9ca3af",
        "500": "#6b7280",
        "600": "#475569",
        "700": "#374151",
        "800": "#1f2937",
        "900": "#111827",
    },
    # Text colours ----------------------------------------------------------
    "text": {
        "fg": "#111827",
        "muted": "#6b7280",
        "on_primary": "#ffffff",
    },
    # Accent colours --------------------------------------------------------
    "accents": {
        "primary": "#1e40af",
        "primary_hover": "#1d4ed8",
    },
    # Scope colours ---------------------------------------------------------
    "scopes": {
        "Env": "#15803d",  # green-700
        "User": "#1e40af",  # blue-900
        "Machine": "#065f46",  # emerald-900
        "Project": "#6d28d9",  # violet-700
        "ProjectMachine": "#c2410c",  # orange-700
        "Def": "#334155",  # slate-700
    },
}

_ACTIVE_PALETTE: dict[str, dict[str, str]] = _AURELIA_PALETTE

SCOPE_COLORS = _AURELIA_PALETTE["scopes"]

# ---------------------------------------------------------------------------
# Palette helpers
# ---------------------------------------------------------------------------


def get_palette() -> dict[str, dict[str, str]]:
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

    for scope, color in scope_colors.items():
        filled = f"Scope.{scope}.TButton"
        outline = f"Scope.{scope}.Outline.TButton"

        style.configure(
            filled,
            background=color,
            foreground=_AURELIA_PALETTE["text"]["on_primary"],
        )
        style.map(
            filled,
            background=[("active", color)],
            foreground=[("active", _AURELIA_PALETTE["text"]["on_primary"])],
        )

        style.configure(
            outline,
            background=_AURELIA_PALETTE["neutrals"]["0"],
            foreground=color,
            bordercolor=color,
            relief="solid",
            borderwidth=1,
        )
        style.map(
            outline,
            background=[("active", _AURELIA_PALETTE["neutrals"]["0"])],
            foreground=[("active", color)],
        )


# ---------------------------------------------------------------------------
# Theme application
# ---------------------------------------------------------------------------


def use(root: tk.Misc, *, palette: dict[str, dict[str, str]] | None = None) -> None:
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
    neutrals = colors["neutrals"]
    text = colors["text"]
    accents = colors["accents"]

    root.configure(bg=neutrals["100"])  # type: ignore[call-arg]

    style.configure("TFrame", background=neutrals["100"])
    style.configure("TLabel", background=neutrals["100"], foreground=text["fg"])

    style.configure(
        "Card.TFrame",
        background=neutrals["0"],
        bordercolor=neutrals["200"],
        borderwidth=1,
        relief="solid",
    )

    style.configure(
        "TButton",
        background=accents["primary"],
        foreground=text["on_primary"],
    )
    style.map(
        "TButton",
        background=[("active", accents["primary_hover"])],
        foreground=[("disabled", text["muted"])],
    )

    register_scope_styles(style, colors["scopes"])


__all__ = ["use", "get_palette", "register_scope_styles", "SCOPE_COLORS"]
