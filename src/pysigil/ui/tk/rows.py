from __future__ import annotations

from typing import Callable, Dict, Any

try:  # pragma: no cover - tkinter may be missing
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover
    tk = None  # type: ignore
    ttk = None  # type: ignore

from ..provider_adapter import ProviderAdapter, ValueInfo
from .widgets import PillButton, SCOPE_COLOR, GREY_BG

# Mapping from scope ids to color constants used by :class:`PillButton`
_SCOPE_COLORS = {
    "env": SCOPE_COLOR["Env"],
    "user": SCOPE_COLOR["User"],
    "user-local": SCOPE_COLOR["Machine"],
    "project": SCOPE_COLOR["Project"],
    "project-local": SCOPE_COLOR["ProjectMachine"],
    "default": SCOPE_COLOR["Def"],
}


class FieldRow(ttk.Frame):
    """Representation of a single field row with scope pills."""

    def __init__(
        self,
        master: tk.Widget,
        adapter: ProviderAdapter,
        key: str,
        on_pill_click: Callable[[str, str], None],
        *,
        compact: bool = True,
    ) -> None:
        super().__init__(master)
        self.adapter = adapter
        self.key = key
        self._on_pill_click = on_pill_click
        self.compact = compact

        # key label
        self.lbl_key = ttk.Label(self, text=key)
        self.lbl_key.grid(row=0, column=0, sticky="w")

        # effective value display
        self.var_eff = tk.StringVar(value="") if tk else None
        self.lbl_eff = tk.Label(
            self,
            textvariable=self.var_eff,
            bg=GREY_BG,
            fg="#111111",
            bd=1,
            relief="ridge",
            padx=10,
            pady=6,
        )
        self.lbl_eff.grid(row=0, column=1, sticky="ew", padx=(8, 8))

        # container for scope pills
        self.pills = ttk.Frame(self)
        self.pills.grid(row=0, column=2, sticky="w")

        self.columnconfigure(1, weight=1)

        self.refresh()

    # ------------------------------------------------------------------
    def set_compact(self, compact: bool) -> None:
        """Toggle compact mode and rebuild pills."""
        if self.compact != compact:
            self.compact = compact
            self.refresh()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """Refresh the effective value and rebuild scope pills."""
        if tk is None:  # pragma: no cover - defensive
            return

        # locked effective value -------------------------------------------------
        eff_val, eff_src = self.adapter.effective_for_key(self.key)
        val_txt = "—" if eff_val is None else str(eff_val)
        if eff_src is None:
            src_txt = "—"
        else:
            src_txt = self.adapter.scope_label(eff_src)
        lock = "\U0001F512 "
        self.var_eff.set(f"{lock}{val_txt}  ({src_txt})")

        # rebuild pills ----------------------------------------------------------
        for child in list(self.pills.winfo_children()):
            child.destroy()

        values: Dict[str, ValueInfo] = self.adapter.values_for_key(self.key)
        scopes = self.adapter.scopes()
        for scope in scopes:
            has_value = scope in values
            if scope == "default" and not has_value:
                continue
            if self.compact and scope != "default" and not has_value:
                continue

            if not self.adapter.can_write(scope):
                state = "disabled"
            elif eff_src == scope:
                state = "effective"
            elif has_value:
                state = "present"
            else:
                state = "empty"

            short_label = self.adapter.scope_label(scope, short=True)
            long_label = self.adapter.scope_label(scope, short=False)
            color = _SCOPE_COLORS.get(scope, "#888888")

            def value_provider(s=scope) -> Any:
                if s in values:
                    return values[s].value
                if s == "default":
                    return self.adapter.default_for_key(self.key)
                return None

            def cb(s=scope, st=state) -> None:
                if st != "disabled" and self._on_pill_click:
                    self._on_pill_click(self.key, s)

            pill = PillButton(
                self.pills,
                text=short_label,
                color=color,
                state=state,  # type: ignore[arg-type]
                value_provider=value_provider,
                clickable=state != "disabled",
                on_click=cb,
                tooltip_title=long_label,
            )
            pill.pack(side="left", padx=(0, 6))


__all__ = ["FieldRow"]
