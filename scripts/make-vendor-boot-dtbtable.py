#!/usr/bin/env python3
"""Make a test vendor_boot.img: the build's own image, but with STOCK's DTB blob (the 64-byte
Android DT table in front of the FDT, which this MediaTek bootloader may need) and optional extra
kernel command-line arguments. Ramdisk fragments, fragment table and bootconfig stay byte for byte.
The AVB footer is dropped (footer-less images are accepted by this bootloader).

    python -I scripts/make-vendor-boot-dtbtable.py OURS.img STOCK.img OUT.img ["extra args ..."]

Why: 2026-11-18, every normal boot of our build sits at the logo with no log, even with panic
timers; the hand-made recovery image (stock DTB with table) works, ours (bare DTB) never starts.
"""
import struct, sys

ours, stock, dst = sys.argv[1], sys.argv[2], sys.argv[3]
extra = sys.argv[4] if len(sys.argv) > 4 else ""
page = 4096
up = lambda x: ((x + page - 1) // page) * page
CMD = 28
DTBS = 28 + 2048 + 4 + 16 + 4          # dtb_size field
TBL = DTBS + 4 + 8                      # table size, entry count, entry size, bootconfig size


def parts(path):
    d = open(path, "rb").read()
    assert d[:8] == b"VNDRBOOT", path
    vrs = struct.unpack_from("<I", d, 24)[0]
    dtbs = struct.unpack_from("<I", d, DTBS)[0]
    tbl, n, esz, bcs = struct.unpack_from("<IIII", d, TBL)
    p = up(2128)
    ramdisk = d[p:p + up(vrs)]; p += up(vrs)
    dtb = d[p:p + dtbs]; p += up(dtbs)
    table = d[p:p + up(tbl)]; p += up(tbl)
    bc = d[p:p + up(bcs)]
    return d, ramdisk, dtb, table, bc


od, ramdisk, odtb, table, bc = parts(ours)
sd, _, sdtb, _, _ = parts(stock)
print("our DTB:", len(odtb), "bytes, starts", odtb[:4].hex(), "| stock DTB:", len(sdtb), "bytes, starts", sdtb[:4].hex())
assert sdtb[64:68] == bytes.fromhex("d00dfeed"), "stock DTB should have a 64-byte table then an FDT"

hdr = bytearray(od[:up(2128)])
struct.pack_into("<I", hdr, DTBS, len(sdtb))
cmd = bytes(hdr[CMD:CMD + 2048]).split(b"\0")[0]
new = (cmd + b" " + extra.encode()).strip()
assert len(new) < 2047, "command line too long"
hdr[CMD:CMD + 2048] = new.ljust(2048, b"\0")

out = bytes(hdr) + ramdisk + sdtb.ljust(up(len(sdtb)), b"\0") + table + bc
assert len(out) < 64 * 1024 * 1024
out = out.ljust(64 * 1024 * 1024, b"\0")
open(dst, "wb").write(out)
print("cmdline:", new.decode())
print("wrote", dst, len(out), "bytes")
