#!/usr/bin/env bash
# After a fresh `repo sync` (WSL or laptop): re-apply our local changes to the
# synced tree, in the order BUILD_PLAN.md (Phase 3) says. Safe to re-run.
#   1. git apply patches 0001-0003 in device/motorola/nevada (skipped if already applied)
#   2. apply-nevada-blob-fixups.sh   (patchelf fixes for 5 vendor blobs)
#   3. install-utah-tree.sh          (device/motorola/utah)
# NOT done here (needs the unpacked firmware and a built host tree): extract-utah-kernel.sh,
# make-utah-vendor.sh, and the 66 regenerated blobs. See BUILD_PLAN.md.
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; REPO="$HERE/.."
SRC="${SRC:-$HOME/lineage/android}"

cd "$SRC/device/motorola/nevada"
for p in "$REPO"/patches/device_motorola_nevada/*.patch; do
  # The repo checkout on Windows can give the patches CRLF line endings; strip them.
  lf() { tr -d '' < "$p"; }
  if lf | git apply --check 2>/dev/null; then lf | git apply; echo "applied $(basename "$p")"
  elif lf | git apply --check -R 2>/dev/null; then echo "already applied: $(basename "$p")"
  else echo "CANNOT APPLY $(basename "$p")" >&2; exit 1; fi
done

"$HERE/apply-nevada-blob-fixups.sh"
"$HERE/install-utah-tree.sh"
python3 -I "$HERE/check-vendor-needed.py" || true
