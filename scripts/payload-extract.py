#!/usr/bin/env python3
"""Rebuild partition images from a FULL OTA zip's payload.bin, without the phone.

    python -I scripts/payload-extract.py ZIP OUTDIR [partition ...]

Handles full-OTA operations only (REPLACE, REPLACE_BZ, REPLACE_XZ, ZERO/DISCARD). Needs only
the Python standard library. Use it to inspect what the build really contains, e.g. with
scripts/erofs-ls.py (list files) after extracting system / system_ext / vendor / product.
"""
import bz2, lzma, os, struct, sys, zipfile


def varint(b, i):
    r = s = 0
    while True:
        c = b[i]; i += 1
        r |= (c & 0x7F) << s; s += 7
        if not c & 0x80: return r, i


def fields(b):
    i = 0
    while i < len(b):
        k, i = varint(b, i); f, w = k >> 3, k & 7
        if w == 0: v, i = varint(b, i)
        elif w == 2:
            n, i = varint(b, i); v = b[i:i + n]; i += n
        elif w == 1: v = b[i:i + 8]; i += 8
        elif w == 5: v = b[i:i + 4]; i += 4
        else: raise ValueError(w)
        yield f, v


def extents(b):
    out = []
    for f, v in fields(b):
        pass
    return out


def parse_extent(b):
    start = num = 0
    for f, v in fields(b):
        if f == 1: start = v
        if f == 2: num = v
    return start, num


zpath, outdir = sys.argv[1], sys.argv[2]
want = set(sys.argv[3:])
os.makedirs(outdir, exist_ok=True)
z = zipfile.ZipFile(zpath)
zi = z.getinfo("payload.bin")
assert zi.compress_type == 0, "payload.bin is compressed inside the zip"
raw = open(zpath, "rb")
raw.seek(zi.header_offset)
lh = raw.read(30)
nlen, elen = struct.unpack("<HH", lh[26:30])
base = zi.header_offset + 30 + nlen + elen

raw.seek(base)
hdr = raw.read(24)
assert hdr[:4] == b"CrAU"
ver, msize = struct.unpack(">QQ", hdr[4:20])
sigsize = struct.unpack(">I", hdr[20:24])[0]
man = raw.read(msize)
data_start = base + 24 + msize + sigsize
BS = 4096
for fn, v in fields(man):
    if fn == 3: BS = v

for fn, v in fields(man):
    if fn != 13: continue
    name, ops = None, []
    for pf, pv in fields(v):
        if pf == 1: name = pv.decode()
        if pf == 8: ops.append(pv)
    if want and name not in want: continue
    path = os.path.join(outdir, name + ".img")
    n_written = 0
    with open(path, "wb") as out:
        for op in ops:
            typ = off = ln = 0; dst = []
            for of, ov in fields(op):
                if of == 1: typ = ov
                elif of == 2: off = ov
                elif of == 3: ln = ov
                elif of == 6: dst.append(parse_extent(ov))
            if typ in (0, 1, 8):
                raw.seek(data_start + off); blob = raw.read(ln)
                data = blob if typ == 0 else bz2.decompress(blob) if typ == 1 else lzma.decompress(blob)
            elif typ in (6, 7):
                data = None
            else:
                sys.exit(f"{name}: unsupported operation type {typ} (this is not a full OTA, or it uses zstd)")
            pos = 0
            for start, num in dst:
                out.seek(start * BS)
                if data is None: out.write(b"\0" * (num * BS))
                else:
                    chunk = data[pos:pos + num * BS]; out.write(chunk); pos += num * BS
                n_written += num
    print(f"{name}: {os.path.getsize(path) / 1e6:.1f} MB, {n_written} blocks -> {path}")
