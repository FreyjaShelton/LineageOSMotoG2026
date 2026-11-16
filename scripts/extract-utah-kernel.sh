#!/usr/bin/env bash
# Phase 3: build device/motorola/utah-kernel from OUR stock firmware, so the
# kernel, DTB and modules all come from the same build as the phone's vendor
# blobs (W1WNS36.18-114-3-2-1-1-1; kernel 5.15.189). Same layout as
# device/motorola/nevada-kernel. Safe to re-run (replaces the directory).
# Needs: firmware in ~/lineage/firmware, the super partitions split into
# ~/lineage/work/parts (vendor_dlkm_a.img), and a built host tree (unpack_bootimg, fsck.erofs).
set -euo pipefail
SRC="${SRC:-$HOME/lineage/android}"; WORK="${WORK:-$HOME/lineage/work}"
FW=$(echo "$HOME"/lineage/firmware/NEVADA*/); HB="$SRC/out/host/linux-x86/bin"
OUT="$SRC/device/motorola/utah-kernel"; T=$(mktemp -d "$WORK/utah-kernel.XXXX"); trap 'rm -rf "$T"' EXIT

mkdir -p "$T/boot" "$T/vboot" "$T/ramdisk" "$T/dlkm"
"$HB/unpack_bootimg" --boot_img "$FW/boot.img" --out "$T/boot" >/dev/null
"$HB/unpack_bootimg" --boot_img "$FW/vendor_boot.img" --out "$T/vboot" >/dev/null
( cd "$T/ramdisk" && lz4 -dc "$T/vboot/vendor_ramdisk00" | cpio -idm --no-absolute-filenames 2>/dev/null )
"$HB/fsck.erofs" --extract="$T/dlkm" --no-preserve "$WORK/parts/vendor_dlkm_a.img" >/dev/null

rm -rf "$OUT"; mkdir -p "$OUT/dtb" "$OUT/vendor" "$OUT/vendor_ramdisk"
cp "$T/boot/kernel" "$OUT/Image.gz"                          # gzip Image from boot.img
tail -c +65 "$T/vboot/dtb" > "$OUT/dtb/nevada.dtb"          # drop the 64-byte DT table header
cp "$T"/dlkm/lib/modules/*.ko "$OUT/vendor/"
cp "$T"/ramdisk/lib/modules/*.ko "$OUT/vendor_ramdisk/"
cp "$T/dlkm/lib/modules/modules.load" "$OUT/modules.load.vendor"
cp "$T/ramdisk/lib/modules/modules.load" "$OUT/modules.load.vendor_ramdisk"
cp "$T/ramdisk/lib/modules/modules.load.recovery" "$OUT/modules.load.recovery"
cp "$SRC/device/motorola/nevada-kernel/LICENSE" "$OUT/"
echo "utah-kernel: $(strings "$OUT/vendor/$(ls "$OUT/vendor" | head -1)" | grep -m1 '^vermagic=' | cut -c1-40), $(ls "$OUT/vendor" | wc -l) vendor + $(ls "$OUT/vendor_ramdisk" | wc -l) ramdisk modules"
