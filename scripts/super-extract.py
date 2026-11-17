import struct, glob, os, sys

FW = r"D:\LineageOS\firmware\NEVADA_G_SYS_W1WNS36.18_114_3_2_1_1_1_subsidy_DEFAULT_regulatory_DEFAULT_cid50_CFC.xml"
files = sorted(glob.glob(os.path.join(FW, "super.img_sparsechunk.*")), key=lambda p: int(p.rsplit(".", 1)[1]))

# --- map the sparse chunks: list of (raw_start, length, kind, file, file_offset, fill) ---
runs = []
for f in files:
    fh = open(f, "rb")
    magic, maj, mnr, fhsz, chsz, bs, tb, tc, ck = struct.unpack("<IHHHHIIII", fh.read(28))
    assert magic == 0xED26FF3A and bs == 4096
    cur = 0
    for _ in range(tc):
        ctype, _r, csz, tsz = struct.unpack("<HHII", fh.read(12))
        n = csz * bs
        if ctype == 0xCAC1:                      # raw
            runs.append((cur * bs, n, "raw", f, fh.tell(), None)); fh.seek(n, 1)
        elif ctype == 0xCAC2:                    # fill
            fill = fh.read(4); runs.append((cur * bs, n, "fill", f, 0, fill))
        elif ctype == 0xCAC3:                    # don't care
            pass
        elif ctype == 0xCAC4:                    # crc
            fh.read(4); n = 0
        cur += csz if ctype != 0xCAC4 else 0
runs.sort()
starts = [r[0] for r in runs]
import bisect

def read(off, length):
    out = bytearray()
    while length > 0:
        i = bisect.bisect_right(starts, off) - 1
        if i < 0 or off >= runs[i][0] + runs[i][1]:
            # hole: zeros up to next run
            nxt = runs[i + 1][0] if i + 1 < len(runs) else off + length
            n = min(length, nxt - off); out += b"\0" * n; off += n; length -= n; continue
        rs, rl, kind, f, fo, fill = runs[i]
        n = min(length, rs + rl - off)
        if kind == "raw":
            with open(f, "rb") as fh:
                fh.seek(fo + off - rs); out += fh.read(n)
        else:
            out += (fill * (n // 4 + 1))[:n]
        off += n; length -= n
    return bytes(out)

# --- LP metadata ---
geo = read(4096, 52)
gmagic, gsz = struct.unpack_from("<II", geo, 0)
assert gmagic == 0x616C4467, hex(gmagic)
max_meta, slots, lbs = struct.unpack_from("<III", geo, 40)
print(f"LP geometry: metadata_max_size={max_meta} slots={slots} logical_block_size={lbs}")
meta_off = 4096 + 8192                           # primary metadata for slot 0
hdr = read(meta_off, 256)
magic, major, minor, hsz = struct.unpack_from("<IHHI", hdr, 0)
assert magic == 0x414C5030, hex(magic)
tables_size = struct.unpack_from("<I", hdr, 44)[0]
po, pn, pe = struct.unpack_from("<III", hdr, 80)
eo, en, ee = struct.unpack_from("<III", hdr, 92)
go, gn, ge = struct.unpack_from("<III", hdr, 104)
tab = read(meta_off + hsz, tables_size)
groups = []
for i in range(gn):
    g = tab[go + i * ge: go + (i + 1) * ge]
    groups.append((g[:36].split(b"\0")[0].decode(), struct.unpack_from("<Q", g, 40)[0]))
parts = []
for i in range(pn):
    p = tab[po + i * pe: po + (i + 1) * pe]
    name = p[:36].split(b"\0")[0].decode()
    attrs, fe, ne, gi = struct.unpack_from("<IIII", p, 36)
    exts = []
    for k in range(ne):
        e = tab[eo + (fe + k) * ee: eo + (fe + k + 1) * ee]
        ns, tt, td, ts = struct.unpack_from("<QIQI", e, 0)
        exts.append((ns, td))
    parts.append((name, gi, sum(e[0] for e in exts) * 512, exts))
print("groups:", groups)
for name, gi, size, exts in parts:
    print(f"  {name:20s} group={groups[gi][0]:24s} {size/1e6:9.2f} MB  extents={len(exts)}")

want = sys.argv[1] if len(sys.argv) > 1 else "system_dlkm_a"
os.makedirs(r"D:\LineageOS\work", exist_ok=True)
for name, gi, size, exts in parts:
    if name == want:
        out = os.path.join(r"D:\LineageOS\work", name + ".img")
        with open(out, "wb") as o:
            for ns, td in exts:
                o.write(read(td * 512, ns * 512))
        print("wrote", out, os.path.getsize(out))
