import tkinter as tk
from tkinter import ttk

"""
Parametric, scalable lock icon — draw BIG, then scale down.
- Pure Canvas vectors (no emoji/images). Pixel-snapped.
- Large preview with live SIZE slider (32 → 512 px) and Solid/Outline + Dark/Light.
- Same geometry renders the small preview row (16..32) so what you tweak scales down.
- Focus: **true semicircle shackle** with legs that visually match band thickness.

If we want to nitpick, adjust the three ratios at the top of draw_shackle().
"""

PALETTE_LIGHT = {"bg": "#ffffff", "fg": "#111827", "accent": "#1e40af"}
PALETTE_DARK  = {"bg": "#0b0f19", "fg": "#e5e7eb", "accent": "#60a5fa"}

SMALL_SIZES = [16, 20, 24, 28, 32]

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

# ----------------- geometry -----------------

def draw_shackle(c, s, *, color, bg, body_top):
    """True semicircle band + legs, parameterized and pixel-snapped.
    Ratios chosen for nice shape; tweak r_frac, t_frac, cy_frac if desired.
    """
    r_frac  = 0.25   # outer radius as a fraction of size
    t_frac  = 0.1   # shackle band thickness as fraction of size
    cy_frac = 0.34   # vertical center of semicircle (lower = taller arch)
    overlap = 0.1   # how far legs overlap into arch (as fraction of band thickness)

    r  = s * r_frac
    t  = max(2, s * t_frac)
    cx = s * 0.50
    cy = s * cy_frac

    # Outer + inner semicircle (band)
    c.create_arc(px(cx - r), px(cy - r), px(cx + r), px(cy + r),
                 start=0, extent=180, style=tk.PIESLICE, outline="", fill=color)
    ri = r - t
    if ri > 0:
        c.create_arc(px(cx - ri), px(cy - ri), px(cx + ri), px(cy + ri),
                     start=0, extent=180, style=tk.PIESLICE, outline="", fill=bg)

    # Clip to a U-shape: keep a sliver below center so legs can blend
    clip_y = cy + (t * 0.5)  # keep ~half band thickness below center for continuity
    c.create_rectangle(px(cx - r - 3), px(clip_y), px(cx + r + 3), px(cy + r + 3), fill=bg, outline="")

    # Legs: width matches band thickness, centers at cx ± (r - t/2)
    leg_w = t
    leg_top_y = cy - (t * overlap)  # slight overlap into the arch for seamless join
    left_center_x  = cx - (r - t/2)
    right_center_x = cx + (r - t/2)

    c.create_rectangle(px(left_center_x - leg_w/2),  px(leg_top_y),
                       px(left_center_x + leg_w/2),  px(body_top),
                       fill=color, outline="")
    c.create_rectangle(px(right_center_x - leg_w/2), px(leg_top_y),
                       px(right_center_x + leg_w/2), px(body_top),
                       fill=color, outline="")


def draw_keyhole(c, s, *, color, body_top, body_bottom):
    cy = (body_top + body_bottom) / 2
    r  = max(1, px(s*0.08))
    c.create_oval(px(s*0.50 - r), px(cy - r), px(s*0.50 + r), px(cy + r), outline=color, fill=color)
    c.create_rectangle(px(s*0.50 - r*0.33), px(cy + r - 1), px(s*0.50 + r*0.33), px(cy + r + r*1.25), outline=color, fill=color)


def draw_lock(c, size, *, fg, bg, accent=None, solid=False):
    c.delete("all")
    c.configure(width=size, height=size, highlightthickness=0, bd=0, bg=bg)
    s = float(size)

    # Body geometry
    body_top    = px(s * 0.52)
    body_bottom = px(s * 0.94)
    body_lr     = px(s * 0.18)
    body_rr     = px(s - s * 0.18)
    radius      = px(s * 0.22)

    # Shackle
    draw_shackle(c, s, color=fg, bg=bg, body_top=body_top)

    # Body
    if solid:
        round_rect(c, body_lr, body_top, body_rr, body_bottom, radius, fill=accent or fg, outline="")
        draw_keyhole(c, s, color=bg, body_top=body_top, body_bottom=body_bottom)
    else:
        round_rect(c, body_lr, body_top, body_rr, body_bottom, radius, fill=bg, outline=fg, width=px(max(2, s*0.06)))
        draw_keyhole(c, s, color=fg, body_top=body_top, body_bottom=body_bottom)

# ----------------- Demo UI -----------------

class Demo(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.pack(fill='both', expand=True)

        self.dark  = tk.BooleanVar(value=False)
        self.solid = tk.BooleanVar(value=False)
        self.size  = tk.IntVar(value=256)

        ctrl = ttk.Frame(self); ctrl.pack(fill='x', pady=(0,8))
        ttk.Label(ctrl, text='Lock Icon — Parametric Big Preview v5').pack(side='left')
        ttk.Checkbutton(ctrl, text='Dark',  variable=self.dark,  command=self.redraw).pack(side='right')
        ttk.Checkbutton(ctrl, text='Solid', variable=self.solid, command=self.redraw).pack(side='right', padx=(0,12))

        size_row = ttk.Frame(self); size_row.pack(fill='x', pady=(0,8))
        ttk.Label(size_row, text='Size').pack(side='left')
        sld = ttk.Scale(size_row, from_=32, to=512, orient='horizontal', command=self._on_size)
        sld.set(self.size.get()); sld.pack(side='left', fill='x', expand=True, padx=8)
        self.size_lbl = ttk.Label(size_row, text=f'{self.size.get()}px'); self.size_lbl.pack(side='left')

        self.big = tk.Canvas(self, width=self.size.get(), height=self.size.get(), highlightthickness=0, bd=0)
        self.big.pack(pady=8)

        # Small preview row
        small_row = ttk.Frame(self); small_row.pack(fill='x', pady=(6,0))
        ttk.Label(small_row, text='Small preview:').pack(side='left')
        self.small = []
        for sz in SMALL_SIZES:
            c = tk.Canvas(small_row, width=sz, height=sz, highlightthickness=0, bd=0)
            c.pack(side='left', padx=8)
            self.small.append((c, sz))

        self.redraw()

    def _on_size(self, _):
        self.size.set(int(float(_)))
        self.size_lbl.configure(text=f'{self.size.get()}px')
        self.big.configure(width=self.size.get(), height=self.size.get())
        self.redraw()

    def palette(self):
        return PALETTE_DARK if self.dark.get() else PALETTE_LIGHT

    def redraw(self):
        pal = self.palette()
        draw_lock(self.big, self.size.get(), fg=pal['fg'], bg=pal['bg'], accent=pal['accent'], solid=self.solid.get())
        for c, sz in self.small:
            draw_lock(c, sz, fg=pal['fg'], bg=pal['bg'], accent=pal['accent'], solid=self.solid.get())

if __name__ == '__main__':
    root = tk.Tk(); root.title('Lock Icon — Parametric Big Preview v5')
    try:
        ttk.Style().theme_use('clam')
    except Exception:
        pass
    Demo(root)
    root.geometry('620x760')
    root.minsize(560, 600)
    root.mainloop()
