#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="${ANKI_ADDON_TARGET:-$HOME/.local/share/Anki2/addons21/guitarist}"

mkdir -p "$target"
rsync -a --delete \
  --exclude .git \
  --exclude __pycache__ \
  --exclude tests \
  "$repo_root/" "$target/"

find "$target" -type d -name '__pycache__' -prune -exec rm -rf {} +
