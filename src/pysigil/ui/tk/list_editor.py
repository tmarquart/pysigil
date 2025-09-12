"""Utility widgets for editing lists in tkinter.

This module provides :class:`ListEditor`, a small composite widget used in
`pysigil`'s tkinter UI to edit lists of values.  The widget supports three
modes:

``"simple"``
    A single column list of values (strings by default).
``"kv"``
    Two columns labelled ``key`` and ``value``.
``"choice"``
    Two columns labelled ``value`` and ``label`` suitable for enum choices.

The implementation intentionally keeps the feature set light weight – it is
primarily intended for tests and manual usage.  It nevertheless exposes a
couple of niceties such as duplicate removal and alphabetic sorting.  The
widget emits ``<<ListChanged>>`` whenever its contents change and offers
``get_list`` / ``set_list`` helpers for converting between the visual list and
Python data structures.

The companion :class:`ListEditDialog` wraps the editor in a modal ``Toplevel``
window and exposes an ``result`` attribute containing the edited list when the
user confirms the dialog.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Sequence

try:  # pragma: no cover - importing tkinter is environment dependent
    import tkinter as tk
    from tkinter import ttk, simpledialog, messagebox, filedialog
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore
    ttk = None  # type: ignore
    simpledialog = None  # type: ignore
    messagebox = None  # type: ignore
    filedialog = None  # type: ignore

import csv
from io import StringIO


Mode = Literal["simple", "kv", "choice"]


@dataclass
class Column:
    """Specification for a Treeview column."""

    id: str
    heading: str
    width: int = 140


class ListEditor(ttk.Frame):  # pragma: no cover - exercised via tk tests
    """Edit a list of values inside a :mod:`tkinter` application.

    Parameters largely mirror the spec from :mod:`AGENTS.md` and have been
    trimmed to fit within the repository's testing needs.  Normalisation and
    validation hooks can be supplied to influence how values are stored.
    """

    def __init__(
        self,
        master: tk.Widget,
        *,
        mode: Mode = "simple",
        value: Sequence[Any] | None = None,
        unique: bool = True,
        allow_empty: bool = False,
        max_items: int | None = None,
        validator: Callable[[Any], tuple[bool, str | None]] | None = None,
        normalizer: Callable[[Any], Any] | None = None,
        columns: Sequence[Column] | None = None,
        allow_reorder: bool = True,
        allow_sort: bool = True,
        allow_paste: bool = True,
        allow_import_export: bool = True,
    ) -> None:
        if tk is None:  # pragma: no cover - environment guard
            raise RuntimeError("tkinter is required for ListEditor")
        super().__init__(master)
        self.mode = mode
        self.unique = unique
        self.allow_empty = allow_empty
        self.max_items = max_items
        self.validator = validator
        self.normalizer = normalizer
        self.allow_reorder = allow_reorder
        self.allow_sort = allow_sort
        self.allow_paste = allow_paste
        self.allow_import_export = allow_import_export
        self._items: list[Any] = []
        self._build(columns)
        self.set_list(list(value or []))

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build(self, columns: Sequence[Column] | None) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=2, pady=2)
        ttk.Button(toolbar, text="Add", command=self._on_add).pack(side="left")
        ttk.Button(toolbar, text="Edit", command=self._on_edit).pack(side="left")
        ttk.Button(toolbar, text="Remove", command=self._on_remove).pack(side="left")
        if self.allow_reorder:
            ttk.Button(toolbar, text="↑", command=lambda: self._move(-1)).pack(
                side="left", padx=(6, 0)
            )
            ttk.Button(toolbar, text="↓", command=lambda: self._move(1)).pack(
                side="left"
            )
        if self.allow_sort:
            ttk.Button(toolbar, text="Sort", command=self.sort_items).pack(
                side="left", padx=(6, 0)
            )
        ttk.Button(toolbar, text="Dedupe", command=self.dedupe).pack(side="left")
        if self.allow_paste:
            ttk.Button(toolbar, text="Paste", command=self._on_paste).pack(
                side="left", padx=(6, 0)
            )
        if self.allow_import_export:
            ttk.Button(toolbar, text="Import CSV…", command=self._on_import).pack(
                side="left", padx=(6, 0)
            )
            ttk.Button(toolbar, text="Export CSV…", command=self._on_export).pack(
                side="left"
            )

        # determine columns
        if columns is None:
            if self.mode == "simple":
                columns = [Column("value", "Value", 200)]
            elif self.mode == "kv":
                columns = [Column("key", "Key"), Column("value", "Value")]
            else:  # choice
                columns = [Column("value", "Value"), Column("label", "Label")]
        self._columns = list(columns)

        self._tree = ttk.Treeview(
            self,
            columns=[c.id for c in self._columns],
            show="headings",
            selectmode="extended",
            height=8,
        )
        for col in self._columns:
            self._tree.heading(col.id, text=col.heading)
            self._tree.column(col.id, width=col.width, anchor="w")
        self._tree.pack(fill="both", expand=True, padx=2, pady=2)
        self._tree.bind("<Double-1>", lambda e: self._on_edit())

    # ------------------------------------------------------------------
    # List manipulation helpers
    # ------------------------------------------------------------------
    def get_list(self) -> list[Any]:
        """Return the currently edited list."""

        return list(self._items)

    def set_list(self, lst: Sequence[Any]) -> None:
        """Replace the contents of the editor with ``lst``."""

        self._items = list(lst)
        self._refresh_tree()
        self.event_generate("<<ListChanged>>")

    def set_readonly(self, flag: bool) -> None:
        """Enable/disable editing."""

        state = "disabled" if flag else "!disabled"
        for child in self.winfo_children():
            try:
                child.state([state])  # type: ignore[call-arg]
            except Exception:
                pass

    # -- internals -----------------------------------------------------
    def _norm(self, item: Any) -> Any:
        return self.normalizer(item) if self.normalizer else item

    def _validate(self, item: Any) -> tuple[bool, str | None]:
        if self.validator:
            return self.validator(item)
        if not self.allow_empty and item in ("", None):
            return False, "Empty values are not allowed"
        return True, None

    def _refresh_tree(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for idx, item in enumerate(self._items):
            values = self._item_to_row(item)
            self._tree.insert("", "end", iid=str(idx), values=values)

    def _item_to_row(self, item: Any) -> Sequence[str]:
        if self.mode == "simple":
            return [str(item)]
        elif self.mode == "kv":
            return [str(item.get("key", "")), str(item.get("value", ""))]
        else:  # choice
            return [str(item.get("value", "")), str(item.get("label", ""))]

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    def _on_add(self) -> None:
        item = self._prompt_item()
        if item is None:
            return
        if self.max_items is not None and len(self._items) >= self.max_items:
            return
        norm = self._norm(item)
        ok, _ = self._validate(norm)
        if not ok:
            return
        if self.unique and self._is_duplicate(norm):
            return
        self._items.append(norm)
        self._refresh_tree()
        self.event_generate("<<ListChanged>>")

    def _on_edit(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        item = self._items[idx]
        new_item = self._prompt_item(item)
        if new_item is None:
            return
        norm = self._norm(new_item)
        ok, _ = self._validate(norm)
        if not ok:
            return
        if self.unique:
            tmp = list(self._items)
            tmp[idx] = norm
            if self._is_duplicate(norm, tmp, idx):
                return
        self._items[idx] = norm
        self._refresh_tree()
        self.event_generate("<<ListChanged>>")

    def _on_remove(self) -> None:
        indices = sorted((int(i) for i in self._tree.selection()), reverse=True)
        for idx in indices:
            del self._items[idx]
        self._refresh_tree()
        if indices:
            self.event_generate("<<ListChanged>>")

    def _move(self, offset: int) -> None:
        if offset not in (-1, 1):
            return
        indices = sorted((int(i) for i in self._tree.selection()))
        if offset > 0:
            indices.reverse()
        moved = False
        for idx in indices:
            new_idx = idx + offset
            if not (0 <= new_idx < len(self._items)):
                continue
            self._items[idx], self._items[new_idx] = (
                self._items[new_idx],
                self._items[idx],
            )
            moved = True
        if moved:
            self._refresh_tree()
            self.event_generate("<<ListChanged>>")

    def sort_items(self) -> None:
        if not self.allow_sort:
            return
        key = self._sort_key
        self._items.sort(key=key)
        self._refresh_tree()
        self.event_generate("<<ListChanged>>")

    def _sort_key(self, item: Any) -> Any:
        if self.mode == "simple":
            return item
        if self.mode == "kv":
            return (item.get("key"), item.get("value"))
        return (item.get("label"), item.get("value"))

    def dedupe(self) -> None:
        seen: set[Any] = set()
        result: list[Any] = []
        for item in self._items:
            key = self._norm_key(item)
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        if len(result) != len(self._items):
            self._items = result
            self._refresh_tree()
            self.event_generate("<<ListChanged>>")

    def _norm_key(self, item: Any) -> Any:
        if self.mode == "simple":
            return self._norm(item)
        if self.mode == "kv":
            return self._norm(item.get("key"))
        return self._norm(item.get("value"))

    def _is_duplicate(self, item: Any, items: Sequence[Any] | None = None, idx: int | None = None) -> bool:
        items = items if items is not None else self._items
        key = self._norm_key(item)
        for i, existing in enumerate(items):
            if idx is not None and i == idx:
                continue
            if self._norm_key(existing) == key:
                return True
        return False

    def _on_paste(self) -> None:
        if simpledialog is None:
            return
        text = simpledialog.askstring("Paste", "Enter items, one per line:", parent=self)
        if not text:
            return
        items = [t.strip() for t in text.replace(",", "\n").splitlines()]
        for raw in items:
            if not raw and not self.allow_empty:
                continue
            norm = self._norm(raw)
            ok, _ = self._validate(norm)
            if not ok or (self.unique and self._is_duplicate(norm)):
                continue
            if self.max_items is not None and len(self._items) >= self.max_items:
                break
            self._items.append(norm)
        self._refresh_tree()
        self.event_generate("<<ListChanged>>")

    def _on_import(self) -> None:
        if filedialog is None:
            return
        path = filedialog.askopenfilename(parent=self, filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with open(path, newline="", encoding="utf8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        if self.mode != "simple" and rows and len(rows[0]) == len(self._columns):
            rows = rows[1:]
        items: list[Any] = []
        for row in rows:
            if self.mode == "simple":
                items.append(row[0])
            elif self.mode == "kv":
                items.append({"key": row[0], "value": row[1] if len(row) > 1 else ""})
            else:
                items.append({"value": row[0], "label": row[1] if len(row) > 1 else ""})
        self.set_list(items)

    def _on_export(self) -> None:
        if filedialog is None:
            return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".csv")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf8") as f:
            writer = csv.writer(f)
            if self.mode != "simple":
                writer.writerow([c.heading for c in self._columns])
            for item in self._items:
                writer.writerow(self._item_to_row(item))

    # ------------------------------------------------------------------
    # Prompt helpers
    # ------------------------------------------------------------------
    def _prompt_item(self, initial: Any | None = None) -> Any | None:
        if simpledialog is None:
            return None
        if self.mode == "simple":
            return simpledialog.askstring("Value", "Value:", parent=self, initialvalue=str(initial or ""))
        if self.mode == "kv":
            key = simpledialog.askstring(
                "Key", "Key:", parent=self, initialvalue=str(initial.get("key", "") if isinstance(initial, dict) else "")
            )
            if key is None:
                return None
            val = simpledialog.askstring(
                "Value", "Value:", parent=self, initialvalue=str(initial.get("value", "") if isinstance(initial, dict) else "")
            )
            if val is None:
                return None
            return {"key": key, "value": val}
        value = simpledialog.askstring(
            "Value", "Value:", parent=self, initialvalue=str(initial.get("value", "") if isinstance(initial, dict) else "")
        )
        if value is None:
            return None
        label = simpledialog.askstring(
            "Label", "Label:", parent=self, initialvalue=str(initial.get("label", "") if isinstance(initial, dict) else "")
        )
        if label is None:
            return None
        return {"value": value, "label": label}


class ListEditDialog(tk.Toplevel):  # pragma: no cover - exercised via tk tests
    """Modal dialog embedding :class:`ListEditor`."""

    def __init__(self, parent: tk.Widget, **kwargs: Any) -> None:
        if tk is None:  # pragma: no cover - environment guard
            raise RuntimeError("tkinter is required for ListEditDialog")
        super().__init__(parent)
        self.title("Edit List")
        self.transient(parent)
        self.grab_set()
        self.resizable(True, True)
        body = ttk.Frame(self, padding=6)
        body.pack(fill="both", expand=True)
        self.editor = ListEditor(body, **kwargs)
        self.editor.pack(fill="both", expand=True)
        buttons = ttk.Frame(body)
        buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(buttons, text="OK", command=self._on_ok).pack(
            side="right", padx=2
        )
        ttk.Button(buttons, text="Cancel", command=self._on_cancel).pack(
            side="right", padx=2
        )
        self.result: list[Any] | None = None

    def _on_ok(self) -> None:
        # Validate the whole list before accepting
        items = self.editor.get_list()
        for item in items:
            ok, err = self.editor._validate(item)
            if not ok:
                if messagebox is not None:
                    messagebox.showerror("Invalid", err or "invalid value", parent=self)
                self.editor.focus_set()
                self.event_generate("<<ListValidated>>")
                return
        self.result = items
        self.event_generate("<<ListValidated>>")
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()


__all__ = ["ListEditor", "ListEditDialog", "Column"]
