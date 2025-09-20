"""Tk based view helpers for :mod:`pysigil`.

This module exposes a tiny :class:`App` class that wires
the :class:`~pysigil.ui.provider_adapter.ProviderAdapter` with a
minimal tkinter user interface.  It is intentionally small and aims to
offer just enough features for manual exploration and for unit tests
exercising the view layer.  The implementation favours simplicity so it
can later be adapted for other widget toolkits.  To make this possible a
lightweight :class:`~pysigil.ui.core.EventBus` instance is used which can
be shared with other UI layers in the future.
"""

from __future__ import annotations

from importlib import resources
import webbrowser

try:  # pragma: no cover - tkinter availability depends on the env
    import tkinter as tk
    from tkinter import messagebox, ttk
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore
    ttk = None  # type: ignore
    messagebox = None  # type: ignore

from ..core import EventBus, AppCore
from ..provider_adapter import ProviderAdapter
from ..sections import bucket_by_section, compute_section_order, field_sort_key
from ..aurelia_theme import get_palette, use
from ..state import load_last_provider, save_last_provider
from .dialogs import EditDialog
from .rows import FieldRow


class SectionFrame(ttk.Frame):  # pragma: no cover - simple container widget
    """Frame grouping field rows for a single section."""

    def __init__(self, master: tk.Widget, name: str, *, collapsible: bool, collapsed: bool) -> None:
        super().__init__(master, style="CardSection.TFrame")
        self.name = name
        self._collapsible = collapsible
        self._collapsed = collapsed if collapsible else False
        header = ttk.Frame(self, style="SectionHeader.TFrame")
        header.pack(fill="x", padx=(0, 0))
        if collapsible:
            self._toggle = ttk.Label(
                header,
                text="\u25B8" if collapsed else "\u25BE",
                width=2,
                style="SectionHeaderToggle.TLabel",
            )
            self._toggle.pack(side="left")
            self._toggle.bind("<Button-1>", lambda e: self.toggle())
        else:
            self._toggle = None
        ttk.Label(
            header, text=name, style="SectionHeader.TLabel", padding=6
        ).pack(side="left")
        self.container = ttk.Frame(self, style="CardSection.TFrame")
        if not self._collapsed:
            self.container.pack(fill="x")

    def toggle(self) -> None:
        if not self._collapsible:
            return
        self._collapsed = not self._collapsed
        if self._toggle is not None:
            self._toggle.configure(text="\u25B8" if self._collapsed else "\u25BE")
        if self._collapsed:
            self.container.pack_forget()
        else:
            self.container.pack(fill="x")

    def set_visible(self, visible: bool) -> None:
        if visible:
            if not self.winfo_ismapped():
                self.pack(fill="x", anchor="w", pady=(6, 0))
        else:
            if self.winfo_ismapped():
                self.pack_forget()


class App:
    """Very small tkinter application shell.

    The class is primarily intended for tests and manual smoke checks.  It
    showcases how :class:`ProviderAdapter` can be bound to a view layer and
    how individual field rows are refreshed when values change.
    """

    def __init__(
        self,
        master: tk.Misc | None = None,
        *,
        adapter: ProviderAdapter | None = None,
        events: EventBus | None = None,
        initial_provider: str | None = None,
        author_mode: bool = False,
        remember: bool = True,
    ) -> None:
        if tk is None:  # pragma: no cover - environment without tkinter
            raise RuntimeError("tkinter is required for App")

        owns_root = master is None
        self.root = master if master is not None else tk.Tk()
        self.adapter = adapter or ProviderAdapter(author_mode=author_mode)
        self.events = events or EventBus()
        self.author_mode = author_mode
        self.core: AppCore | None = AppCore(author_mode=author_mode) if author_mode else None
        self.compact = True
        self.section_frames: dict[str, SectionFrame] = {}
        self.field_rows: dict[str, FieldRow] = {}
        self._initial_provider = initial_provider
        self._remember = remember
        self._align_pending = False
        self._key_col_width: int | None = None
        self._pill_col_width: int | None = None
        self._eff_col_width: int | None = None
        self._edit_col_width: int | None = None
        self._author_tools: tk.Toplevel | None = None
        self._rows_canvas: tk.Canvas | None = None
        self._rows_scrollbar: ttk.Scrollbar | None = None
        self._rows_window: int | None = None
        self._mousewheel_bound = False

        if owns_root:
            self.root.geometry("800x600")
            self.root.minsize(600, 400)

        use(self.root)
        self.palette = get_palette()
        self.root.title("pysigil")
        self.root.configure(bg=self.palette["bg"])
        self.root.option_add("*highlightcolor", self.palette["gold"])
        self.root.option_add("*highlightbackground", self.palette["bg"])
        self.root.option_add("*highlightthickness", 1)

        self._build_header()
        self._build_table()
        self._populate_providers()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_header(self) -> None:
        palette = self.palette
        style = ttk.Style(self.root)
        style.configure("AppHeader.TFrame", background=palette["bg"])
        style.configure("AppHeader.TLabel", background=palette["bg"], foreground=palette["hdr_fg"])
        style.configure(
            "AppHeader.TCheckbutton", background=palette["bg"], foreground=palette["hdr_muted"]
        )

        header = ttk.Frame(self.root, style="AppHeader.TFrame")
        header.pack(fill="x", padx=18, pady=12)

        ttk.Label(header, text="Provider:", style="AppHeader.TLabel").pack(side="left")
        self._provider_var = tk.StringVar()
        self._provider_box = ttk.Combobox(
            header, textvariable=self._provider_var, state="readonly"
        )
        self._provider_box.pack(side="left", padx=(4, 12))
        self._provider_box.bind("<<ComboboxSelected>>", self.on_provider_change)

        self._compact_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            header,
            text="Compact",
            variable=self._compact_var,
            command=self.on_toggle_compact,
            style="AppHeader.TCheckbutton",
        ).pack(side="left")

        ttk.Label(header, text="Project:", style="AppHeader.TLabel").pack(
            side="left", padx=(12, 0)
        )
        self._project_var = tk.StringVar(value="")
        self._project_entry = ttk.Entry(
            header, textvariable=self._project_var, state="readonly"
        )
        self._project_entry.pack(side="left", padx=(4, 0), fill="x", expand=True)
        ttk.Button(
            header,
            text="Quick Reference",
            command=self._open_quick_reference,
        ).pack(side="right", padx=(8, 0))
        if self.author_mode:
            ttk.Button(
                header, text="Author Tools…", command=self._open_author_tools
            ).pack(side="right")

    def _build_table(self) -> None:
        palette = self.palette
        style = ttk.Style(self.root)
        style.configure("CardFrame.TFrame", background=palette["card"])
        style.configure(
            "CardHeader.TLabel",
            background=palette["card"],
            foreground=palette["ink"],
            font=(None, 12, "bold"),
        )

        #style.configure("Title.TLabel", font=(None,12,'bold'),foreground=palette['title_accent']) # foreground=palette['gold'] #set color for mid labels here
        style.configure("Title.TLabel", font=(None, 11,"bold"))

        self._table = tk.Frame(
            self.root,
            bg=palette["card"],
            highlightthickness=0, # this controls the border for the table
            highlightbackground=palette["card_edge"],
            highlightcolor=palette["card_edge"],
        )
        self._table.pack(fill="both", expand=True, padx=18, pady=(6, 18))  # padding for main table
        self._table.columnconfigure(0, weight=1)
        self._table.columnconfigure(1, weight=0)
        self._table.rowconfigure(1, weight=1)

        self._header = ttk.Frame(self._table, style="CardFrame.TFrame")
        self._header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=6)
        self._hdr_key = ttk.Label(
            self._header, text="Key", style="CardHeader.TLabel", anchor="center"
        )
        self._hdr_key.grid(row=0, column=0, sticky="ew")
        self._hdr_eff = ttk.Label(
            self._header, text="Value (effective)", style="CardHeader.TLabel", anchor="center"
        )
        self._hdr_eff.grid(row=0, column=1, sticky="ew")
        self._hdr_scopes = ttk.Label(
            self._header, text="Scopes", style="CardHeader.TLabel", anchor="center"
        )
        self._hdr_scopes.grid(row=0, column=2, sticky="ew")
        self._hdr_edit = ttk.Label(self._header, text="", style="CardHeader.TLabel")
        self._hdr_edit.grid(row=0, column=3, sticky="ew")
        self._header.columnconfigure(1, weight=1)

        try:
            style.configure(
                "Card.Vertical.TScrollbar",
                background=palette["card_edge"],
                troughcolor=palette["card"],
                bordercolor=palette["card"],
                arrowcolor=palette["ink"],
            )
        except tk.TclError:
            style.configure(
                "Card.Vertical.TScrollbar",
                background=palette["card_edge"],
                troughcolor=palette["card"],
            )
        try:
            style.map(
                "Card.Vertical.TScrollbar",
                background=[("active", palette["ink_muted"])],
                arrowcolor=[("active", palette["card"])],
            )
        except tk.TclError:
            pass

        self._rows_canvas = tk.Canvas(
            self._table,
            bg=palette["card"],
            highlightthickness=0,
            bd=0,
        )
        self._rows_canvas.grid(row=1, column=0, sticky="nsew", padx=(12, 0), pady=(0, 0))
        self._rows_scrollbar = ttk.Scrollbar(
            self._table,
            orient="vertical",
            command=self._rows_canvas.yview,
            style="Card.Vertical.TScrollbar",
        )
        self._rows_scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 12), pady=(0, 0))
        self._rows_canvas.configure(yscrollcommand=self._rows_scrollbar.set)

        self._rows_container = ttk.Frame(self._rows_canvas, style="CardFrame.TFrame")
        self._rows_window = self._rows_canvas.create_window(
            (0, 0),
            window=self._rows_container,
            anchor="nw",
        )
        self._rows_container.bind("<Configure>", self._on_rows_container_configure)
        self._rows_container.bind("<Enter>", self._on_rows_mouse_enter)
        self._rows_container.bind("<Leave>", self._on_rows_mouse_leave)
        self._rows_canvas.bind("<Configure>", self._on_rows_canvas_configure)
        self._rows_canvas.bind("<Enter>", self._on_rows_mouse_enter)
        self._rows_canvas.bind("<Leave>", self._on_rows_mouse_leave)

    def _update_rows_scrollregion(self) -> None:
        if not self._rows_canvas:
            return
        bbox = self._rows_canvas.bbox("all")
        if bbox is None:
            bbox = (0, 0, 0, 0)
        self._rows_canvas.configure(scrollregion=bbox)

    def _on_rows_container_configure(self, _event: tk.Event) -> None:
        self._update_rows_scrollregion()

    def _on_rows_canvas_configure(self, event: tk.Event) -> None:
        if not self._rows_canvas or self._rows_window is None:
            return
        self._rows_canvas.itemconfigure(self._rows_window, width=event.width)
        self._update_rows_scrollregion()

    def _on_rows_mouse_enter(self, _event: tk.Event) -> None:
        self._bind_rows_mousewheel()

    def _on_rows_mouse_leave(self, event: tk.Event) -> None:
        if not self._rows_canvas:
            return
        dest_widget = self._rows_canvas.winfo_containing(event.x_root, event.y_root)
        widget = dest_widget
        while widget is not None:
            if widget is self._rows_canvas:
                return
            widget = getattr(widget, "master", None)
        self._unbind_rows_mousewheel()

    def _bind_rows_mousewheel(self) -> None:
        if not self._rows_canvas or self._mousewheel_bound:
            return
        self._rows_canvas.bind_all("<MouseWheel>", self._on_rows_mousewheel)
        self._rows_canvas.bind_all("<Button-4>", self._on_rows_mousewheel)
        self._rows_canvas.bind_all("<Button-5>", self._on_rows_mousewheel)
        self._mousewheel_bound = True

    def _unbind_rows_mousewheel(self) -> None:
        if not self._rows_canvas or not self._mousewheel_bound:
            return
        self._rows_canvas.unbind_all("<MouseWheel>")
        self._rows_canvas.unbind_all("<Button-4>")
        self._rows_canvas.unbind_all("<Button-5>")
        self._mousewheel_bound = False

    def _on_rows_mousewheel(self, event: tk.Event) -> str | None:
        if not self._rows_canvas:
            return None
        delta = getattr(event, "delta", 0)
        if delta:
            if abs(delta) >= 120:
                step = -int(delta / 120)
            else:
                step = -1 if delta > 0 else 1
            self._rows_canvas.yview_scroll(step, "units")
        else:
            num = getattr(event, "num", None)
            if num == 4:
                self._rows_canvas.yview_scroll(-1, "units")
            elif num == 5:
                self._rows_canvas.yview_scroll(1, "units")
        return "break"

    def _style_row(self, row: FieldRow) -> None:
        palette = self.palette
        row.configure(bg=palette["card"], highlightthickness=0)
        row.key_frame.configure(style="CardBody.TFrame")
        row.lbl_key.configure(style="CardKey.TLabel")
        if row.info_btn:
            row.info_btn.configure(bg=palette["card"], fg=palette["ink_muted"])
        if row.lbl_desc:
            row.lbl_desc.configure(style="CardMuted.TLabel")
        row.lbl_eff.configure(
            bg=palette["field"],
            fg=palette["ink"],
            highlightthickness=1,
            highlightbackground=palette["field_bd"],
            highlightcolor=palette["field_bd"],
            bd=0,
            relief="flat",
        )
        row.pills.configure(style="CardBody.TFrame")

    def _populate_providers(self) -> None:
        providers = self.adapter.list_providers()
        self._provider_box["values"] = providers
        if providers:
            initial: str | None = None
            if self._initial_provider and self._initial_provider in providers:
                initial = self._initial_provider
            elif self._remember:
                remembered = load_last_provider()
                if remembered in providers:
                    initial = remembered
            if initial is None:
                initial = providers[0]
            self._provider_var.set(initial)
            self.on_provider_change()

    def _open_quick_reference(self) -> None:  # pragma: no cover - GUI interactions
        if tk is None:
            return
        try:
            ref = resources.files("pysigil.ui").joinpath("static", "pysigil_ui_quick_reference.html")
            with resources.as_file(ref) as path:
                opened = webbrowser.open_new_tab(path.as_uri())
            if not opened:
                raise RuntimeError("browser refused to launch quick reference")
        except Exception:
            if messagebox is None:
                return
            try:
                messagebox.showerror(
                    "pysigil",
                    "Unable to open the quick reference guide.",
                    parent=self.root,
                )
            except Exception:
                pass

    def _open_author_tools(self) -> None:  # pragma: no cover - GUI interactions
        if not (self.author_mode and self.core):
            raise RuntimeError("author tools require author mode")
        if self._author_tools is not None and bool(self._author_tools.winfo_exists()):
            try:
                self._author_tools.lift()
            except Exception:
                pass
            return
        from .author_tools import AuthorTools

        self._author_tools = AuthorTools(self.root, self.core)
        def _on_close() -> None:
            if self._author_tools is not None:
                try:
                    self._author_tools.destroy()
                finally:
                    self._author_tools = None
        self._author_tools.protocol("WM_DELETE_WINDOW", _on_close)

    # ------------------------------------------------------------------
    # Row handling
    # ------------------------------------------------------------------
    def _rebuild_rows(self) -> None:
        fields = self.adapter.list_fields()
        sec_order = compute_section_order(fields, self.adapter.provider_sections_order())
        groups = bucket_by_section(fields)
        collapsed = {s.casefold() for s in self.adapter.provider_sections_collapsed() or []}

        used_rows: set[str] = set()
        used_sections: set[str] = set()
        for sec in sec_order:
            frame = self.section_frames.get(sec)
            if frame is None:
                frame = SectionFrame(
                    self._rows_container,
                    sec,
                    collapsible=sec.casefold() in collapsed,
                    collapsed=sec.casefold() in collapsed,
                )
                self.section_frames[sec] = frame
            rows = sorted(groups.get(sec, []), key=field_sort_key)
            for info in rows:
                row = self.field_rows.get(info.key)
                if row is None or row.master is not frame.container:
                    if row is not None:
                        row.destroy()
                    row = FieldRow(
                        frame.container,
                        self.adapter,
                        info.key,
                        self.on_pill_click,
                        compact=self.compact,
                        on_edit_click=self._open_edit_dialog,
                    )
                    self.field_rows[info.key] = row
                else:
                    row.set_compact(self.compact)
                    row._on_edit_click = self._open_edit_dialog
                if hasattr(row, "update_metadata"):
                    try:
                        row.update_metadata(info)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                self._style_row(row)
                row.pack(fill="x", pady=2)
                used_rows.add(info.key)
            frame.set_visible(bool(rows))
            used_sections.add(sec)

        # remove unused rows and hide unused sections
        for key, row in list(self.field_rows.items()):
            if key not in used_rows:
                row.destroy()
                del self.field_rows[key]
        for name, frame in list(self.section_frames.items()):
            if name not in used_sections:
                frame.destroy()
                del self.section_frames[name]

        self._key_col_width = None
        self._pill_col_width = None
        self._schedule_align()
        self._update_rows_scrollregion()

    def _open_edit_dialog(self, key: str, scope: str | None = None) -> None:
        dlg = EditDialog(
            self.root,
            self.adapter,
            key,
            on_edit_save=self.on_edit_save,
            on_edit_remove=self.on_edit_remove,
        )
        if scope:
            entry = dlg.entries.get(scope)
            if entry is not None:
                try:  # pragma: no cover - focus issues are environment specific
                    entry.focus_set()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def on_provider_change(self, _event: object | None = None) -> None:
        pid = self._provider_var.get()
        if pid:
            try:
                self.adapter.set_provider(pid)
                if self.core is not None:
                    self.core.select_provider(pid).result()
            except Exception as exc:  # pragma: no cover - defensive
                self.events.emit_error(str(exc))
                return
            if self._remember:
                save_last_provider(pid)
            self._rebuild_rows()
            try:
                proj_path = self.adapter.target_path("project")
            except Exception:
                proj_path = ""
            #self._project_var.set(proj_path.as_posix())
            self._project_var.set(str(proj_path))

    def on_pill_click(self, key: str, scope: str) -> None:
        self._open_edit_dialog(key, scope)

    def on_edit_save(self, key: str, scope: str, value: object) -> None:
        try:
            self.adapter.set_value(key, scope, value)
        except Exception as exc:  # pragma: no cover - defensive
            self.events.emit_error(str(exc))
            raise
        row = self.field_rows.get(key)
        if row is not None:
            row.refresh()
            self._schedule_align()

    def on_edit_remove(self, key: str, scope: str) -> None:
        try:
            self.adapter.clear_value(key, scope)
        except Exception as exc:  # pragma: no cover - defensive
            self.events.emit_error(str(exc))
            return
        row = self.field_rows.get(key)
        if row is not None:
            row.refresh()
            self._schedule_align()

    def on_toggle_compact(self) -> None:
        self.compact = bool(self._compact_var.get())
        self._rebuild_rows()

    # -- alignment -----------------------------------------------------
    def _schedule_align(self) -> None:
        if getattr(self, "_align_pending", False):
            return
        self._align_pending = True
        self.root.after_idle(self._align_rows)

    def _align_rows(self) -> None:
        self._align_pending = False
        if not self.field_rows:
            return
        self.root.update_idletasks()
        key_w = max(
            self._hdr_key.winfo_reqwidth(),
            *(r.key_frame.winfo_reqwidth() for r in self.field_rows.values()),
        )
        pills_w = max(
            self._hdr_scopes.winfo_reqwidth(),
            *(r.pills.winfo_reqwidth() for r in self.field_rows.values()),
        )
        eff_w = max(
            self._hdr_eff.winfo_reqwidth(),
            *(r.lbl_eff.winfo_reqwidth() for r in self.field_rows.values()),
        )
        edit_w = max(r.btn_edit.winfo_reqwidth() for r in self.field_rows.values())
        if key_w != self._key_col_width:
            self._header.grid_columnconfigure(0, minsize=key_w)
            for r in self.field_rows.values():
                r.grid_columnconfigure(0, minsize=key_w)
            self._key_col_width = key_w
        if pills_w != self._pill_col_width:
            self._header.grid_columnconfigure(2, minsize=pills_w)
            for r in self.field_rows.values():
                r.grid_columnconfigure(2, minsize=pills_w)
            self._pill_col_width = pills_w
        if eff_w != self._eff_col_width:
            self._header.grid_columnconfigure(1, minsize=eff_w)
            for r in self.field_rows.values():
                r.grid_columnconfigure(1, minsize=eff_w)
            self._eff_col_width = eff_w
        if edit_w != self._edit_col_width:
            self._header.grid_columnconfigure(3, minsize=edit_w)
            for r in self.field_rows.values():
                r.grid_columnconfigure(3, minsize=edit_w)
            self._edit_col_width = edit_w


def launch(
    initial_provider: str | None = None,
    *,
    author_mode: bool = False,
    remember: bool = True,
) -> None:
    """Convenience helper to launch the tkinter UI."""
    app = App(
        initial_provider=initial_provider,
        author_mode=author_mode,
        remember=remember,
    )
    app.root.mainloop()


__all__ = ["App", "launch"]
