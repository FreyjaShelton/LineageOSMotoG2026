#!/usr/bin/env bash
# DEBUG build (r5-debug): the r4 image plus a vendor init rc that panics the kernel 150 s after
# early-init if boot has not completed (UTAH_DEBUG_PANIC=1), so the hung boot leaves a log in
# pstore (bootprof milestones + process list with wait channels). NEVER ship this build.
# Put the result on this flash drive. Run on the laptop:
#
#     bash /media/$USER/FREYJA/rebuild-utah-r5-debug.sh
#
# Why: r3 (real system_dlkm) got past the old boot loop but sat at the Hello Moto logo with no
# USB device. The r3 images, read offline, showed /system/bin/hwservicemanager is a dangling
# symlink (system_ext has no hwservicemanager and no rc), and init logged
# "service hwservicemanager not found". The Android 13 vendor's HIDL HALs cannot register
# without it. device.mk (next to this script) adds hwservicemanager and
# android.hidl.allocator@1.0-service. Steps:
#   1. copy device.mk, BoardConfig.mk and the check scripts from this drive into the repo
#   2. probe that the two modules exist in the source tree (stop early if not)
#   3. scripts/install-utah-tree.sh, then DEVICE=utah JOBS=10 scripts/build-nevada.sh
#   4. check: the files exist in the built system_ext; boot images v4; system_dlkm in payload;
#      no dangling /system/bin/hwservicemanager symlink (rebuilds the images from the zip)
#   5. save ~/lineage/release/utah-20261117-r4/ and copy it to this drive
# Override: REPO=/path/to/LineageOSMotoG2026  SRC=~/lineage/android  JOBS=10. Safe to re-run.
set -euo pipefail

HERE="$(dirname "$(readlink -f "$0")")"
SRC="${SRC:-$HOME/lineage/android}"
OUT="$SRC/out/target/product/utah"
REL="${REL:-$HOME/lineage/release/utah-20261117-r5-debug}"
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

# --- 1. copy the tree files and check scripts ---
grep -q 'UTAH_DEBUG_PANIC' "$HERE/device.mk" || { echo "device.mk next to this script lacks the debug switch." >&2; exit 1; }
grep -q 'hwservicemanager' "$HERE/device.mk" || { echo "device.mk next to this script lacks hwservicemanager." >&2; exit 1; }
grep -q '^BOARD_USES_SYSTEM_DLKMIMAGE := true' "$HERE/BoardConfig.mk" || { echo "BoardConfig.mk next to this script lacks the system_dlkm change." >&2; exit 1; }
cp "$HERE/device.mk" "$REPO/trees/device_motorola_utah/device.mk"
mkdir -p "$REPO/trees/device_motorola_utah/debug"
cp "$HERE/zz-debug-panic.rc" "$REPO/trees/device_motorola_utah/debug/zz-debug-panic.rc"
cp "$HERE/BoardConfig.mk" "$REPO/trees/device_motorola_utah/BoardConfig.mk"
for s in compare-partitions.py payload-extract.py erofs-ls.py dangling-symlinks.py; do cp "$HERE/$s" "$REPO/scripts/$s"; done
echo "== device.mk, BoardConfig.mk and check scripts installed in the repo"

# --- 2. do the modules exist in this source tree? ---
ok=1
grep -rq 'name: "hwservicemanager"' "$SRC/system/hwservicemanager" 2>/dev/null || { echo "No module named hwservicemanager under $SRC/system/hwservicemanager" >&2; ok=0; }
grep -rq 'name: "android.hidl.allocator@1.0-service"' "$SRC/system/libhidl" 2>/dev/null || { echo "No module named android.hidl.allocator@1.0-service under $SRC/system/libhidl" >&2; ok=0; }
if [[ "$ok" != 1 ]]; then
  echo "A module is missing from this LineageOS tree. Where it might be:" >&2
  grep -rl 'hwservicemanager' "$SRC/system" --include=Android.bp 2>/dev/null | head >&2 || true
  echo "Tell Claude what this printed; the fallback is to ship stock's prebuilt binaries." >&2
  exit 1
fi
echo "== both modules exist in the source tree"

# --- 3. install the tree and build ---
powerprofilesctl set balanced 2>/dev/null || true
"$REPO/scripts/install-utah-tree.sh"
echo "== building (about 15 minutes with ccache; Soong re-analysis may take longer); log: ~/lineage/build.log"
UTAH_DEBUG_PANIC=1 DEVICE=utah JOBS="${JOBS:-10}" "$REPO/scripts/build-nevada.sh"

# --- 4. checks ---
echo "== checking the built system_ext"
fail=0
for f in vendor/etc/init/zz-debug-panic.rc system_ext/bin/hwservicemanager system_ext/etc/init/hwservicemanager.rc \
         system_ext/bin/hw/android.hidl.allocator@1.0-service system_ext/etc/init/android.hidl.allocator@1.0-service.rc; do
  if [[ -e "$OUT/$f" ]]; then echo "  ok   $f"; else echo "  MISSING $f" >&2; fail=1; fi
done
[[ "$fail" == 0 ]] || { echo "The build did not install the HIDL service manager files." >&2; exit 1; }
[[ -f "$OUT/system_dlkm.img" ]] || { echo "No system_dlkm.img in $OUT." >&2; exit 1; }
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

# --- 5. release set ---
ZIP=$(ls -t "$OUT"/lineage-23.0-*-UNOFFICIAL-utah.zip | head -1)
echo "== release set in $REL (zip: $(basename "$ZIP"))"
mkdir -p "$REL"
cp "$ZIP" "$REL/"
for f in boot.img init_boot.img vendor_boot.img vbmeta.img vbmeta_system.img dtbo.img system_dlkm.img; do
  [[ -f "$OUT/$f" ]] && cp "$OUT/$f" "$REL/" || echo "  (no $f in the build output, skipped)"
done
( cd "$REL" && rm -f SHA256SUMS && sha256sum -- * > SHA256SUMS && cat SHA256SUMS )

echo "== partition layout of the new zip"
python3 -I "$REPO/scripts/compare-partitions.py" "$REL" "$FW" | tee "$REL/partition-layout.txt"
grep -q 'super group .*system_dlkm' "$REL/partition-layout.txt" || { echo "system_dlkm is NOT in the super group of the payload." >&2; exit 1; }

echo "== rebuilding the images from the zip to scan for dangling symlinks (a few minutes)"
TMP="$(mktemp -d "$HOME/lineage/work/r4-check.XXXX")"
python3 -I "$REPO/scripts/payload-extract.py" "$ZIP" "$TMP" system system_ext vendor product
python3 -I "$REPO/scripts/dangling-symlinks.py" "$TMP" | tee "$REL/dangling-symlinks.txt"
rm -rf "$TMP"
if grep -q 'hwservicemanager' "$REL/dangling-symlinks.txt"; then
  echo "hwservicemanager is STILL a dangling symlink in the zip." >&2; exit 1
fi
echo "hwservicemanager resolves in the built zip."

# --- 6. copy to the drive ---
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
