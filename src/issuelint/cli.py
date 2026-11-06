"""Command line entry point."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    print("issuelint: no checks implemented yet", *args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
