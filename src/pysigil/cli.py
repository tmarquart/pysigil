from __future__ import annotations

import argparse
import configparser
import json
import os
import subprocess
import sys
from pathlib import Path

from .authoring import (
    DefaultsValidationError,
    DevLinkError,
    link as dev_link,
    list_links as dev_list,
    normalize_provider_id,
    unlink as dev_unlink,
    validate_defaults_file,
)
from .config import (
    ensure_gitignore as cfg_ensure_gitignore,
    host_file as cfg_host_file,
    init_config as cfg_init_config,
    load as cfg_load,
    open_scope as cfg_open_scope,
)
from .core import Sigil
from .discovery import pep503_name
from .errors import DevLinkNotFoundError
from .paths import (
    default_config_dir,
    default_data_dir,
    project_cache_dir,
    project_config_dir,
    project_data_dir,
    project_root as paths_project_root,
    user_cache_dir,
    user_config_dir,
    user_data_dir,
)
from .resolver import (
    default_provider_id,
    ensure_defaults_file,
    find_package_dir,
    read_dist_name_from_pyproject,
)
from .root import ProjectRootNotFoundError, find_project_root
from .ui.tk import launch as launch_gui

AUTHOR_FLAG_ENV = "SIGIL_AUTHOR"


def author_mode_enabled(args: argparse.Namespace | None = None) -> bool:
    """Return True if author mode should be enabled."""
    if args and getattr(args, "author", False):
        return True
    if os.environ.get(AUTHOR_FLAG_ENV):
        return True
    cfg = Path.home() / ".sigil" / "author.toml"
    return cfg.is_file()


def _launch(path: Path) -> None:  # pragma: no cover - best effort
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Config commands
# ---------------------------------------------------------------------------


def show_paths(args: argparse.Namespace) -> int:
    data = {
        "user_config": user_config_dir(),
        "user_data": user_data_dir(),
        "user_cache": user_cache_dir(),
        "project_root": paths_project_root(start=args.start),
        "project_config": project_config_dir(start=args.start),
        "project_data": project_data_dir(start=args.start),
        "project_cache": project_cache_dir(start=args.start),
        "default_config": default_config_dir(),
        "default_data": default_data_dir(),
    }
    if args.as_json:
        print(json.dumps({k: str(v) for k, v in data.items()}))
    else:
        for k, v in data.items():
            print(f"{k}: {v}")
    return 0


def config_init(args: argparse.Namespace) -> int:
    path = cfg_init_config(args.provider, args.scope, auto=args.auto)
    print(str(path))
    return 0


def config_open(args: argparse.Namespace) -> int:  # pragma: no cover - best effort
    path = cfg_open_scope(args.provider, args.scope, auto=args.auto)
    _launch(path)
    print(str(path))
    return 0


def config_host(args: argparse.Namespace) -> int:  # pragma: no cover - best effort
    try:
        path = cfg_host_file(args.provider, args.scope, auto=args.auto)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _launch(path)
    print(str(path))
    return 0


def config_show(args: argparse.Namespace) -> int:
    data = cfg_load(args.provider, auto=args.auto)
    if args.format == "json":
        print(json.dumps(data))
        return 0
    parser = configparser.ConfigParser()
    parser[normalize_provider_id(args.provider)] = {k: str(v) for k, v in data.items()}
    from io import StringIO

    buf = StringIO()
    parser.write(buf)
    print(buf.getvalue().strip())
    return 0


def config_gitignore(args: argparse.Namespace) -> int:
    if args.init:
        path = cfg_ensure_gitignore(auto=args.auto)
        print(str(path))
    return 0


def config_gui(_: argparse.Namespace) -> int:  # pragma: no cover - GUI interactions
    from .ui.tk.config_gui import launch as launch_config_gui

    launch_config_gui()
    return 0


# ---------------------------------------------------------------------------
# Basic commands
# ---------------------------------------------------------------------------


def get_cmd(args: argparse.Namespace) -> int:
    sigil = Sigil(args.app)
    val = sigil.get_pref(args.key)
    if val is None:
        return 1
    print(val)
    return 0


def set_cmd(args: argparse.Namespace) -> int:
    sigil = Sigil(args.app)
    sigil.set_pref(args.key, args.value, scope=args.scope)
    return 0


def secret_get(args: argparse.Namespace) -> int:
    sigil = Sigil(args.app)
    val = sigil.get_pref(args.key)
    if val is None:
        return 1
    print(val if args.reveal else "*" * 8)
    return 0


def secret_set(args: argparse.Namespace) -> int:
    sigil = Sigil(args.app)
    try:
        sigil.set_pref(args.key, args.value)
    except Exception:
        return 1
    return 0


def secret_unlock(args: argparse.Namespace) -> int:
    sigil = Sigil(args.app)
    sigil._secrets.unlock()
    return 0


def export_cmd(args: argparse.Namespace) -> int:
    sigil = Sigil(args.app)
    mapping = sigil.export_env(prefix=args.prefix)
    if args.as_json:
        print(json.dumps(mapping))
    else:
        for k, v in mapping.items():
            print(f"{k}={v}")
    return 0


def gui_cmd(args: argparse.Namespace) -> int:  # pragma: no cover - GUI interactions
    launch_gui(initial_provider=args.app, author_mode=author_mode_enabled(args))
    return 0


def launch_author_ui(_ctx: object) -> int:  # pragma: no cover - GUI interactions
    return 0


def author_gui_cmd(_: argparse.Namespace) -> int:  # pragma: no cover - GUI interactions
    import sys

    from .ui.core import AppCore

    try:
        proj_root = find_project_root()
    except ProjectRootNotFoundError:
        proj_root = Path.cwd()
    dist_name = read_dist_name_from_pyproject(proj_root)
    pkg = find_package_dir(proj_root, dist_name)
    if not pkg:
        print("Could not auto-detect package directory", file=sys.stderr)
        return 2
    provider_id = default_provider_id(pkg, dist_name)

    core = AppCore(author_mode=True)
    pid = normalize_provider_id(provider_id)
    try:
        ctx = core.orchestrator.load_author_context(pid)
    except DevLinkNotFoundError:
        err = (
            f"No development link for '{pid}'.\n"
            f"Create one:\n  sigil link --dev /path/to/pkg --provider {pid}"
        )
        print(err, file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Failed to prepare authoring for '{pid}': {exc}", file=sys.stderr)
        return 2

    return launch_author_ui(ctx)


def setup_cmd(_: argparse.Namespace) -> int:  # pragma: no cover - GUI interactions
    from .ui.tk.author import main as author_main

    author_main()
    return 0


# ---------------------------------------------------------------------------
# Author commands
# ---------------------------------------------------------------------------


def author_register(args: argparse.Namespace) -> int:
    if args.auto:
        try:
            root = find_project_root()
        except ProjectRootNotFoundError:
            root = Path.cwd()
        dist_name = read_dist_name_from_pyproject(root)
        pkg = find_package_dir(root, dist_name)
        if not pkg:
            print("Could not auto-detect package directory", file=sys.stderr)
            return 2
        provider_id = default_provider_id(pkg, dist_name)
        settings_path = ensure_defaults_file(pkg, provider_id)
        try:
            dev_link(provider_id, settings_path, validate=not args.no_validate)
        except DevLinkError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(f"Linked {provider_id} -> {settings_path}")
        return 0

    if bool(args.package_dir) == bool(args.defaults):
        print("Use exactly one of --package-dir or --defaults", file=sys.stderr)
        return 2

    if args.package_dir:
        chosen = args.package_dir
        if (chosen / "__init__.py").exists():
            pkg = chosen
        else:
            pkg = find_package_dir(chosen, None)
        if not pkg:
            print("That folder doesn't look like a package", file=sys.stderr)
            return 2
        try:
            root = find_project_root(pkg)
        except ProjectRootNotFoundError:
            root = pkg
        dist_name = read_dist_name_from_pyproject(root)
        provider_id = (
            normalize_provider_id(args.provider)
            if args.provider
            else default_provider_id(pkg, dist_name)
        )
        settings_path = ensure_defaults_file(pkg, provider_id)
        try:
            dev_link(provider_id, settings_path, validate=not args.no_validate)
        except DevLinkError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(f"Linked {provider_id} -> {settings_path}")
        return 0

    assert args.defaults is not None
    if not args.provider:
        print("--provider is required when using --defaults", file=sys.stderr)
        return 2
    provider_id = normalize_provider_id(args.provider)
    try:
        dev_link(provider_id, args.defaults, validate=not args.no_validate)
    except DevLinkError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Linked {provider_id} -> {args.defaults}")
    return 0


def author_link_defaults(args: argparse.Namespace) -> int:
    provider = pep503_name(args.provider_id)
    try:
        dev_link(provider, args.path)
    except (DefaultsValidationError, DevLinkError):
        return 1
    return 0


def author_unlink_defaults(args: argparse.Namespace) -> int:
    provider = pep503_name(args.provider_id)
    ok = dev_unlink(provider)
    if not ok:
        return 1
    return 0


def author_validate(args: argparse.Namespace) -> int:
    provider = pep503_name(args.provider_id)
    try:
        validate_defaults_file(args.path, provider)
    except DefaultsValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def author_list_links(args: argparse.Namespace) -> int:
    entries = dev_list(must_exist_on_disk=args.existing_only)
    if not entries:
        print("No dev links found")
        return 0
    for pid, path in sorted(entries.items()):
        status = "(ok)" if path.exists() else "(missing)"
        print(f"{pid}: {path} {status}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sigil", description="Sigil command line interface.")
    parser.add_argument("--author", action="store_true", help="Enable author mode")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # paths command
    p_paths = subparsers.add_parser("paths", help="Show Sigil paths.")
    p_paths.add_argument("--start", type=Path, default=None)
    p_paths.add_argument("--json", dest="as_json", action="store_true")
    p_paths.set_defaults(func=show_paths)

    # config group
    p_config = subparsers.add_parser("config", help="Manage Sigil configuration files.")
    sp_config = p_config.add_subparsers(dest="config_cmd", required=True)

    p_cfg_init = sp_config.add_parser("init", help="Initialize configuration")
    p_cfg_init.add_argument("--provider", required=True)
    p_cfg_init.add_argument("--scope", choices=["user", "project"], default="user")
    p_cfg_init.add_argument("--auto", action="store_true", help="Auto-detect project root")
    p_cfg_init.set_defaults(func=config_init)

    p_cfg_open = sp_config.add_parser("open", help="Open configuration scope")
    p_cfg_open.add_argument("--provider", required=True)
    p_cfg_open.add_argument("--scope", choices=["user", "project"], default="user")
    p_cfg_open.add_argument("--auto", action="store_true", help="Auto-detect project root")
    p_cfg_open.set_defaults(func=config_open)

    p_cfg_host = sp_config.add_parser("host", help="Open host-specific config")
    p_cfg_host.add_argument("--provider", required=True)
    p_cfg_host.add_argument("--scope", choices=["user", "project"], default="user")
    p_cfg_host.add_argument("--auto", action="store_true", help="Auto-detect project root")
    p_cfg_host.set_defaults(func=config_host)

    p_cfg_show = sp_config.add_parser("show", help="Show configuration")
    p_cfg_show.add_argument("--provider", required=True)
    p_cfg_show.add_argument("--as", dest="format", choices=["ini", "json"], default="ini")
    p_cfg_show.add_argument("--auto", action="store_true", help="Auto-detect project root")
    p_cfg_show.set_defaults(func=config_show)

    p_cfg_git = sp_config.add_parser("gitignore", help="Manage .gitignore")
    p_cfg_git.add_argument("--init", action="store_true", help="Add ignore rule")
    p_cfg_git.add_argument("--auto", action="store_true", help="Auto-detect project root")
    p_cfg_git.set_defaults(func=config_gitignore)

    p_cfg_gui = sp_config.add_parser("gui", help="Launch the config GUI")
    p_cfg_gui.set_defaults(func=config_gui)

    # get command
    p_get = subparsers.add_parser("get", help="Print the value for KEY.")
    p_get.add_argument("key")
    p_get.add_argument("--app", required=True)
    p_get.set_defaults(func=get_cmd)

    # set command
    p_set = subparsers.add_parser("set", help="Set KEY to VALUE.")
    p_set.add_argument("key")
    p_set.add_argument("value")
    p_set.add_argument("--app", required=True)
    p_set.add_argument("--scope", choices=["user", "project"], default="user")
    p_set.set_defaults(func=set_cmd)

    # secret group
    p_secret = subparsers.add_parser("secret", help="Manage secret preferences.")
    sp_secret = p_secret.add_subparsers(dest="secret_cmd", required=True)

    p_sec_get = sp_secret.add_parser("get", help="Get secret value")
    p_sec_get.add_argument("key")
    p_sec_get.add_argument("--app", required=True)
    p_sec_get.add_argument("--reveal", action="store_true", help="Print the secret value")
    p_sec_get.set_defaults(func=secret_get)

    p_sec_set = sp_secret.add_parser("set", help="Set secret value")
    p_sec_set.add_argument("key")
    p_sec_set.add_argument("value")
    p_sec_set.add_argument("--app", required=True)
    p_sec_set.set_defaults(func=secret_set)

    p_sec_unlock = sp_secret.add_parser("unlock", help="Unlock secret store")
    p_sec_unlock.add_argument("--app", required=True)
    p_sec_unlock.set_defaults(func=secret_unlock)

    # export command
    p_export = subparsers.add_parser("export", help="Export preferences as environment variables.")
    p_export.add_argument("--app", required=True)
    p_export.add_argument("--prefix", default="SIGIL_")
    p_export.add_argument("--json", dest="as_json", action="store_true")
    p_export.set_defaults(func=export_cmd)

    # gui command
    p_gui = subparsers.add_parser("gui", help="Launch the preferences GUI.")
    p_gui.add_argument("--app")
    p_gui.add_argument("--include-sigil", action="store_true")
    p_gui.add_argument("--no-remember", action="store_true")
    p_gui.set_defaults(func=gui_cmd)

    # setup command (alias: register)
    p_setup = subparsers.add_parser(
        "setup", help="Launch the defaults registration GUI.", aliases=["register"]
    )
    p_setup.set_defaults(func=setup_cmd)

    # author command / group
    p_author = subparsers.add_parser(
        "author", help="Launch the author tools GUI or manage development links."
    )
    p_author.set_defaults(func=author_gui_cmd)
    sp_author = p_author.add_subparsers(dest="author_cmd")

    p_reg = sp_author.add_parser("register", help="Register package defaults for development.")
    p_reg.add_argument("--package-dir", type=Path, help="Package directory")
    p_reg.add_argument("--defaults", type=Path, help="Path to settings.ini")
    p_reg.add_argument("--provider", help="Override provider id")
    p_reg.add_argument("--auto", action="store_true", help="Auto-detect from current directory")
    p_reg.add_argument("--no-validate", action="store_true", help="Skip defaults validation")
    p_reg.set_defaults(func=author_register)

    p_link = sp_author.add_parser("link-defaults", help="Link defaults file for provider")
    p_link.add_argument("provider_id")
    p_link.add_argument("path", type=Path)
    p_link.set_defaults(func=author_link_defaults)

    p_unlink = sp_author.add_parser("unlink-defaults", help="Unlink defaults file for provider")
    p_unlink.add_argument("provider_id")
    p_unlink.set_defaults(func=author_unlink_defaults)

    p_val = sp_author.add_parser("validate", help="Validate defaults file")
    p_val.add_argument("provider_id")
    p_val.add_argument("path", type=Path)
    p_val.set_defaults(func=author_validate)

    p_list = sp_author.add_parser("list", help="List dev links")
    p_list.add_argument("--existing-only", action="store_true")
    p_list.set_defaults(func=author_list_links)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 1
    try:
        return int(func(args))
    except SystemExit as exc:  # pragma: no cover - argparse may raise
        return int(exc.code)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

