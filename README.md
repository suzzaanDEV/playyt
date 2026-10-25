# PlayYT

A minimal, colorful, robust YouTube music player for the terminal.

Designed primarily for remote SSH servers. No graphical desktop required.

## Features

- Terminal-based music player (TUI) built with Textual
- YouTube browsing and search (via yt-dlp, no API key required)
- Play YouTube videos, playlists, and URLs
- mpv playback with play/pause, next/previous, seek, volume, speed
- Now Playing screen and persistent mini-player
- Local play history (SQLite)
- Persistent playback queue
- Google OAuth 2.0 account integration (device flow, headless-friendly)
- YouTube Data API v3: playlists, subscriptions, search
- Keyboard-first navigation
- Works over SSH, tmux, and screen
- Playback persists across TUI disconnects (attach/detach)
- Colorful, emoji-free UI

## Requirements

- Linux (Linux Mint / Ubuntu based systems recommended)
- Python 3.12+
- mpv
- yt-dlp
- A terminal (80x24 minimum)

## Installation

```bash
git clone <repository>
cd playyt
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Or use the install script:

```bash
./scripts/install.sh
```

## First launch

```bash
playyt
```

## YouTube OAuth setup

Account features require a Google OAuth client ID and secret. Create credentials in the
[Google Cloud Console](https://console.cloud.google.com/), enable the YouTube Data API v3,
and create an OAuth client ID (Desktop app type).

Then export them before launching:

```bash
export PLAYYT_CLIENT_ID="your-client-id"
export PLAYYT_CLIENT_SECRET="your-client-secret"
playyt
```

Run `playyt --logout` to clear stored credentials.

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| Up / Down | Navigate |
| Enter | Select / play |
| Space | Play / pause |
| n | Next track |
| p | Previous track |
| a | Add to queue |
| d | Remove item |
| s | Shuffle |
| r | Repeat |
| + / - | Volume up / down |
| Left / Right | Seek backward / forward |
| / | Search |
| Esc | Back |
| q | Quit |
| ? | Help |

## Configuration

Configuration is stored in `~/.config/playyt/config.toml`.
Database and OAuth tokens are stored under `~/.local/share/playyt/` and
`~/.config/playyt/credentials/` respectively.

## Security

- OAuth tokens are stored with restrictive file permissions (600).
- Tokens, refresh tokens, and client secrets are never logged.
- No passwords are ever requested or stored.

## Development

```bash
pytest
ruff check .
ruff format --check .
mypy src/
```

## License

MIT
