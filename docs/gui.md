# Preferences GUI Overview

Sigil ships with a small Tk based GUI for editing user preferences. Install with
`pip install sigil[gui]` and run:

```
sigil gui --app myapp
```

Alternatively, launch it from Python:

```
from pysigil.ui.tk import launch

launch(initial_provider="myapp")
```

This opens a window showing all user-level preferences defined for *myapp*.

## Layout essentials

* Use regular list bullets for scope selectors; keep the glyphs crisp and
  aligned so the eye can scan down the stack quickly.
* Attach short tooltips to each bullet describing when that scope becomes the
  effective value.
* Keep the entire layout within a single view—avoid modal "smart navigation"
  hops so users can compare scopes at a glance.

## Effective, active, and missing values

The GUI highlights three states for every preference value:

* **Effective** – the value that will be read by clients.
* **Active** – the highest‑precedence scope that currently defines a value.
* **Missing** – scopes that do not define a value.

Example: a `timeout` preference across user, workspace, and machine scopes.

| Scope     | Value | Status                                    |
|-----------|-------|-------------------------------------------|
| User      | 45    | Effective and active (highest precedence) |
| Workspace | 60    | Present but inactive (overridden)         |
| Machine   | —     | Missing – inherits from higher scopes     |

When the user clears their value, the workspace entry becomes both active and
effective. Tooltips for each bullet echo the same explanation so users can
understand the transition without consulting documentation.

## Adapter boundary and scope handling

The GUI communicates with the core only through the
[`ProviderAdapter`](../src/pysigil/ui/provider_adapter.py). Widgets ask the
adapter which scopes to render, obtain human‑readable labels, and read or write
values. This separation keeps toolkit code decoupled from `pysigil.api`.

```python
from pysigil.ui.provider_adapter import ProviderAdapter

adapter = ProviderAdapter()
adapter.set_provider("demo")
for scope in adapter.scopes():
    print(adapter.scope_label(scope, short=True), adapter.can_write(scope))
```

Widgets render one bullet per scope and wire callbacks through the adapter:

```python
from pysigil.ui.tk.rows import FieldRow

def on_scope_selected(key: str, scope: str) -> None:
    adapter.set_value(key, scope, "42")

row = FieldRow(parent, adapter, "alpha", on_scope_selected)
```

Each selection invokes `on_scope_selected` with its scope, allowing dialogs or
other widgets to focus edits to that layer while the adapter manages precedence
and scope visibility.
