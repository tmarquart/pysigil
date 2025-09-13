# demo_aurelia.py
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
import aurelia_theme as aurelia

def main():
    root = tk.Tk()
    root.title("Aurelia — Theme Demo")
    root.geometry("900x620")

    # Apply & use the theme
    aurelia.use(root)

    # Header (dark canvas)
    hdr = ttk.Frame(root)
    hdr.pack(fill="x", padx=16, pady=(16, 8))
    ttk.Label(hdr, text="Aurelia", style="Title.TLabel").pack(side="left")
    ttk.Label(hdr, text="  charcoal canvas • slate cards • sapphire + gold",
              style="Muted.TLabel").pack(side="left", padx=10)

    nb = ttk.Notebook(root); nb.pack(fill="both", expand=True, padx=16, pady=16)

    # --- Controls ---
    tab1 = ttk.Frame(nb); nb.add(tab1, text="Controls")
    left  = ttk.Frame(tab1, style="Card.TFrame"); left.pack(side="left", fill="both", expand=True, padx=(0,8), pady=8)
    right = ttk.Frame(tab1, style="Card.TFrame"); right.pack(side="left", fill="both", expand=True, padx=(8,0), pady=8)

    ttk.Label(left, text="Buttons", style="OnCard.Title.TLabel").pack(anchor="w")
    row = ttk.Frame(left, style="Card.TFrame"); row.configure(borderwidth=0, padding=0); row.pack(anchor="w", pady=8)
    ttk.Button(row, text="Primary",   style="Light.TButton").pack(side="left", padx=6, pady=4)
    ttk.Button(row, text="Secondary", style="Light.Secondary.TButton").pack(side="left", padx=6, pady=4)

    ttk.Separator(left).pack(fill="x", pady=10)
    ttk.Label(left, text="Progress & Scale", style="OnCard.TLabel").pack(anchor="w")
    pb = ttk.Progressbar(left, mode="determinate", length=260, style="Horizontal.TProgressbar")
    pb.pack(anchor="w", pady=6); pb.start(12)
    ttk.Scale(left, from_=0, to=100, style="Horizontal.TScale").pack(anchor="w", pady=4)

    ttk.Label(right, text="Checks & Radios", style="OnCard.Title.TLabel").pack(anchor="w")
    ttk.Checkbutton(right, text="Enable gilded mode", style="Light.TCheckbutton",
                    variable=tk.BooleanVar(value=True)).pack(anchor="w", pady=2)
    ttk.Checkbutton(right, text="Show constellation grid", style="Light.TCheckbutton",
                    variable=tk.BooleanVar(value=False)).pack(anchor="w", pady=2)
    rvar = tk.StringVar(value="eagle")
    ttk.Radiobutton(right, text="Eagle motif", value="eagle", variable=rvar, style="Light.TRadiobutton").pack(anchor="w", pady=2)
    ttk.Radiobutton(right, text="Starburst motif", value="star", variable=rvar, style="Light.TRadiobutton").pack(anchor="w", pady=2)

    # --- Form ---
    tab2 = ttk.Frame(nb); nb.add(tab2, text="Form")
    form = ttk.Frame(tab2, style="Card.TFrame"); form.pack(fill="both", expand=True, padx=8, pady=8)
    ttk.Label(form, text="Credentials", style="OnCard.Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
    ttk.Separator(form).grid(row=1, column=0, columnspan=2, sticky="ew", pady=8)

    ttk.Label(form, text="Display name", style="OnCard.TLabel").grid(row=2, column=0, sticky="e", padx=(0,8), pady=6)
    ttk.Entry(form, width=28, style="Light.TEntry").grid(row=2, column=1, sticky="w")
    ttk.Label(form, text="Role", style="OnCard.TLabel").grid(row=3, column=0, sticky="e", padx=(0,8), pady=6)
    ttk.Combobox(form, width=26, values=["Student","Professor","Archivist","Groundskeeper"],
                 style="Light.TCombobox").grid(row=3, column=1, sticky="w")

    # --- Data ---
    tab3 = ttk.Frame(nb); nb.add(tab3, text="Data")
    table = ttk.Frame(tab3, style="Card.TFrame"); table.pack(fill="both", expand=True, padx=8, pady=8)
    ttk.Label(table, text="Astral Ledger", style="OnCard.TLabel").pack(anchor="w")
    cols = ("id","artifact","status","owner")
    tv = ttk.Treeview(table, columns=cols, show="headings", height=10, style="Light.Treeview")
    for c, w in zip(cols, (80,220,120,160)):
        tv.heading(c, text=c.title(), anchor="w")
        tv.column(c, width=w, anchor="w")
    tv.pack(fill="both", expand=True, pady=(8,0))
    for row in [(1,"Starmap Disk","Catalogued","E. Figg"),
                (2,"Gilded Astrolabe","Loaned","P. Binns"),
                (3,"Orrery Gear","Restored","M. Hagrid"),
                (4,"Runic Tablet","Quarantined","A. Pince")]:
        tv.insert("", "end", values=row)

    # --- Palette peek ---
    tab4 = ttk.Frame(nb); nb.add(tab4, text="Palette")
    pal = ttk.Frame(tab4, style="Card.TFrame"); pal.pack(fill="x", padx=8, pady=8)
    P = aurelia.get_palette()
    def sw(name, hex_):
        f = ttk.Frame(pal, style="Card.TFrame"); f.configure(borderwidth=0, padding=6)
        box = tk.Frame(f, width=42, height=24, bg=hex_, highlightthickness=1, highlightbackground=P["card_edge"])
        box.pack(side="left")
        ttk.Label(f, text=f"{name}  {hex_}", style="OnCard.Muted.TLabel").pack(side="left", padx=8)
        f.pack(side="left", padx=8, pady=8)
    for k in ("bg","card","blue","gold"):
        sw(k, P[k])

    root.mainloop()

if __name__ == "__main__":
    main()
