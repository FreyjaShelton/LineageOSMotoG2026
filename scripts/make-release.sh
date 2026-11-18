#!/usr/bin/env bash
# Run on the build machine after a utah build (the laptop; also works in WSL): check the debug rc and the
# boot image headers, then save a release set in ~/lineage/release/<name> (default utah-<date>-debug).
# Fetch it to the PC with scripts/fetch-release.ps1.
set -euo pipefail
OUT="$HOME/lineage/android/out/target/product/utah"
REL="$HOME/lineage/release/${1:-utah-$(date +%Y%m%d)-debug}"
RC="$OUT/vendor/etc/init/zz-debug-panic.rc"

echo "== debug rc in the built vendor image tree"
test -f "$RC" && echo "present: $RC" || { echo "MISSING $RC"; exit 1; }
grep -q 'grep -q 1' "$RC" && echo "contains 'grep -q 1': yes" || echo "contains 'grep -q 1': NO"
if grep -q '\$' "$RC"; then echo "contains a dollar sign: YES (bad)"; else echo "contains a dollar sign: no"; fi
for f in system_ext/bin/hwservicemanager system_ext/etc/init/hwservicemanager.rc system_ext/bin/hw/android.hidl.allocator@1.0-service; do
  [ -e "$OUT/$f" ] && echo "ok   $f" || echo "MISSING $f"
done

echo "== boot image header versions"
python3 -I - "$OUT" <<'PY'
import struct, sys, os
out = sys.argv[1]
for n in ("boot.img", "init_boot.img", "vendor_boot.img"):
    d = open(os.path.join(out, n), "rb").read(2048)
    v = struct.unpack_from("<I", d, 40)[0] if d[:8] == b"ANDROID!" else struct.unpack_from("<I", d, 8)[0] if d[:8] == b"VNDRBOOT" else None
    print(f"  {n}: header v{v}")
PY

echo "== release set $REL"
mkdir -p "$REL"
ZIP="$OUT/lineage-23.0-$(date +%Y%m%d)-UNOFFICIAL-utah.zip"; [ -f "$ZIP" ] || ZIP=$(ls -t "$OUT"/lineage-23.0-*-UNOFFICIAL-utah.zip | head -1)
cp "$ZIP" "$REL/$(basename "$ZIP" .zip)-DEBUG.zip"
for f in boot.img init_boot.img vendor_boot.img vbmeta.img vbmeta_system.img dtbo.img system_dlkm.img; do
  [ -f "$OUT/$f" ] && cp "$OUT/$f" "$REL/" || echo "  (no $f, skipped)"
done
( cd "$REL" && rm -f SHA256SUMS && sha256sum -- * > SHA256SUMS && cat SHA256SUMS )
