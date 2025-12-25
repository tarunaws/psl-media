#!/bin/zsh
set -euo pipefail

# Get the directory where this script is located as the source
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(dirname "$SCRIPT_DIR")"  # Go up one level from code/ to mediaGenAI/

# Default backup location - can be overridden with BACKUP_TARGET environment variable
DEFAULT_TARGET="$HOME/OneDrive - Persistent Systems Limited/mediaGenAIDemo"
TARGET_BASE="${BACKUP_TARGET:-$DEFAULT_TARGET}"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M")
DEST_DIR="$TARGET_BASE/$TIMESTAMP"

mkdir -p "$DEST_DIR"

rsync -a --delete --exclude '.git/' --exclude 'node_modules/' --exclude 'build/' "$SOURCE_DIR/" "$DEST_DIR/"
