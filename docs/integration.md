# pysigil MVP — Package-Author Integration Checklist

(Everything you need to do; everything you automatically get. Nothing more.)

| # | Action you take in your package | Exact snippet / path | What pysigil gives you for free |
|---|--------------------------------|----------------------|--------------------------------|
| 1 | Create a defaults file (INI only for MVP) | `mypkg/prefs/defaults.ini`<br><br>```ini
[db]
host = localhost
port = 5432
``` | Becomes the base layer of the preference chain. |
| 2 | Declare that file in `pyproject.toml` | ```toml
[tool.pysigil]
defaults = "prefs/defaults.ini"
``` | pysigil-Hub auto-discovers your package during import. |
| 3 | (Optional but recommended) Expose helpers so callers never touch pysigil APIs | ```python
# mypkg/__init__.py
from pysigil.gui.hub import get_preferences as _gp
get_pref, set_pref = _gp(__name__)  # __name__ == "mypkg"
``` | • One-line access:<br>`get_pref("db.host")`<br>• Handles env ▶ project ▶ user ▶ defaults without extra code. |
| 4 | (Optional) ship metadata later | Add `prefs/defaults.meta.json` and set `meta = "prefs/defaults.meta.json"` under `[tool.pysigil]` | When the GUI arrives, titles, tool-tips and “secret” flags will show automatically. No impact on MVP. |

## What you get immediately

Fully merged prefs:
`SIGIL_MYPKG_DB_HOST (env) → ./settings.ini (project) → ~/.config/mypkg/settings.ini (user) → your defaults.ini.`

No boiler-plate: call `get_pref()` / `set_pref()` from anywhere in your code.

User tooling already works:

```
sigil get --app mypkg key
sigil set --app mypkg key value
```

Files auto-created as needed.

Zero runtime deps: pysigil is pure std-lib + your INI file.

That’s it. Add one defaults file, one `[tool.sigil]` line, (optionally) four helper lines — and your package instantly gains a robust, chain-aware configuration system.
