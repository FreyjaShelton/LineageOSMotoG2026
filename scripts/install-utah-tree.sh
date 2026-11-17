#!/usr/bin/env bash
# Copy trees/device_motorola_utah into the Android tree as device/motorola/utah.
# The repo copy is the source of truth; re-run after editing it. Safe to repeat.
# BOOTANIM=circuit scripts/install-utah-tree.sh picks another saved boot animation.
set -euo pipefail
SRC="${SRC:-$HOME/lineage/android}"
HERE="$(dirname "$(readlink -f "$0")")/.."
mkdir -p "$SRC/device/motorola/utah"
rsync -a --delete "$HERE/trees/device_motorola_utah/" "$SRC/device/motorola/utah/"
# Boot animation (45 MB binary, kept under bootanimation/keep/, not under trees/).
ANIM="${BOOTANIM:-trop-pink}"
mkdir -p "$SRC/device/motorola/utah/bootanimation"
cp "$HERE/bootanimation/keep/$ANIM/bootanimation.zip" "$SRC/device/motorola/utah/bootanimation/bootanimation.zip"
echo "boot animation: $ANIM"
echo "installed to $SRC/device/motorola/utah"
