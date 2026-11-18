#!/usr/bin/env bash
# Phase 2: build the community nevada tree as-is (lineage-23.0, BP2A).
# Usage: scripts/build-nevada.sh            (full build: mka bacon)
#        TARGET=systemimage scripts/build-nevada.sh   (any other mka target)
# Log: ~/lineage/build.log. Safe to re-run; ccache makes repeats fast.
#
# Memory: soong_build alone peaks near 28 GB. The script re-runs itself in its
# own systemd scope with a memory cap, so an out-of-memory kill takes down only
# the build, not the terminal or the Claude app that started it.
# systemd-oomd (Ubuntu) kills a scope that sits at its cap while swapping hard ("memory pressure"
# over 60% for 20 s); it did so at 15:11 on 2026-11-18, mid Soong analysis, though the same build
# had run through the same pressure all day. The scope opts out (ManagedOOMPreference=omit): the
# MemoryMax cap above is already what stops a runaway build.
#   MEM_MAX=26G SWAP_MAX=40G   change the caps
#   NO_SCOPE=1                 skip the scope (not recommended)
#   DEVICE=utah                build the utah product instead of nevada (default nevada)
#   JOBS=10                    limit parallel Ninja jobs (default: cores+2). Use ~10 while the Java r8 app steps run, or they fill the memory cap and swap
set -o pipefail

if [[ -z "$NO_SCOPE" && -z "$BUILD_NEVADA_IN_SCOPE" ]] && command -v systemd-run >/dev/null; then
  export BUILD_NEVADA_IN_SCOPE=1
  exec systemd-run --user --scope --quiet \
    --unit="lineage-build-$(date +%Y%m%d-%H%M%S)" \
    -p MemoryMax="${MEM_MAX:-26G}" -p MemorySwapMax="${SWAP_MAX:-40G}" \
    -p ManagedOOMPreference=omit \
    "$(readlink -f "$0")" "$@"
fi

SRC="${SRC:-$HOME/lineage/android}"
DEVICE="${DEVICE:-nevada}"
TARGET="${TARGET:-bacon}"
LOG="${LOG:-$HOME/lineage/build.log}"

# Clear failed leftovers of earlier builds (a build killed for memory leaves its failed scope behind),
# so build-live reports THIS build's ending and not an old one.
systemctl --user reset-failed 'lineage-build-*' 2>/dev/null || true

cd "$SRC" || exit 1

# Fail fast on prebuilt blobs whose DT_NEEDED doesn't match Android.bp (the
# build would otherwise stop at check_elf_files after ~8 minutes).
# Fix with scripts/apply-nevada-blob-fixups.sh. Skip with SKIP_BLOB_CHECK=1.
if [[ -z "$SKIP_BLOB_CHECK" ]]; then
  python3 -I "$(dirname "$(readlink -f "$0")")/check-vendor-needed.py" || {
    echo "== blob check failed; see above (SKIP_BLOB_CHECK=1 to ignore)"; exit 1; }
fi

export USE_CCACHE=1
export CCACHE_EXEC=/usr/bin/ccache
export LC_ALL=C

# envsetup/lunch use unset variables, so no `set -u` here.
source build/envsetup.sh || exit 1
lunch "lineage_${DEVICE}-bp2a-userdebug" || exit 1

start=$(date +%s)
echo "== build started $(date) target=$TARGET"
mka ${JOBS:+-j$JOBS} "$TARGET" 2>&1 | tee "$LOG"
rc=${PIPESTATUS[0]}
echo "== build ended $(date), exit=$rc, $(( ($(date +%s) - start) / 60 )) min"
exit "$rc"
