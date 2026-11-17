"""Make a test vendor_boot: our r2 vendor_boot + one extra recovery ramdisk fragment
holding stock's init.recovery.mt6835.rc. Nothing else changes."""
import struct, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "vendor-ramdisk-compare.py")).read().split("st = ramdisks(S)")[0])   # lz4 / cpio helpers, S, O

PAGE = 4096
up = lambda x: ((x + PAGE - 1) // PAGE) * PAGE

# --- stock rc file ---
stock = ramdisks(S)
rc = {}
for _, _, fs in stock: rc.update(fs)
rcname = "init.recovery.mt6835.rc"
rcdata = rc[rcname][1]
print("stock rc:", len(rcdata), "bytes, mode", oct(rc[rcname][0]))

# --- build a tiny cpio (newc) with just that file ---
def cpio_entry(name, mode, data):
    nm = name.encode() + b"\0"
    h = b"070701" + b"".join(b"%08X" % v for v in (1, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(nm), 0))
    out = h + nm
    out += b"\0" * ((-len(out)) % 4)
    out += data
    out += b"\0" * ((-len(data)) % 4)
    return out
cp = cpio_entry(rcname, rc[rcname][0], rcdata) + cpio_entry("TRAILER!!!", 0, b"")
cp += b"\0" * ((-len(cp)) % 512)

# --- lz4 legacy stream with literal-only blocks (valid, just not compressed) ---
def lz4_literals(data):
    n = len(data)
    tok = bytearray()
    if n < 15:
        tok.append(n << 4)
    else:
        tok.append(15 << 4); r = n - 15
        while r >= 255: tok.append(255); r -= 255
        tok.append(r)
    return bytes(tok) + data
blk = lz4_literals(cp)
frag = bytes.fromhex("02214c18") + struct.pack("<I", len(blk)) + blk
# sanity: our own decoder must give the cpio back
assert lz4_legacy(frag) == cp, "lz4 literal stream does not round-trip"
assert rcname in cpio(lz4_legacy(frag))

# --- parse our vendor_boot ---
d = open(O, "rb").read()
hs = 2128
vrs = struct.unpack_from("<I", d, 24)[0]
dtbs = struct.unpack_from("<I", d, 28 + 2048 + 4 + 16 + 4)[0]
tbl, n, esz, bcs = struct.unpack_from("<IIII", d, 28 + 2048 + 4 + 16 + 4 + 4 + 8)
assert esz == 108 and bcs == 0
base = up(hs)
rd = d[base:base + vrs]
dtb = d[base + up(vrs): base + up(vrs) + dtbs]
tab = base + up(vrs) + up(dtbs)
entries = [d[tab + i * esz: tab + (i + 1) * esz] for i in range(n)]

# --- new fragment table: existing entries + ours ---
new_rd = rd + frag
new_entry = struct.pack("<III", len(frag), len(rd), 2) + b"recovery".ljust(32, b"\0") + b"\0" * 64
assert len(new_entry) == esz
entries.append(new_entry)

hdr = bytearray(d[:hs])
struct.pack_into("<I", hdr, 24, len(new_rd))
tb_off = 28 + 2048 + 4 + 16 + 4 + 4 + 8
struct.pack_into("<IIII", hdr, tb_off, esz * len(entries), len(entries), esz, 0)

out = bytes(hdr).ljust(base, b"\0")
out += new_rd.ljust(up(len(new_rd)), b"\0")
out += dtb.ljust(up(len(dtb)), b"\0")
t = b"".join(entries)
out += t.ljust(up(len(t)), b"\0")
total = 64 * 1024 * 1024
assert len(out) < total
out = out.ljust(total, b"\0")

dst = r"D:\LineageOS\release\test"
os.makedirs(dst, exist_ok=True)
p = os.path.join(dst, "vendor_boot_rc.img")
open(p, "wb").write(out)
print("wrote", p, len(out))

# --- read it back with our own parser ---
back = ramdisks(p)
for typ, nm, fs in back:
    print(f"  fragment type={typ} name={nm!r}: {len(fs)} entries; has {rcname}: {rcname in fs}")
