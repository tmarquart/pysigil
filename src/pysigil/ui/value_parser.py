from __future__ import annotations

from ..settings_metadata import TYPE_REGISTRY


def parse_field_value(type_name: str, raw: object) -> object:
    """Parse *raw* text into a Python value for ``type_name``.

    ``raw`` is typically the content of a text entry widget.  The function
    accepts ``1``/``0`` for booleans in addition to ``true``/``false`` to mirror
    the behaviour of the Tk dialogs.
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        text = raw.strip()
        if type_name == "boolean":
            lower = text.lower()
            if lower == "1":
                text = "true"
            elif lower == "0":
                text = "false"
        adapter = TYPE_REGISTRY[type_name].adapter
        return adapter.parse(text)
    return raw
