#!/usr/bin/env python3
# edit_pill_clean.py — Scopes + seam-free Edit pill (atomic demo)

import tkinter as tk
from tkinter import ttk
import math

# ----- Aurelia palette (your latest) -----
P = {
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
    "primary": "#365DC6",
    "primary_hover": "#587BE2",
    "on_primary": "#F7FAFF",
    "tooltip_bg": "#0E1724",
    "tooltip_fg": "#F7FAFF",
    "scopes": {
        "Env": "#1f9d66",
        "User": "#1e40af",
        "Machine": "#1c6e7d",
        "Project": "#D4B76A",
        "ProjectMachine": "#c25e0c",
        "Def": "#334155",
    },
}

# ---------- tiny helpers ----------
def hex_to_rgb(h): h=h.lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def rgb_to_hex(r,g,b): return "#%02x%02x%02x" % (max(0,min(255,r)),max(0,min(255,g)),max(0,min(255,b)))
def lighten(hex_color, frac=0.18, base="#ffffff"):
    r,g,b = hex_to_rgb(hex_color); R,G,B = hex_to_rgb(base)
    return rgb_to_hex(int(r+(R-r)*frac), int(g+(G-g)*frac), int(b+(B-b)*frac))
def ideal_text_on(bg_hex):
    r,g,b = hex_to_rgb(bg_hex)
    # relative luminance
    y = 0.2126*(r/255)**2.2 + 0.7152*(g/255)**2.2 + 0.0722*(b/255)**2.2
    return "#FFFFFF" if y < 0.55 else P["ink"]

# ---------- minimal Aurelia bits for the demo ----------
def apply_min_aurelia(style: ttk.Style):
    base = "clam"
    try: style.theme_use(base)
    except Exception: base = style.theme_use()

    style.configure("TFrame", background=P["bg"])
    style.configure("Header.TFrame", background=P["bg"])
    style.configure("Header.TLabel", background=P["bg"], foreground=P["hdr_fg"], font=("Segoe UI Semibold", 14))

    # Card container (so pills preview on light slate)
    style.configure("Card.TFrame",
                    background=P["card"], borderwidth=1, relief="solid",
                    bordercolor=P["card_edge"], padding=12)
    style.configure("OnCard.TLabel", background=P["card"], foreground=P["ink"], font=("Segoe UI", 10))
    style.configure("OnCard.Title.TLabel", background=P["card"], foreground=P["ink"], font=("Segoe UI Semibold", 12))
    style.configure("OnCard.Muted.TLabel", background=P["card"], foreground=P["ink_muted"], font=("Segoe UI", 10))

def register_scope_styles(style: ttk.Style):
    for name, base_hex in P["scopes"].items():
        fg = ideal_text_on(base_hex)
        hov = lighten(base_hex, 0.16)
        # filled
        style.configure(f"Scope.{name}.TButton",
                        background=base_hex, foreground=fg,
                        borderwidth=0, padding=(12,4), relief="flat")
        style.map(f"Scope.{name}.TButton",
                  background=[("active", hov), ("pressed", base_hex)])
        # outline
        stroke = lighten(base_hex, 0.45, base=P["card"])
        style.configure(f"Scope.{name}.Outline.TButton",
                        background=P["card"], foreground=base_hex,
                        borderwidth=1, bordercolor=stroke,
                        padding=(10,3), relief="flat")
        style.map(f"Scope.{name}.Outline.TButton",
                  background=[("active", lighten(P["card"], 0.06, base="#ffffff")),
                              ("pressed", P["card"])])

# ---------- seam-free capsule drawing ----------
def capsule_outline_points(x1, y1, x2, y2, r, steps=14):
    """
    Returns a closed path approximating a capsule with radius r using a single
    smooth polyline (top arc → right flank → bottom arc → left flank).
    This is used for the outline (and the gold focus ring).
    """
    # centers of semicircles
    cxL, cy = x1 + r, (y1 + y2) / 2
    cxR = x2 - r

    def arc(cx, cy, radius, start_deg, end_deg, n):
        pts = []
        for i in range(n+1):
            t = math.radians(start_deg + (end_deg - start_deg) * (i/n))
            pts.append((cx + radius * math.cos(t), cy - radius * math.sin(t)))
        return pts

    top = arc(cxL, cy, r, 180, 360, steps//2)           # left top → right top
    right = [(cxR, cy - r), (cxR, cy + r)]              # straight right flank
    bottom = arc(cxR, cy, r,   0, 180, steps//2)        # right bottom → left bottom
    left = [(cxL, cy + r), (cxL, cy - r)]               # straight left flank
    return top + right + bottom + left

class EditPill(tk.Canvas):
    """
    Rounded ghost button rendered with:
      - ONE filled capsule (no outlines)  → no seams
      - ONE smooth outline path           → crisp border
      - ONE smooth gold path on focus     → focus ring
    Keyboard: Tab to focus, Space/Enter to activate.
    """
    def __init__(self, master, text="Edit…", command=None, compact=False, **kw):
        self.h = 28 if not compact else 26
        self.w = 86 if not compact else 70
        super().__init__(master, width=self.w, height=self.h,
                         bg=P["card"], highlightthickness=0, bd=0, **kw)
        self.text = text
        self.command = command
        self.compact = compact

        # colors
        self.stroke = "#D9E2F3"
        self.fill_norm = P["card"]
        self.fill_hover = "#EEF2FA"
        self.fill_press = "#E8EDF7"
        self.text_color = P["ink"]

        # geometry
        self.r = (self.h // 2) - 3
        self.pad = 2

        # items
        self._fill_id = None
        self._outline_id = None
        self._focus_id = None
        self._label_id = None

        self._render(self.fill_norm)
        self._wire_events()
        self.bind("<Configure>", lambda e: self._render(self.fill_norm))

    def _render(self, fill):
        self.delete("all")
        w, h, r = self.winfo_reqwidth(), self.winfo_reqheight(), self.r
        x1, y1 = self.pad, self.pad
        x2, y2 = w - self.pad, h - self.pad

        # 1) Filled capsule → composed of two ovals + center rect, but NO outlines
        self.create_oval(x1, y1, x1 + 2*r, y2, fill=fill, outline="")
        self.create_oval(x2 - 2*r, y1, x2, y2, fill=fill, outline="")
        self.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline="")

        # 2) Single smooth outline path
        pts = capsule_outline_points(x1, y1, x2, y2, r, steps=16)
        flat = [c for xy in pts for c in xy]
        self._outline_id = self.create_line(
            *flat, fill=self.stroke, width=1.0, smooth=True, splinesteps=24
        )

        # 3) Gold focus ring (hidden)
        self._focus_id = self.create_line(
            *flat, fill=P["gold"], width=2.0, smooth=True, splinesteps=24, state="hidden"
        )

        # 4) Label
        self._label_id = self.create_text(
            w//2, h//2, text=self.text, fill=self.text_color, font=("Segoe UI", 10)
        )

    def _wire_events(self):
        self.bind("<Enter>", lambda e: self._set_fill(self.fill_hover))
        self.bind("<Leave>", lambda e: self._set_fill(self.fill_norm))
        self.bind("<ButtonPress-1>", lambda e: self._set_fill(self.fill_press))
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<FocusIn>", lambda e: self.itemconfigure(self._focus_id, state="normal"))
        self.bind("<FocusOut>", lambda e: self.itemconfigure(self._focus_id, state="hidden"))
        self.bind("<space>", lambda e: self._invoke())
        self.bind("<Return>", lambda e: self._invoke())
        self.bind("<Button-1>", lambda e: self.focus_set())
        self.configure(cursor="hand2")

    def _set_fill(self, color):
        # repaint only the fill by re-rendering with same geom
        self._render(color)

    def _on_release(self, e):
        if 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
            self._invoke()
        self._set_fill(self.fill_hover)

    def _invoke(self):
        if callable(self.command):
            self.command()

# ---------- demo UI ----------
def main():
    root = tk.Tk()
    root.title("Scopes + clean Edit pill — Aurelia")
    root.geometry("920x360")
    try: root.tk.call("tk","scaling",1.2)
    except Exception: pass

    style = ttk.Style(root)
    apply_min_aurelia(style)
    register_scope_styles(style)

    hdr = ttk.Frame(root, style="Header.TFrame"); hdr.pack(fill="x", padx=14, pady=(12,8))
    ttk.Label(hdr, text="Scopes preview", style="Header.TLabel").pack(side="left")

    card = ttk.Frame(root, style="Card.TFrame"); card.pack(fill="both", expand=True, padx=14, pady=12)

    # Row 1 — filled + Edit
    ttk.Label(card, text="Has value (filled)", style="OnCard.Muted.TLabel").grid(row=0, column=0, sticky="w", pady=(0,6))
    row1 = ttk.Frame(card, style="Card.TFrame"); row1.configure(borderwidth=0, padding=0)
    row1.grid(row=1, column=0, sticky="w")

    def wrap_pill(parent, text, st, effective=False):
        wrap = tk.Frame(parent, bg=P["card"], bd=0,
                        highlightthickness=(2 if effective else 0),
                        highlightbackground=P["gold"])
        ttk.Button(wrap, text=text, style=st, cursor="hand2").pack()
        return wrap

    pills1 = [
        ("Env",              "Scope.Env.TButton",            False),
        ("Project-Machine",  "Scope.ProjectMachine.TButton", False),
        ("Project",          "Scope.Project.TButton",        True),
        ("Machine",          "Scope.Machine.TButton",        False),
        ("User",             "Scope.User.TButton",           False),
        ("Default",          "Scope.Def.TButton",            False),
    ]
    for i,(label, st, eff) in enumerate(pills1):
        wrap_pill(row1, label, st, eff).grid(row=0, column=i, padx=6, pady=4)

    EditPill(row1, text="Edit…", command=lambda: print("Edit clicked")).grid(
        row=0, column=len(pills1), padx=(12,0), pady=4)

    # Row 2 — outline variants
    ttk.Label(card, text="No value (outline)", style="OnCard.Muted.TLabel").grid(row=2, column=0, sticky="w", pady=(16,6))
    row2 = ttk.Frame(card, style="Card.TFrame"); row2.configure(borderwidth=0, padding=0)
    row2.grid(row=3, column=0, sticky="w")

    for i,(label, st) in enumerate([
        ("Env",              "Scope.Env.Outline.TButton"),
        ("Project-Machine",  "Scope.ProjectMachine.Outline.TButton"),
        ("Project",          "Scope.Project.Outline.TButton"),
        ("Machine",          "Scope.Machine.Outline.TButton"),
        ("User",             "Scope.User.Outline.TButton"),
        ("Default",          "Scope.Def.Outline.TButton"),
    ]):
        ttk.Button(row2, text=label, style=st, cursor="hand2").grid(row=0, column=i, padx=6, pady=4)

    ttk.Label(card, text="Tip: the gold ring marks the effective source. Outline = no value in that scope.",
              style="OnCard.Muted.TLabel").grid(row=4, column=0, sticky="w", pady=(16,0))

    root.mainloop()

if __name__ == "__main__":
    main()
