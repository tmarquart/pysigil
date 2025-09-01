from __future__ import annotations

import re
from collections.abc import Iterator
from importlib.metadata import Distribution, distributions

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


def iter_installed_providers() -> Iterator[tuple[str, str, Distribution]]:
    """Yield unique providers from installed distributions.

    A distribution is considered a provider if it contains a
    ``.sigil/metadata.ini`` resource.  Each item yielded is
    ``(provider_id, display_name, dist)`` with duplicates skipped using
    first-come wins semantics.
    """

    seen: set[str] = set()
    for dist in distributions():
        files = getattr(dist, "files", None)
        if not files:
            continue

        if not any(p.parts[-2:] == (".sigil", "metadata.ini") for p in files):
            continue

        metadata = getattr(dist, "metadata", None)
        name = metadata.get("Name") if metadata is not None else dist.name
        if not name:
            name = dist.name
        if not name:
            continue

        provider_id = pep503_name(name)
        if provider_id in seen:
            continue
        seen.add(provider_id)
        yield provider_id, name, dist
