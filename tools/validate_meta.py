from __future__ import annotations

import logging
import sys
from importlib import resources
from pathlib import Path

from pysigil.errors import SigilMetaError
from pysigil.helpers import load_meta


class WarnCounter(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.count = 0

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno >= logging.WARNING:
            self.count += 1


def validate(package: str, rel_path: str) -> int:
    path = resources.files(package).joinpath(rel_path)
    logger = logging.getLogger("pysigil")
    handler = WarnCounter()
    logger.addHandler(handler)
    try:
        load_meta(Path(path))
    except SigilMetaError as exc:
        print(f"{path}: {exc}")
        return 1
    finally:
        logger.removeHandler(handler)
    if handler.count:
        print(f"{path}: {handler.count} warning(s)")
        return 1
    return 0


def main(argv: list[str]) -> int:
    if len(argv) % 2 or not argv:
        print("usage: validate_meta.py package path [package path ...]")
        return 1
    rc = 0
    for i in range(0, len(argv), 2):
        pkg = argv[i]
        path = argv[i + 1]
        rc |= validate(pkg, path)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
