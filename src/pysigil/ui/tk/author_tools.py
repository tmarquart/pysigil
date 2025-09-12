"""Authoring tools UI."""

from __future__ import annotations

from pathlib import Path

try:  # pragma: no cover - tkinter availability depends on environment
    import tkinter as tk
    from tkinter import messagebox, ttk
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore
    ttk = None  # type: ignore

from ...settings_metadata import TYPE_REGISTRY, FieldType, SHORT_DESC_MAX
from ..author_adapter import AuthorAdapter, FieldInfo
from ..options_form import OptionsForm
from ..core import AppCore
from ..value_parser import parse_field_value


class AuthorTools(tk.Toplevel):  # pragma: no cover - simple UI wrapper
    """Toplevel window exposing authoring helpers for provider authors."""

    def __init__(self, master: tk.Misc, core: AppCore) -> None:
        super().__init__(master)
        pid = core.state.provider_id or ""
        project_root: Path | None = core.state.project_root
        project = project_root.as_posix() if project_root else ""
        title = "Sigil – Author Tools"
        if pid:
            title += f" – {pid}"
        if project:
            title += f" – {project}"
        self.title(title)
        self.core = core
        self._info_var = tk.StringVar()
        info = f"Provider: {pid}"
        if project:
            info += f" – {project}"
        self._info_var.set(info)
        self.adapter = AuthorAdapter(pid or None)
        self._current_key: str | None = None
        self._value_widget: object | None = None
        self._options_widget: object | None = None
        # Undiscovered fields are loaded on demand
        self._undiscovered_loaded = False
        self._build()
        if pid:
            self._reload_tree()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build(self) -> None:
        self.geometry("800x600")
        ttk.Label(self, textvariable=self._info_var).pack(anchor="w", padx=6, pady=6)
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
        self._tree.bind("<<TreeviewOpen>>", self._on_tree_open)

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
        """Populate tree with defined fields and a collapsible undiscovered section."""

        pattern = self._search_var.get().strip().lower()
        self._tree.delete(*self._tree.get_children(""))

        try:
            defined = list(self.adapter.list_defined())
            undiscovered = list(self.adapter.list_undiscovered())
        except RuntimeError:
            return

        # Defined fields appear directly at the root
        for info in defined:
            if pattern and pattern not in info.key.lower():
                continue
            self._tree.insert("", "end", text=info.key, iid=f"defined:{info.key}")

        # Undiscovered fields live under a lazily populated node at the bottom
        if undiscovered:
            undis_id = self._tree.insert(
                "", "end", text="Undiscovered", iid="undiscovered", open=self._undiscovered_loaded
            )
            if self._undiscovered_loaded:
                for info in undiscovered:
                    if pattern and pattern not in info.key.lower():
                        continue
                    self._tree.insert(
                        undis_id, "end", text=info.key, iid=f"undiscovered:{info.key}"
                    )
            else:
                # insert a placeholder so the node is expandable before loading
                self._tree.insert(undis_id, "end")

        else:
            # Reset flag so the node stays collapsed if undiscovered fields later appear
            self._undiscovered_loaded = False

    # ------------------------------------------------------------------
    def _on_tree_open(self, _event: object | None = None) -> None:
        node = self._tree.focus()
        if node == "undiscovered" and not self._undiscovered_loaded:
            self._undiscovered_loaded = True
            self._reload_tree()

    # ------------------------------------------------------------------
    def _build_type_section(
        self,
        field_type: FieldType | None,
        default: object | None = None,
        options: object | None = None,
    ) -> None:
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
            if options is not None and hasattr(self._options_widget, "set_value"):
                try:  # best effort
                    self._options_widget.set_value(options)  # type: ignore[attr-defined]
                except Exception:
                    pass
        elif field_type.option_model is not None:
            self._options_widget = OptionsForm(self._opts_frame, field_type)
            self._options_widget.pack(fill="x")
            if options is not None and hasattr(self._options_widget, "set_values"):
                try:  # best effort
                    self._options_widget.set_values(options)
                except Exception:
                    pass
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
        undiscovered = False
        if info is not None:
            default = self.adapter.default_for_key(key)
        else:
            und = {u.key: u for u in self.adapter.list_undiscovered()}
            uinfo = und.get(key)
            if uinfo is None:
                return
            info = FieldInfo(key=key, type=uinfo.guessed_type)
            default = uinfo.raw
            undiscovered = True
        self._populate_form(info, default, undiscovered=undiscovered)

    def _on_add(self) -> None:
        self._tree.selection_remove(self._tree.selection())
        self._current_key = ""
        info = FieldInfo(key="", type="string")
        self._populate_form(info, None, undiscovered=False)

    # ------------------------------------------------------------------
    def _populate_form(self, info: FieldInfo, default: object | None, *, undiscovered: bool) -> None:
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
        ident.columnconfigure(1, weight=1)

        # Descriptions ---------------------------------------------------
        desc_fr = ttk.LabelFrame(self._form, text="Descriptions")
        desc_fr.pack(fill="x", pady=(0, 6))
        self._desc_short_var = tk.StringVar(value=info.description_short or "")
        ttk.Label(desc_fr, text="Short:").grid(row=0, column=0, sticky="w")
        short_entry = ttk.Entry(desc_fr, textvariable=self._desc_short_var)
        short_entry.grid(row=0, column=1, sticky="ew")
        self._desc_short_count = ttk.Label(desc_fr, text="0/0")
        self._desc_short_count.grid(row=0, column=2, sticky="e")
        desc_fr.columnconfigure(1, weight=1)

        def _update_count(*_args: object) -> None:
            n = len(self._desc_short_var.get())
            fg = "red" if n > SHORT_DESC_MAX else "black"
            self._desc_short_count.config(text=f"{n}/{SHORT_DESC_MAX}", foreground=fg)

        self._desc_short_var.trace_add("write", _update_count)
        _update_count()

        ttk.Label(desc_fr, text="Long:").grid(row=1, column=0, sticky="nw")
        self._desc_text = tk.Text(desc_fr, height=4, wrap="word")
        self._desc_text.grid(row=1, column=1, columnspan=2, sticky="ew")
        if info.description:
            self._desc_text.insert("1.0", info.description)

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
        self._build_type_section(ft, default, info.options)

        # Grouping ------------------------------------------------------
        group_fr = ttk.LabelFrame(self._form, text="Grouping")
        group_fr.pack(fill="x", pady=(0, 6))
        self._section_var = tk.StringVar(value=info.section or "")
        ttk.Label(group_fr, text="Section:").grid(row=0, column=0, sticky="w")
        ttk.Entry(group_fr, textvariable=self._section_var).grid(row=0, column=1, sticky="ew")
        self._order_var = tk.StringVar(
            value="" if info.order is None else str(info.order)
        )
        ttk.Label(group_fr, text="Order:").grid(row=1, column=0, sticky="w")
        ttk.Entry(group_fr, textvariable=self._order_var).grid(row=1, column=1, sticky="ew")
        group_fr.columnconfigure(1, weight=1)

        # Actions --------------------------------------------------------
        actions = ttk.Frame(self._form)
        actions.pack(fill="x", pady=(0, 6))
        ttk.Button(actions, text="Save", command=self._on_save).pack(side="right")
        ttk.Button(actions, text="Revert", command=self._on_revert).pack(side="right")
        ttk.Button(actions, text="Delete", command=self._on_delete).pack(side="right")
        if undiscovered:
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
        desc_short = self._desc_short_var.get().strip() or None
        description = self._desc_text.get("1.0", "end").strip() or None
        options = self._collect_options()
        section = self._section_var.get().strip() or None
        order_val = self._order_var.get().strip()
        order = None
        if order_val:
            try:
                order = int(order_val)
            except ValueError:
                if messagebox is not None:
                    messagebox.showerror("Invalid order", "Order must be an integer", parent=self)
                return
        default = None
        if self._value_widget is not None and hasattr(self._value_widget, "get_value"):
            default = self._value_widget.get_value()  # type: ignore[attr-defined]
        if default is not None:
            try:
                default = parse_field_value(type_name, default)
            except (TypeError, ValueError):
                if messagebox is not None:
                    if type_name == "boolean":
                        msg = "Default must be true/false or 1/0"
                    else:
                        msg = f"Default must be a {type_name}"
                    messagebox.showerror("Invalid default", msg, parent=self)
                return
        # Build kwargs dynamically to match adapter signature
        import inspect

        sig = inspect.signature(self.adapter.upsert_field)
        kwargs: dict[str, object] = {}
        if "label" in sig.parameters:
            kwargs["label"] = label
        if "description_short" in sig.parameters:
            kwargs["description_short"] = desc_short
        if "description" in sig.parameters:
            kwargs["description"] = description
        if "options" in sig.parameters and options is not None:
            kwargs["options"] = options
        if "section" in sig.parameters:
            kwargs["section"] = section
        if "order" in sig.parameters and order is not None:
            kwargs["order"] = order
        if "default" in sig.parameters and default is not None:
            kwargs["default"] = default
        if desc_short is not None and len(desc_short) > SHORT_DESC_MAX:
            if messagebox is not None:
                messagebox.showerror(
                    "Too long", f"Short description exceeds {SHORT_DESC_MAX} characters", parent=self
                )
            return
        self.adapter.upsert_field(key, type_name, **kwargs)  # type: ignore[arg-type]
        self._current_key = key
        self._reload_tree()

    def _on_revert(self) -> None:
        if self._current_key is not None:
            defined = {f.key: f for f in self.adapter.list_defined()}
            info = defined.get(self._current_key)
            default = self.adapter.default_for_key(self._current_key)
            if info is not None:
                self._populate_form(info, default, undiscovered=False)

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
        if self._current_key is None:
            return
        key = self._key_var.get().strip()
        type_name = self._type_var.get().strip()
        try:
            self.adapter.adopt_untracked({key: type_name})
        except Exception:
            return
        self._current_key = key
        self._reload_tree()

    def _toggle_diff(self) -> None:
        if self._diff_shown.get():
            self._diff_frame.pack(fill="both", expand=True)
        else:
            self._diff_frame.pack_forget()

