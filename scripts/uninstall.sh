#!/usr/bin/env bash
#
# PlayYT uninstall script
#
# Removes the PlayYT application. Persistent user data (configuration,
# database, OAuth credentials, cache) is preserved unless explicitly removed.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${PLAYYT_VENV:-$HOME/.local/playyt/.venv}"

log() { printf '[playyt-uninstall] %s\n' "$*"; }
warn() { printf '[playyt-uninstall] WARN: %s\n' "$*" >&2; }

remove_app=1
remove_config=0
remove_db=0
remove_credentials=0
remove_cache=0

usage() {
    cat <<EOF
Usage: $0 [--all] [--keep-app] [--config] [--db] [--credentials] [--cache]

  --all               Remove application and all user data (prompts for data)
  --keep-app          Do not remove the application code/venv
  --config            Also remove configuration
  --db                Also remove the SQLite database
  --credentials       Also remove OAuth credentials
  --cache             Also remove the cache
EOF
    exit 0
}

while [ $# -gt 0 ]; do
    case "$1" in
        --all) remove_app=1; remove_config=1; remove_db=1; remove_credentials=1; remove_cache=1; shift ;;
        --keep-app) remove_app=0; shift ;;
        --config) remove_config=1; shift ;;
        --db) remove_db=1; shift ;;
        --credentials) remove_credentials=1; shift ;;
        --cache) remove_cache=1; shift ;;
        -h|--help) usage ;;
        *) warn "Unknown option: $1"; usage ;;
    esac
done

confirm() {
    local msg="$1"
    printf '%s [y/N] ' "$msg"
    read -r ans
    case "$ans" in
        y|Y) return 0 ;;
        *) return 1 ;;
    esac
}

# Remove application
if [ "$remove_app" -eq 1 ] && [ -d "$VENV_DIR" ]; then
    log "Removing PlayYT virtualenv at $VENV_DIR"
    rm -rf "$VENV_DIR"
fi

# Persistent data (prompt unless --all was given)
if [ "$remove_config" -eq 1 ]; then
    if confirm "Remove configuration (~/.config/playyt)?"; then
        rm -rf ~/.config/playyt
        log "Configuration removed."
    else
        log "Configuration preserved."
    fi
fi

if [ "$remove_db" -eq 1 ]; then
    if confirm "Remove database (~/.local/share/playyt)?"; then
        rm -rf ~/.local/share/playyt
        log "Database removed."
    else
        log "Database preserved."
    fi
fi

if [ "$remove_credentials" -eq 1 ]; then
    if confirm "Remove OAuth credentials (~/.config/playyt/credentials)?"; then
        rm -rf ~/.config/playyt/credentials
        log "Credentials removed."
    else
        log "Credentials preserved."
    fi
fi

if [ "$remove_cache" -eq 1 ]; then
    if confirm "Remove cache (~/.cache/playyt)?"; then
        rm -rf ~/.cache/playyt
        log "Cache removed."
    else
        log "Cache preserved."
    fi
fi

log "Uninstall complete."
