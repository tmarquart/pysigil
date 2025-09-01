import tkinter as tk
from tkinter import ttk

"""
Self‑contained Tk demo focusing on a **clean semicircle shackle** (upside‑down U) with crisp legs.
No emoji/images; all Canvas vectors. Body kept from last version for context.

- Sizes: 16, 20, 24, 28, 32
- Toggles: Solid body vs Outline body; Light vs Dark
- Shackle uses *paired pieslices* (outer fill, inner bg) so the band is crisp at small sizes.
- All geometry is pixel‑snapped.
"""

PALETTE_LIGHT = {"bg": "#ffffff", "fg": "#111827", "muted": "#6b7280", "accent": "#1e40af"}
PALETTE_DARK  = {"bg": "#0b0f19", "fg": "#e5e7eb", "muted": "#9ca3af", "accent": "#60a5fa"}

SIZES = [16, 20, 24, 28, 32]

# ----------------- helpers -----------------

def px(v):
    return int(round(v))


def round_rect(c, x1, y1, x2, y2, r, **kw):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    x1, y1, x2, y2 = map(px, (x1, y1, x2, y2))
    pts = [
        x1+r, y1,  x2-r, y1,  x2, y1,  x2, y1+r,
        x2, y2-r,  x2, y2,    x2-r, y2,  x1+r, y2,
        x1, y2,    x1, y2-r,  x1, y1+r,  x1, y1
    ]
    return c.create_polygon(pts, smooth=True, **kw)


# ----------------- shackle (semicircle + legs) -----------------

def draw_shackle_semicircle(c, s, *, color, bg, body_top):
    """Draw a crisp semicircle shackle (top arch + two legs) aligned to pixels.
    - outer pieslice forms the arch
    - inner pieslice (bg) hollows it into a band of thickness t
    - legs are rectangles that meet the body cleanly
    """
    # Tune these ratios if you want a thicker/thinner shackle
    r = s * 0.34            # radius of outer semicircle
    t = max(2, px(s * 0.14))# band thickness
    cx = s * 0.50           # center x of the arc
    cy = s * 0.5          # center y of the arc (controls arch height)

    # Outer semicircle (top half)
    c.create_arc(px(cx - r), px(cy - r), px(cx + r), px(cy + r),
                 start=0, extent=180, style=tk.PIESLICE, outline="", fill=color)
    # Inner knock-out to create band
    ri = r - t
    if ri > 0:
        c.create_arc(px(cx - ri), px(cy - ri), px(cx + ri), px(cy + ri),
                     start=0, extent=180, style=tk.PIESLICE, outline="", fill=bg)

    # Legs: align to the arc endpoints at y = cy (bottom of the semicircle)
    leg_w = max(2, px(t * 0.95))
    leg_top_y = px(cy)  # where the semicircle ends
    # Place legs just inside the outer radius so they visually connect to the band
    left_leg_x = cx - r + t*0.55
    right_leg_x = cx + r - t*0.55

    # Left leg
    c.create_rectangle(px(left_leg_x - leg_w/2), leg_top_y, px(left_leg_x + leg_w/2), px(body_top),
                       fill=color, outline="")
    # Right leg
    c.create_rectangle(px(right_leg_x - leg_w/2), leg_top_y, px(right_leg_x + leg_w/2), px(body_top),
                       fill=color, outline="")


# ----------------- body + keyhole (unchanged) -----------------

def draw_keyhole(c, s, *, color, body_top, body_bottom):
    cy = (body_top + body_bottom) / 2
    r  = max(1, px(s*0.08))
    c.create_oval(px(s*0.50 - r), px(cy - r), px(s*0.50 + r), px(cy + r), outline=color, fill=color)
    c.create_rectangle(px(s*0.50 - r*0.33), px(cy + r - 1), px(s*0.50 + r*0.33), px(cy + r + r*1.25), outline=color, fill=color)


def draw_lock(c, size, *, palette, solid=False):
    c.delete("all")
    c.configure(width=size, height=size, highlightthickness=0, bd=0, bg=palette["bg"])
    s = float(size)

    # Body geometry
    body_top    = px(s * 0.50)
    body_bottom = px(s * 0.92)
    body_lr     = px(s * 0.16)
    body_rr     = px(s - s * 0.16)
    radius      = px(s * 0.20)

    # --- Shackle first ---
    draw_shackle_semicircle(c, s, color=palette["fg"], bg=palette["bg"], body_top=body_top)

    # --- Body ---
    if solid:
        round_rect(c, body_lr, body_top, body_rr, body_bottom, radius, fill=palette["accent"], outline="")
        draw_keyhole(c, s, color=palette["bg"], body_top=body_top, body_bottom=body_bottom)
    else:
        round_rect(c, body_lr, body_top, body_rr, body_bottom, radius, fill=palette["bg"], outline=palette["fg"], width=2)
        draw_keyhole(c, s, color=palette["fg"], body_top=body_top, body_bottom=body_bottom)


# ----------------- Demo UI -----------------

class Demo(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.pack(fill='both', expand=True)

        self.dark = tk.BooleanVar(value=False)
        self.solid = tk.BooleanVar(value=False)

        ctrl = ttk.Frame(self); ctrl.pack(fill='x', pady=(0,8))
        ttk.Label(ctrl, text='Lock Icon — Shackle Focus v3').pack(side='left')
        ttk.Checkbutton(ctrl, text='Dark', variable=self.dark, command=self.redraw).pack(side='right')
        ttk.Checkbutton(ctrl, text='Solid', variable=self.solid, command=self.redraw).pack(side='right', padx=(0,12))

        self.row = ttk.Frame(self); self.row.pack(fill='x')
        self.canvases = []
        for sz in SIZES:
            c = tk.Canvas(self.row, width=sz, height=sz, highlightthickness=0, bd=0)
            c.pack(side='left', padx=8, pady=6)
            self.canvases.append((c, sz))

        self.redraw()

    def redraw(self):
        pal = PALETTE_DARK if self.dark.get() else PALETTE_LIGHT
        for c, sz in self.canvases:
            draw_lock(c, sz, palette=pal, solid=self.solid.get())


if __name__ == '__main__':
    root = tk.Tk(); root.title('Lock Icon — Shackle Focus v3')
    try:
        ttk.Style().theme_use('clam')
    except Exception:
        pass
    Demo(root)
    root.geometry('420x160')
    root.minsize(380, 140)
    root.mainloop()
