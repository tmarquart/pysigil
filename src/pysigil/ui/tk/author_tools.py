"""Authoring tools UI."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

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
from ..aurelia_theme import get_palette, use


class UnsavedChangesDialog(tk.Toplevel):
    """Modal dialog prompting the user about unsaved changes."""

    def __init__(self, master: tk.Widget) -> None:  # pragma: no cover - simple modal
        super().__init__(master)
        self.title("Unsaved changes")
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        palette = get_palette()
        self.configure(bg=palette["bg"])  # type: ignore[call-arg]
        self._result: str | None = None

        body = ttk.Frame(self, padding=18)
        body.pack(fill="both", expand=True)
        ttk.Label(
            body,
            text="You have unsaved changes.",
            style="Title.TLabel",
            anchor="w",
        ).pack(fill="x")
        ttk.Label(
            body,
            text="Save before leaving?",
            anchor="w",
            padding=(0, 6, 0, 12),
        ).pack(fill="x")

        buttons = ttk.Frame(body)
        buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(buttons, text="Save", command=self._on_save).pack(side="left")
        ttk.Button(buttons, text="Discard", command=self._on_discard).pack(side="left", padx=6)
        ttk.Button(buttons, text="Cancel", command=self._on_cancel).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.bind("<Escape>", lambda _e: self._on_cancel())
        self.after(0, self._focus_default)

    def _focus_default(self) -> None:
        try:
            self.focus_force()
        except Exception:
            pass

    def _finish(self, result: str) -> None:
        self._result = result
        self.destroy()

    def _on_save(self) -> None:
        self._finish("save")

    def _on_discard(self) -> None:
        self._finish("discard")

    def _on_cancel(self) -> None:
        self._finish("cancel")

    def show(self) -> str | None:
        """Block until the dialog is dismissed and return the chosen action."""

        self.wait_visibility()
        self.wait_window()
        return self._result


class AuthorTools(tk.Toplevel):  # pragma: no cover - simple UI wrapper
    """Toplevel window exposing authoring helpers for provider authors."""

    def __init__(self, master: tk.Misc, core: AppCore) -> None:
        super().__init__(master)
        use(self)
        palette = get_palette()
        self.configure(bg=palette["bg"])  # type: ignore[call-arg]
        style = ttk.Style(self)
        style.configure(
            "Treeview",
            background=palette["card"],
            fieldbackground=palette["card"],
            foreground=palette["ink"],
            bordercolor=palette["card_edge"],
        )
        style.map(
            "Treeview",
            background=[("selected", palette["primary_hover"])],
            foreground=[("selected", palette["on_primary"])],
        )
        style.configure(
            "TLabelframe",
            background=palette["bg"],
            foreground=palette["hdr_fg"],
        )
        style.configure(
            "TLabelframe.Label",
            background=palette["bg"],
            foreground=palette["title_accent"],font=10
        )

        #style.configure('TFrame',padding=12)

        style.configure("TLabel",font=(None, 10, "bold"))

        pid = core.state.provider_id or ""
        project_root: Path | None = core.state.project_root
        project = project_root.as_posix() if project_root else ""
        title = "Sigil – Author Tools"
        if pid:
            title += f" – {pid}"
        if project:
            title += f" – {project}"
        self._base_title = title
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
        self._dirty_tabs: dict[str, bool] = {"fields": False, "defaults": False, "untracked": False}
        self._window_dirty = False
        self._field_snapshot: dict[str, Any] | None = None
        self._current_tab = "fields"
        self._suspend_dirty = 0
        self._var_traces: list[tuple[tk.Variable, str]] = []
        self._widget_binds: list[tuple[tk.Widget, str, str]] = []
        self._suspend_tree_select = False
        self._current_tree_selection: str | None = None
        self.protocol("WM_DELETE_WINDOW", self._on_close_request)
        self._update_window_title()
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
    def _update_window_title(self) -> None:
        title = self._base_title
        dirty = any(self._dirty_tabs.values())
        if dirty:
            title = f"* {title}"
        try:
            self.title(title)
        except Exception:
            pass
        self._window_dirty = dirty

    def _set_dirty(self, tab: str, flag: bool) -> None:
        if self._dirty_tabs.get(tab) == flag:
            return
        self._dirty_tabs[tab] = flag
        self._update_window_title()

    def _dirty_any(self) -> bool:
        return any(self._dirty_tabs.values())

    def _clear_dirty_watchers(self) -> None:
        for var, trace_id in self._var_traces:
            try:
                var.trace_remove("write", trace_id)
            except Exception:
                pass
        self._var_traces.clear()
        for widget, sequence, bind_id in self._widget_binds:
            try:
                widget.unbind(sequence, bind_id)
            except Exception:
                pass
        self._widget_binds.clear()

    def _register_var_trace(self, var: tk.Variable) -> None:
        trace_id = var.trace_add("write", self._on_form_var_change)
        self._var_traces.append((var, trace_id))

    def _bind_widget_event(self, widget: tk.Widget, sequence: str) -> None:
        bind_id = widget.bind(sequence, self._on_widget_event, add=True)
        if bind_id:
            self._widget_binds.append((widget, sequence, bind_id))

    def _watch_widget(self, widget: tk.Widget) -> None:
        for seq in ("<KeyRelease>", "<ButtonRelease>", "<<ComboboxSelected>>", "<<ListboxSelect>>", "<<ListChanged>>"):
            self._bind_widget_event(widget, seq)
        for child in widget.winfo_children():
            if isinstance(child, tk.Widget):
                self._watch_widget(child)

    def _register_text_widget(self, widget: tk.Text) -> None:
        widget.edit_modified(False)
        bind_id = widget.bind("<<Modified>>", self._on_text_modified, add=True)
        if bind_id:
            self._widget_binds.append((widget, "<<Modified>>", bind_id))

    def _register_form_watchers(self) -> None:
        if tk is None:
            return
        self._clear_dirty_watchers()
        vars_to_watch = [
            getattr(self, "_key_var", None),
            getattr(self, "_label_var", None),
            getattr(self, "_desc_short_var", None),
            getattr(self, "_type_var", None),
            getattr(self, "_section_var", None),
            getattr(self, "_order_var", None),
        ]
        for var in vars_to_watch:
            if isinstance(var, tk.Variable):
                self._register_var_trace(var)
        desc = getattr(self, "_desc_text", None)
        if isinstance(desc, tk.Text):
            self._register_text_widget(desc)
        for widget in (self._value_widget, self._options_widget, self._form):
            if isinstance(widget, tk.Widget):
                self._watch_widget(widget)

    def _capture_form_state(self) -> dict[str, Any]:
        state: dict[str, Any] = {}
        if not hasattr(self, "_key_var"):
            return state
        state["current_key"] = self._current_key
        state["key"] = self._key_var.get() if hasattr(self, "_key_var") else ""
        state["label"] = self._label_var.get() if hasattr(self, "_label_var") else ""
        state["description_short"] = (
            self._desc_short_var.get() if hasattr(self, "_desc_short_var") else ""
        )
        if isinstance(getattr(self, "_desc_text", None), tk.Text):
            desc_widget: tk.Text = self._desc_text  # type: ignore[assignment]
            state["description"] = desc_widget.get("1.0", "end-1c")
        else:
            state["description"] = ""
        state["type"] = self._type_var.get() if hasattr(self, "_type_var") else ""
        state["section"] = self._section_var.get() if hasattr(self, "_section_var") else ""
        state["order"] = self._order_var.get() if hasattr(self, "_order_var") else ""
        default: Any | None = None
        if self._value_widget is not None and hasattr(self._value_widget, "get_value"):
            try:
                default = self._value_widget.get_value()  # type: ignore[attr-defined]
            except Exception:
                default = None
        state["default"] = deepcopy(default)
        options = self._collect_options()
        state["options"] = deepcopy(options) if options is not None else None
        return state

    def _store_field_snapshot(self) -> None:
        if not self._form.winfo_children():
            self._field_snapshot = None
            self._set_dirty("fields", False)
            return
        self._field_snapshot = deepcopy(self._capture_form_state())
        self._set_dirty("fields", False)

    def _apply_form_state(self, state: dict[str, Any] | None) -> None:
        if state is None:
            self._clear_form()
            return
        self._suspend_dirty += 1
        try:
            if hasattr(self, "_key_var"):
                self._key_var.set(state.get("key", ""))
            if hasattr(self, "_label_var"):
                self._label_var.set(state.get("label", ""))
            if hasattr(self, "_desc_short_var"):
                self._desc_short_var.set(state.get("description_short", ""))
            if isinstance(getattr(self, "_desc_text", None), tk.Text):
                desc_widget = self._desc_text  # type: ignore[assignment]
                desc_widget.delete("1.0", "end")
                desc_widget.insert("1.0", state.get("description", ""))
            if hasattr(self, "_section_var"):
                self._section_var.set(state.get("section", ""))
            if hasattr(self, "_order_var"):
                self._order_var.set(state.get("order", ""))
            type_name = state.get("type", "")
            if hasattr(self, "_type_var"):
                self._type_var.set(type_name)
            ft = TYPE_REGISTRY.get(type_name)
            self._build_type_section(ft, state.get("default"), state.get("options"))
        finally:
            self._suspend_dirty = max(0, self._suspend_dirty - 1)
        self._register_form_watchers()
        self._store_field_snapshot()

    def _update_dirty_state(self) -> None:
        if self._suspend_dirty or self._current_tab != "fields":
            return
        if self._field_snapshot is None:
            self._set_dirty("fields", bool(self._form.winfo_children()))
            return
        current = self._capture_form_state()
        self._set_dirty("fields", current != self._field_snapshot)

    def _on_form_var_change(self, *_args: object) -> None:
        if self._suspend_dirty:
            return
        self._update_dirty_state()

    def _on_widget_event(self, _event: object | None = None) -> None:
        if self._suspend_dirty:
            return
        self._update_dirty_state()

    def _on_text_modified(self, event: tk.Event) -> None:  # type: ignore[override]
        widget = event.widget
        try:
            widget.edit_modified(False)  # type: ignore[call-arg]
        except Exception:
            pass
        self._on_widget_event()

    def _on_close_request(self) -> None:
        self._confirm_unsaved(self.destroy)

    def _confirm_unsaved(
        self,
        on_continue: Callable[[], None],
        *,
        on_cancel: Callable[[], None] | None = None,
    ) -> None:
        if not self._dirty_any():
            on_continue()
            return
        dialog = UnsavedChangesDialog(self)
        choice = dialog.show() or "cancel"
        if choice == "save":
            if self._commit_current_tab():
                on_continue()
            else:
                if on_cancel is not None:
                    on_cancel()
        elif choice == "discard":
            self._discard_current_tab()
            on_continue()
        else:
            if on_cancel is not None:
                on_cancel()

    def _commit_current_tab(self) -> bool:
        if self._current_tab == "fields":
            return self._try_save_field()
        return True

    def _discard_current_tab(self) -> None:
        if self._current_tab == "fields":
            if self._field_snapshot is not None:
                self._apply_form_state(self._field_snapshot)
            else:
                self._clear_form()

    # ------------------------------------------------------------------
    def _clear_form(self) -> None:
        self._clear_dirty_watchers()
        for child in self._form.winfo_children():
            child.destroy()
        self._value_widget = None
        self._options_widget = None
        self._field_snapshot = None
        self._set_dirty("fields", False)

    # ------------------------------------------------------------------
    def _reload_tree(self) -> None:
        """Populate tree with defined fields and a collapsible undiscovered section."""

        pattern = self._search_var.get().strip().lower()
        current = self._current_tree_selection
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

        if current and self._tree.exists(current):
            self._select_tree_iid(current)
        else:
            if not self._tree.selection():
                self._current_tree_selection = None

    # ------------------------------------------------------------------
    def _select_tree_iid(self, iid: str) -> None:
        if not self._tree.exists(iid):
            return
        self._suspend_tree_select = True
        try:
            self._tree.selection_set(iid)
            self._tree.focus(iid)
        finally:
            self._suspend_tree_select = False
        self._current_tree_selection = iid

    def _restore_tree_selection(self) -> None:
        target = self._current_tree_selection
        self._suspend_tree_select = True
        try:
            if target and self._tree.exists(target):
                self._tree.selection_set(target)
                self._tree.focus(target)
            else:
                self._tree.selection_remove(self._tree.selection())
        finally:
            self._suspend_tree_select = False

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
        self._register_form_watchers()
        self._update_dirty_state()

    def _load_tree_node(self, node: str) -> None:
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
        self._current_tree_selection = node

    # ------------------------------------------------------------------
    def _on_select(self, _event: object | None = None) -> None:
        if self._suspend_tree_select:
            return
        sel = self._tree.selection()
        if not sel:
            return
        node = sel[0]
        if node == self._current_tree_selection:
            return

        def proceed() -> None:
            self._select_tree_iid(node)
            self._load_tree_node(node)

        if self._dirty_any():
            self._restore_tree_selection()
            self._confirm_unsaved(proceed)
            return
        proceed()

    def _on_add(self) -> None:
        def perform() -> None:
            self._suspend_tree_select = True
            try:
                self._tree.selection_remove(self._tree.selection())
            finally:
                self._suspend_tree_select = False
            self._current_tree_selection = None
            self._current_key = ""
            info = FieldInfo(key="", type="string")
            self._populate_form(info, None, undiscovered=False)

        if self._dirty_any():
            self._confirm_unsaved(perform)
        else:
            perform()

    # ------------------------------------------------------------------
    def _populate_form(self, info: FieldInfo, default: object | None, *, undiscovered: bool) -> None:
        self._clear_form()

        # Identity -------------------------------------------------------
        ident = ttk.LabelFrame(self._form, text=" Identity ", padding=(12,8,12,12)) #
        ident.pack(fill="x", pady=(0, 6))
        self._key_var = tk.StringVar(value=info.key)
        ttk.Label(ident, text="Key: ").grid(row=0, column=0, sticky="w")
        ttk.Entry(ident, textvariable=self._key_var).grid(row=0, column=1, sticky="ew")
        self._label_var = tk.StringVar(value=info.label or "")
        ttk.Label(ident, text="Label: ").grid(row=1, column=0, sticky="w")
        ttk.Entry(ident, textvariable=self._label_var).grid(row=1, column=1, sticky="ew")
        ident.columnconfigure(1, weight=1)

        # Descriptions ---------------------------------------------------
        desc_fr = ttk.LabelFrame(self._form, text=" Descriptions ", padding=(12,8,12,12))
        desc_fr.pack(fill="x", pady=(0, 6))
        self._desc_short_var = tk.StringVar(value=info.description_short or "")
        ttk.Label(desc_fr, text="Short: ").grid(row=0, column=0, sticky="w")
        short_entry = ttk.Entry(desc_fr, textvariable=self._desc_short_var)
        short_entry.grid(row=0, column=1, sticky="ew")
        self._desc_short_count = ttk.Label(desc_fr, text="0/0")
        self._desc_short_count.grid(row=0, column=2, sticky="e")
        desc_fr.columnconfigure(1, weight=1)

        def _update_count(*_args: object) -> None:
            n = len(self._desc_short_var.get())
            fg = "red" if n > SHORT_DESC_MAX else get_palette()['hdr_fg']
            self._desc_short_count.config(text=f"{n}/{SHORT_DESC_MAX}", foreground=fg)

        self._desc_short_var.trace_add("write", _update_count)
        _update_count()

        ttk.Label(desc_fr, text="Long: ").grid(row=1, column=0, sticky="nw")
        self._desc_text = tk.Text(desc_fr, height=4, wrap="word")
        self._desc_text.grid(row=1, column=1, columnspan=2, sticky="ew")
        if info.description:
            self._desc_text.insert("1.0", info.description)

        # Type -----------------------------------------------------------
        type_fr = ttk.LabelFrame(self._form, text=" Type ", padding=(12,8,12,12))
        type_fr.pack(fill="x", pady=(0, 6))
        self._type_var = tk.StringVar(value=info.type)
        ttk.Label(type_fr, text="Type: ").grid(row=0, column=0, sticky="w")
        type_combo = ttk.Combobox(
            type_fr,
            textvariable=self._type_var,
            state="readonly",
            values=sorted(TYPE_REGISTRY.keys()),
        )
        type_combo.grid(row=0, column=1, sticky="ew")
        type_combo.bind("<<ComboboxSelected>>", self._on_type_change)
        type_fr.columnconfigure(1, weight=1)

        self._opts_frame = ttk.LabelFrame(self._form, text=" Type Options ", padding=(12,8,12,12))
        self._opts_frame.pack(fill="x", pady=(0, 6))
        self._default_frame = ttk.LabelFrame(self._form, text=" Default ", padding=(12,8,12,12))
        self._default_frame.pack(fill="x", pady=(0, 6))
        ft = TYPE_REGISTRY.get(info.type)
        self._build_type_section(ft, default, info.options)

        # Grouping ------------------------------------------------------
        group_fr = ttk.LabelFrame(self._form, text=" Grouping ", padding=(12,8,12,12))
        group_fr.pack(fill="x", pady=(0, 6))
        self._section_var = tk.StringVar(value=info.section or "")
        ttk.Label(group_fr, text="Section: ").grid(row=0, column=0, sticky="w")
        ttk.Entry(group_fr, textvariable=self._section_var).grid(row=0, column=1, sticky="ew")
        self._order_var = tk.StringVar(
            value="" if info.order is None else str(info.order)
        )
        ttk.Label(group_fr, text="Order: ").grid(row=1, column=0, sticky="w")
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
        self._register_form_watchers()
        self._store_field_snapshot()

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

    def _try_save_field(self) -> bool:
        if self._current_key is None:
            return False
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
                return False
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
                return False
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
            return False
        self.adapter.upsert_field(key, type_name, **kwargs)  # type: ignore[arg-type]
        self._current_key = key
        target = f"defined:{key}" if key else None
        if target is not None:
            self._current_tree_selection = target
        self._reload_tree()
        defined = {f.key: f for f in self.adapter.list_defined()}
        info = defined.get(key)
        default_val = self.adapter.default_for_key(key)
        if info is not None:
            self._populate_form(info, default_val, undiscovered=False)
        if target is not None:
            self._select_tree_iid(target)
        return True

    def _on_save(self) -> None:
        self._try_save_field()

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
            self._current_tree_selection = None
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
        target = f"defined:{key}" if key else None
        if target is not None:
            self._current_tree_selection = target
        self._reload_tree()
        defined = {f.key: f for f in self.adapter.list_defined()}
        info = defined.get(key)
        default = self.adapter.default_for_key(key)
        if info is not None:
            self._populate_form(info, default, undiscovered=False)
        if target is not None:
            self._select_tree_iid(target)

    def _toggle_diff(self) -> None:
        if self._diff_shown.get():
            self._diff_frame.pack(fill="both", expand=True)
        else:
            self._diff_frame.pack_forget()
