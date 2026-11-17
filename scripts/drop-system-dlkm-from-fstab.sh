#!/usr/bin/env bash
# Phase 4: remove the `system_dlkm` entries from every nevada fstab, because our
# build's super has no system_dlkm partition (stock's does).
#
# Found 2026-11-17 from the phone's own boot log: first-stage init failed on
#   "DM_DEV_STATUS failed for system_dlkm_a" -> "Failed to mount required partitions early",
# and (after fixing that) vold aborted on "could not find logical partition system_dlkm_a"
# and init rebooted with reason `vold-failed`. Both read the fstab; this edits all copies:
#   device/motorola/nevada/init/fstab.mt6835                  (first-stage ramdisk, recovery)
#   vendor/motorola/nevada/proprietary/vendor/etc/fstab.mt6835 (what vold reads on the phone)
# Originals are kept once as <file>.orig-dlkm. Safe to re-run. Re-run after any `repo sync`
# that resets those repos. A real system_dlkm partition (with stock's GKI modules) is the
# better long-term fix; this is the quick way to a first boot.
set -euo pipefail
SRC="${SRC:-$HOME/lineage/android}"
n=0
while IFS= read -r f; do
  if grep -q '^system_dlkm[[:space:]]' "$f"; then
    [[ -e "$f.orig-dlkm" ]] || cp -p "$f" "$f.orig-dlkm"
    sed -i '/^system_dlkm[[:space:]]/d' "$f"
    echo "patched: $f"
    n=$((n + 1))
  fi
done < <(find "$SRC/device/motorola/nevada" "$SRC/vendor/motorola/nevada" -type f \( -name 'fstab*' -o -name 'recovery.fstab' \) -not -name '*.orig-dlkm' 2>/dev/null)
echo "fstab files patched: $n (0 means already done, or the files are somewhere else)"
