#!/usr/bin/env python3
"""Compare the partition layout our build produces with what stock has.

Reads (no phone needed, Windows or Linux, plain Python):
  - the OTA payload manifest inside our zip (partition list with sizes, super groups, VAB flags)
  - the AVB descriptors of vbmeta.img and vbmeta_system.img, stock vs ours (which partitions
    each vbmeta covers: hashtree, hash, or chain)

Usage: python -I scripts/compare-partitions.py [OUR_RELEASE_DIR] [STOCK_FIRMWARE_DIR]
Defaults are the Windows paths used in BUILD_PLAN.md (D:\\LineageOS\\...).
"""
import glob, os, struct, sys, zipfile

REL = sys.argv[1] if len(sys.argv) > 1 else r"D:\LineageOS\release\utah-20261117-r2"
FW = sys.argv[2] if len(sys.argv) > 2 else [p for p in glob.glob(r"D:\LineageOS\firmware\NEVADA*") if os.path.isdir(p)][0]


# ---------- minimal protobuf reader ----------
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


def payload_info(zpath):
    z = zipfile.ZipFile(zpath)
    with z.open("payload.bin") as f:
        hdr = f.read(24)
        assert hdr[:4] == b"CrAU", hdr[:4]
        ver, msize = struct.unpack(">QQ", hdr[4:20])
        sigsize = struct.unpack(">I", hdr[20:24])[0] if ver == 2 else 0
        man = f.read(msize)
    print(f"payload v{ver}, manifest {msize} bytes")
    parts, groups, flags = [], [], {}
    for fn, v in fields(man):
        if fn == 13:                                   # partitions
            name, size = None, None
            for pf, pv in fields(v):
                if pf == 1: name = pv.decode()
                if pf == 7:
                    for sf, sv in fields(pv):
                        if sf == 1: size = sv
            parts.append((name, size))
        if fn == 15:                                   # dynamic_partition_metadata
            for df, dv in fields(v):
                if df == 1:
                    g = {"name": None, "size": None, "parts": []}
                    for gf, gv in fields(dv):
                        if gf == 1: g["name"] = gv.decode()
                        if gf == 2: g["size"] = gv
                        if gf == 3: g["parts"].append(gv.decode())
                    groups.append(g)
                elif df in (2, 3, 4, 5): flags[df] = dv
        if fn == 3: flags["block_size"] = v
    return parts, groups, flags


# ---------- AVB descriptors ----------
def avb(path):
    d = open(path, "rb").read()
    assert d[:4] == b"AVB0", path
    auth, aux = struct.unpack(">QQ", d[12:28])
    algo = struct.unpack(">I", d[28:32])[0]
    doff, dsz = struct.unpack(">QQ", d[96:112])
    rollback = struct.unpack(">Q", d[112:120])[0]
    flags = struct.unpack(">I", d[120:124])[0]
    base = 256 + auth + doff
    i, out = base, []
    while i < base + dsz:
        tag, n = struct.unpack(">QQ", d[i:i + 16])
        body = d[i + 16:i + 16 + n]
        if tag == 1:                                   # hashtree
            name_len = struct.unpack(">I", body[88:92])[0]
            size = struct.unpack(">Q", body[4:12])[0]
            out.append(("hashtree", body[164:164 + name_len].decode(), size))
        elif tag == 2:                                 # hash
            size = struct.unpack(">Q", body[0:8])[0]
            name_len = struct.unpack(">I", body[40:44])[0]
            out.append(("hash", body[116:116 + name_len].decode(), size))
        elif tag == 4:                                 # chain partition
            name_len = struct.unpack(">I", body[4:8])[0]
            out.append(("chain", body[76:76 + name_len].decode(), None))   # 4 u32 fields + 60 reserved
        i += 16 + ((n + 7) & ~7)
    return dict(algo=algo, rollback=rollback, flags=flags, desc=out)


print("=== OUR OTA payload ===")
zips = glob.glob(os.path.join(REL, "*.zip"))
if zips:
    parts, groups, flags = payload_info(zips[0])
    for name, size in parts:
        print(f"  {name:16s} {size / 1e6:10.2f} MB")
    for g in groups:
        print(f"  super group {g['name']}: max {g['size']} bytes, partitions: {', '.join(g['parts'])}")
    print("  dynamic_partition_metadata flags (field: value):", flags)
else:
    print("  no zip in", REL)

for label, base in (("STOCK", FW), ("OURS", REL)):
    for n in ("vbmeta.img", "vbmeta_system.img"):
        p = os.path.join(base, n)
        if not os.path.exists(p): continue
        a = avb(p)
        print(f"\n=== {label} {n}: algo={a['algo']} rollback={a['rollback']} flags={a['flags']} ===")
        for kind, name, size in a["desc"]:
            print(f"  {kind:9s} {name}" + (f"  ({size / 1e6:.2f} MB)" if size else ""))
