#!/usr/bin/env bash
# Rebuild utah with a REAL system_dlkm partition (r3), check the result, and put the new
# release set on this flash drive. Run on the laptop:
#
#     bash /media/$USER/FREYJA/rebuild-utah-r3.sh
#
# Why: the phone's boot log showed init and vold dying on "system_dlkm_a", because stock's
# super has a system_dlkm partition (an empty placeholder) and ours did not. The utah
# BoardConfig.mk next to this script now builds one. Steps:
#   1. undo the old fstab workaround if it was ever applied
#   2. copy BoardConfig.mk and compare-partitions.py (next to this script) into the repo
#   3. check nevada's BoardConfig really has the super group variable we append to
#   4. scripts/install-utah-tree.sh, then DEVICE=utah JOBS=10 scripts/build-nevada.sh
#   5. check: system_dlkm.img exists, is in the payload and the super group; boot images v4
#   6. save ~/lineage/release/utah-20261117-r3/ and copy it to this drive
# Override: REPO=/path/to/LineageOSMotoG2026  SRC=~/lineage/android  JOBS=10. Safe to re-run.
set -euo pipefail

HERE="$(dirname "$(readlink -f "$0")")"
SRC="${SRC:-$HOME/lineage/android}"
OUT="$SRC/out/target/product/utah"
REL="${REL:-$HOME/lineage/release/utah-20261117-r3}"
FW=$(echo "$HOME"/lineage/firmware/NEVADA*/)

# --- find the repo ---
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

# --- 1. undo the old fstab workaround, if it was applied ---
while IFS= read -r b; do
  f="${b%.orig-dlkm}"; cp -p "$b" "$f"; rm -f "$b"; echo "restored fstab: $f"
done < <(find "$SRC/device/motorola/nevada" "$SRC/vendor/motorola/nevada" -name '*.orig-dlkm' 2>/dev/null)

# --- 2. copy the tree change and the checker ---
grep -q '^BOARD_USES_SYSTEM_DLKMIMAGE := true' "$HERE/BoardConfig.mk" || { echo "BoardConfig.mk next to this script lacks the system_dlkm change." >&2; exit 1; }
cp "$HERE/BoardConfig.mk" "$REPO/trees/device_motorola_utah/BoardConfig.mk"
cp "$HERE/compare-partitions.py" "$REPO/scripts/compare-partitions.py"
echo "== BoardConfig.mk and compare-partitions.py installed in the repo"

# --- 3. the group variable must exist in nevada's BoardConfig ---
if ! grep -q 'BOARD_MOTOROLA_DYNAMIC_PARTITIONS_PARTITION_LIST' "$SRC/device/motorola/nevada/BoardConfig.mk"; then
  echo "nevada's BoardConfig.mk has no BOARD_MOTOROLA_DYNAMIC_PARTITIONS_PARTITION_LIST." >&2
  echo "The super group variable has a different name. Look at what it uses:" >&2
  grep -n 'PARTITION_LIST\|SUPER_PARTITION' "$SRC/device/motorola/nevada/BoardConfig.mk" >&2 || true
  echo "Fix the BOARD_..._PARTITION_LIST += system_dlkm line in the repo's BoardConfig.mk and run again." >&2
  exit 1
fi

# --- 4. install the tree and build ---
powerprofilesctl set balanced 2>/dev/null || true
"$REPO/scripts/install-utah-tree.sh"
echo "== building (about 15 minutes with ccache; Soong re-analysis may take longer); log: ~/lineage/build.log"
DEVICE=utah JOBS="${JOBS:-10}" "$REPO/scripts/build-nevada.sh"

# --- 5. checks ---
echo "== checking the build outputs"
[[ -f "$OUT/system_dlkm.img" ]] || { echo "No system_dlkm.img in $OUT: the partition was not built." >&2; exit 1; }
ls -la "$OUT/system_dlkm.img"
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

# --- 6. release set ---
ZIP=$(ls -t "$OUT"/lineage-23.0-*-UNOFFICIAL-utah.zip | head -1)
echo "== release set in $REL (zip: $(basename "$ZIP"))"
mkdir -p "$REL"
cp "$ZIP" "$REL/"
for f in boot.img init_boot.img vendor_boot.img vbmeta.img vbmeta_system.img dtbo.img system_dlkm.img; do
  [[ -f "$OUT/$f" ]] && cp "$OUT/$f" "$REL/" || echo "  (no $f in the build output, skipped)"
done
( cd "$REL" && rm -f SHA256SUMS && sha256sum -- * > SHA256SUMS && cat SHA256SUMS )

echo "== partition layout of the new zip (compare with stock)"
python3 -I "$REPO/scripts/compare-partitions.py" "$REL" "$FW" | tee "$REL/partition-layout.txt"
grep -q 'super group .*system_dlkm' "$REL/partition-layout.txt" || { echo "system_dlkm is NOT in the super group of the payload." >&2; exit 1; }
grep -q '^  system_dlkm ' "$REL/partition-layout.txt" || { echo "system_dlkm is NOT in the payload's partition list." >&2; exit 1; }
echo "system_dlkm is in the payload and the super group."

# --- 7. copy to the drive ---
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
