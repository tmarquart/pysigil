"""Form utility for editing field options.

The :class:`OptionsForm` class introspects the ``option_model`` dataclass
associated with a :class:`~pysigil.settings_metadata.FieldType` and renders
appropriate editor widgets for each field.  The widget layer itself is kept
very small and reuses the generic editor widgets exposed by
:mod:`pysigil.ui.widgets`.

Only a subset of basic field types is currently supported: ``str``, ``int``,
``float``, ``bool`` and ``list[str]``.  For more elaborate editors a
:class:`~pysigil.settings_metadata.FieldType` can supply its own ``option_widget``
which is used instead of the automatic dataclass based rendering.
"""

from __future__ import annotations

from dataclasses import asdict, fields, is_dataclass
from typing import Any, Mapping, get_args, get_origin, get_type_hints, Union
from types import UnionType

from ..settings_metadata import TYPE_REGISTRY, FieldType
from .widgets import EditorWidget

try:  # pragma: no cover - importing tkinter is environment dependent
    import tkinter as tk  # type: ignore
    from tkinter import ttk  # type: ignore
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore
    ttk = None  # type: ignore


class OptionsForm(ttk.Frame):
    """Render editors for a field type's option model."""

    def __init__(self, master, field_type: str | FieldType) -> None:
        if tk is None or ttk is None:  # pragma: no cover - tkinter missing
            raise RuntimeError("tkinter is required for OptionsForm")
        super().__init__(master, style="CardBody.TFrame")
        self._ft = TYPE_REGISTRY[field_type] if isinstance(field_type, str) else field_type
        self._option_model = self._ft.option_model
        self._widgets: dict[str, EditorWidget] = {}
        self._fields: dict[str, tuple[str, bool]] = {}
        self._custom: EditorWidget | None = None
        if self._ft.option_widget is not None:
            self._custom = self._ft.option_widget(self)
        elif self._option_model is not None and is_dataclass(self._option_model):
            self._build_from_model()
        # when there is neither a custom widget nor option model the form stays empty

    # ------------------------------------------------------------------
    def _build_from_model(self) -> None:
        assert self._option_model is not None
        hints = get_type_hints(self._option_model, include_extras=True)
        for row, f in enumerate(fields(self._option_model)):
            tp = hints.get(f.name, f.type)
            key, optional = self._field_key(tp)
            ft = TYPE_REGISTRY[key]
            if ft.value_widget is None:
                raise TypeError(f"no widget for option field type {key}")
            widget = ft.value_widget(self)  # type: ignore[assignment]
            label = ttk.Label(self, text=f.name.replace("_", " "), style="Card.TLabel")
            label.grid(row=row, column=0, sticky="w", padx=4, pady=2)
            widget.grid(row=row, column=1, sticky="ew", padx=4, pady=2)
            self._widgets[f.name] = widget
            self._fields[f.name] = (key, optional)
        self.columnconfigure(1, weight=1)

    # ------------------------------------------------------------------
    @staticmethod
    def _unwrap_optional(tp: Any) -> tuple[bool, Any]:
        origin = get_origin(tp)
        if origin in (Union, UnionType):
            args = [a for a in get_args(tp) if a is not type(None)]
            if len(args) == 1:
                return True, args[0]
        return False, tp

    def _field_key(self, tp: Any) -> tuple[str, bool]:
        optional, base = self._unwrap_optional(tp)
        origin = get_origin(base)
        if origin is list and get_args(base) == (str,):
            return "string_list", optional
        mapping = {str: "string", int: "integer", float: "number", bool: "boolean"}
        key = mapping.get(base)
        if key is None:
            raise TypeError(f"unsupported option field type: {tp!r}")
        return key, optional

    def _parse_value(self, key: str, optional: bool, raw: Any) -> Any:
        if raw in (None, "") and optional:
            return None
        ft = TYPE_REGISTRY[key]
        to_parse = None if raw in (None, "") else raw
        if to_parse is not None and not isinstance(to_parse, str):
            to_parse = ft.adapter.serialize(to_parse)
        return ft.adapter.parse(to_parse)

    def _format_value(self, key: str, value: Any) -> Any:
        if value is None:
            return None
        ft = TYPE_REGISTRY[key]
        if isinstance(value, str):
            if key == "boolean":
                try:
                    return ft.adapter.parse(value)
                except Exception:
                    return value
            return value
        try:
            serialized = ft.adapter.serialize(value)
        except Exception:
            return value
        if key == "boolean":
            try:
                return ft.adapter.parse(serialized)
            except Exception:
                return serialized
        return serialized

    # ------------------------------------------------------------------
    def get_values(self) -> dict[str, Any]:
        if self._custom is not None:
            val = self._custom.get_value()
            return val if isinstance(val, dict) else {}
        values: dict[str, Any] = {}
        for name, widget in self._widgets.items():
            key, optional = self._fields[name]
            raw = widget.get_value()
            values[name] = self._parse_value(key, optional, raw)
        return values

    def set_values(self, values: Mapping[str, Any] | Any | None) -> None:
        if self._custom is not None:
            self._custom.set_value({} if values is None else (asdict(values) if is_dataclass(values) else values))
            return
        if values is None:
            values = {}
        if is_dataclass(values):
            values = asdict(values)
        for name, widget in self._widgets.items():
            key, _ = self._fields[name]
            widget.set_value(self._format_value(key, values.get(name)))

    def validate(self) -> dict[str, str | None]:
        if self._custom is not None:
            # delegate validation to dataclass if available
            data = self._custom.get_value() or {}
            errors: dict[str, str | None] = {}
            if self._option_model is not None:
                try:
                    self._option_model(**data)
                except Exception as exc:  # pragma: no cover - defensive
                    errors["__all__"] = str(exc)
                else:
                    errors["__all__"] = None
            return errors
        errors: dict[str, str | None] = {}
        data: dict[str, Any] = {}
        for name, widget in self._widgets.items():
            key, optional = self._fields[name]
            raw = widget.get_value()
            try:
                value = self._parse_value(key, optional, raw)
            except Exception as exc:
                widget.set_error(str(exc))
                errors[name] = str(exc)
            else:
                widget.set_error(None)
                data[name] = value
                errors[name] = None
        if errors and any(v is not None for v in errors.values()):
            return errors
        if self._option_model is not None:
            try:
                self._option_model(**data)
            except Exception as exc:  # pragma: no cover - defensive
                errors["__all__"] = str(exc)
            else:
                errors["__all__"] = None
        return errors


__all__ = ["OptionsForm"]
