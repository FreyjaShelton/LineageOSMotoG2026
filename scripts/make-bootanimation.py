#!/usr/bin/env python3
"""Generate LineageOS boot animations: a chrysalis slides up from the bottom of
the screen, pulses, cracks open and releases a butterfly that idles until boot
finishes. Several art styles share the same timeline.

Needs only Pillow (pip install pillow). Works on Windows or Linux.

    python scripts/make-bootanimation.py --list
    python scripts/make-bootanimation.py --style neon              # -> bootanimation/neon/bootanimation.zip
    python scripts/make-bootanimation.py --style all               # every style, one after another
    python scripts/make-bootanimation.py --style prism --stills 0,30,60,100,126,140,170,200
                                                                   # single frames + contact sheet, for quick looks

Zip layout (standard Android bootanimation format, stored/uncompressed):
    desc.txt        "720 1604 24" then one line per part
    part0/*.png     INTRO, plays once (chrysalis rises, pulses, cracks, splits, butterfly emerges)
    part1/*.png     IDLE LOOP, repeats until the system has finished booting (seamless)

Code: scripts/bootanim/core.py (timeline + shared shapes), style_*.py (one per look).
"""
import argparse
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
warnings.filterwarnings("ignore", category=DeprecationWarning)

from bootanim import styles  # noqa: E402
from bootanim import core    # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--style", default="all", help="style name, comma list, or 'all' (see --list)")
    ap.add_argument("--list", action="store_true", help="list the available styles")
    ap.add_argument("--out", default="bootanimation", help="output directory (default: bootanimation)")
    ap.add_argument("--glow", type=float, default=1.0,
                    help="multiply each style's glow level (default 1.0; 0.5 = half as bright, 1.5 = brighter)")
    ap.add_argument("--no-preview", action="store_true", help="skip the preview GIF")
    ap.add_argument("--stills", help="comma list of output-frame numbers: render only these (+ sheet.png) instead of the zip")
    args = ap.parse_args()

    reg = styles()
    if args.list:
        for n, c in reg.items():
            print(f"{n:9} {c.label}\n          {c.blurb}")
        return
    names = list(reg) if args.style == "all" else args.style.split(",")
    for n in names:
        if n not in reg:
            sys.exit(f"unknown style '{n}' (try --list)")
    for n in names:
        style = reg[n]()
        style.glow *= args.glow
        print(f"[{n}] building sprites...", flush=True)
        style.build()
        out = Path(args.out) / n
        if args.stills:
            sheet = core.stills(style, [int(s) for s in args.stills.split(",")], out / "stills")
            print(f"[{n}] wrote {sheet}")
        else:
            out.mkdir(parents=True, exist_ok=True)
            core.build_zip(style, out, preview=not args.no_preview, log=lambda m: print(m, flush=True))


if __name__ == "__main__":
    main()
