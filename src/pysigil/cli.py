from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .authoring import (
    DefaultsValidationError,
    DevLinkError,
    import_package_from,
    link as dev_link,
    list_links as dev_list,
    patch_pyproject_package_data,
    unlink as dev_unlink,
    validate_defaults_file,
)
from .core import Sigil
from .discovery import pep503_name
from .gui import launch_gui


def build_parser(prog: str = "sigil") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog)
    sub = parser.add_subparsers(dest="cmd", required=True)

    get_p = sub.add_parser("get")
    get_p.add_argument("key")
    get_p.add_argument("--app", required=True)

    set_p = sub.add_parser("set")
    set_p.add_argument("key")
    set_p.add_argument("value")
    set_p.add_argument("--app", required=True)
    set_p.add_argument("--scope", choices=["user", "project"], default="user")

    secret_p = sub.add_parser("secret")
    secret_sub = secret_p.add_subparsers(dest="scmd", required=True)

    sec_get = secret_sub.add_parser("get")
    sec_get.add_argument("key")
    sec_get.add_argument("--app", required=True)
    sec_get.add_argument("--reveal", action="store_true")

    sec_set = secret_sub.add_parser("set")
    sec_set.add_argument("key")
    sec_set.add_argument("value")
    sec_set.add_argument("--app", required=True)

    sec_unlock = secret_sub.add_parser("unlock")
    sec_unlock.add_argument("--app", required=True)

    export_p = sub.add_parser("export")
    export_p.add_argument("--app", required=True)
    export_p.add_argument("--prefix", default="SIGIL_")
    export_p.add_argument("--json", action="store_true")

    gui_p = sub.add_parser("gui")
    gui_p.add_argument("--app")
    gui_p.add_argument("--include-sigil", action="store_true")
    gui_p.add_argument("--no-remember", action="store_true")

    auth_p = sub.add_parser("author")
    auth_sub = auth_p.add_subparsers(dest="acmd", required=True)

    reg_p = auth_sub.add_parser("register")
    reg_p.add_argument("--provider", required=True)
    reg_p.add_argument("--defaults", required=True)
    reg_p.add_argument("--add-package-data", action="store_true")
    reg_p.add_argument("--pyproject")
    reg_p.add_argument("--no-dev-link", action="store_true")
    reg_p.add_argument("--yes", action="store_true")

    link_p = auth_sub.add_parser("link-defaults")
    link_p.add_argument("provider_id")
    link_p.add_argument("path")

    unlink_p = auth_sub.add_parser("unlink-defaults")
    unlink_p.add_argument("provider_id")

    val_p = auth_sub.add_parser("validate")
    val_p.add_argument("provider_id")
    val_p.add_argument("path")

    list_p = auth_sub.add_parser("list")
    list_p.add_argument("--existing-only", action="store_true")

    return parser


def _find_pyproject(start: Path) -> Path | None:
    for parent in [start, *start.parents]:
        candidate = parent / "pyproject.toml"
        if candidate.is_file():
            return candidate
    return None


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    prog = os.path.basename(sys.argv[0]) or "sigil"
    if prog == "__main__.py":
        prog = "pysigil"
    parser = build_parser(prog)
    args = parser.parse_args(argv)
    if args.cmd not in {"gui", "author"}:
        sigil = Sigil(args.app)
    if args.cmd == "get":
        val = sigil.get_pref(args.key)
        if val is None:
            return 1
        print(val)
        return 0
    elif args.cmd == "set":
        sigil.set_pref(args.key, args.value, scope=args.scope)
        return 0
    elif args.cmd == "export":
        mapping = sigil.export_env(prefix=args.prefix)
        if args.json:
            import json

            print(json.dumps(mapping))
        else:
            for k, v in mapping.items():
                print(f"{k}={v}")
        return 0
    elif args.cmd == "secret":
        if args.scmd == "get":
            val = sigil.get_pref(args.key)
            if val is None:
                return 1
            if args.reveal:
                print(val)
            else:
                print("*" * 8)
            return 0
        elif args.scmd == "set":
            try:
                sigil.set_pref(args.key, args.value)
            except Exception:
                return 1
            return 0
        elif args.scmd == "unlock":
            sigil._secrets.unlock()
            return 0
    elif args.cmd == "gui":
        launch_gui(
            package=args.app,
            include_sigil=args.include_sigil,
            remember_state=not args.no_remember,
        )
        return 0
    elif args.cmd == "author":
        if args.acmd == "register":
            provider = pep503_name(args.provider)
            ini_path = Path(args.defaults)
            try:
                validate_defaults_file(ini_path, provider)
            except DefaultsValidationError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            if not args.no_dev_link:
                try:
                    dev_link(provider, ini_path)
                except DevLinkError as exc:
                    print(str(exc), file=sys.stderr)
                    return 1
            if args.add_package_data:
                if args.pyproject:
                    pyproject = Path(args.pyproject)
                else:
                    pyproject = _find_pyproject(ini_path)
                if pyproject is not None:
                    patch_pyproject_package_data(
                        pyproject, import_package_from(ini_path)
                    )
            return 0
        elif args.acmd == "link-defaults":
            provider = pep503_name(args.provider_id)
            try:
                dev_link(provider, Path(args.path))
            except (DefaultsValidationError, DevLinkError):
                return 1
            return 0
        elif args.acmd == "unlink-defaults":
            provider = pep503_name(args.provider_id)
            ok = dev_unlink(provider)
            return 0 if ok else 1
        elif args.acmd == "validate":
            provider = pep503_name(args.provider_id)
            try:
                validate_defaults_file(Path(args.path), provider)
            except DefaultsValidationError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            return 0
        elif args.acmd == "list":
            entries = dev_list(must_exist_on_disk=args.existing_only)
            if not entries:
                print("No dev links found")
                return 0
            for pid, path in sorted(entries.items()):
                status = "(ok)" if path.exists() else "(missing)"
                print(f"{pid}: {path} {status}")
            return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
