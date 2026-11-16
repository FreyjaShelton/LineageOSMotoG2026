#!/usr/bin/env bash
# Apply the ELF blob fixups that device/motorola/nevada/extract-files.py
# defines but that the published vendor/motorola/nevada repo is missing.
#
# The vendor repo's Android.bp was generated from fixed-up blobs, but the
# .so files it ships are the unfixed originals, so check_elf_files fails
# (first seen: pq_aidl-V1-ndk needs graphics.common-V3, Android.bp says V6).
# These are exactly the extract-files.py fixups for the 5 blobs below, run with
# the same patchelf build extract-utils uses by default (0_18).
#
# Safe to re-run: each step only runs if the blob still needs it. Originals are
# saved once to ~/lineage/work/blob-orig/ before the first change.
# Re-run after any `repo sync` that resets vendor/motorola/nevada.
# Check with: scripts/check-vendor-needed.py   (should report 0 blobs)
set -euo pipefail

TOP="${TOP:-$HOME/lineage/android}"
P="$TOP/vendor/motorola/nevada/proprietary"
PATCHELF="$TOP/prebuilts/extract-tools/linux-x86/bin/patchelf-0_18"
READELF="$TOP/prebuilts/clang/host/linux-x86/llvm-binutils-stable/llvm-readelf"
BACKUP="${BACKUP:-$HOME/lineage/work/blob-orig}"

has() { "$READELF" -d "$1" | grep -q "(NEEDED).*\[$2\]"; }

backup() {
  local rel=$1
  if [[ ! -e "$BACKUP/$rel" ]]; then
    mkdir -p "$(dirname "$BACKUP/$rel")"
    cp -p "$P/$rel" "$BACKUP/$rel"
  fi
}

# op <blob> remove <lib> | add <lib> | replace <old> <new>
op() {
  local rel=$1 action=$2 f="$P/$1"
  case $action in
    remove)
      if has "$f" "$3"; then backup "$rel"; "$PATCHELF" --remove-needed "$3" "$f"; echo "$rel: removed $3"; fi ;;
    add)
      if ! has "$f" "$3"; then backup "$rel"; "$PATCHELF" --add-needed "$3" "$f"; echo "$rel: added $3"; fi ;;
    replace)
      if has "$f" "$3"; then backup "$rel"; "$PATCHELF" --replace-needed "$3" "$4" "$f"; echo "$rel: $3 -> $4"; fi ;;
  esac
}

op vendor/lib64/libtpa.so remove android.hardware.security.keymint-V2-ndk.so
op vendor/lib64/libtpa.so remove libkeymint.so
op vendor/lib64/libtpa.so add    android.hardware.security.keymint-V1-ndk.so
op vendor/lib64/libtpa.so add    android.hardware.security.rkp-V3-ndk.so

op vendor/lib64/librilfusion.so remove android.hardware.radio.sim-V2-ndk.so
op vendor/lib64/librilfusion.so remove android.hardware.radio.config-V2-ndk.so
op vendor/lib64/librilfusion.so add    android.hardware.radio.sim-V1-ndk.so
op vendor/lib64/librilfusion.so add    android.hardware.radio.config-V1-ndk.so

op vendor/lib64/vendor.mediatek.hardware.pq_aidl-V1-ndk.so replace \
   android.hardware.graphics.common-V3-ndk.so android.hardware.graphics.common-V6-ndk.so

for p in AIMEMC AISR; do
  op "vendor/lib64/libcodec2_vpp_${p}_plugin.so" remove android.hardware.graphics.allocator-V1-ndk.so
  op "vendor/lib64/libcodec2_vpp_${p}_plugin.so" remove android.hardware.graphics.common-V3-ndk.so
done
echo "done"
