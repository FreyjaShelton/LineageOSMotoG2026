#!/usr/bin/env bash
# Unpack OUR stock firmware's super image into partition images and extracted trees,
# the way the laptop's ~/lineage/work was made (BUILD_PLAN.md, Phase 2 and 3):
#   ~/lineage/work/parts/<name>_a.img   the EROFS partitions (system, vendor, product, ...)
#   ~/lineage/work/x/<name>/            each one unpacked  (x/system/system/lib64/... nests twice)
# Needs: firmware in ~/lineage/firmware/NEVADA*/ and `fsck.erofs` (apt: erofs-utils).
# Safe to re-run: finished partitions are skipped.
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"
WORK="${WORK:-$HOME/lineage/work}"
FW=$(echo "$HOME"/lineage/firmware/NEVADA*/); FW="${FW%/}"
mkdir -p "$WORK/parts" "$WORK/x"

if ! ls "$WORK"/parts/system_a.img >/dev/null 2>&1; then
  echo "== splitting super into partitions"
  FW="$FW" OUT="$WORK/parts" python3 -I "$HERE/super-extract.py" all | tail -15
fi

for img in "$WORK"/parts/*_a.img; do
  n=$(basename "$img" _a.img)
  if [ -e "$WORK/x/$n/.done" ]; then echo "== $n: already unpacked"; continue; fi
  echo "== unpacking $n"
  rm -rf "$WORK/x/$n"; mkdir -p "$WORK/x/$n"
  fsck.erofs --extract="$WORK/x/$n" --no-preserve "$img" >/dev/null
  touch "$WORK/x/$n/.done"
done
echo "unpacked: $(ls "$WORK/x" | tr '\n' ' ')"
