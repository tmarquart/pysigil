#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aurelia v3 — lighter charcoal canvas • crisp slate cards • sapphire (toned) + gold
- Blue is now the default button (slightly muted)
- Removed red sample; added neutral "Secondary"
- Increased text contrast
"""

import tkinter as tk
from tkinter import ttk

# -------- palette (tuned for contrast) --------
P = {
    # canvas / chrome
    "bg":        "#2B313B",   # lighter charcoal
    "line":      "#3A4252",

    # light foreground panels
    "card":      "#EEF3FA",   # light slate
    "card_edge": "#D4DEEE",
    "ink":       "#0E1724",   # darker ink on card (more contrast)
    "ink_muted": "#586A84",

    # inputs on card
    "field":     "#FFFFFF",
    "field_bd":  "#C8D3E6",

    # accents
    "blue":      "#365DC6",   # toned-down sapphire (was 3D6BE0)
    "blue_hi":   "#587BE2",
    "neutral":   "#F5F7FC",   # secondary / quiet button
    "neutral_bd":" #D9E2F3",
    "gold":      "#D4B76A",
    "gold_hi":   "#F2DEA2",

    # misc
    "muted_hdr": "#C3CFE4",   # muted text on dark header
    "hdr_fg":    "#F4F8FF",   # brighter text on dark header
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

    st.theme_create(
        "aurelia",
        parent=base,
        settings={
            # ----- dark header / chrome -----
            "TFrame": {"configure": {"background": P["bg"], "borderwidth": 0}},
            "TLabel": {"configure": {"background": P["bg"], "foreground": P["hdr_fg"], "font": base_font}},
            "Title.TLabel": {"configure": {"background": P["bg"], "foreground": P["gold_hi"], "font": title_font}},
            "Muted.TLabel": {"configure": {"background": P["bg"], "foreground": P["muted_hdr"], "font": base_font}},
            "TSeparator": {"configure": {"background": P["line"]}},
            "TNotebook": {"configure": {"background": P["bg"], "borderwidth": 0, "tabmargins": [6,6,6,0]}},
            "TNotebook.Tab": {
                "configure": {"padding": (14,8), "background": P["bg"], "foreground": P["muted_hdr"], "font": semi_font}
            },
            "TScrollbar": {
                "configure": {"troughcolor": P["line"], "background": "#313846", "bordercolor": P["line"]}
            },

            # ----- light cards (content) -----
            "Card.TFrame": {
                "configure": {
                    "background": P["card"], "borderwidth": 1, "relief": "solid",
                    "bordercolor": P["card_edge"], "padding": 12
                }
            },
            "OnCard.TLabel": {"configure": {"background": P["card"], "foreground": P["ink"], "font": base_font}},
            "OnCard.Title.TLabel": {"configure": {"background": P["card"], "foreground": P["ink"], "font": title_font}},
            "OnCard.Muted.TLabel": {"configure": {"background": P["card"], "foreground": P["ink_muted"], "font": base_font}},

            # Buttons on cards
            "Light.TButton": {   # DEFAULT = BLUE
                "configure": {
                    "background": P["blue"], "foreground": "#F7FAFF",
                    "borderwidth": 0, "padding": (14,7), "relief": "flat"
                }
            },
            "Light.Secondary.TButton": {  # neutral, quiet button
                "configure": {
                    "background": P["neutral"], "foreground": P["ink"],
                    "borderwidth": 1, "bordercolor": P["neutral_bd"],
                    "padding": (12,6), "relief": "flat"
                }
            },

            # Inputs on cards
            "Light.TEntry": {
                "configure": {
                    "foreground": P["ink"], "fieldbackground": P["field"], "background": P["field"],
                    "padding": (8,6), "insertcolor": P["gold"],
                    "bordercolor": P["field_bd"], "lightcolor": P["field_bd"], "darkcolor": P["field_bd"]
                }
            },
            "Light.TCombobox": {
                "configure": {
                    "foreground": P["ink"], "fieldbackground": P["field"], "background": P["field"],
                    "arrowcolor": P["ink_muted"], "bordercolor": P["field_bd"], "padding": (8,4)
                }
            },
            "Light.TSpinbox": {
                "configure": {
                    "foreground": P["ink"], "fieldbackground": P["field"], "background": P["field"],
                    "bordercolor": P["field_bd"], "insertcolor": P["gold"], "arrowsize": 12, "padding": (6,2)
                }
            },
            "Light.TCheckbutton": {"configure": {"background": P["card"], "foreground": P["ink"]}},
            "Light.TRadiobutton": {"configure": {"background": P["card"], "foreground": P["ink"]}},

            # Tables / progress / scales on card
            "Light.Treeview": {
                "configure": {
                    "background": P["field"], "fieldbackground": P["field"], "foreground": P["ink"],
                    "rowheight": 26, "bordercolor": P["field_bd"]
                }
            },
            "Treeview.Heading": {  # global heading style (compat)
                "configure": {"background": "#F4F7FD", "foreground": P["ink"], "padding": (8,6), "relief": "flat", "font": semi_font}
            },
            "Horizontal.TProgressbar": {
                "configure": {"background": P["blue"], "troughcolor": "#E7EEF9", "bordercolor": "#E7EEF9"}
            },
            "Horizontal.TScale": {
                "configure": {"troughcolor": "#E7EEF9", "background": "#F1F5FD"}
            },
        }
    )

    # States / hovers
    map_style(st, "TNotebook.Tab", {
        "background": [("selected", P["card"]), ("!selected", P["bg"])],
        "foreground": [("selected", P["ink"]), ("!selected", P["muted_hdr"])]
    })
    map_style(st, "Light.TButton", {
        "background": [("active", P["blue_hi"]), ("pressed", P["blue"])],
        "relief":     [("pressed", "sunken"), ("!pressed", "flat")]
    })
    map_style(st, "Light.Secondary.TButton", {
        "background": [("active", "#EEF2FA"), ("pressed", "#E8EDF7")],
        "bordercolor":[("focus", P["gold"])]
    })

    st.theme_use("aurelia")


# -------- demo --------
def demo(root):
    apply_aurelia(root)
    root.title("Aurelia v3 — Charcoal • Slate • Sapphire (muted) • Gold")
    root.configure(background=P["bg"])
    root.geometry("980x680")
    try:
        root.tk.call("tk", "scaling", 1.2)
    except Exception:
        pass

    header = ttk.Frame(root); header.pack(fill="x", padx=16, pady=(16, 8))
    ttk.Label(header, text="Aurelia", style="Title.TLabel").pack(side="left")
    ttk.Label(header, text=" lighter charcoal canvas with crisp slate panels and gold accents",
              style="Muted.TLabel").pack(side="left", padx=10)

    nb = ttk.Notebook(root); nb.pack(fill="both", expand=True, padx=16, pady=16)

    # Controls
    t_controls = ttk.Frame(nb); nb.add(t_controls, text="Controls")
    left  = ttk.Frame(t_controls, style="Card.TFrame"); left.pack(side="left", fill="both", expand=True, padx=(0,8), pady=8)
    right = ttk.Frame(t_controls, style="Card.TFrame"); right.pack(side="left", fill="both", expand=True, padx=(8,0), pady=8)

    ttk.Label(left, text="Buttons", style="OnCard.Title.TLabel").pack(anchor="w")
    row = ttk.Frame(left, style="Card.TFrame"); row.configure(borderwidth=0, padding=0); row.pack(anchor="w", pady=8)
    ttk.Button(row, text="Primary",  style="Light.TButton").pack(side="left", padx=6, pady=4)
    ttk.Button(row, text="Secondary",style="Light.Secondary.TButton").pack(side="left", padx=6, pady=4)

    ttk.Separator(left).pack(fill="x", pady=10)
    ttk.Label(left, text="Progress & Scale", style="OnCard.TLabel").pack(anchor="w")
    pb = ttk.Progressbar(left, mode="determinate", length=260, style="Horizontal.TProgressbar")
    pb.pack(anchor="w", pady=6); pb.start(12)
    sc = ttk.Scale(left, from_=0, to=100, style="Horizontal.TScale"); sc.pack(anchor="w", pady=4)

    ttk.Label(right, text="Checks & Radios", style="OnCard.Title.TLabel").pack(anchor="w")
    ttk.Checkbutton(right, text="Enable gilded mode", style="Light.TCheckbutton",
                    variable=tk.BooleanVar(value=True)).pack(anchor="w", pady=2)
    ttk.Checkbutton(right, text="Show constellation grid", style="Light.TCheckbutton",
                    variable=tk.BooleanVar(value=False)).pack(anchor="w", pady=2)
    rb = tk.StringVar(value="eagle")
    ttk.Radiobutton(right, text="Eagle motif", value="eagle", variable=rb, style="Light.TRadiobutton").pack(anchor="w", pady=2)
    ttk.Radiobutton(right, text="Starburst motif", value="star", variable=rb, style="Light.TRadiobutton").pack(anchor="w", pady=2)

    # Form
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
    ttk.Button(form, text="Save", style="Light.TButton").grid(row=7, column=1, sticky="e")
    form.columnconfigure(1, weight=1)

    # Data
    t_data = ttk.Frame(nb); nb.add(t_data, text="Data")
    table = ttk.Frame(t_data, style="Card.TFrame"); table.pack(fill="both", expand=True, padx=4, pady=8)
    ttk.Label(table, text="Astral Ledger", style="OnCard.TLabel").pack(anchor="w")
    cols = ("id","artifact","status","owner")
    tv = ttk.Treeview(table, columns=cols, show="headings", height=10, style="Light.Treeview")
    for c, w in zip(cols, (80,220,120,160)):
        tv.heading(c, text=c.title(), anchor="w")  # global heading style
        tv.column(c, width=w, anchor="w")
    tv.pack(fill="both", expand=True, pady=(8,0))
    for row in [(1,"Starmap Disk","Catalogued","E. Figg"),
                (2,"Gilded Astrolabe","Loaned","P. Binns"),
                (3,"Orrery Gear","Restored","M. Hagrid"),
                (4,"Runic Tablet","Quarantined","A. Pince")]:
        tv.insert("", "end", values=row)

    # Palette
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
    for k in ("bg","card","blue","gold"):
        sw(k, P[k]).pack(side="left", padx=8, pady=8)

if __name__ == "__main__":
    root = tk.Tk()
    demo(root)
    root.mainloop()
