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
from pysigil import get_project_directory, get_user_directory, helpers_for

get_setting, set_setting = helpers_for("pysigil")
project_assets = get_project_directory()
user_assets = get_user_directory("pysigil")

get_setting("ui.color")
set_setting("ui.color", "blue")
print(project_assets)
print(user_assets)
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
Project and user data folders are provided via
`get_project_directory()` / `get_user_directory()` and are created on demand.
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
sigil register  # alias: `sigil setup`
```

Launch authoring tools without the editor:

```bash
sigil author
```

Or launch it programmatically:

```python
from pysigil.ui.tk import launch

launch()
```
