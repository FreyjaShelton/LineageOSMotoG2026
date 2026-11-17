import struct, sys

img = open(sys.argv[1], "rb").read()
sb = img[1024:1024 + 128]
magic = struct.unpack_from("<I", sb, 0)[0]
assert magic == 0xE0F5E1E2, hex(magic)
blkbits = sb[12]; bs = 1 << blkbits
root_nid = struct.unpack_from("<H", sb, 14)[0]
inos = struct.unpack_from("<Q", sb, 16)[0]
meta_blk = struct.unpack_from("<I", sb, 40)[0]
feat_inc = struct.unpack_from("<I", sb, 80)[0]
print(f"EROFS: block={bs} root_nid={root_nid} inodes={inos} meta_blkaddr={meta_blk} incompat=0x{feat_inc:x} volume={sb[64:80].split(bytes(1))[0]!r}")

def inode(nid):
    off = meta_blk * bs + nid * 32
    fmt, xc, mode = struct.unpack_from("<HHH", img, off)
    ext = fmt & 1; layout = (fmt >> 1) & 7
    if ext:
        size = struct.unpack_from("<Q", img, off + 8)[0]; u = struct.unpack_from("<I", img, off + 16)[0]; hsz = 64
    else:
        size = struct.unpack_from("<I", img, off + 8)[0]; u = struct.unpack_from("<I", img, off + 16)[0]; hsz = 32
    xsz = (12 + (xc - 1) * 4) if xc else 0
    return dict(mode=mode, size=size, layout=layout, u=u, data_off=off + hsz + xsz)

def data(node):
    # layouts: 0 flat plain, 2 flat inline (tail packed); others (compressed/chunk) unsupported here
    size = node["size"]; lay = node["layout"]
    if lay == 0:
        return img[node["u"] * bs: node["u"] * bs + size]
    if lay == 2:
        nblk = size // bs
        head = img[node["u"] * bs: node["u"] * bs + nblk * bs] if nblk else b""
        tail = img[node["data_off"]: node["data_off"] + (size - nblk * bs)]
        return head + tail
    return None

def listdir(node):
    d = data(node)
    out = []
    for b in range(0, len(d), bs):
        blk = d[b:b + bs]
        if len(blk) < 12: break
        first = struct.unpack_from("<H", blk, 8)[0]
        cnt = first // 12
        ents = [struct.unpack_from("<QHBB", blk, i * 12) for i in range(cnt)]
        for i, (nid, noff, ftype, _) in enumerate(ents):
            end = ents[i + 1][1] if i + 1 < cnt else len(blk)
            name = blk[noff:end].split(bytes(1))[0].decode("latin1") if i + 1 < cnt else blk[noff:].split(bytes(1))[0].decode("latin1")
            if name not in (".", ".."): out.append((name, nid, ftype))
    return out

LAYOUT = {0: "plain", 1: "compressed", 2: "inline", 3: "compressed-compact", 4: "chunk"}
files = {}
def walk(nid, path):
    n = inode(nid)
    for name, cnid, ftype in listdir(n):
        p = path + "/" + name
        c = inode(cnid)
        if (c["mode"] & 0o170000) == 0o040000:
            print(f"{p}/")
            walk(cnid, p)
        else:
            files[p] = c
            extra = ""
            if (c["mode"] & 0o170000) == 0o120000:             # symlink: show where it points
                t = data(c)
                if t is not None: extra = "  -> " + t.decode("latin1")
            print(f"{p}  {c['size']} B  [{LAYOUT.get(c['layout'], c['layout'])}]{extra}")
walk(root_nid, "")
for p in files:
    if p.endswith("modules.load") or p.endswith("modules.dep") or p.endswith("modules.softdep"):
        d = data(files[p])
        print(f"\n== {p} ==\n" + (d.decode('latin1') if d is not None else "(compressed: cannot read here)"))
