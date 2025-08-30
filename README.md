# pysigil

Preference management for small apps.

## Quick start

Install pysigil in a virtual environment to make the `sigil` and `pysigil` commands available:

```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\Activate
pip install -e .  # or `pip install .` for a normal install
```

```bash
sigil --help
# or
pysigil --help
# or
python -m pysigil --help
```

```python
from pysigil.gui.hub import get_preferences
get_pref, set_pref, sigil = get_preferences("pysigil")
```

Once installed, try a few commands:

```bash
sigil set ui.color blue --app demo
sigil get ui.color --app demo
sigil export --app demo
```

The CLI stores data under your user config directory (e.g. `~/.config/sigil/demo/settings.ini`),
so you can run these commands right from the source tree without creating a
separate project. See `tests/manual_tests/README.md` for more examples.

Typed helper methods are available for convenient access:
`Sigil.get_int()`, `get_float()`, `get_bool()`.
For package integration details see [docs/integration.md](docs/integration.md).

## Policy API

The merge order and write permissions are managed by a configurable
`ScopePolicy`.  The default policy prefers project settings over user ones.
To inspect or extend the policy:

```python
from pysigil.policy import Scope, ScopePolicy, policy

# clone and add a git-tracked scope
scopes = [*policy._scopes, Scope("git", writable=True)]
git_policy = ScopePolicy(scopes)

# precedence can be switched at runtime
policy.set_store("user", {("pysigil", "policy"): "user_over_project"})
```

## Using the GUI

pysigil ships with a simple graphical editor for viewing and editing
preferences. After installation launch it with:

```bash
sigil gui
```


Any providers with existing configuration directories (e.g.
`~/.config/sigil/user-custom`) are automatically listed in the package
selector.


To initialise or inspect the user configuration directory from a small
helper interface, run:

```bash
sigil config gui
```


Click **Initialize User Custom** to create a per-host `user-custom` section.
A confirmation dialog appears and the folder opens (e.g.
`~/.config/sigil/user-custom`) so you can edit the newly created file.



Package authors can register development defaults via:

```bash
sigil setup
```

Or launch it programmatically:

```python
from pysigil.gui import launch_gui
launch_gui()
```
