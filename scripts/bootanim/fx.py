"""Frame-level effects shared by the glitchy styles: chromatic aberration, scanlines, tape tearing, grid and sun."""
import math
import random

from PIL import Image, ImageChops, ImageDraw

from .core import CX, H, LOOP_UNITS, W, add_blob, clamp, mixc


def scanlines(depth=50, period=4):
    scan = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(scan)
    for y in range(period - 1, H, period):
        d.line([(0, y), (W, y)], fill=255 - depth)
    return Image.merge("RGB", [scan] * 3)


def chroma(fr, px):
    """Red channel left, blue right."""
    if px <= 0:
        return fr
    r, g, b = fr.split()
    return Image.merge("RGB", (ImageChops.offset(r, -px, 0), g, ImageChops.offset(b, px, 0)))


def tear(fr, seed, strips=6, amp=34, y_lo=300, y_hi=1300, hmin=10, hmax=70):
    """Shift random horizontal strips sideways (a tape / data glitch)."""
    rng = random.Random(seed)
    for _ in range(strips):
        h = rng.randint(hmin, hmax)
        y = rng.randint(y_lo, y_hi)
        dx = rng.choice((-1, 1)) * rng.randint(amp // 3, amp)
        strip = fr.crop((0, y, W, y + h))
        fr.paste(ImageChops.offset(strip, dx, 0), (0, y))
    return fr


def roll_bar(fr, T, k=0.16, speed=2.0):
    """A soft bright band that rolls down the screen (period divides the loop)."""
    y = ((T * speed) % LOOP_UNITS) / LOOP_UNITS * (H + 400) - 200
    add_blob(fr, CX, y, 520, 90, k, (0.8, 0.8, 1.0))


def _ramp(stops, f):
    """Evenly spaced colour stops (a flag's stripes, say) with hard bands, top to bottom."""
    return stops[min(len(stops) - 1, int(clamp(f) * len(stops)))]


def retro_sun(fr, cx, cy, r, T, top, bot, k=0.6, slats=9, stops=None, ramp=None):
    """Synthwave sun: a vertical gradient disc cut by horizontal slats that thicken toward the bottom."""
    if k <= 0.01 or r < 4:
        return
    d = ImageDraw.Draw(fr)
    for y in range(int(cy - r), int(cy + r)):
        f = (y - (cy - r)) / (2 * r)
        hw = math.sqrt(max(0.0, r * r - (y - cy) ** 2))
        if hw < 1:
            continue
        # slat gaps: bands every ~r/4.5 px whose thickness grows toward the bottom, drifting slowly
        band = (y - (cy - r)) / (r / slats * 2)
        gap = clamp((f - 0.42) / 0.58) * 0.62
        if f > 0.42 and (band % 1.0) < gap:
            continue
        base = ramp(f) if ramp else _ramp(stops, f) if stops else mixc(top, bot, f)
        col = tuple(int(c * k) for c in base)
        d.line([(cx - hw, y), (cx + hw, y)], fill=col)


def perspective_grid(fr, T, horizon, color, k=0.5, rows=9, cols=13, spread=150, thick=False):
    """Retro floor grid; rows scroll toward the viewer, one row-spacing per loop (seamless)."""
    if k <= 0.01:
        return
    d = ImageDraw.Draw(fr)
    col = tuple(int(c * k) for c in color)
    span = H - horizon
    for j in range(-cols // 2, cols // 2 + 1):
        d.line([(CX, horizon), (CX + j * spread * 2.4, H)], fill=col, width=3 if thick else 2)
    ph = (T / LOOP_UNITS) % 1.0
    for i in range(rows + 1):
        f = ((i + ph) / rows) ** 2.2
        y = horizon + span * f
        a = clamp(f * 3)
        d.line([(0, y), (W, y)], fill=tuple(int(c * a) for c in col), width=(2 + round(6 * f)) if thick else 2)
