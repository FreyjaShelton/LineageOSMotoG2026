# Saved boot animations (not in the build yet)

Both are 720x1604 @ 24 fps: 200 intro frames (`part0`, plays once) + 96 loop frames (`part1`, loops until boot finishes).
Intro: the shell melts from the top, a blob hangs for a second, bobs, then bursts into the butterfly, which spins
about its vertical axis and settles into the idle loop.

| Folder | Size | Look |
|---|---|---|
| `trop-pink/` | 44.7 MB | angular "flag-shard" butterfly, coral -> hot pink -> violet, light-pink outline, retro sun + grid |
| `circuit/` | 18.5 MB | angular circuit-board butterfly, green + magenta, data pulses along the traces |

Each folder has `bootanimation.zip` (ZIP_STORED, as Android requires) and `preview.gif` (half rate).

**TODO once a build has booted successfully on the phone:** pick one and add it.
- Quick test: push the zip to the phone as `/data/local/bootanimation.zip` (unverified on Android 16).
- Real build: copy into the device tree and `PRODUCT_COPY_FILES += ...bootanimation.zip:$(TARGET_COPY_OUT_PRODUCT)/media/bootanimation.zip`;
  check `vendor/lineage` bootanimation.mk for clashes on the laptop tree.
- Too big? Re-render smaller: `python scripts/make-bootanimation.py --style trop-pink --out <dir>` (styles live in `scripts/bootanim/`).
