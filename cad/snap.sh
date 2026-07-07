#!/usr/bin/env bash
# Snapshot the current machine render into the dated log.
# usage:  MACHINE=cnc_hotwire NOTE=initial-model bash cad/snap.sh
set -euo pipefail
MACHINE="${MACHINE:-cnc_hotwire}"
NOTE="${NOTE:-update}"
here="$(cd "$(dirname "$0")" && pwd)"
dir="$here/renders/$MACHINE"
mkdir -p "$dir"
n=$(printf '%04d' $(( $(ls "$dir"/*.png 2>/dev/null | wc -l) + 1 )))
cp "$here/build/${MACHINE}_iso.png" "$dir/${n}-${NOTE}.png"
echo "- ${n}-${NOTE}.png — $(date -I) — ${NOTE}" >> "$dir/INDEX.md"
echo "logged $dir/${n}-${NOTE}.png"
