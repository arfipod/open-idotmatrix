"""Entry point for the optional PySide6 desktop app."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    try:
        from .qt_window import run
    except ModuleNotFoundError as exc:
        if exc.name == "PySide6":
            print("error: PySide6 is required. Install it with: pip install -e '.[qt]'", file=sys.stderr)
            return 2
        raise
    return run(argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
