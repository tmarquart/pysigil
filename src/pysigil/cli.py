from __future__ import annotations

import argparse
import os
import sys

from .core import Sigil


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

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    prog = os.path.basename(sys.argv[0]) or "sigil"
    if prog == "__main__.py":
        prog = "pysigil"
    parser = build_parser(prog)
    args = parser.parse_args(argv)
    if args.cmd != "gui":
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
        from .gui import launch_gui

        launch_gui(
            package=args.app,
            include_sigil=args.include_sigil,
            remember_state=not args.no_remember,
        )
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
