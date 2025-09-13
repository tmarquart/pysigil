# aurelia_theme.py
# -----------------------------------------------------------------------------
# Aurelia — ttk theme: lighter charcoal canvas • light-slate cards • sapphire
# primary + gold accents. This module is intentionally minimal and stable.
#
# Public API:
#   - apply(root_or_style=None, *, palette=None, theme_name="aurelia") -> ttk.Style
#   - use(root_or_style=None, theme_name="aurelia") -> ttk.Style
#   - get_palette() -> dict (copy of defaults)
#
# Notes:
#   * Safe on stock Tk: no per-column Treeview heading styles, no custom layouts.
#   * Horizontal widgets use built-in style names (e.g., "Horizontal.TScale").
#   * Only essential styles are defined to keep it easy to extend in-app.
# -----------------------------------------------------------------------------

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from copy import deepcopy

# ---- default palette (tuned) ----
_AURELIA_PALETTE = {
    # canvas / chrome
    "bg":        "#2B313B",   # lighter charcoal
    "line":      "#3A4252",   # separators on charcoal

    # light foreground cards
    "card":      "#EEF3FA",   # clean light slate
    "card_edge": "#D4DEEE",
    "ink":       "#0E1724",   # text on cards (high contrast)
    "ink_muted": "#586A84",

    # inputs on card
    "field":     "#FFFFFF",
    "field_bd":  "#C8D3E6",

    # accents
    "blue":      "#365DC6",   # primary button (muted sapphire)
    "blue_hi":   "#587BE2",   # hover
    "gold":      "#D4B76A",   # focus ring / highlight
    "gold_hi":   "#F2DEA2",

    # header text on dark
    "hdr_fg":    "#F4F8FF",
    "hdr_muted": "#C3CFE4",
}

def get_palette() -> dict:
    """Return a copy of the Aurelia default palette (safe to mutate)."""
    return deepcopy(_AURELIA_PALETTE)

def _style_from_root_or_style(root_or_style: tk.Tk | ttk.Style | None) -> ttk.Style:
    if isinstance(root_or_style, ttk.Style):
        return root_or_style
    if isinstance(root_or_style, (tk.Tk, tk.Toplevel)):
        return ttk.Style(root_or_style)
    # fall back to default root if already created, else create a hidden root
    try:
        return ttk.Style()
    except tk.TclError:
        _root = tk.Tk()
        _root.withdraw()
        return ttk.Style(_root)

def _map(style: ttk.Style, widget: str, mapping: dict):
    for opt, rules in mapping.items():
        style.map(widget, **{opt: rules})

def apply(root_or_style: tk.Tk | ttk.Style | None = None, *, palette: dict | None = None,
          theme_name: str = "aurelia") -> ttk.Style:
    """
    Create (or update) the Aurelia theme and return a ttk.Style bound to it.
    - Pass a custom `palette` dict to override any colors.
    - Safe to call multiple times.
    """
    P = get_palette()
    if palette:
        P.update(palette)

    style = _style_from_root_or_style(root_or_style)

    # Use a portable base
    base = "clam"
    try:
        style.theme_use(base)
    except Exception:
        base = style.theme_use()

    settings = {
        # --- dark chrome (canvas) ---
        "TFrame": {"configure": {"background": P["bg"], "borderwidth": 0}},
        "TLabel": {"configure": {"background": P["bg"], "foreground": P["hdr_fg"]}},
        "Title.TLabel": {"configure": {"background": P["bg"], "foreground": P["gold_hi"], "font": ("Segoe UI Semibold", 14)}},
        "Muted.TLabel": {"configure": {"background": P["bg"], "foreground": P["hdr_muted"]}},
        "TSeparator": {"configure": {"background": P["line"]}},
        "TNotebook": {"configure": {"background": P["bg"], "borderwidth": 0, "tabmargins": [6, 6, 6, 0]}},
        "TNotebook.Tab": {
            "configure": {"padding": (12, 7), "background": P["bg"], "foreground": P["hdr_muted"], "font": ("Segoe UI Semibold", 10)}
        },

        # --- light cards (foreground area) ---
        "Card.TFrame": {
            "configure": {
                "background": P["card"], "borderwidth": 1, "relief": "solid",
                "bordercolor": P["card_edge"], "padding": 12
            }
        },
        "OnCard.TLabel": {"configure": {"background": P["card"], "foreground": P["ink"]}},
        "OnCard.Title.TLabel": {"configure": {"background": P["card"], "foreground": P["ink"], "font": ("Segoe UI Semibold", 14)}},
        "OnCard.Muted.TLabel": {"configure": {"background": P["card"], "foreground": P["ink_muted"]}},

        # --- buttons (on cards) ---
        # Primary (blue)
        "Light.TButton": {
            "configure": {"background": P["blue"], "foreground": "#F7FAFF", "borderwidth": 0, "padding": (14, 7), "relief": "flat"}
        },
        # Secondary (neutral)
        "Light.Secondary.TButton": {
            "configure": {"background": "#F5F7FC", "foreground": P["ink"], "borderwidth": 1,
                          "bordercolor": "#D9E2F3", "padding": (12, 6), "relief": "flat"}
        },

        # --- inputs on cards ---
        "Light.TEntry": {
            "configure": {
                "foreground": P["ink"], "fieldbackground": P["field"], "background": P["field"],
                "padding": (8, 6), "insertcolor": P["gold"],
                "bordercolor": P["field_bd"], "lightcolor": P["field_bd"], "darkcolor": P["field_bd"]
            }
        },
        "Light.TCombobox": {
            "configure": {
                "foreground": P["ink"], "fieldbackground": P["field"], "background": P["field"],
                "arrowcolor": P["ink_muted"], "bordercolor": P["field_bd"], "padding": (8, 4)
            }
        },
        "Light.TCheckbutton": {"configure": {"background": P["card"], "foreground": P["ink"]}},
        "Light.TRadiobutton": {"configure": {"background": P["card"], "foreground": P["ink"]}},
        "Light.TSpinbox": {
            "configure": {"foreground": P["ink"], "fieldbackground": P["field"], "background": P["field"],
                          "bordercolor": P["field_bd"], "insertcolor": P["gold"], "arrowsize": 12, "padding": (6, 2)}
        },

        # --- data / progress ---
        "Light.Treeview": {
            "configure": {"background": P["field"], "fieldbackground": P["field"], "foreground": P["ink"],
                          "rowheight": 26, "bordercolor": P["field_bd"]}
        },
        "Treeview.Heading": {  # global (compat)
            "configure": {"background": "#F4F7FD", "foreground": P["ink"], "padding": (8, 6),
                          "relief": "flat", "font": ("Segoe UI Semibold", 10)}
        },
        "Horizontal.TProgressbar": {
            "configure": {"background": P["blue"], "troughcolor": "#E7EEF9", "bordercolor": "#E7EEF9"}
        },
        "Horizontal.TScale": {
            "configure": {"troughcolor": "#E7EEF9", "background": "#F1F5FD"}
        },
    }

    if theme_name in style.theme_names():
        # Update existing theme in place (lets callers re-apply with overrides)
        style.theme_settings(theme_name, settings)
    else:
        style.theme_create(theme_name, parent=base, settings=settings)

    # State maps
    _map(style, "TNotebook.Tab", {
        "background": [("selected", _AURELIA_PALETTE["card"]), ("!selected", _AURELIA_PALETTE["bg"])],
        "foreground": [("selected", _AURELIA_PALETTE["ink"]), ("!selected", _AURELIA_PALETTE["hdr_muted"])]
    })
    _map(style, "Light.TButton", {
        "background": [("active", _AURELIA_PALETTE["blue_hi"]), ("pressed", _AURELIA_PALETTE["blue"])],
        "relief":     [("pressed", "sunken"), ("!pressed", "flat")]
    })
    _map(style, "Light.Secondary.TButton", {
        "background": [("active", "#EEF2FA"), ("pressed", "#E8EDF7")],
        "bordercolor":[("focus", _AURELIA_PALETTE["gold"])]
    })

    return style

def use(root_or_style: tk.Tk | ttk.Style | None = None, *, theme_name: str = "aurelia") -> ttk.Style:
    """Ensure Aurelia exists and activate it. Returns the bound ttk.Style."""
    style = apply(root_or_style, theme_name=theme_name)
    style.theme_use(theme_name)
    return style
