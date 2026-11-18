"""Test vendor_boot #2: our r2 ramdisk content, but laid out like stock:
 - ONE fragment (type 1): our platform + our recovery + stock's init.recovery.mt6835.rc, concatenated
 - stock's DTB blob (with its 64-byte DT table)
 - stock's kernel command line
"""
import struct, os

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "make-vendor-boot-test-rc.py")).read()
exec(src.split("# --- parse our vendor_boot ---")[0])      # helpers, `frag` (rc fragment), up(), PAGE

def raw_fragments(path):
    d = open(path, "rb").read()
    hs = 2128
    vrs = struct.unpack_from("<I", d, 24)[0]
    dtbs = struct.unpack_from("<I", d, 28 + 2048 + 4 + 16 + 4)[0]
    tbl, n, esz, bcs = struct.unpack_from("<IIII", d, 28 + 2048 + 4 + 16 + 4 + 4 + 8)
    base = up(hs)
    tab = base + up(vrs) + up(dtbs)
    frags = []
    for i in range(n):
        sz, off, typ = struct.unpack_from("<III", d, tab + i * esz)
        frags.append(d[base + off: base + off + sz])
    dtb = d[base + up(vrs): base + up(vrs) + dtbs]
    cmd = d[28:28 + 2048].split(b"\0")[0]
    return d, frags, dtb, cmd

od, ofr, odtb, ocmd = raw_fragments(O)
sd, sfr, sdtb, scmd = raw_fragments(S)
print("our cmdline  :", ocmd)
print("stock cmdline:", scmd)
print("our fragments:", [len(x) for x in ofr], " stock DTB:", len(sdtb), " our DTB:", len(odtb))

merged = b"".join(ofr) + frag            # platform + recovery + rc
hdr = bytearray(od[:2128])
struct.pack_into("<I", hdr, 24, len(merged))
hdr[28:28 + 2048] = scmd.ljust(2048, b"\0")
dtb_off = 28 + 2048 + 4 + 16 + 4
struct.pack_into("<I", hdr, dtb_off, len(sdtb))
tb_off = dtb_off + 4 + 8
esz = 108
struct.pack_into("<IIII", hdr, tb_off, esz, 1, esz, 0)
entry = struct.pack("<III", len(merged), 0, 1) + b"\0" * 32 + b"\0" * 64

base = up(2128)
out = bytes(hdr).ljust(base, b"\0")
out += merged.ljust(up(len(merged)), b"\0")
out += sdtb.ljust(up(len(sdtb)), b"\0")
out += entry.ljust(up(len(entry)), b"\0")
total = 64 * 1024 * 1024
assert len(out) < total
out = out.ljust(total, b"\0")
p = os.environ.get("VB_OUT", r"D:\LineageOS\release\test\vendor_boot_stocklayout.img")   # env VB_OUT: output path
open(p, "wb").write(out)
print("wrote", p)

# the kernel decodes the single fragment as 3 concatenated lz4+cpio archives; check all three come out
stream = lz4_legacy(merged)
allfs = {}; pos = 0; narch = 0
while pos < len(stream):
    if stream[pos:pos + 6] != b"070701":
        pos += 1; continue            # padding between archives
    i = pos; narch += 1
    while True:
        f = [int(stream[i + 6 + 8 * k:i + 14 + 8 * k], 16) for k in range(13)]
        i += 110; nm = stream[i:i + f[11] - 1].decode("latin1"); i += f[11]; i = (i + 3) & ~3
        data = stream[i:i + f[6]]; i = (i + f[6] + 3) & ~3
        if nm == "TRAILER!!!": break
        allfs[nm] = data
    pos = i
print("  archives found in the merged fragment:", narch, " entries:", len(allfs))
print("  merged fragment has: first_stage_ramdisk:", any(k.startswith("first_stage_ramdisk") for k in allfs),
      "| system/bin/recovery:", "system/bin/recovery" in allfs, "| rc:", "init.recovery.mt6835.rc" in allfs)
