from __future__ import annotations

import argparse
import sys

from .core import Sigil


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sigil")
    sub = parser.add_subparsers(dest="cmd", required=True)

    get_p = sub.add_parser("get")
    get_p.add_argument("key")
    get_p.add_argument("--app", required=True)

    set_p = sub.add_parser("set")
    set_p.add_argument("key")
    set_p.add_argument("value")
    set_p.add_argument("--app", required=True)
    set_p.add_argument("--scope", choices=["user", "project"], default="user")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
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
    return 1


if __name__ == "__main__":
    sys.exit(main())
