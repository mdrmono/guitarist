#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version="$(sed -n 's/^version = "\([^"]*\)"/\1/p' "$repo_root/pyproject.toml")"

if [[ -z "$version" ]]; then
  echo "Could not read the project version from pyproject.toml." >&2
  exit 1
fi

output_dir="$repo_root/dist"
artifact="$output_dir/Guitarist-$version.ankiaddon"

mkdir -p "$output_dir"
rm -f "$artifact"

cd "$repo_root"
zip -q -r "$artifact" \
  __init__.py \
  config.json \
  config.md \
  manifest.json \
  LICENSE \
  assets \
  core \
  dev \
  integration \
  ui \
  -x '*/__pycache__/*' '*.pyc'

echo "$artifact"
