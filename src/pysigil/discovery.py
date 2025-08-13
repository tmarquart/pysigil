from __future__ import annotations

from collections.abc import Iterator
from importlib.metadata import Distribution, entry_points
import re

GROUPS = ("pysigil_providers", "pysigil.providers")

_RE = re.compile(r"[-_.]+")


def pep503_name(dist_name: str) -> str:
    """Return the PEP 503 normalised project name."""
    return _RE.sub("-", dist_name.strip().lower())


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


def iter_providers() -> Iterator[tuple[str, str, Distribution]]:
    """Yield unique providers discovered via entry points.

    Each item is ``(provider_id, display_name, dist)``.  Duplicate provider IDs
    are skipped with first-come wins semantics.
    """
    seen: set[str] = set()
    for ep in _iter_entry_points():
        dist: Distribution = ep.dist  # type: ignore[attr-defined]
        name = getattr(dist, "metadata", {}).get("Name") or dist.name
        if not name:
            continue
        provider_id = pep503_name(name)
        if provider_id in seen:
            continue
        seen.add(provider_id)
        yield provider_id, name, dist
