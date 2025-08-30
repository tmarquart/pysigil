import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont

# --- Visual constants ---
SCOPES = ["User", "Machine", "Project", "ProjectMachine"]
SCOPE_LABEL = {
    "User": "User",
    "Machine": "Machine",
    "Project": "Project",
    "ProjectMachine": "Project · Machine",
}
SCOPE_COLOR = {
    "User": "#1e40af",          # blue
    "Machine": "#065f46",       # green
    "Project": "#6d28d9",       # purple
    "ProjectMachine": "#c2410c" # orange
}
GREY_BG = "#f3f4f6"
GREY_TXT = "#6b7280"
GREY_BORDER = "#e5e7eb"

# --- Minimal in‑memory orchestrator stub (replace with sigil.api.Handle) ---
class ProviderHandleStub:
    def __init__(self, data, policy="all"):
        # data: { key: {scope: value} }
        self.data = data
        self.policy = policy  # 'all' or 'machine-only'

    def fields(self):
        return list(self.data.keys())

    def layers(self, key):
        return {s: self.data.get(key, {}).get(s) for s in SCOPES}

    def effective(self, key):
        lyr = self.layers(key)
        for s in SCOPES:  # precedence: User > Machine > Project > ProjectMachine
            if lyr.get(s) is not None:
                return lyr[s], s
        return None, None

    def can_write(self, scope):
        if self.policy == "machine-only":
            return scope in ("Machine", "ProjectMachine")
        return True

    def set(self, key, scope, value):
        if not self.can_write(scope):
            raise PermissionError(f"Writes not allowed to {scope} for this provider")
        self.data.setdefault(key, {})[scope] = value

    def clear(self, key, scope):
        if not self.can_write(scope):
            raise PermissionError(f"Writes not allowed to {scope} for this provider")
        if key in self.data and scope in self.data[key]:
            del self.data[key][scope]

# --- Hover tooltip (reliable, styled) ---
class HoverTip:
    def __init__(self, widget, text_fn, *, delay=250):
        self.widget = widget
        self.text_fn = text_fn
        self.delay = delay
        self._after = None
        self.tip = None
        widget.bind("<Enter>", self._schedule, add=True)
        widget.bind("<Leave>", self._hide, add=True)

    def _schedule(self, _):
        self._after = self.widget.after(self.delay, self._show)

    def _show(self):
        if self.tip:
            return
        txt = self.text_fn() or ""
        if not txt:
            return
        x = self.widget.winfo_rootx() + 4
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        frm = tk.Frame(self.tip, bg="#111827", bd=0)
        frm.pack()
        lbl = tk.Label(frm, text=txt, bg="#111827", fg="#ffffff", padx=8, pady=6)
        lbl.pack()
        # small rounded effect
        frm.update_idletasks()

    def _hide(self, _):
        if self._after:
            self.widget.after_cancel(self._after)
            self._after = None
        if self.tip:
            self.tip.destroy()
            self.tip = None

# --- Rounded pill button drawn on Canvas (so it looks like the Edit one) ---
class PillButton(tk.Canvas):
    def __init__(self, master, *, text, color, state, value_provider, clickable=True, on_click=None):
        """state: 'effective' | 'present' | 'empty' | 'disabled'"""
        super().__init__(master, height=28, highlightthickness=0, bd=0)
        self.text = text
        self.color = color
        self.state = state
        self.clickable = clickable and state != 'disabled'
        self.on_click = on_click
        self.font = tkfont.Font(size=9, weight="bold")
        self.value_provider = value_provider
        self.pad_x = 14
        self.rad = 14
        self.bind("<Configure>", lambda e: self._draw())
        if self.clickable:
            self.bind("<Button-1>", lambda e: on_click() if on_click else None)
            self.configure(cursor="hand2")
        else:
            self.configure(cursor="arrow")
        HoverTip(self, self._tip_text)
        # initial width
        self._draw(initial=True)

    def _measure_width(self):
        t = self.font.measure(self.text)
        return max(48, t + self.pad_x*2)

    def _draw(self, initial=False):
        w = self._measure_width()
        self.configure(width=w)
        self.delete("all")
        # colors per state
        if self.state == 'effective':
            fill = self.color
            outline = self.color
            fg = "#ffffff"
        elif self.state == 'present':
            fill = "#ffffff"
            outline = self.color
            fg = self.color
        elif self.state == 'disabled':
            fill = GREY_BG
            outline = GREY_BORDER
            fg = GREY_TXT
        else:  # empty
            fill = "#ffffff"
            outline = GREY_BORDER
            fg = GREY_TXT
        r = self.rad
        self._round_rect(1, 1, w-1, 26, r, fill=fill, outline=outline)
        self.create_text(w/2, 14, text=self.text, fill=fg, font=self.font)

    def _round_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [x1+r, y1,  x2-r, y1,  x2, y1,  x2, y1+r,  x2, y2-r,  x2, y2,  x2-r, y2,  x1+r, y2,  x1, y2,  x1, y2-r,  x1, y1+r,  x1, y1]
        return self.create_polygon(pts, smooth=True, **kw)

    def _tip_text(self):
        val = self.value_provider()
        return f"{self.text}: {val if val is not None else '—'}"

# --- Edit dialog (per key) ---
class EditDialog(tk.Toplevel):
    def __init__(self, master, handle: ProviderHandleStub, key: str):
        super().__init__(master)
        self.title(f"Edit — {key}")
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        self.handle = handle
        self.key = key

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text=f"{key}", font=(None, 12, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0,6))
        ttk.Separator(body).grid(row=1, column=0, columnspan=4, sticky="ew", pady=(0,8))

        self.entries = {}
        r = 2
        for scope in SCOPES:
            val = handle.layers(key).get(scope)
            can = handle.can_write(scope)
            ttk.Label(body, text=SCOPE_LABEL[scope]).grid(row=r, column=0, sticky="w", padx=(0,8), pady=4)
            e = ttk.Entry(body)
            e.grid(row=r, column=1, sticky="ew", pady=4)
            if val is not None:
                e.insert(0, str(val))
            if not can:
                e.state(["disabled"])  # read-only if policy forbids write
            self.entries[scope] = e
            # Save / Remove per scope
            btn_save = ttk.Button(body, text="Save", command=lambda s=scope: self._save_scope(s))
            btn_save.grid(row=r, column=2, padx=4)
            btn_rm = ttk.Button(body, text="Remove", command=lambda s=scope: self._remove_scope(s))
            btn_rm.grid(row=r, column=3, padx=4)
            if not can:
                btn_save.state(["disabled"]) ; btn_rm.state(["disabled"])
            r += 1

        body.columnconfigure(1, weight=1)
        ttk.Separator(body).grid(row=r, column=0, columnspan=4, sticky="ew", pady=8)
        r += 1
        ttk.Button(body, text="Close", command=self.destroy).grid(row=r, column=3, sticky="e")

    def _save_scope(self, scope):
        val = self.entries[scope].get()
        try:
            self.handle.set(self.key, scope, val)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
            return
        self.master.event_generate("<<SigilRowChanged>>", when="tail")

    def _remove_scope(self, scope):
        try:
            self.handle.clear(self.key, scope)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
            return
        self.entries[scope].delete(0, "end")
        self.master.event_generate("<<SigilRowChanged>>", when="tail")

# --- FieldRow widget ---
class FieldRow(ttk.Frame):
    def __init__(self, master, handle: ProviderHandleStub, key: str):
        super().__init__(master)
        self.handle = handle
        self.key = key

        # Key
        self.lbl_key = ttk.Label(self, text=key, style="Key.TLabel")
        self.lbl_key.grid(row=0, column=0, sticky="w")

        # Effective (read-only, non-entry look with lock)
        self.var_eff = tk.StringVar(value="—")
        self.lbl_eff = tk.Label(self, textvariable=self.var_eff, bg=GREY_BG, fg="#111", bd=1, relief="solid")
        self.lbl_eff.configure(padx=10, pady=6)
        self.lbl_eff.grid(row=0, column=1, sticky="ew", padx=(8,8))

        # Pills area
        self.pills = ttk.Frame(self)
        self.pills.grid(row=0, column=2, sticky="w")

        # Edit action
        self.btn_edit = ttk.Button(self, text="Edit…", command=self.open_editor)
        self.btn_edit.grid(row=0, column=3, padx=4)

        self.columnconfigure(1, weight=1)

        # Listen for refresh requests
        self.bind("<<SigilRowChanged>>", lambda e: self.refresh(), add=True)
        self.refresh()

    def refresh(self):
        # Effective value
        val, src = self.handle.effective(self.key)
        lock = "🔒 "  # 🔒
        eff_txt = f"{lock}{val if val is not None else '—'}  ({SCOPE_LABEL[src] if src else '—'})"
        self.var_eff.set(eff_txt)

        # Rebuild pills (always render all 4, with state)
        for w in self.pills.winfo_children():
            w.destroy()
        lyr = self.handle.layers(self.key)
        for scope in SCOPES:
            present = lyr.get(scope) is not None
            effective = (src == scope)
            can = self.handle.can_write(scope)
            state = 'disabled' if not can else ('effective' if effective else ('present' if present else 'empty'))
            pill = PillButton(
                self.pills,
                text=SCOPE_LABEL[scope],
                color=SCOPE_COLOR[scope],
                state=state,
                value_provider=lambda s=scope: self.handle.layers(self.key).get(s),
                clickable=can,
                on_click=lambda s=scope: self._open_editor_focus(s)
            )
            pill.pack(side="left", padx=(0,6))

    def _open_editor_focus(self, scope):
        dlg = EditDialog(self.winfo_toplevel(), self.handle, self.key)
        e = dlg.entries.get(scope)
        if e:
            e.focus_set(); e.icursor("end")

    def open_editor(self):
        EditDialog(self.winfo_toplevel(), self.handle, self.key)

# --- Demo app ---
class App(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.pack(fill="both", expand=True)

        # Provider stubs — in real app you would swap in sigil.api.handle(pid)
        self.handle = ProviderHandleStub(
            data={
                "Alpha": {"User": "hello"},
                "Beta": {"User": "3", "Project": "42"},
                "Gamma": {"Machine": "true", "ProjectMachine": "false"},
                "Endpoint": {"Project": "https://api.example", "ProjectMachine": "https://api.local"},
            },
            policy="machine-only"  # try "all" to enable all writes
        )

        # Header (very light — mainly to show intent)
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0,8))
        ttk.Label(header, text="Provider:").pack(side="left")
        ttk.Combobox(header, values=["sigil-dummy", "myapp-core", "user-custom"], state="readonly").pack(side="left", padx=6)
        ttk.Label(header, text="Will write to:").pack(side="left", padx=(16,4))
        ttk.Label(header, text="<resolved path>", foreground=GREY_TXT).pack(side="left")

        # Table header
        head = ttk.Frame(self)
        head.pack(fill="x")
        for i, title in enumerate(["Key", "Value (effective)", "Scopes (hover)", ""]):
            ttk.Label(head, text=title, font=(None, 10, "bold")).grid(row=0, column=i, sticky="w", padx=(0,8))
        head.columnconfigure(1, weight=1)

        # Rows
        self.rows = []
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        for k in self.handle.fields():
            row = FieldRow(body, self.handle, k)
            row.pack(fill="x", pady=6)
            self.rows.append(row)

# --- Styling ---
style = ttk.Style()
try:
    style.theme_use("clam")
except Exception:
    pass
style.configure("Key.TLabel", font=(None, 10, "bold"))

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Sigil — Tk Prototype (Scope Pills)")
    root.geometry("980x500")
    App(root)
    root.mainloop()
