#!/usr/bin/env bash
# Put OUR firmware's blobs into vendor/motorola/nevada, the restricted way BUILD_PLAN.md
# Phase 3 describes (this recreates what lived on the laptop in ~/lineage/work):
#   1. add the 3 blobs the published vendor repo lacks (checked against
#      patches/extracted-blobs.sha256)
#   2. back up the vendor repo, run device/motorola/nevada/extract-files.py on our unpacked
#      firmware (it rebuilds the repo strictly from proprietary-files.txt, deleting ~400 files),
#      keep that result in ~/lineage/work/vendor-nevada-regen, and list the blobs it modified
#      in ~/lineage/work/regen-modified.txt
#   3. restore the backup and copy over only the modified blobs (about 66)
# Needs scripts/unpack-firmware.sh done first, and wsl-after-sync.sh (patches + 5 ELF fixups).
# Re-running is safe: it starts again from the pristine backup, once one exists.
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; REPO="$HERE/.."
SRC="${SRC:-$HOME/lineage/android}"; WORK="${WORK:-$HOME/lineage/work}"
V="$SRC/vendor/motorola/nevada"; X="$WORK/x"
BACKUP="$WORK/vendor-nevada-backup"; REGEN="$WORK/vendor-nevada-regen"; DUMP="$WORK/dump"
FW=$(echo "$HOME"/lineage/firmware/NEVADA*/); FW="${FW%/}"

# --- 1. the three missing blobs ---
get() { # <path under proprietary/> <path under x/>
  mkdir -p "$(dirname "$V/proprietary/$1")"; cp -f "$X/$2" "$V/proprietary/$1"; }
get system_ext/lib64/libhidltcmd.so                                   system_ext/lib64/libhidltcmd.so
get system/lib64/com.motorola.hardware.biometric.fingerprint-V1-ndk.so system/system/lib64/com.motorola.hardware.biometric.fingerprint-V1-ndk.so
get vendor/bin/hw/android.hardware.bluetooth@1.1-service-mediatek     vendor/bin/hw/android.hardware.bluetooth@1.1-service-mediatek
( cd "$V/proprietary" && sha256sum -c <(tr -d '\r' < "$REPO/patches/extracted-blobs.sha256") )

# --- 2. extract with the tree's own script ---
if [ ! -d "$BACKUP" ]; then cp -a "$V" "$BACKUP"; fi          # pristine copy, made once
rm -rf "$DUMP"; mkdir -p "$DUMP"
for p in system vendor product system_ext vendor_dlkm system_dlkm; do ln -s "$X/$p" "$DUMP/$p"; done
for f in "$FW"/*.img; do ln -sf "$f" "$DUMP/$(basename "$f")"; done
rm -rf "$V"; cp -a "$BACKUP" "$V"
( cd "$SRC/device/motorola/nevada" && PYTHONPATH="$SRC/tools/extract-utils" python3 extract-files.py "$DUMP" )

# --- 3. keep only the modified blobs ---
rm -rf "$REGEN"; cp -a "$V" "$REGEN"
( cd "$REGEN/proprietary" && find . -type f | sort ) | while read -r f; do
  if [ -f "$BACKUP/proprietary/$f" ] && ! cmp -s "$REGEN/proprietary/$f" "$BACKUP/proprietary/$f"; then echo "$f"; fi
done > "$WORK/regen-modified.txt"
rm -rf "$V"; cp -a "$BACKUP" "$V"
while read -r f; do cp -f "$REGEN/proprietary/$f" "$V/proprietary/$f"; done < "$WORK/regen-modified.txt"
echo "modified blobs copied: $(wc -l < "$WORK/regen-modified.txt")  (the laptop had 66)"
python3 -I "$HERE/check-vendor-needed.py" || true
