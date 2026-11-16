#!/usr/bin/env python3
"""Stitch every style's preview.gif side by side into bootanimation/compare.gif.

    python scripts/compare-bootanimations.py [bootanimation-dir]

Run scripts/make-bootanimation.py first. All styles share one timeline, so the
frames line up.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageSequence

root = Path(sys.argv[1] if len(sys.argv) > 1 else "bootanimation")
order = sys.argv[2:] or ["neon", "crystal", "stardust"]
gifs = [(n, root / n / "preview.gif") for n in order if (root / n / "preview.gif").exists()]
if not gifs:
    sys.exit("no preview.gif files found; run make-bootanimation.py first")

SCALE = 1.0                                  # three side by side at the preview size (240x534 each)
seqs = []
for n, p in gifs:
    with Image.open(p) as im:
        frames = [f.convert("RGB") for f in ImageSequence.Iterator(im)]
        dur = im.info.get("duration", 83)
    tw, th = int(frames[0].width * SCALE), int(frames[0].height * SCALE)
    seqs.append([f.resize((tw, th), Image.Resampling.LANCZOS) for f in frames])
n_frames = min(len(s) for s in seqs)
tw, th = seqs[0][0].size
label_h, gap = 22, 6
sheet_w = len(seqs) * tw + (len(seqs) - 1) * gap
out = []
for i in range(n_frames):
    sheet = Image.new("RGB", (sheet_w, th + label_h), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    for k, ((name, _), s) in enumerate(zip(gifs, seqs)):
        x = k * (tw + gap)
        sheet.paste(s[i], (x, label_h))
        d.text((x + 6, 5), name, fill=(200, 255, 220))
    out.append(sheet.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))
out[0].save(root / "compare.gif", save_all=True, append_images=out[1:], duration=dur, loop=0, optimize=True)
print(f"wrote {root / 'compare.gif'} ({n_frames} frames, {sheet_w}x{th + label_h})")
