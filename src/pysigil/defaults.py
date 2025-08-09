from __future__ import annotations

from importlib.metadata import Distribution
from pathlib import Path
from typing import Dict

from .backend_ini import read_sections


class DefaultsFormatError(Exception):
    pass


def load_provider_defaults(provider_id: str, dist: Distribution) -> Dict[str, Dict[str, str]]:
    """Load provider defaults from a distribution.

    Parameters
    ----------
    provider_id:
        PEP 503 normalised provider name.
    dist:
        Distribution object representing the provider.
    """
    cfg_path = Path(dist.locate_file("pysigil/defaults.ini"))
    if not cfg_path.is_file():
        return {}
    data = read_sections(cfg_path)
    expected_section = f"provider:{provider_id}"
    for section in data:
        if section.startswith("provider:") and section != expected_section:
            raise DefaultsFormatError("provider section name mismatch")
    if expected_section not in data:
        raise DefaultsFormatError("missing provider section")
    result: Dict[str, Dict[str, str]] = {expected_section: data[expected_section]}
    if "pysigil" in data:
        result["pysigil"] = data["pysigil"]
    return result
