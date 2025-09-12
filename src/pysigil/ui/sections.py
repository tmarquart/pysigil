from __future__ import annotations

from typing import Dict, List

from ..api import FieldInfo


def field_sort_key(f: FieldInfo) -> tuple[int, str, str]:
    """Sorting key for fields within a section."""
    return (
        10**9 if f.order is None else f.order,
        (f.label or f.key).casefold(),
        f.key,
    )


def bucket_by_section(fields: List[FieldInfo]) -> Dict[str, List[FieldInfo]]:
    """Group fields by section name.

    Field sections are treated case-insensitively. Fields without a section are
    grouped under ``"Other"``.
    """
    groups: Dict[str, List[FieldInfo]] = {}
    name_map: Dict[str, str] = {}
    for f in fields:
        sec = f.section or "Other"
        norm = sec.casefold()
        display = name_map.setdefault(norm, sec)
        groups.setdefault(display, []).append(f)
    return groups


def compute_section_order(
    fields: List[FieldInfo], provider_order: List[str] | None
) -> List[str]:
    """Determine display order for sections.

    The order starts with ``provider_order`` if supplied, followed by any
    additional sections derived from ``fields`` in alphabetical order. A section
    named ``"Untracked"`` (case-insensitively) is always forced to the end.
    """
    mapping: Dict[str, str] = {}
    if provider_order:
        for sec in provider_order:
            mapping.setdefault(sec.casefold(), sec)
    for f in fields:
        sec = f.section or "Other"
        mapping.setdefault(sec.casefold(), sec)

    order: List[str] = []
    seen: set[str] = set()
    if provider_order:
        for sec in provider_order:
            norm = sec.casefold()
            if norm in mapping and norm not in seen:
                order.append(mapping[norm])
                seen.add(norm)

    remaining = [disp for norm, disp in mapping.items() if norm not in seen]
    remaining.sort(key=lambda s: s.casefold())

    untracked = [s for s in remaining if s.casefold() == "untracked"]
    remaining = [s for s in remaining if s.casefold() != "untracked"]

    order.extend(remaining)
    order.extend(untracked)
    return order


__all__ = [
    "field_sort_key",
    "bucket_by_section",
    "compute_section_order",
]
