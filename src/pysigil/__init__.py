from .core import Sigil, SigilError
from .merge_policy import parse_key
from .policy import policy
from .toolkit import helpers_for, get_project_directory, get_user_directory


# Toggle visibility of machine-specific scopes in the UI.  When ``False``
# machine scopes such as ``user-local`` and ``project-local`` are hidden.
show_machine_scope = False


__all__ = [
    "Sigil",
    "SigilError",
    "parse_key",
    "policy",
    "helpers_for",
    "get_project_directory",
    "get_user_directory",
    "show_machine_scope",

]
