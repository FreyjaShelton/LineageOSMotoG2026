#!/usr/bin/env python3
"""Find prebuilt blobs whose real DT_NEEDED libraries differ from the
shared_libs listed for them in a vendor repo's Android.bp.

The build's check_elf_files step stops at the first such mismatch, which costs
a full rebuild per blob. This finds them all in one pass.

Usage: scripts/check-vendor-needed.py [VENDOR_DIR]
       (default ~/lineage/android/vendor/motorola/nevada)
Prints one line per blob with a problem: libraries the blob needs that the
blueprint does not list ("missing"), and listed libraries the blob does not
need ("extra"). Only "missing" breaks the build.
"""
import os
import re
import subprocess
import sys

TOP = os.path.expanduser("~/lineage/android")
VENDOR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(TOP, "vendor/motorola/nevada")
READELF = os.path.join(TOP, "prebuilts/clang/host/linux-x86/llvm-binutils-stable/llvm-readelf")
if not os.path.exists(READELF):
    READELF = "readelf"

# Libraries the build adds implicitly for every module; never "missing".
IMPLICIT = {"libc", "libm", "libdl", "ld-android"}


def modules(text):
    """Yield (type, body) for each top-level module block in Android.bp."""
    for m in re.finditer(r"^(\w+) \{\n(.*?)^\}", text, re.S | re.M):
        yield m.group(1), m.group(2)


def listed(body, key):
    m = re.search(key + r": \[(.*?)\]", body, re.S)
    return re.findall(r'"([^"]+)"', m.group(1)) if m else []


def needed(path):
    out = subprocess.run([READELF, "-d", path], capture_output=True, text=True).stdout
    return re.findall(r"\(NEEDED\).*?\[(.+?)\]", out)


def stems(texts):
    """Map module name -> output name, for modules that rename with `stem`
    (e.g. foo_vendor -> foo). A blob needing "foo.so" is satisfied by them."""
    out = {}
    for text in texts:
        for _, body in modules(text):
            n = re.search(r'name: "([^"]+)"', body)
            s = re.search(r'^    stem: "([^"]+)"', body, re.M)
            if n and s:
                out[n.group(1)] = s.group(1)
    return out


# Other Android.bp files whose renamed modules the vendor blueprint uses.
STEM_SOURCES = [os.path.join(TOP, "prebuilts/misc/protobuf_vendorcompat/Android.bp")]


def main():
    bp = open(os.path.join(VENDOR, "Android.bp")).read()
    renamed = stems([bp] + [open(p).read() for p in STEM_SOURCES if os.path.exists(p)])
    problems = 0
    for mtype, body in modules(bp):
        if not mtype.startswith("cc_prebuilt"):
            continue
        name = re.search(r'name: "([^"]+)"', body).group(1)
        # Each arch block has its own srcs + shared_libs; check each pair.
        arch_blocks = re.findall(r"android_\w+: \{(.*?)\n        \}", body, re.S) or [body]
        for blk in arch_blocks:
            srcs = listed(blk, "srcs")
            if not srcs:
                continue
            path = os.path.join(VENDOR, srcs[0])
            if not os.path.exists(path):
                print(f"{name}: source file missing: {srcs[0]}")
                problems += 1
                continue
            need = {n[:-3] if n.endswith(".so") else n for n in needed(path)}
            have = {renamed.get(lib, lib) for lib in listed(blk, "shared_libs")}
            missing = sorted(need - have - IMPLICIT)
            extra = sorted(have - need - IMPLICIT - {"libc++"})
            if missing:
                problems += 1
                print(f"{name} ({srcs[0]}): missing {missing}" + (f" extra {extra}" if extra else ""))
    print(f"-- {problems} blob(s) with missing shared_libs", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
