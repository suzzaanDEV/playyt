#!/usr/bin/env bash
#
# PlayYT install script
#
# Installs PlayYT and its runtime dependencies into a user-level virtualenv.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_PREFIX="${PLAYYT_PREFIX:-$HOME/.local}"
VENV_DIR="${PLAYYT_VENV:-$INSTALL_PREFIX/playyt/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

log() { printf '[playyt] %s\n' "$*"; }
err() { printf '[playyt] ERROR: %s\n' "$*" >&2; exit 1; }

# 1. Detect Linux
case "$(uname -s)" in
    Linux) ;;
    *) err "This installer targets Linux. Detected: $(uname -s)" ;;
esac

# 2. Detect Python
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    err "Python ($PYTHON_BIN) not found. Install python3 (>=3.12)."
fi
PY_VERSION=$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
log "Python $PY_VERSION detected"

# 3. Detect mpv
if ! command -v mpv >/dev/null 2>&1; then
    err "mpv not found. Install mpv (e.g. sudo apt install mpv)."
fi
log "mpv detected: $(mpv --version 2>/dev/null | head -1)"

# 4. Detect yt-dlp
if ! command -v yt-dlp >/dev/null 2>&1; then
    err "yt-dlp not found. Install yt-dlp (e.g. sudo apt install yt-dlp)."
fi
log "yt-dlp detected: $(yt-dlp --version 2>/dev/null)"

# 5. Create virtual environment
log "Creating virtual environment at $VENV_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

# 6. Install PlayYT
log "Installing PlayYT"
pip install --upgrade pip >/dev/null 2>&1
pip install -e "$REPO_DIR"

# 7. Create configuration directories
log "Creating configuration directories"
mkdir -p "$HOME/.config/playyt/credentials"
mkdir -p "$HOME/.config/playyt/logs"
mkdir -p "$HOME/.local/share/playyt"
mkdir -p "$HOME/.cache/playyt"

# 8. Verify dependencies
log "Verifying dependencies"
"$VENV_DIR/bin/python3" -c "import textual, rich, pydantic, yt_dlp, google_auth; print('Python deps OK')"
command -v mpv >/dev/null && echo "mpv OK"
command -v yt-dlp >/dev/null && echo "yt-dlp OK"

# 9. Basic health check
log "Running health check"
"$VENV_DIR/bin/playyt" --version

# 10. Instructions
cat <<EOF

PlayYT installed successfully.

Run with:
  $VENV_DIR/bin/playyt

Optional: add to your PATH:
  export PATH=\"$VENV_DIR/bin:\$PATH\"

OAuth setup (for account features):
  export PLAYYT_CLIENT_ID="your-client-id"
  export PLAYYT_CLIENT_SECRET="your-client-secret"
  playyt

Documentation: see README.md

EOF
