from __future__ import annotations

import os
from typing import Any, Callable, Dict

try:  # pragma: no cover - tkinter may be missing
    import tkinter as tk
    from tkinter import ttk, messagebox
except Exception:  # pragma: no cover
    tk = None  # type: ignore
    ttk = None  # type: ignore
    messagebox = None  # type: ignore

from ..aurelia_theme import SCOPE_COLORS, get_palette
from ..provider_adapter import ProviderAdapter, ValueInfo
from .widgets import PillButton, HoverTip

# Mapping from scope ids to color constants used by :class:`PillButton`
_SCOPE_COLORS = {
    "env": SCOPE_COLORS["Env"],
    "user": SCOPE_COLORS["User"],
    "user-local": SCOPE_COLORS["Machine"],
    "project": SCOPE_COLORS["Project"],
    "project-local": SCOPE_COLORS["ProjectMachine"],
    "default": SCOPE_COLORS["Def"],
}


def _debug_columns() -> bool:
    """Return True when the debug column overlay is enabled."""
    return bool(os.environ.get("PYSGIL_DEBUG_COLUMNS"))


class FieldRow(tk.Frame):
    """Representation of a single field row with scope pills."""

    def __init__(
        self,
        master: tk.Widget,
        adapter: ProviderAdapter,
        key: str,
        on_pill_click: Callable[[str, str], None],
        *,
        compact: bool = True,
        on_edit_click: Callable[[str], None] | None = None,
    ) -> None:
        palette = get_palette()
        super().__init__(master, bg=palette["card"], highlightthickness=0)
        self.adapter = adapter
        self.key = key
        self._on_pill_click = on_pill_click
        self._on_edit_click = on_edit_click
        self.compact = compact

        ink = palette["ink"]
        ink_muted = palette["ink_muted"]
        field = palette["field"]

        # container for key + info button
        self.key_frame = ttk.Frame(self, style="CardBody.TFrame")

        self.key_frame.grid(row=0, column=0, sticky="w", pady=(6, 0))

        info = None
        if hasattr(adapter, "field_info"):
            try:
                info = adapter.field_info(key)  # type: ignore[attr-defined]
            except Exception:
                info = None
        label = getattr(info, "label", None) or key
        self.lbl_key = ttk.Label(
            self.key_frame,
            text=label,
            padding=6,
            style="CardKey.TLabel",
        )
        self.lbl_key.pack(side="left")

        self.info_btn: tk.Label | None = None
        self.lbl_desc: ttk.Label | None = None
        if info:
            desc = info.description or info.description_short
            tip_lines = [f"Key: {key}"]
            if desc:
                tip_lines.append(desc)
            tip = "\n\n".join(tip_lines)
            if desc or key:
                self.info_btn = tk.Label(
                    self.key_frame,
                    text="\u24D8",
                    fg=ink_muted,
                    cursor="question_arrow",
                    bg=palette["card"],
                    takefocus=1,
                )
                self.info_btn.pack(side="left", padx=(4, 0))
                HoverTip(self.info_btn, lambda: tip)
                HoverTip(self.lbl_key, lambda: tip)
            if info.description_short:
                self.lbl_desc = ttk.Label(
                    self,
                    text=info.description_short,
                    style="CardMuted.TLabel",
                    wraplength=600,
                    padding=(6,0,0,0) # (left, top, right, bottom)
                )
                self.lbl_desc.grid(row=1, column=0, columnspan=3, sticky="w")

        # effective value display
        self.var_eff = tk.StringVar(value="") if tk else None
        self.lbl_eff = tk.Label(
            self,
            textvariable=self.var_eff,
            bg=field,
            fg=ink,
            bd=1,
            relief="ridge",
            padx=10,

            pady=0,
            anchor="nw",
        )
        self.lbl_eff.grid(row=0, column=1, sticky="new", padx=(8, 8), pady=(6, 0))
        self._eff_fg_normal = ink
        self._eff_fg_error = "#b91c1c"
        self._value_pad: int | None = None

        # container for scope pills
        self.pills = ttk.Frame(self, style="CardBody.TFrame")
        self.pills.grid(row=0, column=2, sticky="nw", pady=(6, 0))


        # edit action button
        self.btn_edit = ttk.Button(
            self,
            text="Edit…",
            command=lambda: self._on_edit_click(self.key) if self._on_edit_click else None,
        )

        self.btn_edit.grid(row=0, column=3, padx=4, pady=(6, 0), sticky="n")

        # ensure value box matches edit button height
        if tk is not None:
            self.after_idle(self._sync_value_height)


        self.columnconfigure(1, weight=1)

        self._pill_widgets: Dict[str, PillButton] = {}

        self.refresh()

        if _debug_columns() and tk is not None:
            self._debug_canvas = tk.Canvas(self, highlightthickness=0)
            self._debug_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.bind("<Configure>", self._on_debug_configure)

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
        eff_info, eff_src = self.adapter.effective_for_key(self.key)
        if eff_src is None:
            src_txt = "—"
        else:
            src_txt = self.adapter.scope_label(eff_src)
        if eff_info is None:
            val_txt = "—"
            self.lbl_eff.configure(fg=self._eff_fg_normal)
            self.var_eff.set(f"{val_txt}  ({src_txt})")
        elif eff_info.error:
            raw_txt = eff_info.raw if eff_info.raw not in (None, "") else "—"
            err_txt = eff_info.error
            self.lbl_eff.configure(fg=self._eff_fg_error)
            self.var_eff.set(f"{raw_txt}  ({src_txt})  ⚠ {err_txt}")
        else:
            val_txt = "—" if eff_info.value is None else str(eff_info.value)
            self.lbl_eff.configure(fg=self._eff_fg_normal)
            self.var_eff.set(f"{val_txt}  ({src_txt})")

        values: Dict[str, ValueInfo] = self.adapter.values_for_key(self.key)
        default_info = self.adapter.default_for_key(self.key)
        scopes = self.adapter.scopes()

        def tooltip_value(info: ValueInfo | None) -> Any:
            if info is None:
                return None
            if info.error:
                raw_txt = info.raw if info.raw not in (None, "") else "—"
                return f"{raw_txt} (invalid: {info.error})"
            return info.value

        # Ensure pills are packed in the same order as ``scopes`` by first
        # unpacking any existing widgets.  Without this, newly created scopes
        # would always be appended to the end regardless of the desired order.
        for child in self.pills.pack_slaves():
            child.pack_forget()

        for scope in scopes:
            has_value = scope in values
            scope_info = values.get(scope)

            def value_provider(s=scope, info=scope_info) -> Any:
                scoped = info
                if scoped is None and s == "default":
                    scoped = default_info
                return tooltip_value(scoped)

            display_info = scope_info if scope_info is not None else (
                default_info if scope == "default" else None
            )
            desc = self.adapter.scope_description(scope)
            if display_info is not None and display_info.error:
                if desc:
                    desc = f"{desc}\n\n⚠ {display_info.error}"
                else:
                    desc = f"⚠ {display_info.error}"
            can_write = self.adapter.can_write(scope)
            self.update_pill(
                scope,
                effective=(eff_src == scope),
                present=has_value,
                can_write=can_write,
                value_provider=value_provider,
                tooltip_desc=desc,
            )

        # adjust value label height when geometry might change
        self._sync_value_height()

    def _sync_value_height(self) -> None:
        if tk is None:  # pragma: no cover - defensive
            return
        try:
            # ``winfo_height`` reflects the actual rendered size whereas
            # ``winfo_reqheight`` only reports the requested size.  Using the
            # real height keeps the effective value box in sync with themed
            # button and pill widgets whose final size may exceed their
            # request due to style padding.
            self.update_idletasks()
            btn_h = self.btn_edit.winfo_height()
            lbl_h = self.lbl_eff.winfo_height()
            if btn_h <= 0 or lbl_h <= 0:
                return
            if self._value_pad is None:
                diff = btn_h - lbl_h
                pad = (diff + 1) // 5 if diff > 0 else 0
                if pad < 0:
                    pad = 0
                self._value_pad = pad
            self.lbl_eff.configure(pady=self._value_pad)
        except Exception:
            pass

    def _on_debug_configure(self, event: tk.Event) -> None:
        if not _debug_columns():
            return
        canvas = getattr(self, "_debug_canvas", None)
        if canvas is None:
            return
        canvas.delete("all")
        cols = self.grid_size()[0]
        for col in range(cols - 1):
            try:
                x, y, w, h = self.grid_bbox(col, 0)
            except Exception:
                continue
            canvas.create_line(x + w, 0, x + w, event.height, fill="red", width=2)

    def update_pill(
        self,
        name: str,
        *,
        effective: bool,
        present: bool,
        can_write: bool,
        value_provider: Callable[[], Any],
        tooltip_desc: str | None = None,
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
        palette = get_palette()
        color = _SCOPE_COLORS.get(name, palette["ink_muted"])
        desc_text = tooltip_desc if tooltip_desc is not None else self.adapter.scope_description(name)

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
                tooltip_desc=desc_text,
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
            pill.tooltip_desc = desc_text
            pill.on_click = cb
            pill.bind("<Button-1>", lambda e: cb())
            pill.configure(cursor="hand2")
            pill._draw()

        if not pill.winfo_ismapped():
            pill.pack(side="left", padx=(0, 6))

    # ------------------------------------------------------------------
    def update_metadata(self, info: object) -> None:  # pragma: no cover - simple
        """Update field key label based on new metadata."""
        key = getattr(info, "key", self.key)
        self.key = key
        label = getattr(info, "label", None) or key
        self.lbl_key.configure(text=label)
        desc = getattr(info, "description", None) or getattr(info, "description_short", None)
        tip_lines = [f"Key: {key}"]
        if desc:
            tip_lines.append(desc)
        tip = "\n\n".join(tip_lines)
        if self.info_btn is not None:
            HoverTip(self.info_btn, lambda: tip)
        HoverTip(self.lbl_key, lambda: tip)


__all__ = ["FieldRow"]
