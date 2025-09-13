#!/usr/bin/env python3
# scope_color_tester.py
import tkinter as tk
from tkinter import ttk

CARD_BG = "#EEF3FA"   # Aurelia card
INK     = "#0E1724"   # text on card

OPTIONS = {
    "Env": [
        ("E1 Emerald",   "#1F9D66"),
        ("E2 Verdigris", "#2CB67D"),  # current
        ("E3 Evergreen", "#0F7B5C"),
    ],
    "Machine": [
        ("M1 Jade",       "#2F9E8F"), # current candidate
        ("M2 Deep Teal",  "#1C6E7D"),
        ("M3 Oxford Teal","#157C8C"),
    ],
    "Project·Machine": [
        ("PM1 Copper",      "#B56A2B"),
        ("PM2 Burnt Amber", "#C25E0C"), # current-ish
        ("PM3 Golden Amber","#D8891C"),
    ],
}

def hex_to_rgb(h): h=h.lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def rgb_to_hex(r,g,b): return "#%02x%02x%02x" % (max(0,min(255,r)),max(0,min(255,g)),max(0,min(255,b)))
def mix(h, frac, base="#ffffff"):  # lighten toward base (default white)
    r,g,b = hex_to_rgb(h); R,G,B = hex_to_rgb(base)
    return rgb_to_hex(int(r+(R-r)*frac), int(g+(G-g)*frac), int(b+(B-b)*frac))

def ideal_text(hexcolor):
    # simple luminance check for white vs dark text
    r,g,b = hex_to_rgb(hexcolor)
    y = 0.2126*(r/255)**2.2 + 0.7152*(g/255)**2.2 + 0.0722*(b/255)**2.2
    return "#FFFFFF" if y < 0.5 else "#0E1724"

def make_style(style, key, base_hex):
    fg = ideal_text(base_hex)
    hov = mix(base_hex, 0.18)               # 18% toward white
    style.configure(f"{key}.TButton", background=base_hex, foreground=fg,
                    borderwidth=0, padding=(14,6), relief="flat")
    style.map(f"{key}.TButton", background=[("active", hov), ("pressed", base_hex)])

def copy_to_clipboard(root, text):
    root.clipboard_clear(); root.clipboard_append(text)

def build_row(root, style, parent, title, items):
    row = ttk.Frame(parent, style="Card.TFrame"); row.pack(fill="x", pady=8)
    ttk.Label(row, text=title, style="OnCard.Title.TLabel").grid(row=0, column=0, sticky="w", padx=(0,8))
    pills = ttk.Frame(row, style="Card.TFrame"); pills.grid(row=1, column=0, sticky="w")
    for i,(name,hexv) in enumerate(items):
        key = f"Pill.{title}.{i}"
        make_style(style, key, hexv)
        btn = ttk.Button(pills, text=f"{name}  {hexv}", style=f"{key}.TButton", cursor="hand2")
        btn.grid(row=0, column=i, padx=6, pady=4)
        btn.bind("<Button-1>", lambda e,h=hexv: copy_to_clipboard(root, h))

def main():
    root = tk.Tk()
    root.title("Aurelia — Scope Color Tester")
    root.geometry("760x360")
    try: root.tk.call("tk","scaling",1.2)
    except Exception: pass

    style = ttk.Style(root)
    base = "clam";
    try: style.theme_use(base)
    except Exception: base = style.theme_use()

    # Minimal “card” look so colors are previewed on the right background
    style.configure("TFrame", background="#2B313B")  # charcoal canvas
    style.configure("Card.TFrame", background=CARD_BG, borderwidth=1, relief="solid", bordercolor="#D4DEEE", padding=12)
    style.configure("OnCard.TLabel", background=CARD_BG, foreground=INK, font=("Segoe UI", 10))
    style.configure("OnCard.Title.TLabel", background=CARD_BG, foreground=INK, font=("Segoe UI Semibold", 12))

    wrap = ttk.Frame(root); wrap.pack(fill="both", expand=True, padx=14, pady=14)
    for scope, items in OPTIONS.items():
        build_row(root, style, wrap, scope, items)

    hint = ttk.Label(wrap, text="Tip: click any swatch to copy its hex", style="OnCard.TLabel")
    hint.pack(anchor="w", pady=(8,0))

    root.mainloop()

if __name__ == "__main__":
    main()
