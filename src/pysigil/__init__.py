from .core import Sigil, SigilError
from .merge_policy import parse_key
from .policy import policy
from .toolkit import get_setting, init, set_setting

__all__ = [
    "Sigil",
    "SigilError",
    "parse_key",
    "policy",
    "init",
    "get_setting",
    "set_setting",
]
