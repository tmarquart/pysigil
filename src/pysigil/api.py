from __future__ import annotations

from pathlib import Path

from .backend_ini import read_sections, write_sections
from .core_defaults import CORE_DEFAULTS
from .defaults import DefaultsFormatError, load_provider_defaults
from .provider_id import pep503_name
from .resolver import DEFAULT_FILENAME, project_settings_file

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_settings_path(app: str) -> Path:
    return Path.home() / ".config" / app / DEFAULT_FILENAME


def _find_distribution(provider_id: str):  # pragma: no cover - thin wrapper
    try:
        from importlib.metadata import distributions
    except Exception:  # pragma: no cover
        return None
    for dist in distributions():
        name = getattr(dist, "metadata", {}).get("Name") or dist.name
        if name and pep503_name(name) == provider_id:
            return dist
    return None


def _merge_dicts(chain):
    result = {}
    for d in chain:
        for section, kv in d.items():
            result.setdefault(section, {}).update(kv)
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_value(
    provider_id: str,
    dotted_key: str,
    *,
    project_file: Path | None = None,
    app: str | None = None,
) -> str | None:
    app_name = app or provider_id
    project_path = project_settings_file(project_file)
    user_path = _user_settings_path(app_name)

    project_sections = read_sections(project_path)
    user_sections = read_sections(user_path)

    defaults = {}
    dist = _find_distribution(provider_id)
    if dist is not None:
        try:
            defaults = load_provider_defaults(provider_id, dist)
        except DefaultsFormatError:
            defaults = {}

    policy = CORE_DEFAULTS.get("pysigil", {}).get("policy", "project_over_user")
    policy = defaults.get("pysigil", {}).get("policy", policy)
    policy = project_sections.get("pysigil", {}).get("policy", policy)
    policy = user_sections.get("pysigil", {}).get("policy", policy)

    chain = [CORE_DEFAULTS]
    if defaults:
        chain.append(defaults)
    if policy == "project_over_user":
        chain.extend([user_sections, project_sections])
    else:
        chain.extend([project_sections, user_sections])
    merged = _merge_dicts(chain)

    section = f"provider:{provider_id}"
    return merged.get(section, {}).get(dotted_key)


def set_project_value(
    provider_id: str,
    dotted_key: str,
    value: str,
    *,
    project_file: Path | None = None,
) -> None:
    path = project_settings_file(project_file)
    data = read_sections(path)
    section = f"provider:{provider_id}"
    data.setdefault(section, {})[dotted_key] = value
    write_sections(path, data)


def set_user_value(
    provider_id: str,
    dotted_key: str,
    value: str,
    *,
    app: str | None = None,
) -> None:
    app_name = app or provider_id
    path = _user_settings_path(app_name)
    data = read_sections(path)
    section = f"provider:{provider_id}"
    data.setdefault(section, {})[dotted_key] = value
    write_sections(path, data)
