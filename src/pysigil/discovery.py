from __future__ import annotations

from importlib.metadata import entry_points, Distribution
from typing import Iterator, Tuple

from .provider_id import pep503_name

GROUPS = ("pysigil_providers", "pysigil.providers")


def _iter_entry_points():
    eps = entry_points()
    if hasattr(eps, "select"):
        for group in GROUPS:
            for ep in eps.select(group=group):
                yield ep
    else:  # pragma: no cover - legacy API
        for group in GROUPS:
            for ep in eps.get(group, []):  # type: ignore[call-arg]
                yield ep


def iter_providers() -> Iterator[Tuple[str, str, Distribution]]:
    """Yield unique providers discovered via entry points.

    Each item is ``(provider_id, display_name, dist)``.  Duplicate provider IDs
    are skipped with first-come wins semantics.
    """
    seen: set[str] = set()
    for ep in _iter_entry_points():
        dist: Distribution = ep.dist  # type: ignore[attr-defined]
        name = getattr(dist, "metadata", {}).get("Name") or getattr(dist, "name")
        if not name:
            continue
        provider_id = pep503_name(name)
        if provider_id in seen:
            continue
        seen.add(provider_id)
        yield provider_id, name, dist
