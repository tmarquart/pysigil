#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Celestia — a lighter ttk theme inspired by vaulted stone, sapphire fabric,
teal inlays, and warm gold trim.

Run this file to preview the theme.
"""

import tkinter as tk
from tkinter import ttk

# ---------- palette (lighter, cleaner) ----------
PALETTE = {
    # base
    "bg":        "#1F2E4A",  # sapphire wall
    "surface":   "#2A3E6A",  # panel / card
    "sunken":    "#23355C",  # troughs
    "raise":     "#375082",  # raised controls
    "line":      "#4461A1",  # outlines / separators

    # text
    "fg":        "#F1F5FF",  # light ink (parchment on blue)
    "muted":     "#C9D4F1",  # secondary text
    "muted2":    "#97A9D7",

    # accents
    "teal":      "#25D0EC",  # teal glass
    "teal_hi":   "#8AEAF8",
    "gold":      "#D7B768",  # warm gilded trim
    "gold_hi":   "#F4DDA3",

    # states
    "danger":    "#E65C61",
    "ok":        "#33D487",
}

def map_style(style, widget, maps):
    for opt, rules in maps.items():
        style.map(widget, **{opt: rules})

def apply_celestia(root):
    style = ttk.Style(root)
    base = "clam"
    try:
        style.theme_use(base)
    except Exception:
        base = style.theme_use()

    base_font = ("Segoe UI", 10)
    semi_font = ("Segoe UI Semibold", 10)
    title_font = ("Segoe UI Semibold", 14)
    mono_font = ("Consolas", 10)

    style.theme_create(
        "celestia",
        parent=base,
        settings={
            # ------- containers -------
            "TFrame": {
                "configure": {"background": PALETTE["bg"], "borderwidth": 0}
            },
            "Card.TFrame": {
                "configure": {
                    "background": PALETTE["surface"],
                    "borderwidth": 1,
                    "relief": "solid",
                    "bordercolor": PALETTE["line"],
                    "padding": 12
                }
            },

            # ------- text -------
            "TLabel": {
                "configure": {
                    "background": PALETTE["bg"],
                    "foreground": PALETTE["fg"],
                    "font": base_font
                }
            },
            "Title.TLabel": {
                "configure": {
                    "background": PALETTE["bg"],
                    "foreground": PALETTE["gold_hi"],
                    "font": title_font
                }
            },
            "Muted.TLabel": {
                "configure": {
                    "background": PALETTE["bg"],
                    "foreground": PALETTE["muted"],
                    "font": base_font
                }
            },
            "Code.TLabel": {
                "configure": {
                    "background": PALETTE["surface"],
                    "foreground": PALETTE["teal_hi"],
                    "font": mono_font,
                    "padding": (8, 6)
                }
            },

            # ------- buttons -------
            "TButton": {
                "configure": {
                    "background": PALETTE["raise"],
                    "foreground": PALETTE["fg"],
                    "padding": (12, 6),
                    "relief": "flat",
                    "borderwidth": 1,
                    "bordercolor": PALETTE["line"],
                    "focuscolor": PALETTE["gold"]
                }
            },
            "Accent.TButton": {
                "configure": {
                    "background": PALETTE["teal"],
                    "foreground": "#04212A",
                    "padding": (14, 7),
                    "borderwidth": 0
                }
            },
            "Destructive.TButton": {
                "configure": {
                    "background": PALETTE["danger"],
                    "foreground": "#2A0D0E",
                    "padding": (14, 7),
                    "borderwidth": 0
                }
            },

            # ------- inputs -------
            "TEntry": {
                "configure": {
                    "foreground": PALETTE["fg"],
                    "fieldbackground": PALETTE["surface"],
                    "background": PALETTE["surface"],
                    "padding": (8, 6),
                    "insertcolor": PALETTE["gold"],
                    "bordercolor": PALETTE["line"],
                    "lightcolor": PALETTE["line"],
                    "darkcolor": PALETTE["line"]
                }
            },
            "TSpinbox": {
                "configure": {
                    "foreground": PALETTE["fg"],
                    "fieldbackground": PALETTE["surface"],
                    "background": PALETTE["surface"],
                    "insertcolor": PALETTE["gold"],
                    "bordercolor": PALETTE["line"],
                    "arrowsize": 12,
                    "padding": (6, 2)
                }
            },
            "TCombobox": {
                "configure": {
                    "foreground": PALETTE["fg"],
                    "fieldbackground": PALETTE["surface"],
                    "background": PALETTE["surface"],
                    "arrowcolor": PALETTE["muted2"],
                    "bordercolor": PALETTE["line"],
                    "padding": (8, 4)
                }
            },

            # ------- selections -------
            "TCheckbutton": {
                "configure": {
                    "background": PALETTE["bg"],
                    "foreground": PALETTE["fg"],
                    "font": base_font,
                    "focuscolor": PALETTE["gold"]
                }
            },
            "TRadiobutton": {
                "configure": {
                    "background": PALETTE["bg"],
                    "foreground": PALETTE["fg"],
                    "font": base_font,
                    "focuscolor": PALETTE["gold"]
                }
            },

            # ------- notebook -------
            "TNotebook": {
                "configure": {
                    "background": PALETTE["bg"],
                    "tabmargins": [6, 6, 6, 0],
                    "borderwidth": 0
                }
            },
            "TNotebook.Tab": {
                "configure": {
                    "background": PALETTE["surface"],
                    "foreground": PALETTE["muted2"],
                    "padding": (14, 8),
                    "font": semi_font
                }
            },

            # ------- treeview -------
            "Treeview": {
                "configure": {
                    "background": PALETTE["surface"],
                    "fieldbackground": PALETTE["surface"],
                    "foreground": PALETTE["fg"],
                    "rowheight": 26,
                    "bordercolor": PALETTE["line"]
                }
            },
            "Treeview.Heading": {
                "configure": {
                    "background": PALETTE["raise"],
                    "foreground": PALETTE["fg"],
                    "padding": (8, 6),
                    "relief": "flat",
                    "font": semi_font
                }
            },

            # ------- misc -------
            "Horizontal.TProgressbar": {
                "configure": {
                    "background": PALETTE["teal"],
                    "troughcolor": PALETTE["sunken"],
                    "bordercolor": PALETTE["sunken"]
                }
            },
            "TScale": {
                "configure": {
                    "troughcolor": PALETTE["sunken"],
                    "background": PALETTE["raise"]
                }
            },
            "TSeparator": {
                "configure": {"background": PALETTE["line"]}
            },
            "TScrollbar": {
                "configure": {
                    "troughcolor": PALETTE["sunken"],
                    "background": PALETTE["raise"],
                    "bordercolor": PALETTE["line"]
                }
            },
        }
    )

    # state maps
    map_style(style, "TButton", {
        "background": [("active", "#3F5A90"), ("pressed", "#2C447A")],
        "foreground": [("disabled", PALETTE["muted2"])],
        "relief":     [("pressed", "sunken"), ("!pressed", "flat")],
        "bordercolor":[("focus", PALETTE["gold"])]
    })
    map_style(style, "Accent.TButton", {
        "background": [("active", PALETTE["teal_hi"]), ("pressed", PALETTE["teal"])],
        "foreground": [("disabled", "#5C8C95")]
    })
    map_style(style, "Destructive.TButton", {
        "background": [("active", "#FF7C82"), ("pressed", PALETTE["danger"])],
        "foreground": [("disabled", "#8B5A5C")]
    })
    map_style(style, "TNotebook.Tab", {
        "background": [("selected", PALETTE["raise"]), ("!selected", PALETTE["surface"])],
        "foreground": [("selected", PALETTE["fg"]), ("!selected", PALETTE["muted2"])]
    })

    style.theme_use("celestia")


# ---------- demo UI ----------
def demo(root):
    apply_celestia(root)
    root.title("Celestia — ttk Theme Preview")
    root.configure(background=PALETTE["bg"])
    root.geometry("980x680")
    try:
        root.tk.call("tk", "scaling", 1.2)
    except Exception:
        pass

    header = ttk.Frame(root)
    header.pack(fill="x", padx=16, pady=(16, 8))
    ttk.Label(header, text="Celestia", style="Title.TLabel").pack(side="left")
    ttk.Label(header, text=" lighter sapphire + teal with gilded accents", style="Muted.TLabel").pack(side="left", padx=12)

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=16, pady=16)

    # Controls
    t_controls = ttk.Frame(nb); nb.add(t_controls, text="Controls")
    left = ttk.Frame(t_controls, style="Card.TFrame"); left.pack(side="left", fill="both", expand=True, padx=(0,8), pady=8)
    right = ttk.Frame(t_controls, style="Card.TFrame"); right.pack(side="left", fill="both", expand=True, padx=(8,0), pady=8)

    ttk.Label(left, text="Buttons").pack(anchor="w")
    row = ttk.Frame(left); row.pack(anchor="w", pady=8)
    ttk.Button(row, text="Default").pack(side="left", padx=6, pady=4)
    ttk.Button(row, text="Accent", style="Accent.TButton").pack(side="left", padx=6, pady=4)
    ttk.Button(row, text="Danger", style="Destructive.TButton").pack(side="left", padx=6, pady=4)

    ttk.Separator(left).pack(fill="x", pady=10)
    ttk.Label(left, text="Progress & Scale").pack(anchor="w")
    pr = ttk.Progressbar(left, mode="determinate", length=260); pr.pack(anchor="w", pady=6); pr.start(12)
    sc = ttk.Scale(left, from_=0, to=100); sc.pack(anchor="w", pady=4)

    ttk.Label(right, text="Checks & Radios").pack(anchor="w")
    ttk.Checkbutton(right, text="Enable celestial mode", variable=tk.BooleanVar(value=True)).pack(anchor="w", pady=2)
    ttk.Checkbutton(right, text="Show constellation grid", variable=tk.BooleanVar(value=False)).pack(anchor="w", pady=2)
    rbv = tk.StringVar(value="eagle")
    ttk.Radiobutton(right, text="Eagle motif", value="eagle", variable=rbv).pack(anchor="w", pady=2)
    ttk.Radiobutton(right, text="Starburst motif", value="star", variable=rbv).pack(anchor="w", pady=2)

    # Form
    t_form = ttk.Frame(nb); nb.add(t_form, text="Form")
    form = ttk.Frame(t_form, style="Card.TFrame"); form.pack(fill="both", expand=True, padx=4, pady=8)
    ttk.Label(form, text="Credentials").grid(row=0, column=0, columnspan=2, sticky="w")
    ttk.Separator(form).grid(row=1, column=0, columnspan=2, sticky="ew", pady=8)

    ttk.Label(form, text="Display name").grid(row=2, column=0, sticky="e", padx=(0,8), pady=6)
    ttk.Entry(form, width=28).grid(row=2, column=1, sticky="w", pady=6)

    ttk.Label(form, text="Role").grid(row=3, column=0, sticky="e", padx=(0,8), pady=6)
    ttk.Combobox(form, width=26, values=["Student","Professor","Archivist","Groundskeeper"]).grid(row=3, column=1, sticky="w", pady=6)

    ttk.Label(form, text="API Token").grid(row=4, column=0, sticky="e", padx=(0,8), pady=6)
    ttk.Entry(form, width=28, show="•").grid(row=4, column=1, sticky="w", pady=6)

    ttk.Label(form, text="Notes").grid(row=5, column=0, sticky="ne", padx=(0,8), pady=6)
    notes = tk.Text(form, height=6, width=40, bg=PALETTE["surface"], fg=PALETTE["fg"],
                    insertbackground=PALETTE["gold"], relief="flat")
    notes.grid(row=5, column=1, sticky="we", pady=6)
    ttk.Separator(form).grid(row=6, column=0, columnspan=2, sticky="ew", pady=10)
    ttk.Button(form, text="Save", style="Accent.TButton").grid(row=7, column=1, sticky="e")
    form.columnconfigure(1, weight=1)

    # Data
    t_data = ttk.Frame(nb); nb.add(t_data, text="Data")
    table = ttk.Frame(t_data, style="Card.TFrame"); table.pack(fill="both", expand=True, padx=4, pady=8)
    ttk.Label(table, text="Astral Ledger").pack(anchor="w")
    cols = ("id","artifact","status","owner")
    tv = ttk.Treeview(table, columns=cols, show="headings", height=10)
    for c, w in zip(cols, (80,220,120,160)):
        tv.heading(c, text=c.title())
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

    def swatch(name, hex_):
        f = ttk.Frame(pal, style="Card.TFrame"); f.configure(borderwidth=0, padding=6)
        box = tk.Frame(f, width=42, height=24, bg=hex_, highlightthickness=1, highlightbackground=PALETTE["line"])
        box.pack(side="left")
        ttk.Label(f, text=f"{name}  {hex_}", style="Muted.TLabel").pack(side="left", padx=8)
        return f

    row1 = ttk.Frame(pal); row1.pack(fill="x")
    for k in ("bg","surface","sunken","raise","line"):
        swatch(k, PALETTE[k]).pack(side="left", padx=8, pady=8)

    row2 = ttk.Frame(pal); row2.pack(fill="x")
    for k in ("fg","muted","muted2","teal","gold"):
        swatch(k, PALETTE[k]).pack(side="left", padx=8, pady=8)

    footer = ttk.Frame(root); footer.pack(fill="x", padx=16, pady=(0,12))
    ttk.Label(footer, text="Try hover, focus, tabs, and inputs. Gold indicates focus.", style="Muted.TLabel").pack(side="left")

if __name__ == "__main__":
    root = tk.Tk()
    demo(root)
    root.mainloop()
