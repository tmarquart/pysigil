from __future__ import annotations

try:  # pragma: no cover - tkinter availability depends on environment
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore
    ttk = None  # type: ignore

from ...settings_metadata import TYPE_REGISTRY, FieldType
from ..options_form import OptionsForm
from ..author_adapter import AuthorAdapter
from ..core import AppCore


class AuthorTools(tk.Toplevel):  # pragma: no cover - simple UI wrapper
    """Toplevel window exposing authoring tools.

    The implementation intentionally keeps the interface minimal.  It
    presents a tabbed notebook with three placeholder tabs: *Fields*,
    *Defaults* and *Untracked*.  Content is read-only for now and pulled
    from :class:`~pysigil.ui.core.AppCore`.
    """

    def __init__(self, master: tk.Misc, core: AppCore) -> None:
        super().__init__(master)
        self.title("Sigil – Author Tools")
        self.core = core
        self.adapter = AuthorAdapter(core.state.provider_id or "")
        self._current_key: str | None = None
        self._value_widget: object | None = None
        self._options_widget: object | None = None
        self._build()
        self._populate_fields()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        self.geometry("640x480")
        nb = ttk.Notebook(self)
        self._tab_fields = ttk.Frame(nb)
        self._tab_defaults = ttk.Frame(nb)
        self._tab_untracked = ttk.Frame(nb)
        nb.add(self._tab_fields, text="Fields")
        nb.add(self._tab_defaults, text="Defaults")
        nb.add(self._tab_untracked, text="Untracked")
        nb.pack(fill="both", expand=True)

        fields_body = ttk.Frame(self._tab_fields)
        fields_body.pack(fill="both", expand=True)
        self._fields_list = tk.Listbox(fields_body)
        self._fields_list.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self._fields_list.bind("<<ListboxSelect>>", self._on_field_select)
        self._detail = ttk.Frame(fields_body)
        self._detail.pack(side="left", fill="both", expand=True, padx=(6, 6), pady=6)

    # ------------------------------------------------------------------
    def _build_type_section(self, field_type: FieldType) -> None:
        for child in self._type_frame.winfo_children():
            child.destroy()
        self._value_widget = None
        self._options_widget = None
        row = 0
        if field_type.value_widget is not None:
            ttk.Label(self._type_frame, text="Default:").grid(row=row, column=0, sticky="w")
            widget = field_type.value_widget(self._type_frame)  # type: ignore[assignment]
            widget.grid(row=row, column=1, sticky="ew")
            self._value_widget = widget
            row += 1
        if field_type.option_widget is not None:
            self._options_widget = field_type.option_widget(self._type_frame)
            self._options_widget.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        elif field_type.option_model is not None:
            self._options_widget = OptionsForm(self._type_frame, field_type)
            self._options_widget.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        self._type_frame.columnconfigure(1, weight=1)

    # ------------------------------------------------------------------
    def _on_type_change(self, _event: object | None = None) -> None:
        type_name = self._type_var.get()
        ft = TYPE_REGISTRY.get(type_name)
        if ft is None:
            return
        self._build_type_section(ft)

    # ------------------------------------------------------------------
    def _on_field_select(self, _event: object | None = None) -> None:
        cur = self._fields_list.curselection()
        if not cur:
            return
        key = self._fields_list.get(cur[0])
        info = next((f for f in self.core.state.fields if f.key == key), None)
        if info is None:
            return
        self._current_key = key
        for child in self._detail.winfo_children():
            child.destroy()
        ttk.Label(self._detail, text="Key:").grid(row=0, column=0, sticky="w")
        self._key_var = tk.StringVar(value=info.key)
        ttk.Entry(self._detail, textvariable=self._key_var).grid(row=0, column=1, sticky="ew")
        ttk.Label(self._detail, text="Label:").grid(row=1, column=0, sticky="w")
        self._label_var = tk.StringVar(value=info.label or "")
        ttk.Entry(self._detail, textvariable=self._label_var).grid(row=1, column=1, sticky="ew")
        ttk.Label(self._detail, text="Type:").grid(row=2, column=0, sticky="w")
        self._type_var = tk.StringVar(value=info.type)
        type_combo = ttk.Combobox(
            self._detail,
            textvariable=self._type_var,
            state="readonly",
            values=sorted(TYPE_REGISTRY.keys()),
        )
        type_combo.grid(row=2, column=1, sticky="ew")
        type_combo.bind("<<ComboboxSelected>>", self._on_type_change)
        ttk.Label(self._detail, text="Description:").grid(row=3, column=0, sticky="w")
        self._desc_var = tk.StringVar(value=info.description or "")
        ttk.Entry(self._detail, textvariable=self._desc_var).grid(row=3, column=1, sticky="ew")
        self._type_frame = ttk.Frame(self._detail)
        self._type_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        ft = TYPE_REGISTRY.get(info.type)
        if ft is not None:
            self._build_type_section(ft)
        ttk.Button(self._detail, text="Save", command=self._on_save).grid(row=5, column=1, sticky="e", pady=8)
        self._detail.columnconfigure(1, weight=1)

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

    # ------------------------------------------------------------------
    def _on_save(self) -> None:
        if self._current_key is None:
            return
        key = self._key_var.get().strip()
        type_name = self._type_var.get().strip()
        label = self._label_var.get().strip() or None
        desc = self._desc_var.get().strip() or None
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
            kwargs["description"] = desc
        if "options" in sig.parameters and options is not None:
            kwargs["options"] = options
        if "default" in sig.parameters and default is not None:
            kwargs["default"] = default
        self.adapter.upsert_field(key, type_name, **kwargs)  # type: ignore[arg-type]
        self._populate_fields()

    def _populate_fields(self) -> None:
        self._fields_list.delete(0, tk.END)
        for info in self.core.state.fields:
            self._fields_list.insert(tk.END, info.key)
