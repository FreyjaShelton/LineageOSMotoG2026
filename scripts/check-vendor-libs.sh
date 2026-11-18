#!/usr/bin/env bash
# Run on the build machine after every utah build, BEFORE installing it: for every stock ELF file we
# ship (vendor/motorola/utah/stock), check that each library it needs can really be loaded by a
# process in /vendor: found in the built vendor/lib64 (also following the dependencies of those
# libraries) or on the LL-NDK list (system/etc/llndk.libraries.txt). A library that only exists in
# /system/lib64 does NOT count: vendor processes cannot see it (2026-11-18: composer@3.1 and the
# audio HAL died in a restart loop with "CANNOT LINK EXECUTABLE ... library ... not found").
# Prints one line per problem; the last line says how many. Exit status 1 if there are any.
#   scripts/check-vendor-libs.sh [PRODUCT_OUT]
PRODUCT_OUT="${1:-$HOME/lineage/android/out/target/product/utah}"
ST="${STOCK_DIR:-$HOME/lineage/android/vendor/motorola/utah/stock/vendor}"
LL="$PRODUCT_OUT/system/etc/llndk.libraries.txt"
[ -f "$LL" ] || { echo "no $LL: wrong PRODUCT_OUT?" >&2; exit 2; }
declare -A seen
OUTF=$(mktemp)
check() {
  local f=$1 lib
  for lib in $(readelf -d "$f" 2>/dev/null | grep NEEDED | sed 's/.*\[//;s/\]//'); do
    case "$lib" in libc.so|libm.so|libdl.so|libc++.so) continue ;; esac
    if [ -e "$PRODUCT_OUT/vendor/lib64/$lib" ]; then
      if [ -z "${seen[$lib]}" ]; then seen[$lib]=1; check "$PRODUCT_OUT/vendor/lib64/$lib"; fi
    elif [ -e "$PRODUCT_OUT/vendor/lib64/hw/$lib" ] || grep -qx "$lib" "$LL"; then :
    else
      echo "NOT VISIBLE TO VENDOR: $lib (needed by $(basename "$f"))" >> "$OUTF"
    fi
  done
}
n=0
for src in $(find "$ST" -type f ! -name '*.rc'); do
  rel=${src#$ST/}; dst="$PRODUCT_OUT/vendor/$rel"; n=$((n + 1))
  if [ ! -e "$dst" ]; then echo "NOT IN IMAGE: $rel" >> "$OUTF"; continue; fi
  cmp -s "$src" "$dst" || echo "DIFFERS from what was staged: $rel" >> "$OUTF"
  check "$dst"
done
sort -u "$OUTF"
bad=$(sort -u "$OUTF" | wc -l)
rm -f "$OUTF"
if [ "$n" = 0 ]; then echo "checked 0 stock files: $ST is empty or missing, nothing was verified" >&2; exit 2; fi
echo "checked $n stock files; problems: $bad"
[ "$bad" = 0 ]
