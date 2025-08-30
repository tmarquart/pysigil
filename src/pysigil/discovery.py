from __future__ import annotations

import re
from collections.abc import Iterator
from importlib.metadata import Distribution, entry_points

GROUPS = ("pysigil_providers", "pysigil.providers")

_RE = re.compile(r"[-_.]+")
_VALID_RE = re.compile(r"^[a-z0-9-]+$")


def pep503_name(dist_name: str) -> str:
    """Return the PEP 503 normalised project name.

    ``dist_name`` must normalise to only contain lowercase letters, digits and
    hyphens.  Names containing path separators or ``..`` are rejected.
    """

    stripped = dist_name.strip()
    name = _RE.sub("-", stripped.lower())
    if (
        "/" in stripped
        or "\\" in stripped
        or ".." in stripped
        or not _VALID_RE.fullmatch(name)
    ):
        raise ValueError(f"invalid project name: {dist_name!r}")
    return name


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
