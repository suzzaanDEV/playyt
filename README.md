# PlayYT

PlayYT — a warm, minimal, robust YouTube music player for the terminal.

Designed primarily for remote SSH servers. No graphical desktop, no X11, no browser required.

## What PlayYT is

PlayYT is a terminal-native music browser and player for YouTube. It runs inside any terminal
emulator and is optimized for use over SSH on headless Linux servers. You connect to a server,
launch PlayYT, browse YouTube, search for music, manage playlists, build a queue, and control
playback through mpv — all from the keyboard.

The interface is colorful but restrained, minimal but polished, and contains zero emojis.

## Features

- Terminal-based music player (TUI) built with Textual and Rich
- YouTube browsing and search via yt-dlp (no API key required for playback/search)
- Play YouTube videos, playlists, and URLs
- mpv playback with play/pause, next/previous, seek, volume, speed
- Now Playing screen and persistent mini-player visible while browsing
- Local play history (SQLite)
- Persistent playback queue (saved across restarts)
- Google OAuth 2.0 account integration (device flow, headless-friendly)
- YouTube Data API v3: playlists, subscriptions, search
- Keyboard-first navigation with configurable bindings
- Works over SSH, tmux, and screen
- Playback persists across TUI disconnects (attach/detach to existing mpv instance)
- Colorful, emoji-free UI with responsive layouts for 80x24 and larger terminals

## Requirements

- Linux (Linux Mint / Ubuntu based systems recommended)
- Python 3.12+
- mpv
- yt-dlp
- A terminal (80x24 minimum)

For account features (playlists, subscriptions, liked videos), you also need a Google OAuth
client ID and client secret from the Google Cloud Console.

## Installation

### Method 1: Install script (recommended)

The install script detects Python, mpv, and yt-dlp, creates a virtual environment, installs
PlayYT, creates configuration directories, and verifies the installation.

```bash
git clone <repository-url>
cd playyt
./scripts/install.sh
~/.local/playyt/.venv/bin/playyt
```

Optionally add PlayYT to your PATH:

```bash
export PATH="$HOME/.local/playyt/.venv/bin:$PATH"
playyt
```

### Method 2: Manual install

```bash
git clone <repository-url>
cd playyt
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
playyt
```

## First launch

```bash
playyt
```

On first launch, PlayYT creates its configuration directory at `~/.config/playyt/`, its data
directory at `~/.local/share/playyt/`, and its cache directory at `~/.cache/playyt/`.

Press `?` at any time to open the help screen with the full list of keyboard shortcuts.

## CLI

```bash
playyt              Launch the application
playyt --help       Show help
playyt --version    Show version
playyt --debug      Enable debug logging
playyt --logout     Clear OAuth credentials
playyt --reset-cache Clear the application cache
```

## YouTube OAuth setup

Account features (your playlists, subscriptions, liked videos) require Google OAuth 2.0
authentication. PlayYT uses the device flow, which works on headless servers without a browser.

### 1. Create OAuth credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the YouTube Data API v3 for the project
4. Go to Credentials and create an OAuth client ID (Desktop app type)
5. Copy the client ID and client secret

### 2. Configure PlayYT

Export the credentials before launching:

```bash
export PLAYYT_CLIENT_ID="your-client-id"
export PLAYYT_CLIENT_SECRET="your-client-secret"
playyt
```

### 3. Authenticate

When you navigate to Account (or press the Authenticate button), PlayYT will:

1. Display a user code and a verification URL
2. Instruct you to open the URL on another device (phone or computer)
3. Wait for you to authorize the application

Once authorized, PlayYT stores the tokens locally with restrictive file permissions (600) and
refreshes the access token automatically when needed.

Run `playyt --logout` to clear stored credentials.

## SSH usage

PlayYT is designed to be used over SSH:

```bash
ssh user@server
playyt
```

The TUI works correctly over OpenSSH, standard terminal emulators, tmux, and screen. It tolerates
SSH disconnects, terminal resize, slow connections, and temporary network failure.

### Recommended tmux workflow

```bash
tmux new -s playyt
playyt
```

Then detach with `Ctrl-b d`. Playback continues in mpv even after you disconnect from SSH. Reattach
later:

```bash
ssh user@server
tmux attach -t playyt
```

PlayYT detects the existing mpv instance and reattaches to it instead of starting a second player.

### Playback lifecycle operations

- **Quit**: Press `q` or `Ctrl+Q` — playback stops and mpv exits
- **Suspend**: Press `Ctrl+Z` — returns to the shell while audio keeps playing; run `fg` to return
- **SSH/tmux disconnect**: If PlayYT is still running, audio continues; reattach later
- **Reattach**: Launching `playyt` reconnects to an existing mpv if one is still running

## tmux / screen usage

PlayYT works properly inside tmux and screen.

```bash
tmux new -s playyt
playyt
```

Detach and reattach freely. mpv runs in its own session (`start_new_session`) so it survives SSH
disconnects and terminal detaches.

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
| , / . | Playback speed down / up |
| Left / Right | Seek backward / forward (10 seconds) |
| / | Search |
| Tab | Search: move to results |
| Shift+Tab | Search: return to the query |
| Esc | Back |
| Ctrl+Z | Suspend to the shell |
| q / Ctrl+Q | Quit and stop playback |
| ? | Help |

Open the help screen at any time by pressing `?`.

## Playback controls

The mini-player at the bottom of the screen always shows what is playing:

```
Song Title · Artist    0:45 / 3:42   >   80%
```

The Now Playing screen (reached by playing a track) shows:

- Two animated cassette reels that spin while audio plays and freeze when
  paused or buffering
- Instant loading view while a track is resolved, then live status
  (LOADING, PLAYING, PAUSED, BUFFERING, STOPPED)
- Track title, artist/channel, and source
- Progress bar with elapsed and total time
- Shuffle, repeat, volume, and playback-speed indicators
- Control hints, with Esc returning to the previous screen

The reels adapt to the terminal width and fall back to ASCII on terminals
without Unicode support (or when `PLAYYT_ASCII=1` is set), so the screen
works over SSH on basic console setups.

Playback speed adjusts in 0.25x steps with `,` and `.`, between 0.25x and
2.0x (for example `Speed 1.25x`).

## Configuration

Configuration is stored in `~/.config/playyt/config.toml` (TOML format).

Example:

```toml
volume = 80
playback_speed = 1.0
repeat_mode = "off"
shuffle = false
theme = "dark"
audio_output = "auto"
search_limit = 20
cache_size = 200
mpv_path = "mpv"
yt_dlp_path = "yt-dlp"
```

Settings include:

| Setting | Description | Default |
|---------|-------------|---------|
| volume | Playback volume (0-100) | 80 |
| playback_speed | Playback speed multiplier | 1.0 |
| repeat_mode | off, one, or all | off |
| shuffle | Shuffle queue | false |
| theme | Color theme | dark |
| audio_output | mpv audio output | auto |
| search_limit | Max search results | 20 |
| cache_size | Max cached items | 200 |
| mpv_path | Path to mpv binary | mpv |
| yt_dlp_path | Path to yt-dlp binary | yt-dlp |

Never put secrets (OAuth client secret, tokens) in this file. Use environment variables instead:
`PLAYYT_CLIENT_ID` and `PLAYYT_CLIENT_SECRET`.

## Directory layout

```
~/.config/playyt/
├── config.toml       # User configuration
├── credentials/      # OAuth tokens (chmod 600)
├── logs/             # Log files
└── ...

~/.local/share/playyt/
└── database.sqlite   # SQLite database (history, queue, playlists)

~/.cache/playyt/      # Media metadata cache
```

## Troubleshooting

### playyt command not found

Make sure the virtualenv bin directory is on your PATH:

```bash
export PATH="$HOME/.local/playyt/.venv/bin:$PATH"
```

Or run directly:

```bash
$HOME/.local/playyt/.venv/bin/playyt
```

### mpv not found

Install mpv:

```bash
sudo apt install mpv
```

### yt-dlp not found

Install yt-dlp:

```bash
sudo apt install yt-dlp
```

### No audio

Check that mpv can play audio on your system. PlayYT uses mpv's default audio output, which works
with PipeWire, PulseAudio, and ALSA on Linux. You can configure `audio_output` in `config.toml`.

### OAuth authentication fails

- Make sure `PLAYYT_CLIENT_ID` and `PLAYYT_CLIENT_SECRET` are exported
- Make sure the YouTube Data API v3 is enabled in your Google Cloud project
- Make sure your OAuth client is configured as a Desktop app
- Check `~/.config/playyt/logs/playyt.log` for details

### Playback does not start

- Verify `mpv` and `yt-dlp` are installed and on your PATH
- Check the network connection
- Run with `playyt --debug` and check the logs
- Make sure no other mpv instance is holding the IPC socket

### Terminal too small

PlayYT requires at least 80x24. Resize your terminal or SSH window and restart.

## Security

Security is a core requirement of PlayYT:

- OAuth tokens are stored with restrictive file permissions (600)
- Access tokens, refresh tokens, and client secrets are never logged
- No passwords are ever requested or stored
- OAuth uses Google's supported device flow, never custom login forms
- No shell evaluation (`shell=True`) is used for external commands
- All external metadata is treated as untrusted
- PlayYT does not bypass DRM, implement ad-blocking, or use private Google endpoints

## Development

PlayYT uses a modular Python package layout under `src/playyt/`.

### Setup

```bash
git clone <repository-url>
cd playyt
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Run

```bash
playyt
```

### Run tests

```bash
pytest
```

### Lint

```bash
ruff check src/ tests/
```

### Format

```bash
ruff format src/ tests/
```

### Type check

```bash
mypy src/
```

### Project structure

```
playyt/
├── pyproject.toml
├── README.md
├── LICENSE
├── Makefile
├── .gitignore
├── scripts/
│   ├── install.sh
│   ├── update.sh
│   └── uninstall.sh
├── src/
│   └── playyt/
│       ├── __main__.py     # CLI entry point
│       ├── app.py          # Textual application
│       ├── config/         # Settings, paths, defaults
│       ├── models/         # Video, Playlist, Queue, Playback, Account
│       ├── services/       # Playback, Search, YouTube, Authentication
│       ├── integrations/   # mpv IPC, yt-dlp, Google OAuth
│       ├── database/       # SQLite layer, repositories, migrations
│       ├── ui/             # Screens, widgets, styles, bindings
│       └── utils/          # Errors, logging
└── tests/
    └── unit/
```

## Testing

PlayYT includes unit tests for the queue model, settings, database repositories, search service,
and playback model. Tests do not make real YouTube API calls.

```bash
pytest
```

## Updating

```bash
./scripts/update.sh
```

The update script preserves your database, configuration, and OAuth credentials, runs database
migrations, and verifies the installation.

## Uninstalling

```bash
./scripts/uninstall.sh
```

The uninstall script separates application code from configuration, database, OAuth credentials,
and cache. It asks before deleting persistent user data.

## License

MIT