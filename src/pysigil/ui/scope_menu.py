"""Build per-row scope menu data structures.

This module contains a small helper that translates the specification for
the per-row scope dropdown into a framework agnostic representation.  The
resulting list can be consumed by concrete UI toolkits to render the menu
and wire callbacks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from .. import api


@dataclass
class Action:
    label: str
    enabled: bool = True
    handler: Callable[[], Any] | None = None


@dataclass
class ScopeRow:
    scope: str
    effective: bool = False
    present: bool = False
    actions: List[Action] = field(default_factory=list)

    def add(self, action: Action) -> None:
        self.actions.append(action)


@dataclass
class Separator:
    pass


def build_menu(
    handle: api.ProviderHandle,
    key: str,
    active_scope: str,
    policy,
) -> List[object]:
    """Return a list describing the per-row scope menu.

    The returned list contains :class:`Action`, :class:`ScopeRow` and
    :class:`Separator` instances as described in the specification.  Concrete
    view layers can interpret this structure to render the dropdown.
    """

    eff = handle.effective().get(key)
    layers = handle.layers().get(key, {})
    paths = {
        scope: handle.target_path(scope)
        for scope in ("user", "user-local", "project", "project-local")
    }

    def has(scope: str) -> bool:
        return layers.get(scope) is not None

    def writable(scope: str) -> bool:
        allows = getattr(policy, "allows", lambda s: True)
        return bool(allows(scope))

    menu: List[object] = []

    # Quick actions
    menu.append(Action(f"Edit at {active_scope}", enabled=writable(active_scope)))
    same_as_eff = has(active_scope) and eff is not None and layers[active_scope].value == eff.value
    copy_enabled = writable(active_scope) and eff is not None and eff.value is not None and not same_as_eff
    menu.append(
        Action(
            f"Copy effective here ({active_scope})",
            enabled=copy_enabled,
        )
    )
    menu.append(Separator())

    # Scopes list
    for scope in ["user", "user-local", "project", "project-local"]:
        row = ScopeRow(scope, effective=(eff is not None and eff.source == scope), present=has(scope))
        if has(scope):
            row.add(Action("Edit…", enabled=writable(scope)))
            row.add(Action("Remove", enabled=writable(scope)))
        else:
            row.add(Action("Add…", enabled=writable(scope)))
        menu.append(row)

    menu.append(Separator())
    menu.append(Action("Show layers…"))

    # Files
    for scope in ["user", "project", "user-local", "project-local"]:
        menu.append(Action(f"Open file for {scope}", enabled=paths.get(scope) is not None))

    return menu


__all__ = ["Action", "ScopeRow", "Separator", "build_menu"]

