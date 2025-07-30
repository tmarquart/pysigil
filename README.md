# Sigil

Preference management for small apps.

## Quick start

Install Sigil in a virtual environment to make the `sigil` command available:

```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\Activate
pip install -e .  # or `pip install .` for a normal install
```

Once installed, try a few commands:

```bash
sigil set ui.color blue --app demo
sigil get ui.color --app demo
sigil export --app demo
```

The CLI stores data under your user config directory (e.g. `~/.config/demo`),
so you can run these commands right from the source tree without creating a
separate project. See `tests/manual_tests/README.md` for more examples.

Typed helper methods are available for convenient access:
`Sigil.get_int()`, `get_float()`, `get_bool()`.
