#!/usr/bin/env python3
"""Make a test vendor_boot.img with extra kernel command-line arguments (nothing else changes).

    python -I scripts/make-vendor-boot-cmdline.py IN.img OUT.img "arg1 arg2 ..."

The AVB footer is dropped (content is kept byte for byte, the rest is zeroed): this bootloader's
preflash validation accepts footer-less images, and an image with a changed command line would
not match the installed vbmeta anyway. Example (verbose kernel and init log in pstore):
    ... "ignore_loglevel printk.devkmsg=on"
"""
import struct, sys

src, dst, extra = sys.argv[1], sys.argv[2], sys.argv[3]
d = bytearray(open(src, "rb").read())
assert d[:8] == b"VNDRBOOT"
page = 4096; up = lambda x: ((x + page - 1) // page) * page
vrs = struct.unpack_from("<I", d, 24)[0]
dtbs = struct.unpack_from("<I", d, 28 + 2048 + 4 + 16 + 4)[0]
tbl, n, esz, bcs = struct.unpack_from("<IIII", d, 28 + 2048 + 4 + 16 + 4 + 4 + 8)
end = up(2128) + up(vrs) + up(dtbs) + up(tbl) + up(bcs)
cmd = bytes(d[28:28 + 2048]).split(b"\0")[0]
new = (cmd + b" " + extra.encode()).strip()
assert len(new) < 2047, "command line too long"
d[28:28 + 2048] = new.ljust(2048, b"\0")
out = bytes(d[:end]).ljust(len(d), b"\0")
open(dst, "wb").write(out)
print("old cmdline:", cmd.decode())
print("new cmdline:", new.decode())
print("wrote", dst, len(out), "bytes; content", end, "bytes; footer dropped")
