"""Application entry point."""

from __future__ import annotations

import argparse
import shutil
import sys

from .app import PlayYTApp
from .config.paths import cache_dir
from .services.authentication import auth


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="playyt",
        description="A minimal, colorful, robust YouTube music player for the terminal.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"playyt {__import__('playyt').__version__}",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging.",
    )
    parser.add_argument(
        "--logout",
        action="store_true",
        help="Clear OAuth credentials.",
    )
    parser.add_argument(
        "--reset-cache",
        action="store_true",
        help="Clear the application cache.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.logout:
        auth.logout()
        print("Logged out. OAuth credentials cleared.")
        return 0

    if args.reset_cache:
        cache = cache_dir()
        if cache.exists():
            shutil.rmtree(cache)
        cache.mkdir(parents=True, exist_ok=True)
        print("Cache cleared.")
        return 0

    app = PlayYTApp(debug=args.debug)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
