import re

_re = re.compile(r"[-_.]+")


def pep503_name(dist_name: str) -> str:
    """Return the PEP 503 normalised project name."""
    return _re.sub("-", dist_name.strip().lower())
