from __future__ import annotations

import re

from .constants import BOOT_KEY_DELIMITERS

KeyPath = tuple[str, ...]


def get_pref(key: str, default: str | None = None) -> str | None:  # pragma: no cover - patched at runtime
    return default


def parse_key(raw: str | KeyPath, delims: str | None = None) -> KeyPath:
    """Parse *raw* into a canonical ``KeyPath``.

    ``delims`` is a string containing single-character delimiters. If
    ``None``, the active ``sigil.key_delimiters`` preference is used, falling
    back to :data:`BOOT_KEY_DELIMITERS`. An empty string disables splitting.
    """
    if isinstance(raw, tuple):
        return raw
    if delims is None:
        delims = get_pref("sigil.key_delimiters", BOOT_KEY_DELIMITERS) or BOOT_KEY_DELIMITERS
    if not delims:
        return (raw,)
    pattern = "[" + re.escape(delims) + "]"
    parts = re.split(pattern, raw)
    if any(p == "" for p in parts):
        raise ValueError(
            f"Malformed key '{raw}' (consecutive/edge delimiter)"
        )
    return tuple(parts)
