#!/usr/bin/env bash
# Copy trees/device_motorola_utah into the Android tree as device/motorola/utah.
# The repo copy is the source of truth; re-run after editing it. Safe to repeat.
set -euo pipefail
SRC="${SRC:-$HOME/lineage/android}"
HERE="$(dirname "$(readlink -f "$0")")/.."
mkdir -p "$SRC/device/motorola/utah"
rsync -a --delete "$HERE/trees/device_motorola_utah/" "$SRC/device/motorola/utah/"
echo "installed to $SRC/device/motorola/utah"
