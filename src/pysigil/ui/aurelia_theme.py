"""Aurelia ttk theme palette definitions."""

from __future__ import annotations

from collections.abc import Mapping

from .theme import (
    ThemeSpec,
    apply_theme,
    get_active_palette,
    register_scope_styles as _register_scope_styles,
)

try:  # pragma: no cover - importing tkinter is environment dependent
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore
    ttk = None  # type: ignore

_AURELIA_PALETTE: dict[str, object] = {
    "bg": "#2B313B",
    "card": "#EEF3FA",
    "card_edge": "#D4DEEE",
    "hdr_fg": "#F4F8FF",
    "hdr_muted": "#C3CFE4",
    "ink": "#0E1724",
    "ink_muted": "#586A84",
    "field": "#FFFFFF",
    "field_bd": "#C8D3E6",
    "gold": "#D4B76A",
    "gold_hi": "#f1d48e",
    "title_accent": "#f1d48e",
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

SCOPE_COLORS: dict[str, str] = _AURELIA_PALETTE["scopes"]  # type: ignore[index]

THEME = ThemeSpec(name="aurelia", ttk_theme="clam", palette=_AURELIA_PALETTE)


def get_palette() -> dict[str, object]:
    """Return the palette for the active Aurelia theme."""

    palette = get_active_palette()
    return palette if palette else _AURELIA_PALETTE


def use(root: tk.Misc, *, palette: Mapping[str, object] | None = None) -> None:
    """Apply the Aurelia theme to *root*."""

    apply_theme(root, THEME, palette_override=palette)


def register_scope_styles(style: ttk.Style, scope_colors: Mapping[str, str]) -> None:
    """Register scope-specific styles for Aurelia."""

    _register_scope_styles(style, scope_colors)


__all__ = ["THEME", "use", "get_palette", "register_scope_styles", "SCOPE_COLORS"]
