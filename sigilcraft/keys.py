from __future__ import annotations

import re

KeyPath = tuple[str, ...]


def parse_key(raw: str | KeyPath, delims: str | None = None) -> KeyPath:
    """Parse *raw* into a canonical ``KeyPath``.

    ``delims`` is a string containing single-character delimiters. If
    ``None``, ``"._"`` is used. An empty string disables splitting.
    """
    if isinstance(raw, tuple):
        return raw
    delims = "._" if delims is None else delims
    if not delims:
        return (raw,)
    pattern = "[" + re.escape(delims) + "]"
    parts = re.split(pattern, raw)
    if any(p == "" for p in parts):
        raise ValueError(
            f"Malformed key '{raw}' (consecutive/edge delimiter)"
        )
    return tuple(parts)
