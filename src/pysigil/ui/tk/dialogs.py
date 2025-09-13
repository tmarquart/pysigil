"""Dialog windows used by :mod:`pysigil.ui.tk`."""

from __future__ import annotations

from collections.abc import Callable

try:  # pragma: no cover - importing tkinter is environment dependent
    import tkinter as tk
    from tkinter import messagebox, ttk
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore
    messagebox = None  # type: ignore
    ttk = None  # type: ignore

from ..aurelia_theme import SCOPE_COLORS, get_palette
from ..provider_adapter import ProviderAdapter, ValueInfo
from ..value_parser import parse_field_value
from .widgets import PillButton


_SCOPE_COLORS = {
    "env": SCOPE_COLORS["Env"],
    "user": SCOPE_COLORS["User"],
    "user-local": SCOPE_COLORS["Machine"],
    "project": SCOPE_COLORS["Project"],
    "project-local": SCOPE_COLORS["ProjectMachine"],
    "default": SCOPE_COLORS["Def"],
}


class EditDialog(tk.Toplevel):  # type: ignore[misc]
    """Simple dialog for editing a key across scopes."""

    def __init__(
        self,
        master: tk.Widget,
        adapter: ProviderAdapter,
        key: str,
        *,
        on_edit_save: Callable[[str, str, object], None] | None = None,
        on_edit_remove: Callable[[str, str], None] | None = None,
    ) -> None:
        super().__init__(master)
        info = adapter.field_info(key)
        label = info.label or key
        self.title(f"Edit — {label}")
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        self.adapter = adapter
        self.key = key
        self.on_edit_save = on_edit_save
        self.on_edit_remove = on_edit_remove

        palette = get_palette()
        self.configure(bg=palette["bg"])  # type: ignore[call-arg]

        ttk.Label(self, text=label, style="Title.TLabel").pack(
            anchor="w", padx=18, pady=(12, 0)
        )
        ttk.Style(self).configure(
            "Key.TLabel", background=palette["bg"], foreground=palette["hdr_muted"]
        )
        ttk.Label(self, text=key, style="Key.TLabel").pack(
            anchor="w", padx=18, pady=(0, 6)
        )
        body = ttk.Frame(self, padding=12, style="Card.TFrame")
        body.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        self.entries: dict[str, ttk.Entry] = {}

        values = adapter.values_for_key(key)
        scopes = list(adapter.scopes())
        if "default" not in scopes:
            scopes.append("default")

        _, eff_src = adapter.effective_for_key(key)

        row = 0
        for scope in scopes:
            if scope == "env" and scope not in values:
                continue

            vinfo: ValueInfo | None = values.get(scope)

            def value_provider(s=scope) -> object:
                v = values.get(s)
                if v and v.value is not None:
                    return v.value
                if s == "default":
                    return self.adapter.default_for_key(self.key)
                return None

            can_write = adapter.can_write(scope)
            if scope == "default":
                can_write = False
            elif scope == "env" or adapter.is_overlay(scope):
                can_write = False

            locked = not can_write
            if locked and scope != "default" and not adapter.is_overlay(scope):
                state = "disabled"
            elif eff_src == scope:
                state = "effective"
            elif vinfo and vinfo.value is not None:
                state = "present"
            else:
                state = "empty"

            short_label = adapter.scope_label(scope, short=True)
            long_label = adapter.scope_label(scope, short=False)
            palette = get_palette()
            color = _SCOPE_COLORS.get(scope, palette["ink_muted"])

            pill = PillButton(
                body,
                text=short_label,
                color=color,
                state=state,  # type: ignore[arg-type]
                value_provider=value_provider,
                clickable=False,
                tooltip_title=long_label,
                tooltip_desc=adapter.scope_description(scope),
                locked=locked,
            )
            pill.grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)

            entry = ttk.Entry(body)
            entry.grid(row=row, column=1, sticky="ew", pady=4)

            if vinfo and vinfo.value is not None:
                entry.insert(0, str(vinfo.value))

            if scope == "default":
                entry.state(["readonly"])
            elif scope == "env" or adapter.is_overlay(scope):
                entry.state(["readonly"])
            elif not can_write:
                entry.state(["disabled"])

            btn_save = ttk.Button(
                body,
                text="Save",
                command=lambda s=scope: self._save_scope(s),
                style="Plain.TButton",
            )
            btn_save.grid(row=row, column=2, padx=4)
            btn_remove = ttk.Button(
                body,
                text="Remove",
                command=lambda s=scope: self._remove_scope(s),
                style="Plain.TButton",
            )
            btn_remove.grid(row=row, column=3, padx=4)

            if not can_write:
                btn_save.state(["disabled"])
                btn_remove.state(["disabled"])

            if vinfo and vinfo.error:
                err = ttk.Label(body, text=vinfo.error, foreground="#b91c1c")
                err.grid(row=row + 1, column=1, columnspan=3, sticky="w", pady=(0, 4))
                row += 1

            self.entries[scope] = entry
            row += 1
        ttk.Style(self).configure(
            "Desc.TLabel", background=palette["card"], foreground=palette["ink_muted"]
        )
        if info.description_short:
            ttk.Label(
                body,
                text=info.description_short,
                style="Desc.TLabel",
                wraplength=400,
                anchor="w",
                justify="left",
            ).grid(row=row, column=0, columnspan=4, sticky="w", pady=(12, 0))
            row += 1
        if info.description:
            ttk.Label(
                body,
                text=info.description,
                style="Desc.TLabel",
                wraplength=400,
                anchor="w",
                justify="left",
            ).grid(row=row, column=0, columnspan=4, sticky="w")
            row += 1

        ttk.Button(
            body, text="Close", command=self.destroy, style="Plain.TButton"
        ).grid(row=row, column=3, sticky="e")
        body.columnconfigure(1, weight=1)

    # -- callbacks ---------------------------------------------------------
    def _save_scope(self, scope: str) -> None:
        if self.on_edit_save is None:
            return

        raw = self.entries[scope].get()
        type_name = self.adapter.field_info(self.key).type

        try:
            value = parse_field_value(type_name, raw)
        except (TypeError, ValueError):
            if messagebox is not None:
                if type_name == "boolean":
                    msg = "Value must be true/false or 1/0"
                else:
                    msg = f"Value must be a {type_name}"
                messagebox.showerror("Invalid value", msg, parent=self)
            return

        try:
            self.on_edit_save(self.key, scope, value)
        except PermissionError as exc:
            if messagebox is not None:
                messagebox.showinfo("Read-only", str(exc), parent=self)
        except Exception as exc:  # pragma: no cover - defensive
            if messagebox is not None:
                messagebox.showerror("Error", str(exc), parent=self)

    def _remove_scope(self, scope: str) -> None:
        if self.on_edit_remove is None:
            return
        try:
            self.on_edit_remove(self.key, scope)
        except PermissionError as exc:
            if messagebox is not None:
                messagebox.showinfo("Read-only", str(exc), parent=self)
            return
        except Exception as exc:  # pragma: no cover - defensive
            if messagebox is not None:
                messagebox.showerror("Error", str(exc), parent=self)
            return
        entry = self.entries.get(scope)
        if entry is not None:
            entry.delete(0, "end")
