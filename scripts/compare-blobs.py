#!/usr/bin/env python3
"""Phase 3: hash-compare every file in the nevada tree's proprietary-files.txt against the same
path in our own firmware (unpacked in ~/lineage/work/x). Writes ~/lineage/work/cmp/blob-diff.txt and
blob-missing.txt. Run: python3 -I scripts/compare-blobs.py. Diffs include fixup-patched files."""
import os, re, hashlib, collections
tree = os.path.expanduser('~/lineage/android/device/motorola/nevada/proprietary-files.txt')
voff = os.path.expanduser('~/lineage/android/vendor/motorola/nevada/proprietary')
x = os.path.expanduser('~/lineage/work/x')
def ours(p):
    # tree path -> our extracted path; system image nests under system/system
    if p.startswith('system/'): return os.path.join(x, 'system', p)
    return os.path.join(x, p)
def h(p):
    try:
        if os.path.isdir(p) or not os.path.exists(p): return None
        s = hashlib.sha256()
        with open(p,'rb') as f:
            for c in iter(lambda: f.read(1<<20), b''): s.update(c)
        return s.hexdigest()
    except OSError: return None
cnt = collections.Counter(); diff = []; missing = []; part = collections.defaultdict(collections.Counter)
for line in open(tree):
    line = line.strip()
    if not line or line.startswith('#'): continue
    line = line.lstrip('-')
    src = line.split(';')[0]
    tpath, _, opath = src.partition(':')
    opath = opath or tpath
    top = opath.split('/')[0]
    a = h(os.path.join(voff, tpath)) or h(os.path.join(voff, opath))
    b = h(ours(opath))
    if b is None: cnt['not in our firmware'] += 1; missing.append(opath); part[top]['missing'] += 1
    elif a is None: cnt['tree copy absent'] += 1; part[top]['absent'] += 1
    elif a == b: cnt['identical'] += 1; part[top]['same'] += 1
    else: cnt['different'] += 1; diff.append(opath); part[top]['diff'] += 1
print(dict(cnt))
for k, v in part.items(): print(k, dict(v))
open(os.path.expanduser('~/lineage/work/cmp/blob-diff.txt'),'w').write('\n'.join(diff))
open(os.path.expanduser('~/lineage/work/cmp/blob-missing.txt'),'w').write('\n'.join(missing))
print('--- first missing:'); print('\n'.join(missing[:12]))
print('--- different (sample):'); print('\n'.join(diff[:12]))
