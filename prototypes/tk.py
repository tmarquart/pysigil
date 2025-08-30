import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont

# --- Visual constants ---
FILE_SCOPES = ["User", "Machine", "Project", "ProjectMachine"]
ALL_SCOPES = ["Env", *FILE_SCOPES]  # display order for non-compact
SCOPE_LABEL = {
    "Env": "Env",
    "User": "User",
    "Machine": "Machine",
    "Project": "Project",
    "ProjectMachine": "Project · Machine",
    "Def": "Default",  # synthetic (file-only effective)
}
SCOPE_LABEL_SHORT = {
    "Env": "Env",
    "User": "User",
    "Machine": "Machine",
    "Project": "Project",
    "ProjectMachine": "Proj·Mach",
    "Def": "Def",
}
SCOPE_COLOR = {
    "Env": "#15803d",            # green-700
    "User": "#1e40af",          # blue-900
    "Machine": "#065f46",       # emerald-900
    "Project": "#6d28d9",       # violet-700
    "ProjectMachine": "#c2410c",# orange-700
    "Def": "#334155",           # slate-700
}
GREY_BG = "#f3f4f6"
GREY_TXT = "#6b7280"
GREY_BORDER = "#e5e7eb"

# --- Minimal in‑memory orchestrator stub (swap with sigil.api.Handle) ---
class ProviderHandleStub:
    """Stores file-backed scopes separately from Env overlay.
    data: { key: {scope: value} }  # scopes are from FILE_SCOPES
    env:  { key: value }           # overlay (read-only in UI)
    policy: 'all' | 'machine-only'
    """
    def __init__(self, data, env=None, policy="all"):
        self.data = data
        self.env = env or {}
        self.policy = policy

    def fields(self):
        # union of keys across file scopes and env
        keys = set(self.data.keys()) | set(self.env.keys())
        return sorted(keys)

    # --- reads
    def layers(self, key, include_env=True):
        layers = {s: self.data.get(key, {}).get(s) for s in FILE_SCOPES}
        if include_env:
            layers["Env"] = self.env.get(key)
        return layers

    def effective(self, key, include_env=True):
        if include_env and key in self.env:
            return self.env[key], "Env"
        # file precedence: User > Machine > Project > ProjectMachine
        for s in FILE_SCOPES:
            v = self.data.get(key, {}).get(s)
            if v is not None:
                return v, s
        return None, None

    def base_effective(self, key):
        """Effective ignoring Env (used for the synthetic Def pill)."""
        for s in FILE_SCOPES:
            v = self.data.get(key, {}).get(s)
            if v is not None:
                return v, s
        return None, None

    # --- writes
    def can_write(self, scope):
        if scope == "Env":
            return False
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

# --- Hover tooltip ---
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
        self.tip.attributes('-topmost', True)
        self.tip.wm_geometry(f"+{x}+{y}")
        frm = tk.Frame(self.tip, bg="#111827", bd=0)
        frm.pack()
        lbl = tk.Label(frm, text=txt, bg="#111827", fg="#ffffff", padx=8, pady=6)
        lbl.pack()

    def _hide(self, _):
        if self._after:
            self.widget.after_cancel(self._after)
            self._after = None
        if self.tip:
            tip = self.tip
            self.tip = None
            tip.after(120, tip.destroy)

# --- Rounded pill button ---
class PillButton(tk.Canvas):
    def __init__(self, master, *, text, color, state, value_provider, clickable=True, on_click=None, tooltip_title=None):
        """state: 'effective' | 'present' | 'empty' | 'disabled' | 'synthetic'"""
        super().__init__(master, height=28, highlightthickness=0, bd=0)
        self.text = text
        self.tooltip_title = tooltip_title or text
        self.color = color
        self.state = state
        self.clickable = clickable and state not in ('disabled',)
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
        # keyboard support
        self.configure(takefocus=1)
        self.bind('<FocusIn>', lambda e: self._draw())
        self.bind('<FocusOut>', lambda e: self._draw())
        self.bind('<Key-Return>', lambda e: (self.on_click() if self.clickable and self.on_click else None))
        self.bind('<Key-space>',  lambda e: (self.on_click() if self.clickable and self.on_click else None))
        HoverTip(self, self._tip_text)
        self._draw(initial=True)

    def _measure_width(self):
        t = self.font.measure(self.text)
        return max(64, t + self.pad_x*2)

    def _draw(self, initial=False):
        w = self._measure_width()
        self.configure(width=w)
        self.delete("all")
        # colors per state
        if self.state == 'effective':
            fill = self.color; outline = self.color; fg = "#ffffff"; width = 1
        elif self.state == 'present':
            fill = "#ffffff"; outline = self.color; fg = self.color; width = 2
        elif self.state == 'disabled':
            fill = GREY_BG; outline = GREY_BORDER; fg = GREY_TXT; width = 1
        elif self.state == 'synthetic':  # 'Def'
            fill = "#ffffff"; outline = self.color; fg = self.color; width = 1
        else:  # empty
            fill = "#ffffff"; outline = GREY_BORDER; fg = GREY_TXT; width = 1
        r = self.rad
        self._round_rect(1, 1, w-1, 26, r, fill=fill, outline=outline, width=width)
        self.create_text(w/2, 14, text=self.text, fill=fg, font=self.font)
        if self.focus_displayof() is self:
            self.create_rectangle(3, 3, w-3, 24, outline='#111', dash=(2,2))

    def _round_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [x1+r, y1,  x2-r, y1,  x2, y1,  x2, y1+r,  x2, y2-r,  x2, y2,  x2-r, y2,  x1+r, y2,  x1, y2,  x1, y2-r,  x1, y1+r,  x1, y1]
        return self.create_polygon(pts, smooth=True, **kw)

    def _tip_text(self):
        val = self.value_provider()
        return f"{self.tooltip_title}: {val if val is not None else '—'}"

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
        for scope in FILE_SCOPES:  # Env is not editable here
            val = handle.layers(key, include_env=False).get(scope)
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

        # Read-only Env display row (if present)
        env_val = handle.layers(key).get("Env")
        ttk.Separator(body).grid(row=r, column=0, columnspan=4, sticky="ew", pady=(8,4)) ; r += 1
        ttk.Label(body, text="Env (read-only)").grid(row=r, column=0, sticky="w", padx=(0,8), pady=4)
        e_env = ttk.Entry(body, state='readonly')
        e_env.grid(row=r, column=1, sticky='ew', pady=4)
        if env_val is not None:
            e_env.configure(state='normal')
            e_env.insert(0, str(env_val))
            e_env.configure(state='readonly')
        ttk.Button(body, text="Close", command=self.destroy).grid(row=r, column=3, sticky="e")
        body.columnconfigure(1, weight=1)

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
    def __init__(self, master, handle: ProviderHandleStub, key: str, *, compact=True):
        super().__init__(master)
        self.handle = handle
        self.key = key
        self.compact = compact

        # Key
        self.lbl_key = ttk.Label(self, text=key, style="Key.TLabel")
        self.lbl_key.grid(row=0, column=0, sticky="w")

        # Effective (read-only, panel look with lock)
        self.var_eff = tk.StringVar(value="—")
        self.lbl_eff = tk.Label(
            self, textvariable=self.var_eff, bg=GREY_BG, fg="#111",
            bd=1, relief="ridge", padx=10, pady=6
        )
        self.lbl_eff.grid(row=0, column=1, sticky="ew", padx=(8,8))

        # Pills area
        self.pills = ttk.Frame(self)
        self.pills.grid(row=0, column=2, sticky="w")

        # Edit action
        self.btn_edit = ttk.Button(self, text="Edit…", command=self.open_editor)
        self.btn_edit.grid(row=0, column=3, padx=4)

        self.columnconfigure(1, weight=1)
        self.bind("<<SigilRowChanged>>", lambda e: self.refresh(), add=True)
        self.refresh()

    def refresh(self):
        # Effective value
        val_eff, src_eff = self.handle.effective(self.key)
        lock = "\U0001F512 "
        eff_txt = f"{lock}{val_eff if val_eff is not None else '—'}  ({SCOPE_LABEL.get(src_eff, '—')})"
        self.var_eff.set(eff_txt)

        # Build pills (compact: only active + synthetic Def)
        for w in self.pills.winfo_children():
            w.destroy()

        layers_with_env = self.handle.layers(self.key, include_env=True)
        layers_no_env = self.handle.layers(self.key, include_env=False)
        base_val, base_src = self.handle.base_effective(self.key)

        def add_pill(scope, state, tooltip_title=None):
            color = SCOPE_COLOR[scope]
            label = SCOPE_LABEL_SHORT[scope]
            can = self.handle.can_write(scope) if scope in FILE_SCOPES else False
            pill = PillButton(
                self.pills,
                text=label,
                color=color,
                state=state,
                value_provider=lambda s=scope: (layers_with_env if s=="Env" else layers_no_env).get(s) if s!="Def" else base_val,
                clickable=can or (scope=="Def" and base_src is not None),
                on_click=(lambda s=scope: self._open_target_for_def(base_src) if s=="Def" else self._open_editor_focus(s)),
                tooltip_title=tooltip_title or SCOPE_LABEL[scope],
            )
            pill.pack(side="left", padx=(0,6))

        # Decide which scopes to show
        if self.compact:
            # Show Env (if present), the file scope that wins, any other file scopes that have values, and the synthetic Def
            if layers_with_env.get("Env") is not None:
                add_pill("Env", 'effective' if src_eff=="Env" else 'present')
            shown_file_scopes = [s for s,v in layers_no_env.items() if v is not None]
            for s in FILE_SCOPES:
                if s in shown_file_scopes:
                    state = 'effective' if (src_eff==s) else 'present'
                    add_pill(s, state)
            if base_val is not None:
                # Synthetic Def: means "file-only" effective
                add_pill("Def", 'synthetic', tooltip_title="File layers (effective)")
        else:
            # Non-compact: show all scopes including Env and a Def pill at end
            for s in ["Env", *FILE_SCOPES]:
                present = layers_with_env.get(s) if s=="Env" else layers_no_env.get(s)
                if s=="Env":
                    st = 'effective' if src_eff=="Env" else ('present' if present is not None else 'empty')
                else:
                    st = 'effective' if src_eff==s else ('present' if present is not None else 'empty')
                add_pill(s, st)
            add_pill("Def", 'synthetic', tooltip_title="File layers (effective)")

    def _open_target_for_def(self, base_src):
        if base_src is None:
            return
        # Open editor focused on the underlying winning file scope
        self._open_editor_focus(base_src)

    def _open_editor_focus(self, scope):
        if scope == "Env":
            return  # read-only
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

        # Provider stub with ENV overlay
        self.handle = ProviderHandleStub(
            data={
                "Alpha": {"User": "hello"},
                "Beta": {"User": "3", "Project": "42"},
                "Gamma": {"Machine": "true", "ProjectMachine": "false"},
                "Endpoint": {"Project": "https://api.example", "ProjectMachine": "https://api.local"},
                "Timeout": {"User": "5"},
            },
            env={
                "Beta": "99",                # ENV overrides Beta
                "Endpoint": "https://env.example",  # ENV overrides Endpoint
            },
            policy="machine-only"  # try "all" to enable all writes
        )

        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0,8))
        ttk.Label(header, text="Provider:").pack(side="left")
        ttk.Combobox(header, values=["sigil-dummy", "myapp-core", "user-custom"], state="readonly").pack(side="left", padx=6)
        ttk.Label(header, text="Will write to:").pack(side="left", padx=(16,4))
        ttk.Label(header, text="<resolved path>", foreground=GREY_TXT).pack(side="left")

        # Compact toggle
        self.compact_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(header, text="Compact (active scopes)", variable=self.compact_var, command=self._rebuild_rows).pack(side="right")

        # Table header
        head = ttk.Frame(self)
        head.pack(fill="x")
        for i, title in enumerate(["Key", "Value (effective)", "Scopes", ""]):
            ttk.Label(head, text=title, font=(None, 10, "bold")).grid(row=0, column=i, sticky="w", padx=(0,8))
        head.columnconfigure(1, weight=1)

        # Rows
        self.rows_container = ttk.Frame(self)
        self.rows_container.pack(fill="both", expand=True)
        self.rows = []
        self._rebuild_rows()

    def _rebuild_rows(self):
        for w in self.rows_container.winfo_children():
            w.destroy()
        self.rows = []
        for k in self.handle.fields():
            row = FieldRow(self.rows_container, self.handle, k, compact=self.compact_var.get())
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
    root.title("Sigil — Tk Prototype (Dynamic + Env)")
    root.geometry("1040x560")
    App(root)
    root.mainloop()
