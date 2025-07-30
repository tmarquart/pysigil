# Sigil

Preference management for small apps.

Install the package in your virtual environment to get the
`sigil` command-line tool:

```bash
pip install -e .  # or `pip install .` for a normal install
```

After installing you can run commands like:

```bash
sigil set ui.color blue --app demo
sigil get ui.color --app demo
eval "$(sigil export --app demo)"  # shell-friendly
```

You don't need a separate project to try Sigil. The CLI stores data in your user
config directory, so you can run these commands from the source tree itself.
See `tests/manual_tests/README.md` for a step-by-step guide.

Typed helper methods are available for convenient access:
`Sigil.get_int()`, `get_float()`, `get_bool()`.
