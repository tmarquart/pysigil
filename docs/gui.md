# Launching the Preferences GUI

Sigil ships with a small Tk based GUI for editing preferences.  Install with
`pip install sigil[gui]` and run:

```
sigil-gui --app myapp
```

This opens a window showing all preferences defined for *myapp* using the
metadata loaded from `defaults.meta.csv` if present.
