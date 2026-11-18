#!/usr/bin/env python3
"""Symbol-level check of the stock HAL files we ship, on a built utah image (run on the build machine).

check-vendor-libs.sh only asks "is every needed library loadable by vendor code?". That is not enough:
on 2026-11-18 the audio HAL died with `cannot locate symbol "_ZTVN7android5media9AudioPortE" referenced
by libaudiofoundation-stock.so`: the library NAME was in the image, but it was the Android 16 build of
`audioclient-types-aidl-cpp.so`, which does not define what stock's copy of its user expects.

This does what the dynamic linker does. For every ELF file in vendor/motorola/utah/stock (and every
"-stock" library) it follows DT_NEEDED through the image's vendor/lib64 (+ hw/) and the LL-NDK /
bionic libraries of the system image, and reports each undefined (non-weak) symbol that nothing in that
closure defines. Executables and libraries that are dlopen'ed (hw impls) are all treated as roots.

    python3 -I scripts/check-vendor-symbols.py [PRODUCT_OUT] [--all-services]   exit status 1 if anything is unresolved
    (--all-services: every executable in vendor/bin and vendor/bin/hw, not only the stock files we ship)
"""
import os
import re
import subprocess
import sys

OUT = [a for a in sys.argv[1:] if not a.startswith("--")][0] if [a for a in sys.argv[1:] if not a.startswith("--")] else os.path.expanduser("~/lineage/android/out/target/product/utah")
STOCK = os.environ.get("STOCK_DIR", os.path.expanduser("~/lineage/android/vendor/motorola/utah/stock/vendor"))
LLNDK = [l.strip() for l in open(os.path.join(OUT, "system/etc/llndk.libraries.txt")) if l.strip()]
SEARCH = [os.path.join(OUT, "vendor/lib64"), os.path.join(OUT, "vendor/lib64/hw")]
SYSTEM_DIRS = [os.path.join(OUT, "system/lib64"), os.path.join(OUT, "system/lib64/bootstrap")]
BIONIC = {"libc.so", "libm.so", "libdl.so"}  # file lives in system/lib64/bootstrap

cache = {}
# provided by the dynamic linker itself (not by any .so), so no library defines them
LINKER = re.compile(r"^(__loader_.*|android_(get|create|link|init|set)_[a-z_]*namespace.*|android_dlopen_ext|android_dlwarning|__cfi_.*)$")


def find(name):
    for d in SEARCH:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    if name in LLNDK or name in BIONIC or name == "libc++.so":
        for d in SYSTEM_DIRS:
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
    return None


def nm(path):
    """(defined set, undefined strong set, needed list) of a shared object."""
    if path in cache:
        return cache[path]
    defined, undefined = set(), set()
    out = subprocess.run(["nm", "-D", path], capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2:
            kind, sym = parts
        elif len(parts) == 3:
            _, kind, sym = parts
        else:
            continue
        sym = sym.split("@")[0]
        if kind in ("U",):
            undefined.add(sym)
        elif kind in ("w", "v"):
            continue  # weak undefined: allowed to stay unresolved
        else:
            defined.add(sym)
    needed = re.findall(r"\(NEEDED\)\s+Shared library: \[([^\]]+)\]",
                        subprocess.run(["readelf", "-d", path], capture_output=True, text=True).stdout)
    cache[path] = (defined, undefined, needed)
    return cache[path]


def closure(root):
    seen, order, todo = {}, [], [root]
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen[p] = True
        order.append(p)
        for n in nm(p)[2]:
            q = find(n)
            if q:
                todo.append(q)
    return order


def demangle(syms):
    if not syms:
        return {}
    out = subprocess.run(["c++filt"], input="\n".join(syms), capture_output=True, text=True).stdout.splitlines()
    return dict(zip(syms, out))


roots = []
if "--all-services" in sys.argv:  # every executable of the vendor image instead of the stock files only
    for sub in ("vendor/bin", "vendor/bin/hw"):
        d = os.path.join(OUT, sub)
        if os.path.isdir(d):
            roots += [os.path.join(d, f) for f in os.listdir(d)
                      if os.path.isfile(os.path.join(d, f)) and open(os.path.join(d, f), "rb").read(4) == b"ELF"]
else:
    for dp, _, files in os.walk(STOCK):
        for f in files:
            if not f.endswith(".rc"):
                roots.append(os.path.join(OUT, "vendor", os.path.relpath(os.path.join(dp, f), STOCK)))
if not roots:
    print(f"no stock files under {STOCK}: nothing verified", file=sys.stderr)
    sys.exit(2)

problems = {}  # (root name, lib name) -> set of symbols
for root in sorted(roots):
    if not os.path.exists(root):
        problems[(os.path.basename(root), "(file missing from the image)")] = {"-"}
        continue
    libs = closure(root)
    provided = set()
    for p in libs:
        provided |= nm(p)[0]
    for p in libs:
        if os.path.dirname(p).startswith(os.path.join(OUT, "system")):
            continue  # LL-NDK / bionic: their own dependencies live on the system side, out of the check
        missing = {s for s in nm(p)[1] if s not in provided and not LINKER.match(s)}
        if missing:
            problems.setdefault((os.path.basename(root), os.path.basename(p)), set()).update(missing)

if not problems:
    print(f"checked {len(roots)} stock files and everything they load: every symbol resolves")
    sys.exit(0)
by_lib = {}  # lib -> (set of symbols, set of roots that load it)
for (root, lib), syms in problems.items():
    by_lib.setdefault(lib, [set(), set()])
    by_lib[lib][0] |= syms
    by_lib[lib][1].add(root)
for lib, (syms, rts) in sorted(by_lib.items()):
    names = demangle(sorted(syms))
    print(f"UNRESOLVED in {lib}: {len(syms)} symbol(s) nothing it loads defines (seen when loading {len(rts)} of the stock files)")
    for s in sorted(syms)[:6]:
        print(f"    {names.get(s, s)}")
    if len(syms) > 6:
        print(f"    ... and {len(syms) - 6} more")
print(f"\n{len(by_lib)} library/libraries with unresolved symbols, {len(roots)} stock files checked")
sys.exit(1)
