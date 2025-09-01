"""Authoring tools UI."""

from __future__ import annotations

try:  # pragma: no cover - tkinter availability depends on environment
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore
    ttk = None  # type: ignore

from ...settings_metadata import TYPE_REGISTRY, FieldType
from ..author_adapter import AuthorAdapter, FieldInfo
from ..options_form import OptionsForm
from ..core import AppCore


class AuthorTools(tk.Toplevel):  # pragma: no cover - simple UI wrapper
    """Toplevel window exposing authoring helpers for provider authors."""

    def __init__(self, master: tk.Misc, core: AppCore) -> None:
        super().__init__(master)
        self.title("Sigil – Author Tools")
        self.core = core
        self.adapter = AuthorAdapter(core.state.provider_id or "")
        self._current_key: str | None = None
        self._value_widget: object | None = None
        self._options_widget: object | None = None
        self._build()
        self._reload_tree()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build(self) -> None:
        self.geometry("800x600")
        pw = ttk.PanedWindow(self, orient="horizontal")
        self._left = ttk.Frame(pw)
        self._right = ttk.Frame(pw)
        pw.add(self._left, weight=1)
        pw.add(self._right, weight=3)
        pw.pack(fill="both", expand=True)

        # -- left: search + tree -------------------------------------------------
        search = ttk.Frame(self._left)
        search.pack(fill="x", padx=6, pady=(6, 0))
        self._search_var = tk.StringVar()
        entry = ttk.Entry(search, textvariable=self._search_var)
        entry.pack(fill="x", side="left", expand=True)
        ttk.Button(search, text="Add", command=self._on_add).pack(side="right", padx=(4, 0))
        self._search_var.trace_add("write", lambda *_: self._reload_tree())

        self._tree = ttk.Treeview(self._left, show="tree")
        self._tree.pack(fill="both", expand=True, padx=6, pady=6)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # -- right: placeholder frame for form -----------------------------------
        self._form = ttk.Frame(self._right)
        self._form.pack(fill="both", expand=True, padx=6, pady=6)

    # ------------------------------------------------------------------
    def _clear_form(self) -> None:
        for child in self._form.winfo_children():
            child.destroy()
        self._value_widget = None
        self._options_widget = None

    # ------------------------------------------------------------------
    def _reload_tree(self) -> None:
        """Populate tree with defined and undiscovered fields."""

        pattern = self._search_var.get().strip().lower()
        self._tree.delete(*self._tree.get_children(""))
        defined_id = self._tree.insert("", "end", text="Defined", iid="defined")
        for info in self.adapter.list_defined():
            if pattern and pattern not in info.key.lower():
                continue
            self._tree.insert(defined_id, "end", text=info.key, iid=f"defined:{info.key}")
        undis_id = self._tree.insert("", "end", text="Undiscovered", iid="undiscovered")
        for info in self.adapter.list_undiscovered():
            if pattern and pattern not in info.key.lower():
                continue
            self._tree.insert(undis_id, "end", text=info.key, iid=f"undiscovered:{info.key}")
        self._tree.item(defined_id, open=True)
        self._tree.item(undis_id, open=True)

    # ------------------------------------------------------------------
    def _build_type_section(self, field_type: FieldType | None, default: object | None = None) -> None:
        for child in self._opts_frame.winfo_children():
            child.destroy()
        for child in self._default_frame.winfo_children():
            child.destroy()
        self._value_widget = None
        self._options_widget = None
        if field_type is None:
            return
        # Options
        if field_type.option_widget is not None:
            self._options_widget = field_type.option_widget(self._opts_frame)
            self._options_widget.pack(fill="x")
        elif field_type.option_model is not None:
            self._options_widget = OptionsForm(self._opts_frame, field_type)
            self._options_widget.pack(fill="x")
        # Default editor
        if field_type.value_widget is not None:
            widget = field_type.value_widget(self._default_frame)  # type: ignore[assignment]
            widget.pack(fill="x")
            self._value_widget = widget
            if default is not None and hasattr(widget, "set_value"):
                try:  # best effort
                    widget.set_value(default)  # type: ignore[attr-defined]
                except Exception:
                    pass

    # ------------------------------------------------------------------
    def _on_type_change(self, _event: object | None = None) -> None:
        ft = TYPE_REGISTRY.get(self._type_var.get())
        default = None
        if self._value_widget is not None and hasattr(self._value_widget, "get_value"):
            try:
                default = self._value_widget.get_value()  # type: ignore[attr-defined]
            except Exception:
                default = None
        self._build_type_section(ft, default)

    # ------------------------------------------------------------------
    def _on_select(self, _event: object | None = None) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        node = sel[0]
        if ":" not in node:
            return
        _, key = node.split(":", 1)
        self._current_key = key
        defined = {f.key: f for f in self.adapter.list_defined()}
        info: FieldInfo | None = defined.get(key)
        default: object | None = None
        if info is not None:
            default = self.adapter.default_for_key(key)
        else:
            und = {u.key: u for u in self.adapter.list_undiscovered()}
            uinfo = und.get(key)
            if uinfo is None:
                return
            info = FieldInfo(key=key, type=uinfo.guessed_type)
            default = uinfo.raw
        self._populate_form(info, default)

    def _on_add(self) -> None:
        self._tree.selection_remove(self._tree.selection())
        self._current_key = ""
        info = FieldInfo(key="", type="string")
        self._populate_form(info, None)

    # ------------------------------------------------------------------
    def _populate_form(self, info: FieldInfo, default: object | None) -> None:
        self._clear_form()

        # Identity -------------------------------------------------------
        ident = ttk.LabelFrame(self._form, text="Identity")
        ident.pack(fill="x", pady=(0, 6))
        self._key_var = tk.StringVar(value=info.key)
        ttk.Label(ident, text="Key:").grid(row=0, column=0, sticky="w")
        ttk.Entry(ident, textvariable=self._key_var).grid(row=0, column=1, sticky="ew")
        self._label_var = tk.StringVar(value=info.label or "")
        ttk.Label(ident, text="Label:").grid(row=1, column=0, sticky="w")
        ttk.Entry(ident, textvariable=self._label_var).grid(row=1, column=1, sticky="ew")
        self._desc_var = tk.StringVar(value=info.description or "")
        ttk.Label(ident, text="Description:").grid(row=2, column=0, sticky="w")
        ttk.Entry(ident, textvariable=self._desc_var).grid(row=2, column=1, sticky="ew")
        ident.columnconfigure(1, weight=1)

        # Type -----------------------------------------------------------
        type_fr = ttk.LabelFrame(self._form, text="Type")
        type_fr.pack(fill="x", pady=(0, 6))
        self._type_var = tk.StringVar(value=info.type)
        ttk.Label(type_fr, text="Type:").grid(row=0, column=0, sticky="w")
        type_combo = ttk.Combobox(
            type_fr,
            textvariable=self._type_var,
            state="readonly",
            values=sorted(TYPE_REGISTRY.keys()),
        )
        type_combo.grid(row=0, column=1, sticky="ew")
        type_combo.bind("<<ComboboxSelected>>", self._on_type_change)
        type_fr.columnconfigure(1, weight=1)

        self._opts_frame = ttk.LabelFrame(self._form, text="Type Options")
        self._opts_frame.pack(fill="x", pady=(0, 6))
        self._default_frame = ttk.LabelFrame(self._form, text="Default")
        self._default_frame.pack(fill="x", pady=(0, 6))
        ft = TYPE_REGISTRY.get(info.type)
        self._build_type_section(ft, default)

        # Actions --------------------------------------------------------
        actions = ttk.Frame(self._form)
        actions.pack(fill="x", pady=(0, 6))
        ttk.Button(actions, text="Save", command=self._on_save).pack(side="right")
        ttk.Button(actions, text="Revert", command=self._on_revert).pack(side="right")
        ttk.Button(actions, text="Delete", command=self._on_delete).pack(side="right")
        ttk.Button(actions, text="Adopt", command=self._on_adopt).pack(side="right")

        # Diff drawer ----------------------------------------------------
        self._diff_shown = tk.BooleanVar(value=False)
        toggle = ttk.Checkbutton(
            self._form,
            text="Show Diff",
            variable=self._diff_shown,
            command=self._toggle_diff,
            style="Toolbutton",
        )
        toggle.pack(anchor="w")
        self._diff_frame = ttk.Frame(self._form)
        self._diff_text = tk.Text(self._diff_frame, height=6)
        self._diff_text.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------
    def _collect_options(self) -> dict | None:
        ow = self._options_widget
        if ow is None:
            return None
        if hasattr(ow, "get_values"):
            return ow.get_values()  # type: ignore[no-any-return]
        if hasattr(ow, "get_value"):
            val = ow.get_value()  # type: ignore[no-untyped-call]
            return val if isinstance(val, dict) else {}
        return None

    def _on_save(self) -> None:
        if self._current_key is None:
            return
        key = self._key_var.get().strip()
        type_name = self._type_var.get().strip()
        label = self._label_var.get().strip() or None
        description = self._desc_var.get().strip() or None
        options = self._collect_options()
        default = None
        if self._value_widget is not None and hasattr(self._value_widget, "get_value"):
            default = self._value_widget.get_value()  # type: ignore[attr-defined]
        # Build kwargs dynamically to match adapter signature
        import inspect

        sig = inspect.signature(self.adapter.upsert_field)
        kwargs: dict[str, object] = {}
        if "label" in sig.parameters:
            kwargs["label"] = label
        if "description" in sig.parameters:
            kwargs["description"] = description
        if "options" in sig.parameters and options is not None:
            kwargs["options"] = options
        if "default" in sig.parameters and default is not None:
            kwargs["default"] = default
        self.adapter.upsert_field(key, type_name, **kwargs)  # type: ignore[arg-type]
        self._current_key = key
        self._reload_tree()

    def _on_revert(self) -> None:
        if self._current_key is not None:
            defined = {f.key: f for f in self.adapter.list_defined()}
            info = defined.get(self._current_key)
            default = self.adapter.default_for_key(self._current_key)
            if info is not None:
                self._populate_form(info, default)

    def _on_delete(self) -> None:
        if self._current_key:
            try:
                self.adapter.delete_field(self._current_key)
            except Exception:
                pass
            self._current_key = None
            self._reload_tree()
        self._clear_form()

    def _on_adopt(self) -> None:
        # For now adopt simply saves the field
        self._on_save()

    def _toggle_diff(self) -> None:
        if self._diff_shown.get():
            self._diff_frame.pack(fill="both", expand=True)
        else:
            self._diff_frame.pack_forget()

