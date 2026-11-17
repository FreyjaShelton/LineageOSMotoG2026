#!/usr/bin/env python3
"""Find symlinks in our built partition images whose target does not exist in the image set.

A symlink that points at a file the build never installed (for example
/system/bin/hwservicemanager -> /system/system_ext/bin/hwservicemanager, with no such file in
system_ext) is a sign of a package missing from the product. Found 2026-11-17: that exact one
kept the phone at the logo.

    python -I scripts/payload-extract.py ZIP DIR system system_ext vendor product
    python -I scripts/dangling-symlinks.py DIR

Runs scripts/erofs-ls.py on each image (plain and inline files only), then resolves the targets
across partitions: /system_ext, /vendor, /product and /odm map to their own image, and the
"system" image keeps system-as-root paths (/system/...).
"""
import os, posixpath, re, subprocess, sys

d = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__))
roots = {"system": "", "system_ext": "/system_ext", "vendor": "/vendor", "product": "/product"}
paths, links = set(), []
for part, prefix in roots.items():
    img = os.path.join(d, part + ".img")
    out = subprocess.run([sys.executable, "-I", os.path.join(here, "erofs-ls.py"), img],
                         capture_output=True, text=True, encoding="latin1").stdout
    for line in out.splitlines():
        m = re.match(r"^(/\S.*?)(/|  \d+ B  \[[^\]]*\](?:  -> (.*))?)$", line)
        if not m: continue
        p, tail, tgt = m.group(1), m.group(2), m.group(3)
        full = (prefix + p) if prefix else p
        paths.add(full)
        if tgt: links.append((full, tgt))
# system_ext etc. are also reachable as /system/system_ext (symlinks in the system image)
alias = {"/system/system_ext": "/system_ext", "/system/vendor": "/vendor", "/system/product": "/product", "/system/odm": "/odm"}

def exists(p):
    p = posixpath.normpath(p)
    if p in paths: return True
    for a, b in alias.items():
        if p == a or p.startswith(a + "/"):
            if posixpath.normpath(b + p[len(a):]) in paths: return True
    return p in ("/data", "/dev", "/proc", "/sys", "/storage", "/metadata", "/cache", "/mnt", "/odm", "/apex") or p.startswith(("/data/", "/dev/", "/proc/", "/sys/", "/storage/", "/mnt/", "/apex/", "/odm/", "/cache/", "/metadata/"))

bad = []
for full, tgt in links:
    t = tgt if tgt.startswith("/") else posixpath.join(posixpath.dirname(full), tgt)
    if not exists(t): bad.append((full, tgt))
print(f"{len(paths)} paths, {len(links)} symlinks, {len(bad)} dangling")
for full, tgt in sorted(bad): print(f"  {full} -> {tgt}")
