import struct, os, sys, collections, hashlib

S = r"D:\LineageOS\firmware\NEVADA_G_SYS_W1WNS36.18_114_3_2_1_1_1_subsidy_DEFAULT_regulatory_DEFAULT_cid50_CFC.xml\vendor_boot.img"
O = os.environ.get("VB_OURS", r"D:\LineageOS\release\utah-20261117-r2\vendor_boot.img")   # env VB_OURS: the build's vendor_boot.img

def lz4_block(src, max_out):
    out = bytearray(); i = 0; n = len(src)
    while i < n:
        t = src[i]; i += 1
        lit = t >> 4
        if lit == 15:
            while True:
                b = src[i]; i += 1; lit += b
                if b != 255: break
        out += src[i:i + lit]; i += lit
        if i >= n: break
        off = src[i] | (src[i + 1] << 8); i += 2
        ml = t & 15
        if ml == 15:
            while True:
                b = src[i]; i += 1; ml += b
                if b != 255: break
        ml += 4
        st = len(out) - off
        if off >= ml:
            out += out[st:st + ml]
        else:
            for k in range(ml):
                out.append(out[st + k])
    return bytes(out)

def lz4_legacy(d):
    assert d[:4] == bytes.fromhex("02214c18"), "not lz4 legacy"
    i = 4; out = []
    while i + 4 <= len(d):
        sz = struct.unpack_from("<I", d, i)[0]; i += 4
        if sz == 0x184c2102 or sz == 0: continue
        out.append(lz4_block(d[i:i + sz], 8 << 20)); i += sz
    return b"".join(out)

def cpio(d):
    files = {}; i = 0
    while i + 110 <= len(d):
        assert d[i:i + 6] == b"070701", f"bad cpio magic at {i}"
        f = [int(d[i + 6 + 8 * k:i + 14 + 8 * k], 16) for k in range(13)]
        mode, filesize, namesize = f[1], f[6], f[11]
        i += 110
        name = d[i:i + namesize - 1].decode("latin1"); i += namesize
        i = (i + 3) & ~3
        data = d[i:i + filesize]; i = (i + filesize + 3) & ~3
        if name == "TRAILER!!!": break
        files[name] = (mode, data)
    return files

def ramdisks(path):
    d = open(path, "rb").read()
    page = 4096; hs = 2128
    up = lambda x: ((x + page - 1) // page) * page
    vrs = struct.unpack_from("<I", d, 24)[0]
    tbl, n, esz = struct.unpack_from("<III", d, 28 + 2048 + 4 + 16 + 4 + 4 + 8)
    base = up(hs); res = []
    tab = base + up(vrs) + up(struct.unpack_from("<I", d, 28 + 2048 + 4 + 16 + 4)[0])
    for k in range(n):
        e = d[tab + k * esz: tab + (k + 1) * esz]
        sz, off, typ = struct.unpack_from("<III", e, 0)
        nm = e[12:44].split(b"\0")[0].decode()
        raw = d[base + off: base + off + sz]
        res.append((typ, nm, cpio(lz4_legacy(raw))))
    return res

def summarize(label, rds):
    for typ, nm, fs in rds:
        tot = sum(len(v[1]) for v in fs.values())
        ko = [k for k in fs if k.endswith(".ko")]
        print(f"{label} ramdisk type={typ} name={nm!r}: {len(fs)} entries, {tot/1e6:.1f} MB uncompressed, {len(ko)} .ko ({sum(len(fs[k][1]) for k in ko)/1e6:.1f} MB)")

st = ramdisks(S); ou = ramdisks(O)
summarize("STOCK", st); summarize("OURS ", ou)

def merged(rds, types=None):
    m = {}
    for typ, nm, fs in rds:
        if types is None or typ in types:
            m.update(fs)
    return m

sp = merged(st); op = merged(ou, {1})   # stock platform vs our platform
print()
print("stock platform entries:", len(sp), " our platform entries:", len(op))
only_s = sorted(k for k in sp if k not in op and sp[k][0] & 0o170000 != 0o040000)
only_o = sorted(k for k in op if k not in sp and op[k][0] & 0o170000 != 0o040000)
diff = sorted(k for k in sp if k in op and sp[k][1] != op[k][1] and sp[k][0] & 0o170000 == 0o100000)
print(f"files only in STOCK platform: {len(only_s)}; only in OURS platform: {len(only_o)}; same name, different bytes: {len(diff)}")

def bucket(ks, fs):
    c = collections.Counter(); b = collections.Counter()
    for k in ks:
        top = "/".join(k.split("/")[:2])
        c[top] += 1; b[top] += len(fs[k][1])
    return c, b

c, b = bucket(only_s, sp)
print("\nonly in STOCK, by directory (count, MB):")
for k, v in c.most_common(15): print(f"  {k:45s} {v:5d}  {b[k]/1e6:7.2f}")
c, b = bucket(only_o, op)
print("\nonly in OURS, by directory (count, MB):")
for k, v in c.most_common(15): print(f"  {k:45s} {v:5d}  {b[k]/1e6:7.2f}")
c, b = bucket(diff, sp)
print("\nsame name but different content, by directory (count, stock MB):")
for k, v in c.most_common(15): print(f"  {k:45s} {v:5d}  {b[k]/1e6:7.2f}")

print("\nexamples only in STOCK:", only_s[:25])
print("examples only in OURS:", only_o[:25])
print("examples different:", diff[:25])

# .ko comparison: stripped?
ko_s = {k: sp[k][1] for k in sp if k.endswith(".ko")}
ko_o = {k: op[k][1] for k in op if k.endswith(".ko")}
common = sorted(set(ko_s) & set(ko_o))
print(f"\n.ko in both: {len(common)}; identical: {sum(1 for k in common if ko_s[k] == ko_o[k])}")
if common:
    k = common[0]
    print(f"  example {k}: stock {len(ko_s[k])} B, ours {len(ko_o[k])} B")
    tot_s = sum(len(ko_s[k]) for k in common); tot_o = sum(len(ko_o[k]) for k in common)
    print(f"  total common .ko: stock {tot_s/1e6:.1f} MB, ours {tot_o/1e6:.1f} MB")
    print("  stock ends with module signature marker:", sum(1 for k in common if ko_s[k].endswith(b"~Module signature appended~\n")), "of", len(common))
    print("  ours  ends with module signature marker:", sum(1 for k in common if ko_o[k].endswith(b"~Module signature appended~\n")), "of", len(common))
