# Sigil – Author Registration Guide

This guide shows package authors how to register their package defaults so Sigil can find them **during development** (without installing the package).

## What you’re doing (in one sentence)
Creating a small dev-link file under your user config (e.g. `~/.config/sigil/dev/<provider>.ini`) that points to your package’s `.sigil/settings.ini`.

## Prereqs
- Your package repository contains `.sigil/settings.ini` next to your `__init__.py` (e.g. `my_pkg/.sigil/settings.ini`).
- You installed Sigil with the CLI/GUI:
  ```bash
  pip install sigil  # or your editable install
  ```

## Provider ID

We use your **PEP 503 normalized** distribution name as the provider id (lowercase; runs of `-_.` become `-`). Examples:

* `My_Package.Name` → `my-package-name`
* `awesome.pkg` → `awesome-pkg`

## Option A — CLI (Click)

Register a dev link:

```bash
sigil author register --provider my-package \
  --defaults /abs/path/to/my_pkg/.sigil/settings.ini
```

If you want to skip shape validation (not recommended):

```bash
sigil author register --provider my-package --defaults /path/to/settings.ini --no-validate
```

List and inspect links:

```bash
sigil author list
sigil author list --existing-only  # hide missing targets
```

Remove a link:

```bash
sigil author unlink-defaults my-package
```

## Option B — GUI (Tkinter)

Launch the GUI wizard:

```bash
sigil-gui
```

Steps:

1. Click **Browse…** and choose your `.sigil/settings.ini`.
2. Confirm the suggested provider id (edit if you like; it will be normalized when saved).
3. Click **Register**. A success message will show the link destination.
4. (Optional) **Open dev-links folder** to verify the file was created.

## Where does Sigil store the link?

* **Windows**: `%APPDATA%/sigil/dev/<provider>.ini`
* **macOS**: `~/Library/Application Support/sigil/dev/<provider>.ini`
* **Linux**: `~/.config/sigil/dev/<provider>.ini`

Each link file is a tiny INI like:

```ini
[link]
defaults=/abs/path/to/my_pkg/.sigil/settings.ini
```

## Packaging tip

When you publish, include `.sigil/settings.ini` in your wheel:

```toml
# pyproject.toml (example)
[tool.setuptools.package-data]
"my_pkg" = [".sigil/settings.ini"]
```

## Troubleshooting

* **“Defaults file must be inside a '.sigil' directory.”**
  Ensure the file is literally named `settings.ini` and lives under a folder named `.sigil`.
* **“No dev link found” when unlinking**
  Run `sigil author list` to see what’s registered; check for normalization (`my-package` vs `my_package`).
* **Path shows (missing)** in `list`
  Move/restore the target file or re-register with the new absolute path.
