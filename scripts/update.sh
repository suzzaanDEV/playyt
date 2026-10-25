#!/usr/bin/env bash
#
# PlayYT update script
#
# Updates PlayYT code while preserving database, configuration, and OAuth
# credentials. Runs database migrations and verifies the installation.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${PLAYYT_VENV:-$HOME/.local/playyt/.venv}"

log() { printf '[playyt-update] %s\n' "$*"; }

if [ ! -d "$VENV_DIR" ]; then
    echo "Virtualenv not found at $VENV_DIR. Run scripts/install.sh first." >&2
    exit 1
fi
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

log "Updating PlayYT code"
cd "$REPO_DIR"
git pull --ff-only || true

log "Reinstalling PlayYT"
pip install --upgrade pip >/dev/null 2>&1
pip install -e "$REPO_DIR"

log "Running database migrations (via health check)"
"$VENV_DIR/bin/python3" -c "
from playyt.database import db
print('Database initialized OK')
db.close()
"

log "Update complete. Run: $VENV_DIR/bin/playyt --version"
