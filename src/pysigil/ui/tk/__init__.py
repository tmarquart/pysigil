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

try:  # pragma: no cover - tkinter availability depends on the env
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore
    ttk = None  # type: ignore

from ..core import EventBus, AppCore
from ..provider_adapter import ProviderAdapter
from ..sections import bucket_by_section, compute_section_order, field_sort_key
from ..aurelia_theme import get_palette, use
from .dialogs import EditDialog
from .rows import FieldRow


class SectionFrame(ttk.Frame):  # pragma: no cover - simple container widget
    """Frame grouping field rows for a single section."""

    def __init__(self, master: tk.Widget, name: str, *, collapsible: bool, collapsed: bool) -> None:
        super().__init__(master)
        self.name = name
        self._collapsible = collapsible
        self._collapsed = collapsed if collapsible else False
        header = ttk.Frame(self)
        header.pack(fill="x")
        if collapsible:
            self._toggle = ttk.Label(header, text="\u25B8" if collapsed else "\u25BE", width=2)
            self._toggle.pack(side="left")
            self._toggle.bind("<Button-1>", lambda e: self.toggle())
        else:
            self._toggle = None
        ttk.Label(header, text=name, style="Title.TLabel").pack(side="left")
        self.container = ttk.Frame(self)
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
    ) -> None:
        if tk is None:  # pragma: no cover - environment without tkinter
            raise RuntimeError("tkinter is required for App")

        self.root = master if master is not None else tk.Tk()
        self.adapter = adapter or ProviderAdapter(author_mode=author_mode)
        self.events = events or EventBus()
        self.author_mode = author_mode
        self.core: AppCore | None = AppCore(author_mode=author_mode) if author_mode else None
        self.compact = True
        self.section_frames: dict[str, SectionFrame] = {}
        self.field_rows: dict[str, FieldRow] = {}
        self._initial_provider = initial_provider
        self._align_pending = False
        self._key_col_width: int | None = None
        self._pill_col_width: int | None = None
        self._eff_col_width: int | None = None
        self._edit_col_width: int | None = None
        self._author_tools: tk.Toplevel | None = None

        use(self.root)
        core_palette = get_palette()
        self.palette = {
            "bg": core_palette["bg"],
            "gold": core_palette["gold"],
            "hdr_fg": core_palette["hdr_fg"],
            "hdr_muted": core_palette["hdr_muted"],
            "card": core_palette["card"],
            "card_edge": core_palette["card_edge"],
            "ink": core_palette["ink"],
            "ink_muted": core_palette["ink_muted"],
            "field": core_palette["field"],
            "field_bd": core_palette["field_bd"],
        }
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
        header.pack(fill="x", padx=12, pady=12)

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
            font=(None, 10, "bold"),
        )
        style.configure("Title.TLabel", font=(None, 10, "bold"))

        self._table = tk.Frame(
            self.root,
            bg=palette["card"],
            highlightthickness=2,
            highlightbackground=palette["card_edge"],
            highlightcolor=palette["card_edge"],
        )
        self._table.pack(fill="both", expand=True, padx=12, pady=12)

        self._header = ttk.Frame(self._table, style="CardFrame.TFrame")
        self._header.pack(fill="x", padx=12, pady=12)
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

        self._rows_container = ttk.Frame(self._table, style="CardFrame.TFrame")
        self._rows_container.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _style_row(self, row: FieldRow) -> None:
        palette = self.palette
        row.configure(bg=palette["card"])
        row.key_frame.configure(style="CardFrame.TFrame")
        row.lbl_key.configure(background=palette["card"], foreground=palette["ink"])
        if row.info_btn:
            row.info_btn.configure(bg=palette["card"], fg=palette["ink_muted"])
        if row.lbl_desc:
            row.lbl_desc.configure(background=palette["card"], foreground=palette["ink_muted"])
        row.lbl_eff.configure(
            bg=palette["field"],
            fg=palette["ink"],
            highlightthickness=1,
            highlightbackground=palette["field_bd"],
            highlightcolor=palette["field_bd"],
            bd=0,
            relief="flat",
        )
        row.pills.configure(style="CardFrame.TFrame")

    def _populate_providers(self) -> None:
        providers = self.adapter.list_providers()
        self._provider_box["values"] = providers
        if providers:
            initial = (
                self._initial_provider
                if self._initial_provider in providers
                else providers[0]
            )
            self._provider_var.set(initial)
            self.on_provider_change()

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
                frame.configure(style="CardFrame.TFrame")
                frame.container.configure(style="CardFrame.TFrame")
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


def launch(initial_provider: str | None = None, *, author_mode: bool = False) -> None:
    """Convenience helper to launch the tkinter UI."""
    app = App(initial_provider=initial_provider, author_mode=author_mode)
    app.root.mainloop()


__all__ = ["App", "launch"]
