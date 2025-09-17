# pysigil MVP — Package-Author Integration Checklist

(Everything you need to do; everything you automatically get. Nothing more.)

Providers are auto-discovered by scanning installed distributions for
`.sigil/metadata.ini` and `.sigil/settings.ini`, so there are no Python entry
points or `pyproject.toml` hooks to maintain.

| # | Action you take in your package | Exact snippet / path | What pysigil gives you for free |
|---|--------------------------------|----------------------|--------------------------------|
| 1 | Create a defaults file under `.sigil` | `mypkg/.sigil/settings.ini`<br><br>```ini
[db]
host = localhost
port = 5432
``` | Becomes the base layer of the preference chain. |
| 2 | Register the package during development | ```bash
sigil author register --auto  # or `sigil setup` / `sigil register`
``` | Dev links let Sigil find your defaults without installing the package. |
| 3 | Ship settings and metadata files | ```toml
# pyproject.toml
[tool.setuptools.package-data]
"mypkg" = [".sigil/settings.ini", ".sigil/metadata.ini"]
``` | Installed distributions are scanned for these files—no Python entry points needed. |
| 4 | (Optional) Expose helpers so callers never touch pysigil APIs | ```python
# mypkg/__init__.py

from pysigil import (
    get_project_directory,
    get_user_directory,
    helpers_for,
)

get_setting, set_setting = helpers_for(__name__)

PROJECT_DATA = get_project_directory()
USER_DATA = get_user_directory(__name__)
__all__ = ["get_setting", "set_setting", "PROJECT_DATA", "USER_DATA"]

``` | • One-line access:<br>`get_setting("db.host")`<br>• Handles env ▶ project ▶ user ▶ defaults without extra code.<br>• Ready-to-use storage roots for data files. |


Launch authoring tools without starting the main editor:

```bash
sigil author
```

## What you get immediately

Fully merged prefs:
`SIGIL_MYPKG_DB_HOST (env) → ./settings.ini (project) → ~/.config/mypkg/settings.ini (user) → your defaults.ini.`

Need machine-specific values?  The default policy also includes an optional
`user-local` layer.  It lives alongside the regular user file but is named per
host and is handy for paths or secrets that shouldn't roam between machines.
If you don't need that separation simply ignore it—`pysigil` works fine without
the extra file.

No boiler-plate: call `get_setting()` / `set_setting()` from anywhere in your code.

Need to ship additional assets (templates, caches, exports)?  Use
`get_project_directory()` for project-scoped data and `get_user_directory()` for

per-user storage.  The project helper returns the shared ``.sigil/data``
directory for your workspace.  Combine it with
``pysigil.discovery.pep503_name(__name__)`` if you want a dedicated folder per
package.  The user helper normalises the application name so that ``mypkg`` and
``My-Pkg`` stay in sync with the settings helpers:

```python
from pysigil import get_project_directory, get_user_directory, helpers_for
from pysigil.discovery import pep503_name

get_setting, set_setting = helpers_for(__name__)
shared_root = get_project_directory()
shared_assets = shared_root / pep503_name(__name__) / "templates"

user_exports = get_user_directory(__name__) / "exports"
```

User tooling already works:

```
sigil get --app mypkg key
sigil set --app mypkg key value
```

Files auto-created as needed.

Zero runtime deps: pysigil is pure std-lib + your INI file.

That’s it. Add one defaults file, register a dev link, (optionally) four helper
lines — and your package instantly gains a robust, chain-aware configuration
system.

## Custom scopes

If the defaults are not enough you can extend the policy.  A *git-only* scope
keeps settings under version control while a *machine* scope stores
host-specific files.

```python
from pysigil.policy import Scope, ScopePolicy, policy

git_only = Scope("git", writable=True)
machine = Scope("ci", writable=True, machine=True)
custom = ScopePolicy([*policy._scopes, git_only, machine])
```

The `machine=True` flag causes the file name to include the host, e.g.
`settings-local-myhost.ini`.

The default set of scopes already contains a machine-specific `user-local`
layer.  If you don't need a separate file per host you can build a custom
policy without it:

```python
from pysigil.policy import ScopePolicy, policy

custom = ScopePolicy([s for s in policy._scopes if s.name != "user-local"])
```

