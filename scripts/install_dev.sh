#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "$(uname)" = "Darwin" ]]; then
  target="${ANKI_ADDON_TARGET:-$HOME/Library/Application Support/Anki2/addons21/guitarist}"
else
  target="${ANKI_ADDON_TARGET:-$HOME/.local/share/Anki2/addons21/guitarist}"
fi

mkdir -p "$target"
rsync -a --delete \
  --exclude .git \
  --exclude __pycache__ \
  --exclude tests \
  "$repo_root/" "$target/"

find "$target" -type d -name '__pycache__' -prune -exec rm -rf {} +
