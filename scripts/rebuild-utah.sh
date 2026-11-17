#!/usr/bin/env bash
# Rebuild utah with the init_boot header-version fix, check the result, and put
# the new release set on this flash drive. Run on the laptop:
#
#     bash /media/$USER/FREYJA/rebuild-utah.sh
#
# The BoardConfig.mk next to this script is the fixed one (it adds
# BOARD_MKBOOTIMG_INIT_ARGS += --header_version 4). Steps:
#   1. copy it into the repo's trees/device_motorola_utah/
#   2. scripts/install-utah-tree.sh, then DEVICE=utah JOBS=10 scripts/build-nevada.sh
#   3. check boot.img, vendor_boot.img and init_boot.img are all header v4
#   4. save a release set in ~/lineage/release/utah-20261117-r2/ and copy it to this drive
# Override the repo location with REPO=/path/to/LineageOSMotoG2026, the Android
# tree with SRC=, and the build speed with JOBS=. Safe to re-run (ccache).
set -euo pipefail

HERE="$(dirname "$(readlink -f "$0")")"
SRC="${SRC:-$HOME/lineage/android}"
OUT="$SRC/out/target/product/utah"
REL="${REL:-$HOME/lineage/release/utah-20261117-r2}"

# --- find the repo (the one that has scripts/install-utah-tree.sh) ---
REPO="${REPO:-}"
if [[ -z "$REPO" ]]; then
  for c in "$HOME/LineageOSMotoG2026" "$HOME/lineage/LineageOSMotoG2026" "$HOME/projects/LineageOSMotoG2026"; do
    [[ -f "$c/scripts/install-utah-tree.sh" ]] && { REPO="$c"; break; }
  done
fi
if [[ -z "$REPO" ]]; then
  f=$(find "$HOME" -maxdepth 4 -name install-utah-tree.sh -not -path "$SRC/*" 2>/dev/null | head -1 || true)
  [[ -n "$f" ]] && REPO="$(dirname "$(dirname "$f")")"
fi
[[ -n "$REPO" && -f "$REPO/scripts/install-utah-tree.sh" ]] || { echo "Cannot find the repo. Run again with REPO=/path/to/LineageOSMotoG2026" >&2; exit 1; }
echo "== repo: $REPO"

# --- 1. the fixed BoardConfig.mk ---
# Use the one next to this script (flash drive) if present; otherwise the repo's own.
if [[ -f "$HERE/BoardConfig.mk" ]]; then
  grep -q '^BOARD_MKBOOTIMG_INIT_ARGS += --header_version 4' "$HERE/BoardConfig.mk" || { echo "BoardConfig.mk next to this script lacks the fix." >&2; exit 1; }
  cp "$HERE/BoardConfig.mk" "$REPO/trees/device_motorola_utah/BoardConfig.mk"
fi
grep -q '^BOARD_MKBOOTIMG_INIT_ARGS += --header_version 4' "$REPO/trees/device_motorola_utah/BoardConfig.mk" || { echo "Repo BoardConfig.mk lacks the init_boot header v4 fix." >&2; exit 1; }
echo "== BoardConfig.mk ready in the repo"

# --- 2. install the tree and build ---
powerprofilesctl set balanced 2>/dev/null || true
"$REPO/scripts/install-utah-tree.sh"
echo "== building (about 15 minutes with ccache); log: ~/lineage/build.log"
DEVICE=utah JOBS="${JOBS:-10}" "$REPO/scripts/build-nevada.sh"

# --- 3. check the headers ---
echo "== checking boot image header versions"
python3 -I - "$OUT" <<'PY'
import struct, sys, os
out = sys.argv[1]
bad = False
for n in ("boot.img", "init_boot.img", "vendor_boot.img"):
    d = open(os.path.join(out, n), "rb").read(2048)
    if d[:8] == b"ANDROID!":
        v = struct.unpack_from("<I", d, 40)[0]
    elif d[:8] == b"VNDRBOOT":
        v = struct.unpack_from("<I", d, 8)[0]
    else:
        v = None
    print(f"  {n}: header v{v}")
    if v != 4:
        bad = True
sys.exit(1 if bad else 0)
PY

# --- 4. release set ---
ZIP=$(ls -t "$OUT"/lineage-23.0-*-UNOFFICIAL-utah.zip | head -1)
echo "== release set in $REL (zip: $(basename "$ZIP"))"
mkdir -p "$REL"
cp "$ZIP" "$REL/"
for f in boot.img init_boot.img vendor_boot.img vbmeta.img vbmeta_system.img dtbo.img; do
  [[ -f "$OUT/$f" ]] && cp "$OUT/$f" "$REL/" || echo "  (no $f in the build output, skipped)"
done
( cd "$REL" && rm -f SHA256SUMS && sha256sum -- * > SHA256SUMS && cat SHA256SUMS )

# --- 5. copy to the drive (skipped when run from inside the repo) ---
if [[ "$HERE" == "$REPO/scripts" ]]; then
  echo; echo "Done. Release set: $REL"; exit 0
fi
DEST="$HERE/$(basename "$REL")"
need_kb=$(du -sk "$REL" | cut -f1)
free_kb=$(df -Pk "$HERE" | awk 'NR==2 {print $4}')
(( free_kb > need_kb + 102400 )) || { echo "Not enough space on the drive." >&2; exit 1; }
echo "== copying to $DEST"
mkdir -p "$DEST"
cp -r --no-preserve=mode,ownership "$REL"/. "$DEST"/
echo "== flushing to the drive"
sync
( cd "$DEST" && sha256sum -c SHA256SUMS )

echo
echo "Done. Eject the drive before unplugging it:"
echo "    udisksctl unmount -b \$(findmnt -no SOURCE \"$HERE\")"
