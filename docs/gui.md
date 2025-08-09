# Launching the Preferences GUI

Sigil ships with a small Tk based GUI for editing preferences.  Install with
`pip install sigil[gui]` and run:

```
sigil-gui --app myapp
```

This opens a window showing all preferences defined for *myapp* using the
metadata loaded from `defaults.meta.csv` if present.

## Debug logging

Set the environment variable `SIGIL_GUI_DEBUG=1` before launching the GUI to
emit verbose debug information to the console.  This can help diagnose problems
with package loading or preference updates and can be disabled by unsetting the
variable.
