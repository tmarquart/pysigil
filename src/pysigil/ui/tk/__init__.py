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

from ..provider_adapter import ProviderAdapter
from ..core import EventBus
from .rows import FieldRow
from .dialogs import EditDialog


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
    ) -> None:
        if tk is None:  # pragma: no cover - environment without tkinter
            raise RuntimeError("tkinter is required for App")

        self.root = master if master is not None else tk.Tk()
        self.adapter = adapter or ProviderAdapter()
        self.events = events or EventBus()
        self.compact = True
        self.rows: dict[str, FieldRow] = {}
        self._edit_buttons: dict[str, ttk.Button] = {}
        self._initial_provider = initial_provider
        self._align_pending = False

        self.root.title("pysigil")

        self._build_header()
        self._build_table()
        self._populate_providers()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_header(self) -> None:
        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=6, pady=6)

        ttk.Label(header, text="Provider:").pack(side="left")
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
        ).pack(side="left")

        ttk.Label(header, text="Project:").pack(side="left", padx=(12, 0))
        self._project_var = tk.StringVar(value="")
        self._project_entry = ttk.Entry(
            header, textvariable=self._project_var, state="readonly"
        )
        self._project_entry.pack(side="left", padx=(4, 0), fill="x", expand=True)

    def _build_table(self) -> None:
        self._table = ttk.Frame(self.root)
        self._table.pack(fill="both", expand=True, padx=6, pady=6)

        style = ttk.Style(self.root)
        style.configure("Title.TLabel", font=(None, 10, "bold"), anchor="center")

        ttk.Label(self._table, text="Key", style="Title.TLabel").grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Label(
            self._table, text="Value (effective)", style="Title.TLabel"
        ).grid(row=0, column=1, sticky="ew")
        ttk.Label(self._table, text="Scopes", style="Title.TLabel").grid(
            row=0, column=2, sticky="ew"
        )

        self._table.columnconfigure(1, weight=1)

    def _populate_providers(self) -> None:
        providers = self.adapter.list_providers()
        self._provider_box["values"] = providers
        if providers:
            initial = self._initial_provider if self._initial_provider in providers else providers[0]
            self._provider_var.set(initial)
            self.on_provider_change()

    # ------------------------------------------------------------------
    # Row handling
    # ------------------------------------------------------------------
    def _clear_rows(self) -> None:
        for row in self.rows.values():
            row.destroy()
        for btn in self._edit_buttons.values():
            btn.destroy()
        self.rows.clear()
        self._edit_buttons.clear()

    def _rebuild_rows(self) -> None:
        self._clear_rows()
        for idx, key in enumerate(self.adapter.fields(), start=1):
            row = FieldRow(
                self._table,
                self.adapter,
                key,
                self.on_pill_click,
                compact=self.compact,
            )
            row.grid(row=idx, column=0, columnspan=3, sticky="ew", pady=2)
            btn = ttk.Button(
                self._table,
                text="Edit…",
                command=lambda k=key: self._open_edit_dialog(k),
            )
            btn.grid(row=idx, column=3, sticky="w", padx=4)
            self.rows[key] = row
            self._edit_buttons[key] = btn
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
            except Exception as exc:  # pragma: no cover - defensive
                self.events.emit_error(str(exc))
                return
            self._rebuild_rows()
            try:
                proj_path = self.adapter.target_path("project")
            except Exception:
                proj_path = ""
            self._project_var.set(str(proj_path))

    def on_pill_click(self, key: str, scope: str) -> None:
        self._open_edit_dialog(key, scope)

    def on_edit_save(self, key: str, scope: str, value: object) -> None:
        try:
            self.adapter.set_value(key, scope, value)
        except Exception as exc:  # pragma: no cover - defensive
            self.events.emit_error(str(exc))
            return
        row = self.rows.get(key)
        if row is not None:
            row.refresh()
            self._schedule_align()

    def on_edit_remove(self, key: str, scope: str) -> None:
        try:
            self.adapter.clear_value(key, scope)
        except Exception as exc:  # pragma: no cover - defensive
            self.events.emit_error(str(exc))
            return
        row = self.rows.get(key)
        if row is not None:
            row.refresh()
            self._schedule_align()

    def on_toggle_compact(self) -> None:
        self.compact = bool(self._compact_var.get())
        for row in self.rows.values():
            row.set_compact(self.compact)
        self._align_rows()

    # -- alignment -----------------------------------------------------
    def _schedule_align(self) -> None:
        if getattr(self, "_align_pending", False):
            return
        self._align_pending = True
        self.root.after_idle(self._align_rows)

    def _align_rows(self) -> None:
        self._align_pending = False
        if not self.rows:
            return
        self.root.update_idletasks()
        key_w = max(r.lbl_key.winfo_reqwidth() for r in self.rows.values())
        pills_w = max(r.pills.winfo_reqwidth() for r in self.rows.values())
        for r in self.rows.values():
            r.grid_columnconfigure(0, minsize=key_w)
            r.grid_columnconfigure(2, minsize=pills_w)


def launch(initial_provider: str | None = None) -> None:
    """Convenience helper to launch the tkinter UI."""
    app = App(initial_provider=initial_provider)
    app.root.mainloop()


__all__ = ["App", "launch"]

