# Launching the Preferences GUI

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

## Debug logging

Set the environment variable `SIGIL_GUI_DEBUG=1` before launching the GUI to
emit verbose debug information to the console.  This can help diagnose problems
with package loading or preference updates and can be disabled by unsetting the
variable.

## Adapter boundary and scope handling

The GUI communicates with the core only through the
[`ProviderAdapter`](../src/pysigil/ui/provider_adapter.py).  Widgets ask the
adapter which scopes to render, obtain human‑readable labels, and read or write
values.  This separation keeps toolkit code decoupled from `pysigil.api`.

```python
from pysigil.ui.provider_adapter import ProviderAdapter

adapter = ProviderAdapter()
adapter.set_provider("demo")
for scope in adapter.scopes():
    print(adapter.scope_label(scope, short=True), adapter.can_write(scope))
```

Toolkit components can mirror the prototype’s pill behaviour by wiring the
adapter into callbacks:

```python
from pysigil.ui.tk.rows import FieldRow

def on_pill_click(key: str, scope: str) -> None:
    adapter.set_value(key, scope, "42")

row = FieldRow(parent, adapter, "alpha", on_pill_click)
```

Each pill invokes `on_pill_click` with its scope, allowing dialogs or other
widgets to focus edits to that layer while the adapter manages precedence and
scope visibility.
