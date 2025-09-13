#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aurelia v2 — lighter charcoal canvas, clean slate/blue cards, warm gold accents.
Fix: Treeview heading styling is applied via "Treeview.Heading" (no per-column -style).
"""

import tkinter as tk
from tkinter import ttk

# ---------- palette (tuned) ----------
P = {
    # canvas / chrome
    "bg":        "#2B313B",   # lighter charcoal
    "line":      "#3A4252",   # separators on charcoal

    # light foreground panels
    "card":      "#EEF3FA",   # clean light slate
    "card_edge": "#D4DEEE",
    "ink":       "#162235",   # dark ink on light card
    "ink_muted": "#5D6E87",

    # inputs on card
    "field":     "#FFFFFF",
    "field_bd":  "#C8D3E6",

    # accents
    "blue":      "#3D6BE0",   # sapphire
    "blue_hi":   "#6E90F0",
    "teal":      "#28C6DA",
    "teal_hi":   "#83E6EE",
    "gold":      "#D4B76A",
    "gold_hi":   "#F2DEA2",

    # states
    "danger":    "#E1646B",
    "ok":        "#31D18A",
}

def map_style(st, widget, mapping):
    for opt, rules in mapping.items():
        st.map(widget, **{opt: rules})

def apply_aurelia(root):
    st = ttk.Style(root)
    base = "clam"
    try:
        st.theme_use(base)
    except Exception:
        base = st.theme_use()

    base_font  = ("Segoe UI", 10)
    semi_font  = ("Segoe UI Semibold", 10)
    title_font = ("Segoe UI Semibold", 14)
    mono_font  = ("Consolas", 10)

    # ---------------- theme ----------------
    st.theme_create(
        "aurelia",
        parent=base,
        settings={
            # canvas containers (dark)
            "TFrame": {"configure": {"background": P["bg"], "borderwidth": 0}},
            "TLabel": {"configure": {"background": P["bg"], "foreground": "#E7EDF8", "font": base_font}},
            "Title.TLabel": {"configure": {"background": P["bg"], "foreground": P["gold_hi"], "font": title_font}},
            "Muted.TLabel": {"configure": {"background": P["bg"], "foreground": "#AAB7CE", "font": base_font}},
            "TSeparator": {"configure": {"background": P["line"]}},
            "TNotebook": {"configure": {"background": P["bg"], "borderwidth": 0, "tabmargins": [6,6,6,0]}},
            "TNotebook.Tab": {
                "configure": {
                    "padding": (14, 8),
                    "background": P["bg"],
                    "foreground": "#AAB7CE",
                    "font": semi_font
                }
            },
            "TScrollbar": {
                "configure": {
                    "troughcolor": P["line"],
                    "background": "#313846",
                    "bordercolor": P["line"]
                }
            },

            # light cards (foreground panels)
            "Card.TFrame": {
                "configure": {
                    "background": P["card"],
                    "borderwidth": 1,
                    "relief": "solid",
                    "bordercolor": P["card_edge"],
                    "padding": 12
                }
            },
            "OnCard.TLabel": {"configure": {"background": P["card"], "foreground": P["ink"], "font": base_font}},
            "OnCard.Title.TLabel": {"configure": {"background": P["card"], "foreground": P["ink"], "font": title_font}},
            "OnCard.Muted.TLabel": {"configure": {"background": P["card"], "foreground": P["ink_muted"], "font": base_font}},

            # Buttons (on cards)
            "Light.TButton": {
                "configure": {
                    "background": "#F6F9FF", "foreground": P["ink"],
                    "borderwidth": 1, "bordercolor": P["card_edge"],
                    "padding": (12,6), "relief": "flat"
                }
            },
            "Light.Accent.TButton": {
                "configure": {
                    "background": P["blue"], "foreground": "#0B1830",
                    "borderwidth": 0, "padding": (14,7)
                }
            },
            "Light.Danger.TButton": {
                "configure": {
                    "background": P["danger"], "foreground": "#2A0D0E",
                    "borderwidth": 0, "padding": (14,7)
                }
            },

            # Inputs on card
            "Light.TEntry": {
                "configure": {
                    "foreground": P["ink"],
                    "fieldbackground": P["field"],
                    "background": P["field"],
                    "padding": (8,6),
                    "insertcolor": P["gold"],
                    "bordercolor": P["field_bd"],
                    "lightcolor": P["field_bd"],
                    "darkcolor": P["field_bd"]
                }
            },
            "Light.TCombobox": {
                "configure": {
                    "foreground": P["ink"],
                    "fieldbackground": P["field"],
                    "background": P["field"],
                    "arrowcolor": P["ink_muted"],
                    "bordercolor": P["field_bd"],
                    "padding": (8,4)
                }
            },
            "Light.TSpinbox": {
                "configure": {
                    "foreground": P["ink"],
                    "fieldbackground": P["field"],
                    "background": P["field"],
                    "bordercolor": P["field_bd"],
                    "insertcolor": P["gold"],
                    "arrowsize": 12,
                    "padding": (6,2)
                }
            },
            "Light.TCheckbutton": {"configure": {"background": P["card"], "foreground": P["ink"]}},
            "Light.TRadiobutton": {"configure": {"background": P["card"], "foreground": P["ink"]}},

            # Tables / progress / scales on card
            "Light.Treeview": {
                "configure": {
                    "background": P["field"],
                    "fieldbackground": P["field"],
                    "foreground": P["ink"],
                    "rowheight": 26,
                    "bordercolor": P["field_bd"]
                }
            },
            # IMPORTANT: Headings are styled globally for compatibility
            "Treeview.Heading": {
                "configure": {
                    "background": "#F4F7FD",
                    "foreground": P["ink"],
                    "padding": (8,6),
                    "relief": "flat",
                    "font": semi_font
                }
            },

            "Horizontal.TProgressbar": {
                "configure": {"background": P["blue"], "troughcolor": "#E7EEF9", "bordercolor": "#E7EEF9"}
            },
            "Horizontal.TScale": {
                "configure": {"troughcolor": "#E7EEF9", "background": "#F1F5FD"}
            },
        }
    )

    # State/hover maps
    map_style(st, "TNotebook.Tab", {
        "background": [("selected", P["card"]), ("!selected", P["bg"])],
        "foreground": [("selected", P["ink"]), ("!selected", "#AAB7CE")]
    })
    map_style(st, "Light.TButton", {
        "background": [("active", "#EEF3FF"), ("pressed", "#E8EEF9")],
        "bordercolor":[("focus", P["gold"])],
        "relief":     [("pressed", "sunken"), ("!pressed", "flat")]
    })
    map_style(st, "Light.Accent.TButton", {
        "background": [("active", P["blue_hi"]), ("pressed", P["blue"])],
        "foreground": [("disabled", "#6D86C0")]
    })
    map_style(st, "Light.Danger.TButton", {
        "background": [("active", "#FF7D84"), ("pressed", P["danger"])]
    })

    st.theme_use("aurelia")


# ---------- demo ----------
def demo(root):
    apply_aurelia(root)
    root.title("Aurelia v2 — Lighter Charcoal • Slate/Blue • Gold")
    root.configure(background=P["bg"])
    root.geometry("1000x720")
    try:
        root.tk.call("tk", "scaling", 1.2)
    except Exception:
        pass

    # Header (dark)
    header = ttk.Frame(root)
    header.pack(fill="x", padx=16, pady=(16, 8))
    ttk.Label(header, text="Aurelia", style="Title.TLabel").pack(side="left")
    ttk.Label(header, text="  lighter charcoal canvas with crisp slate/blue panels and gold accents",
              style="Muted.TLabel").pack(side="left", padx=10)

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=16, pady=16)

    # Controls tab
    t_controls = ttk.Frame(nb); nb.add(t_controls, text="Controls")
    left = ttk.Frame(t_controls, style="Card.TFrame"); left.pack(side="left", fill="both", expand=True, padx=(0,8), pady=8)
    right = ttk.Frame(t_controls, style="Card.TFrame"); right.pack(side="left", fill="both", expand=True, padx=(8,0), pady=8)

    ttk.Label(left, text="Buttons", style="OnCard.Title.TLabel").pack(anchor="w")
    r = ttk.Frame(left, style="Card.TFrame"); r.configure(borderwidth=0, padding=0)
    r.pack(anchor="w", pady=8)
    ttk.Button(r, text="Default", style="Light.TButton").pack(side="left", padx=6, pady=4)
    ttk.Button(r, text="Accent", style="Light.Accent.TButton").pack(side="left", padx=6, pady=4)
    ttk.Button(r, text="Danger", style="Light.Danger.TButton").pack(side="left", padx=6, pady=4)

    ttk.Separator(left).pack(fill="x", pady=10)
    ttk.Label(left, text="Progress & Scale", style="OnCard.TLabel").pack(anchor="w")
    pb = ttk.Progressbar(left, mode="determinate", length=260, style="Horizontal.TProgressbar")
    pb.pack(anchor="w", pady=6); pb.start(12)
    sc = ttk.Scale(left, from_=0, to=100, style="Horizontal.TScale")
    sc.pack(anchor="w", pady=4)

    ttk.Label(right, text="Checks & Radios", style="OnCard.Title.TLabel").pack(anchor="w")
    ttk.Checkbutton(right, text="Enable gilded mode", style="Light.TCheckbutton",
                    variable=tk.BooleanVar(value=True)).pack(anchor="w", pady=2)
    ttk.Checkbutton(right, text="Show constellation grid", style="Light.TCheckbutton",
                    variable=tk.BooleanVar(value=False)).pack(anchor="w", pady=2)
    rb = tk.StringVar(value="eagle")
    ttk.Radiobutton(right, text="Eagle motif", value="eagle", variable=rb, style="Light.TRadiobutton").pack(anchor="w", pady=2)
    ttk.Radiobutton(right, text="Starburst motif", value="star", variable=rb, style="Light.TRadiobutton").pack(anchor="w", pady=2)

    # Form tab
    t_form = ttk.Frame(nb); nb.add(t_form, text="Form")
    form = ttk.Frame(t_form, style="Card.TFrame"); form.pack(fill="both", expand=True, padx=4, pady=8)
    ttk.Label(form, text="Credentials", style="OnCard.Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
    ttk.Separator(form).grid(row=1, column=0, columnspan=2, sticky="ew", pady=8)

    ttk.Label(form, text="Display name", style="OnCard.TLabel").grid(row=2, column=0, sticky="e", padx=(0,8), pady=6)
    ttk.Entry(form, width=28, style="Light.TEntry").grid(row=2, column=1, sticky="w", pady=6)

    ttk.Label(form, text="Role", style="OnCard.TLabel").grid(row=3, column=0, sticky="e", padx=(0,8), pady=6)
    ttk.Combobox(form, width=26, values=["Student","Professor","Archivist","Groundskeeper"],
                 style="Light.TCombobox").grid(row=3, column=1, sticky="w", pady=6)

    ttk.Label(form, text="API Token", style="OnCard.TLabel").grid(row=4, column=0, sticky="e", padx=(0,8), pady=6)
    ttk.Entry(form, width=28, show="•", style="Light.TEntry").grid(row=4, column=1, sticky="w", pady=6)

    ttk.Label(form, text="Notes", style="OnCard.TLabel").grid(row=5, column=0, sticky="ne", padx=(0,8), pady=6)
    notes = tk.Text(form, height=6, width=42, bg=P["field"], fg=P["ink"],
                    insertbackground=P["gold"], relief="flat",
                    highlightthickness=1, highlightbackground=P["field_bd"])
    notes.grid(row=5, column=1, sticky="we", pady=6)
    ttk.Separator(form).grid(row=6, column=0, columnspan=2, sticky="ew", pady=10)
    ttk.Button(form, text="Save", style="Light.Accent.TButton").grid(row=7, column=1, sticky="e")
    form.columnconfigure(1, weight=1)

    # Data tab
    t_data = ttk.Frame(nb); nb.add(t_data, text="Data")
    table = ttk.Frame(t_data, style="Card.TFrame"); table.pack(fill="both", expand=True, padx=4, pady=8)
    ttk.Label(table, text="Astral Ledger", style="OnCard.TLabel").pack(anchor="w")
    cols = ("id","artifact","status","owner")
    tv = ttk.Treeview(table, columns=cols, show="headings", height=10, style="Light.Treeview")
    for c, w in zip(cols, (80,220,120,160)):
        tv.heading(c, text=c.title(), anchor="w")  # <- no per-column style (compat)
        tv.column(c, width=w, anchor="w")
    tv.pack(fill="both", expand=True, pady=(8,0))
    for row in [(1,"Starmap Disk","Catalogued","E. Figg"),
                (2,"Gilded Astrolabe","Loaned","P. Binns"),
                (3,"Orrery Gear","Restored","M. Hagrid"),
                (4,"Runic Tablet","Quarantined","A. Pince")]:
        tv.insert("", "end", values=row)

    # Palette tab
    t_palette = ttk.Frame(nb); nb.add(t_palette, text="Palette")
    pal = ttk.Frame(t_palette, style="Card.TFrame"); pal.pack(fill="x", padx=4, pady=8)

    def sw(name, hex_):
        f = ttk.Frame(pal, style="Card.TFrame"); f.configure(borderwidth=0, padding=6)
        box = tk.Frame(f, width=42, height=24, bg=hex_,
                       highlightthickness=1, highlightbackground=P["card_edge"])
        box.pack(side="left")
        ttk.Label(f, text=f"{name}  {hex_}", style="OnCard.Muted.TLabel").pack(side="left", padx=8)
        return f

    row1 = ttk.Frame(pal, style="Card.TFrame"); row1.configure(borderwidth=0, padding=0); row1.pack(fill="x")
    for k in ("bg","card","blue","gold","teal"):
        sw(k, P[k]).pack(side="left", padx=8, pady=8)

    footer = ttk.Frame(root)
    footer.pack(fill="x", padx=16, pady=(0,12))
    ttk.Label(footer, text="Lighter charcoal canvas • crisp slate panels • sapphire + gold accents",
              style="Muted.TLabel").pack(side="left")


if __name__ == "__main__":
    root = tk.Tk()
    demo(root)
    root.mainloop()
