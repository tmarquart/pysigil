# Manual Testing Guide

This directory contains simple scenarios for exploring Sigil by hand. Any files
or screenshots generated during these steps should be saved under the
`tests/manual_tests/artifacts/` folder so they remain isolated from automated
unit tests.

## 1. Set a preference via the CLI

```bash
sigil set ui.color blue --app demo
sigil get ui.color --app demo
```

The `get` command should print `blue`. Feel free to inspect the resulting
configuration file placed under the application config directory (for example
`~/.config/demo` on Linux).

## 2. Launch the preferences GUI

Ensure the optional GUI extras are installed:

```bash
pip install sigil[gui]
```

Start the GUI with:

```bash
sigil-gui --app demo
```

The window will display all known preferences. Modify a value and save it.
Take a screenshot and store it in `tests/manual_tests/artifacts/`.

## 3. Export preferences as environment variables

```bash
sigil export --app demo > tests/manual_tests/artifacts/env.sh
```

The resulting shell script can be sourced to populate environment variables
matching the stored preferences.

## 4. Working with secrets (optional)

Install the crypto extras if you want to try secret storage:

```bash
pip install sigil[secrets-crypto]
```

Set and retrieve a secret value:

```bash
sigil secret set secret.api_key mysecret --app demo
sigil secret get secret.api_key --app demo --reveal
```

The decrypted secret should be printed to the console. As with the other steps,
any screenshots or notes can be placed in the `artifacts/` folder.
