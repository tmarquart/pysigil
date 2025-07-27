Below is a formal requirements specification (v0.1-draft) for Sigil.
It consolidates every design choice we’ve locked plus the separation-of-concerns mandate.  Sections flagged [FUTURE] describe stubs / extension points only—no concrete code is expected until later milestones.

⸻

1  Purpose & Vision

Provide a lightweight, extensible preference manager for Python projects that
	•	merges settings from multiple scopes (default → user → project → env),
	•       supports multiple on-disk formats (INI first),
        •       Sigil reads .ini and .json out of the box; install ``sigil[json5]`` for relaxed JSON5 syntax,
	•	exposes a tiny, intuitive API (get_pref, set_pref),
	•	keeps UI layers (CLI, Tk GUI) and Secrets entirely decoupled from the core logic.

⸻

2  Glossary

Term	Meaning
Scope	One storage layer: default, user, project, env-override.
Backend	Serializer/loader for a file format (e.g. IniBackend).
Provider	Run-time source of values not stored in a file, e.g. EnvProvider, [FUTURE] KeyringProvider.
Core	Pure-Python engine that knows nothing about CLI, GUI or secrets.


⸻

3  In/Out of Scope for v0.1

Included
	•	Reading/writing INI files.
	•	Env-var overrides (SIGIL_<APP>_<UPPER_SNAKE_KEY>).
	•	Auto-casting of primitive literals (int, float, bool, JSON‐style lists/dicts).
	•	Public class Sigil in sigil.core plus supporting helpers.
	•	Simple console tool (sigil get / set) implemented in a separate module that imports only sigil.core.
	•	Registry for future back-ends and providers.

Deferred
	•	Additional formats (TOML, JSON, XML, YAML).
	•	Secrets chain (keyring, encrypted file, etc.).
	•	Tkinter GUI.
	•	Live file-watch reload, watchdog optional dependency.
	•	Any crypto or GUI third-party packages.

⸻

4  Functional Requirements

4.1  Merge & Precedence

env-override  >  project  >  user  >  default

	•	Precedence is deterministic and configurable only via explicit API (no implicit re-ordering).
	•	Env values are mapped SIGIL_<APP>_<UPPER_SNAKE_KEY> → lower.dot.path.

4.2  API (sigil.core)

ID	Requirement
F-1	`Sigil(app_name: str, *, user_scope: Path
F-2	`get_pref(key: str, *, default: Any = None, cast: Callable
F-3	set_pref(key: str, value: Any, *, scope: Literal['user','project']) -> None (writing to default or env raises)
F-4	Context manager Sigil.project(path) temporarily forces scope='project' for nested set_pref calls.
F-5	Sigil.invalidate_cache() reloads all scopes on demand.
F-6	All operations are thread-safe; file writes use atomic rename.
F-7	Auto-cast rules: int, float, bool, JSON list/obj via json.loads fallback; else str.  Explicit cast= supersedes.

4.3  Back-end Abstraction

ID	Requirement
B-1	BaseBackend ABC defines suffixes, load(path)->Mapping, save(path, Mapping)->None.
B-2	IniBackend ships in sigil.backend.ini_backend, registered for .ini.
B-3	Factory get_backend_for_path(path) lives in sigil.backend.__init__ and is the only path Core uses.
B-4	Adding TOML later requires only pip install sigil[toml]; no Core edits.

4.4  Environment Provider

ID	Requirement
E-1	sigil.env.read_env(app_name) -> Mapping returns a flat dict ready to insert at top of merge chain.
E-2	Mapper is overridable by passing a callable to Sigil(..., env_reader=callable).

4.5  CLI (sigil.cli)

ID	Requirement
C-1	Uses argparse; entry-points sigil get KEY and `sigil set KEY VALUE [–scope user
C-2	Imports only sigil.core (no backend or env internals).
C-3	Returns non-zero exit code on error; error messages from Core exceptions.

4.6  GUI [FUTURE]
	•	Module sigil.gui depends on tkinter and sigil.core only.
	•	Must communicate via Core public API; no direct file I/O.

4.7  Secrets [FUTURE]
	•	Module sigil.secrets provides SecretProvider ABC and NullSecretProvider.
	•	Core owns a .secrets attribute defaulting to NullSecretProvider and never imports optional secret providers.

⸻

5  Non-Functional Requirements

ID	Requirement
N-1	Supported Python versions: 3.9 – 3.13.
N-2	Core depends only on stdlib + appdirs + typing_extensions (for Literal on 3.9).
N-3	py.typed included, full type hints; mypy passes under strict = False.
N-4	Cold load < 50 ms for ≤ 3 INI files totalling ≤ 30 KB on mid-range laptop.
N-5	Unit-test coverage ≥ 90 % lines, tracked in CI (GitHub Actions, Windows/macOS/Linux).
N-6	Logging uses stdlib logging.getLogger('sigil'); no print-statements in library code.
N-7	License: MIT (default unless overridden before first release).
N-8	Semantic versioning (0.1.x while API may break, 1.x once stable).


⸻

6  Package & Module Boundaries

sigil/
│
├─ core.py          ← **only point of truth for preference logic**
├─ backend/         ← serializers (pluggable)
│   ├─ __init__.py  ← registry + factory
│   └─ ini_backend.py
├─ env.py           ← env-var mapper
├─ secrets/         ← [FUTURE] secret providers
│   └─ __init__.py
├─ cli.py           ← thin argparse wrapper (imports core)
├─ gui/             ← [FUTURE] Tk widgets (imports core)
├─ errors.py        ← typed exception hierarchy
└─ __init__.py      ← re-exports `Sigil`, version, etc.

Core must not import cli, gui, or secrets.*.
cli and gui must only interact through the public interface re-exported in sigil.__init__.

⸻

7  Road-map (high-level)

Version	Headline Features
0.1	INI support, env overrides, CLI set/get, plugin registry.
0.2	Secrets chain (keyring & encrypted file), sigil secret CLI.
0.3	Tk GUI inspector/editor, TOML backend.
0.4	JSON & YAML back-ends, live-reload extra.
1.0	Frozen public API, stability & docs polish.


⸻

8  Open Items (pre-coding)
	1.	Default section name in INI when user writes a top-level key (e.g. ui.theme)—use "global" or enforce explicit section?
	2.	Error policy—get_pref('missing') returns None vs raising? (Current spec = returns default arg, defaulting to None.)
	3.	File naming convention—hard-code settings.ini or allow arbitrary file names declared in Sigil(...)?

Let me know tweaks on those items, or any other gaps.
After that this doc is “spec-frozen” and ready to hand to implementers (or your future self).