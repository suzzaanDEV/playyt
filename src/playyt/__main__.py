"""Application entry point."""

from __future__ import annotations

import argparse
import shutil
import sys

from dotenv import load_dotenv

from .app import PlayYTApp
from .config.paths import cache_dir, config_dir
from .services.authentication import auth
from .services.playback import playback
from .utils.logging import setup_logging


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
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Check mpv/yt-dlp setup and exit.",
    )
    return parser


def load_env() -> None:
    """Load environment variables from .env file if it exists."""
    env_path = config_dir() / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def main(argv: list[str] | None = None) -> int:
    load_env()

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

    if args.doctor:
        setup_logging(debug=args.debug)
        print("PlayYT playback diagnostics")
        print("-" * 40)
        for line in playback.diagnose():
            print(line)
        print("-" * 40)
        print(f"Logs: {config_dir() / 'logs'}")
        return 0

    app = PlayYTApp(debug=args.debug)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
