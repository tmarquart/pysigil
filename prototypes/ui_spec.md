# Sigil GUI Wiring Plan — **Default** & Central Policy (Final Handoff)

This is the **hand‑off spec** for wiring the current Tk UI to `sigil.api`. It removes any local assumptions about scope precedence and treats **Default** as a first‑class scope. You can give this doc directly to Codex along with the existing prototype.

---

## Ground rules

* **Precedence is centralized.** The UI must not hard‑code any scope order. It asks the orchestrator (or adapter) for the **display order** and for the **effective source**.
* **Scopes are centrally defined.** The set of scopes comes from the orchestrator; the UI renders whatever it’s given.
* **Default is a real scope.** It represents the provider’s default/spec value and **always exists** (bottom of precedence by policy). Whether Default is writable is determined by policy.
* **Env overlay is optional.** If present, it’s just another scope surfaced by policy. Whether it’s writable comes from policy.

---

## Minimal adapter (between UI and `sigil.api`)

Codex should implement an adapter so the UI never reaches into `sigil.api` directly. Names below are suggestions; keep them stable.

```python
class ProviderAdapter:
    def __init__(self, api_handle):
        self.h = api_handle

    # Provider / scope discovery
    def list_providers(self) -> list[str]: ...
    def set_provider(self, provider_id: str) -> None: ...

    def scopes(self) -> list[str]:
        """Return scope IDs in **display order** as defined by central policy.
        Example: ["Env", "User", "Machine", "Project", "ProjectMachine", "Default"]
        Not all scopes must appear; Env may be omitted by policy.
        """

    def scope_label(self, scope_id: str, short: bool = False) -> str: ...
    def can_write(self, scope_id: str) -> bool: ...
    def is_overlay(self, scope_id: str) -> bool: ...  # e.g., Env

    # Values
    def values_for_key(self, key: str) -> dict[str, "ValueInfo"]:
        """Return raw values per scope (missing scope ⇒ no entry)."""

    def effective_for_key(self, key: str) -> tuple[object | None, str | None]:
        """(value, source_scope) according to central precedence."""

    def default_for_key(self, key: str) -> object | None:
        """Convenience for the Default scope’s value."""

    # Writes
    def set_value(self, key: str, scope_id: str, value: object) -> None: ...
    def clear_value(self, key: str, scope_id: str) -> None: ...

    # Hints
    def target_path(self, scope_id: str) -> str: ...
    def fields(self) -> list[str]: ...        # ordered per provider spec
    def field_info(self, key: str) -> "FieldInfo": ...  # type, label, description
```

**`ValueInfo`** (suggested): `{ value: any, error: str | None }`.

> If the core API doesn’t yet expose `scopes()` or `effective_for_key()`, the adapter should compute them using the centralized policy entry points (`policy.scopes()`, `policy.precedence()`, etc.). The UI never hard‑codes.

---

## UI rendering rules (what the adapter must enable)

* **Rows** show: `Key | Value (effective) | Scope pills | Edit…`.
* **Value (effective)** is read‑only and shows `🔒 <value>  (<scope_label>)`.
* **Scope pills** use the list from `adapter.scopes()` and tooltips from `scope_label(scope, short=False)`.

  * `effective` scope → filled pill (white text)
  * `present` scope (has a value but not effective) → white pill with 2px colored outline
  * `empty` scope (no value) → gray outline (hidden in Compact mode)
  * `disabled` (policy says cannot write) → gray fill, not clickable
* **Always show `Default`.** It must appear in `adapter.scopes()` and be rendered even if other scopes are empty. Tooltip shows its value.
* **Compact mode:** show only scopes with values **plus** `Default`. Full mode shows all scopes.

---

## Interactions & events

* **Click a pill** → open the Edit dialog **focused to that scope** (no‑op if policy makes it read‑only).
* **Right‑click a pill** → context menu: `Edit…`; and `Remove` when the scope currently has a value and is writable.
* **Edit dialog**

  * One row per scope returned by `adapter.scopes()`.
  * Each row shows the current value; controls (Save/Remove) are enabled only if `can_write(scope)`.
  * `Default` row is present. Whether it’s writable is governed by `can_write("Default")`.
  * If `ValueInfo.error` exists, show `⚠︎` and the parse message under that row.

**Callbacks Codex wires:**

```python
def on_pill_click(key: str, scope_id: str):
    # open dialog and focus that scope

def on_edit_save(key: str, scope_id: str, value):
    adapter.set_value(key, scope_id, value); refresh_row(key)

def on_edit_remove(key: str, scope_id: str):
    adapter.clear_value(key, scope_id); refresh_row(key)

# Optional
def on_provider_change(provider_id: str): ...
def on_toggle_compact(is_compact: bool): ...
```

---

## Acceptance checklist

* [ ] The **scope list** and **order** come from `adapter.scopes()`; no hard‑coded precedence in the UI.
* [ ] **Default** is always rendered as a pill with a tooltip showing its value.
* [ ] **Effective** value and source update correctly after Save/Remove.
* [ ] **Compact mode** hides empty scopes but **never hides Default**.
* [ ] Policy makes non‑writable scopes disabled in both dialog and pills.
* [ ] Context menu shows **Remove** only when the scope has a value and is writable.
* [ ] Tooltips show `Full Scope Name: raw value` (no truncation issues).

---

## Notes for Codex

* Keep the adapter boundary: **UI → Adapter → `sigil.api`**.
* Use the existing UI components (pills, dialog). Swap the current stub for `ProviderAdapter` and map the callbacks.
* Avoid `ttk` background lookups (`cget('background')`) in Canvas; they throw on ttk widgets.
* Rows should **refresh in place**; no full rebuilds on every change.

---

## Change log vs prior draft

* Replaced the synthetic **Def** pill with a real **Default** scope.
* Removed the locally defined **scope model/precedence**; the UI now asks the adapter for `scopes()` and the effective source.
* Clarified that **Default** is always visible and exists regardless of other layers.
