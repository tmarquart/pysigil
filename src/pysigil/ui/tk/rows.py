from __future__ import annotations

from typing import Callable, Dict, Any

try:  # pragma: no cover - tkinter may be missing
    import tkinter as tk
    from tkinter import ttk, messagebox
except Exception:  # pragma: no cover
    tk = None  # type: ignore
    ttk = None  # type: ignore
    messagebox = None  # type: ignore

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

        self._pill_widgets: Dict[str, PillButton] = {}

        self.refresh()

    # ------------------------------------------------------------------
    def set_compact(self, compact: bool) -> None:
        """Toggle compact mode and rebuild pills."""
        if self.compact != compact:
            self.compact = compact
            self.refresh()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """Refresh the effective value and update scope pills."""
        if tk is None:  # pragma: no cover - defensive
            return

        # effective value -------------------------------------------------------
        eff_val, eff_src = self.adapter.effective_for_key(self.key)
        val_txt = "—" if eff_val is None else str(eff_val)
        if eff_src is None:
            src_txt = "—"
        else:
            src_txt = self.adapter.scope_label(eff_src)
        self.var_eff.set(f"{val_txt}  ({src_txt})")

        values: Dict[str, ValueInfo] = self.adapter.values_for_key(self.key)
        scopes = self.adapter.scopes()
        for scope in scopes:
            has_value = scope in values
            def value_provider(s=scope) -> Any:
                if s in values:
                    return values[s].value
                if s == "default":
                    return self.adapter.default_for_key(self.key)
                return None
            can_write = self.adapter.can_write(scope)
            self.update_pill(
                scope,
                effective=(eff_src == scope),
                present=has_value,
                can_write=can_write,
                value_provider=value_provider,
            )

    def update_pill(
        self,
        name: str,
        *,
        effective: bool,
        present: bool,
        can_write: bool,
        value_provider: Callable[[], Any],
    ) -> None:
        """Update or create a single pill widget.

        ``effective`` indicates whether the pill represents the effective
        scope while ``present`` reports if the scope has an explicit value.
        ``can_write`` controls the clickable state and ``value_provider`` is
        used for tooltip display.
        """
        if tk is None:  # pragma: no cover - defensive
            return

        if (
            name == "default" and not present and self.compact
        ) or (self.compact and name != "default" and not present):
            pill = self._pill_widgets.get(name)
            if pill and pill.winfo_ismapped():
                pill.pack_forget()
            return

        locked = not can_write
        if (not can_write and name != "default" and not self.adapter.is_overlay(name)):
            state = "disabled"
        elif effective:
            state = "effective"
        elif present:
            state = "present"
        else:
            state = "empty"

        short_label = self.adapter.scope_label(name, short=True)
        long_label = self.adapter.scope_label(name, short=False)
        color = _SCOPE_COLORS.get(name, "#888888")

        def cb() -> None:
            if not locked and self._on_pill_click:
                self._on_pill_click(self.key, name)
            elif locked:
                hint = self.adapter.scope_hint(name)
                if messagebox is not None and hint:
                    try:
                        messagebox.showinfo("Read-only", hint)
                    except Exception:
                        pass

        pill = self._pill_widgets.get(name)
        if pill is None:
            pill = PillButton(
                self.pills,
                text=short_label,
                color=color,
                state=state,  # type: ignore[arg-type]
                value_provider=value_provider,
                clickable=True,
                on_click=cb,
                tooltip_title=long_label,
                locked=locked,
            )
            self._pill_widgets[name] = pill
        else:
            pill.text = short_label
            pill.color = color
            pill.state = state  # type: ignore[assignment]
            pill.locked = locked
            pill.clickable = True
            pill.value_provider = value_provider
            pill.tooltip_title = long_label
            pill.on_click = cb
            pill.bind("<Button-1>", lambda e: cb())
            pill.configure(cursor="hand2")
            pill._draw()

        if not pill.winfo_ismapped():
            pill.pack(side="left", padx=(0, 6))


__all__ = ["FieldRow"]
