# pysigil Requirements (v0.2-draft)

## Purpose
pysigil is a minimal preference manager for Python projects. It merges
settings from core defaults, optional package defaults, user files,
project files and environment variables. The public surface is the
``Sigil`` class and a small CLI wrapper.

## Philosophy
- Single source of truth lives in ``core.Sigil``.
- Support code in ``merge_policy`` and ``io_config`` is pure and free of
dependency on the rest of the package.
 - Modules such as the CLI, backends, GUI and secret providers are thin layers
 built on the core API.
 - Legacy modules (provider hub, metadata processing) were removed to avoid
 duplicated logic and unclear responsibility.

## Module Layout
 - ``core.py`` – ``Sigil`` class and merge precedence.
 - ``errors.py`` – shared error hierarchy.
- ``merge_policy.py`` – dotted-key helpers, environment reader and built-in
  core defaults.
- ``io_config.py`` – INI read/write helpers and distribution defaults
  loader.
 - ``backends/`` – pluggable file backends (INI, JSON, YAML).
 - ``resolver.py`` – project-root discovery helpers.
 - ``secrets/`` – optional secret provider chain.
 - ``cli.py`` – argparse based command line interface.
 - ``gui.py`` – minimal Tk preferences editor.

## Out of Scope
Features present in earlier iterations were intentionally dropped for a
cleaner baseline:
- provider-discovery API
- metadata-driven policies and locking

Future releases may reincorporate these features as separate layers built
strictly on top of the refined core.
