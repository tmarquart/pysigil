from __future__ import annotations

import re

KeyPath = tuple[str, ...]


_SPLIT_RX = re.compile(r"[._]")


def parse_key(raw: str | KeyPath) -> KeyPath:
    """Parse *raw* into a canonical ``KeyPath``.

    ``raw`` may be a string using ``.`` or ``_`` as delimiters or an already
    split :class:`KeyPath` tuple. The function is pure and does not consult
    runtime preferences.
    """
    if isinstance(raw, tuple):
        return raw
    parts = _SPLIT_RX.split(raw) if _SPLIT_RX.search(raw) else [raw]
    if any(p == "" for p in parts):
        raise ValueError(f"Malformed key '{raw}'")
    return tuple(parts)
