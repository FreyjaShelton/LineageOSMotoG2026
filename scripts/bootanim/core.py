"""Shared engine for the chrysalis -> butterfly boot animations.

Everything that is the same between art styles lives here: the screen/timing
constants, the timeline (chrysalis rises from the bottom of the screen,
pulses, cracks, splits; butterfly emerges, unfolds, then idles), the shared
geometry (chrysalis outline, crack path, wing/vein shapes), drawing helpers
and the zip packager. A style only decides how the shapes are *rendered*.

Timeline is authored in "logical units" of 1/30 s and sampled at FPS (24), so
the tuning numbers below read as frames at 30 fps.
"""
import math
import random
import shutil
import zipfile
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

RS = Image.Resampling

# --- Screen / timing --------------------------------------------------------
W, H = 720, 1604                 # moto g 2026 (utah) panel
FPS = 24
STEP = 30 / FPS                  # logical units per output frame
CX, CY = W // 2, 800             # centre of the action

T_RISE = 50                      # chrysalis finishes sliding up from the bottom
T_MELT0, T_MELT1 = 66, 130       # the shell melts away, top first
T_HANG1 = 160                    # the exposed blob hangs here (1 s), then...
T_DIP1 = 172                     # ...bobs down (anticipation squash) until here, then leaps
T_LEAP1 = 190                    # crest of the leap
T_SPIN0 = 174                    # spin starts (blob bursts into the butterfly)
T_SPIN1 = 250                    # spin has settled into the idle pose
INTRO_UNITS = T_SPIN1            # 250 units = 200 frames (8.3 s), plays once
LOOP_UNITS = 120                 # idle loop (4 s) = 96 frames
SPIN_DEG = 720.0                 # two full turns about the vertical axis
FLAP = 40                        # 3 gentle flaps per loop
N_INTRO = round(INTRO_UNITS / STEP)
N_LOOP = round(LOOP_UNITS / STEP)
FINAL_Y = CY - 20                # butterfly thorax y when idle
FINAL_SC = 0.80


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(a, b, x):
    t = clamp((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def ease_out(t):
    return 1 - (1 - clamp(t)) ** 3


def ease_back(t, s=0.7):
    """Ease-out with a small overshoot, then settle."""
    t = clamp(t) - 1
    return 1 + (s + 1) * t ** 3 + s * t ** 2


def scale_img(im, k):
    n = len(im.getbands())
    return im.point([min(255, int(i * k)) for i in range(256)] * n)


def mixc(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


# ===========================================================================
# Drawing helpers
# ===========================================================================
def _make_blob():
    """256x256 soft round falloff: 255 at the centre, exactly 0 at the circle's edge."""
    n = 256
    px = []
    for y in range(n):
        for x in range(n):
            d = math.hypot(x - (n - 1) / 2, y - (n - 1) / 2) / (n / 2)
            px.append(int(255 * (1 - d) ** 2.2) if d < 1 else 0)
    im = Image.new("L", (n, n))
    im.putdata(px)
    return im


BLOB = _make_blob()


def add_blob(frame, cx, cy, rx, ry, k, color=(0.35, 1.0, 0.6)):
    """Additive soft glow centred on (cx, cy)."""
    rx, ry = int(rx), int(ry)
    if rx < 1 or ry < 1 or k <= 0.003:
        return
    x0, y0 = int(cx) - rx, int(cy) - ry
    box = (max(0, x0), max(0, y0), min(W, x0 + 2 * rx), min(H, y0 + 2 * ry))
    if box[0] >= box[2] or box[1] >= box[3]:
        return
    b = BLOB.resize((2 * rx, 2 * ry), RS.BILINEAR)
    b = b.crop((box[0] - x0, box[1] - y0, box[2] - x0, box[3] - y0))
    rgb = Image.merge("RGB", [b.point(lambda v, c=c: min(255, int(v * c * k))) for c in color])
    frame.paste(ImageChops.add(frame.crop(box), rgb), box[:2])


def bloom(fr, gain=1.0):
    """Cheap glow: blur a quarter-size copy and add it back."""
    sm = fr.resize((W // 4, H // 4), RS.BOX)
    b = ImageChops.add(
        scale_img(sm.filter(ImageFilter.GaussianBlur(3)), 0.55 * gain),
        scale_img(sm.filter(ImageFilter.GaussianBlur(12)), 0.90 * gain),
    )
    return ImageChops.add(fr, b.resize((W, H), RS.BICUBIC))


def blit(frame, spr, anchor, pos, angle=0.0, scale=1.0, alpha=1.0):
    """Paste RGBA `spr` so its `anchor` lands on `pos`, optionally rotating
    (degrees, CCW) about the anchor and scaling."""
    if alpha <= 0.002:
        return
    if scale != 1.0:
        spr = spr.resize((max(1, round(spr.width * scale)), max(1, round(spr.height * scale))), RS.BICUBIC)
        anchor = (anchor[0] * scale, anchor[1] * scale)
    if angle:
        spr = spr.rotate(angle, resample=RS.BICUBIC, center=anchor)
    a = spr.getchannel("A")
    if alpha < 1.0:
        a = a.point([int(i * alpha) for i in range(256)])
    frame.paste(spr.convert("RGB"), (round(pos[0] - anchor[0]), round(pos[1] - anchor[1])), a)


def catmull(pts, n=14):
    """Closed Catmull-Rom spline through pts -> dense polyline."""
    out, N = [], len(pts)
    for i in range(N):
        p0, p1, p2, p3 = pts[(i - 1) % N], pts[i], pts[(i + 1) % N], pts[(i + 2) % N]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(
                0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t
                       + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                       + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3)
                for j in (0, 1)))
    return out


def resample_closed(poly, spacing):
    """Evenly spaced points along a closed polyline."""
    pts = poly + [poly[0]]
    seg = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    total = sum(seg)
    n = max(3, int(total / spacing))
    out, acc, i = [], 0.0, 0
    for k in range(n):
        target = total * k / n
        while acc + seg[i] < target and i < len(seg) - 1:
            acc += seg[i]
            i += 1
        f = (target - acc) / seg[i] if seg[i] else 0
        out.append((lerp(pts[i][0], pts[i + 1][0], f), lerp(pts[i][1], pts[i + 1][1], f)))
    return out


def resample_open(pts, spacing):
    seg = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    total = sum(seg)
    n = max(2, int(total / spacing))
    out, acc, i = [], 0.0, 0
    for k in range(n + 1):
        target = total * k / n
        while acc + seg[i] < target and i < len(seg) - 1:
            acc += seg[i]
            i += 1
        f = (target - acc) / seg[i] if seg[i] else 0
        out.append((lerp(pts[i][0], pts[i + 1][0], f), lerp(pts[i][1], pts[i + 1][1], f)))
    return out


# ===========================================================================
# Shared geometry: sprite canvases (fixed) and the Shape class (per style)
# ===========================================================================
L_MAX = 480                              # longest chrysalis any shape may use
PAD = 200
SW, SH = 2 * PAD + 300, 2 * PAD + L_MAX + 40
SX, SY = SW // 2, PAD + 16               # top centre of the body inside the sprite

WCW, WCH = 480, 830                      # right-wing sprite canvas
WAX, WAY = 14, 420                       # thorax anchor inside the wing sprite
BW, BH, BX, BY = 200, 360, 100, 190      # body sprite size and thorax anchor


def densify(poly, step=9.0, closed=True):
    """Insert points so straight edges are sampled every ~step px."""
    pts = list(poly) + ([poly[0]] if closed else [])
    out = []
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
        for k in range(n):
            out.append((lerp(a[0], b[0], k / n), lerp(a[1], b[1], k / n)))
    return out


def poly_mask(poly, S=2, size=(WCW, WCH)):
    m = Image.new("L", (size[0] * S, size[1] * S), 0)
    ImageDraw.Draw(m).polygon([(x * S, y * S) for x, y in poly], fill=255)
    return m


def _wing_geom(ctrl, smooth):
    """ctrl: wing outline control points relative to the thorax (x out, y down)."""
    raw = catmull(ctrl) if smooth else densify(ctrl)
    poly = [(x + WAX, y + WAY) for x, y in raw]
    base = (WAX + 6.0, WAY - 4.0)
    far = [p for p in poly if math.hypot(p[0] - base[0], p[1] - base[1]) > 130]
    step = max(1, len(far) // 9)
    edge = far[::step]
    veins, dots = [], []
    for i, (ex, ey) in enumerate(edge):
        dx, dy = ex - base[0], ey - base[1]
        ln = math.hypot(dx, dy)
        end = (base[0] + dx * 0.96, base[1] + dy * 0.96)
        mid = (base[0] + dx * 0.5 - dy / ln * 7, base[1] + dy * 0.5 + dx / ln * 7)
        veins.append([base, mid, end])
        bx, by = base[0] + dx * 0.62, base[1] + dy * 0.62
        for sgn in (-1, 1):
            veins.append([(bx, by), (bx + dx * 0.2 + sgn * dy / ln * 22, by + dy * 0.2 - sgn * dx / ln * 22)])
        dots.append((ex - dx / ln * 9, ey - dy / ln * 9, 4.2 if i % 2 == 0 else 2.8))
    sub = far[::max(1, step // 3)]
    for p in sub:
        ln = math.hypot(p[0] - base[0], p[1] - base[1])
        dots.append((p[0] - (p[0] - base[0]) / ln * 5, p[1] - (p[1] - base[1]) / ln * 5, 1.4))
    return dict(poly=poly, base=base, veins=veins, dots=dots, ctrl=[(x + WAX, y + WAY) for x, y in ctrl])


class Shape:
    """Silhouettes: the chrysalis body and the butterfly's wings. Styles pick one.

    profile   [(s, w)]: half-width (as a fraction of `radius`) at fraction s down the body
    bow       sideways bend of the body's centre line, px
    bf_scale  butterfly size multiplier (wide-winged shapes use < 1)
    fore/hind right-wing outline control points relative to the thorax (x out, y down);
              hindwing is drawn first, forewing over it
    smooth_*  False = straight-edged polygon (cut-gem look) instead of a smooth curve
    """

    def __init__(self, name, length, radius, profile, bow, fore, hind, smooth_body=True, smooth_wings=True,
                 crack_seed=7, bf_scale=1.0):
        assert length <= L_MAX
        self.name, self.L, self.R, self.profile, self.bow = name, length, radius, profile, bow
        self.smooth_body = smooth_body
        self.bf_scale = bf_scale          # butterfly size factor so wide wings keep a margin from the screen edge
        self.wing_geom = [_wing_geom(hind, smooth_wings), _wing_geom(fore, smooth_wings)]
        self._build_crack(crack_seed)

    # -- body -----------------------------------------------------------------
    def r(self, s):
        """Half-width at fraction s (0 top .. 1 bottom)."""
        s = clamp(s)
        P = self.profile
        i = 0
        while i < len(P) - 2 and s > P[i + 1][0]:
            i += 1
        p0, p1, p2 = P[max(i - 1, 0)], P[i], P[i + 1]
        p3 = P[min(i + 2, len(P) - 1)]
        t = (s - p1[0]) / (p2[0] - p1[0])
        if self.smooth_body:
            y0, y1, y2, y3 = p0[1], p1[1], p2[1], p3[1]
            w = 0.5 * ((2 * y1) + (-y0 + y2) * t + (2 * y0 - 5 * y1 + 4 * y2 - y3) * t * t
                       + (-y0 + 3 * y1 - 3 * y2 + y3) * t ** 3)
        else:
            w = lerp(p1[1], p2[1], t)
        return max(self.R * w, 1.0)

    def c(self, s):
        return self.bow * math.sin(math.pi * clamp(s))

    def pt(self, s, u):
        """Sprite coordinates for fraction s along, u in [-1, 1] across."""
        return (SX + self.c(s) + u * self.r(s), SY + s * self.L)

    @property
    def anchor(self):
        """Rotation/placement point = body centre."""
        return (SX + self.c(0.5), SY + self.L * 0.5)

    def outline(self, n=200):
        left = [self.pt(i / n, -1) for i in range(n + 1)]
        right = [self.pt(i / n, 1) for i in range(n + 1)]
        return left + right[::-1]

    def body_mask(self, S=3):
        m = Image.new("L", (SW * S, SH * S), 0)
        ImageDraw.Draw(m).polygon([(x * S, y * S) for x, y in self.outline()], fill=255)
        return m.resize((SW, SH), RS.LANCZOS)

    # -- crack ----------------------------------------------------------------
    def _build_crack(self, seed):
        rng = random.Random(seed)
        n = 22
        pts = []
        for i in range(n + 1):
            s = 0.03 + 0.95 * i / n
            u = rng.uniform(-0.30, 0.30) * (0.4 if i in (0, n) else 1.0)
            pts.append(self.pt(s, u))
        twigs = []
        for i in (3, 6, 9, 12, 15, 18):
            x, y = pts[i]
            ang = rng.uniform(-0.9, 0.9) + (math.pi / 2 if rng.random() < 0.5 else -math.pi / 2)
            ln = rng.uniform(18, 38)
            twigs.append((i, (x, y), (x + math.cos(ang) * ln * 0.9, y + math.sin(ang) * ln * 0.5)))
        self.crack, self.twigs, self.crack_m, self.crack_n = pts, twigs, 9, n

    @staticmethod
    def _interp(pts, f):
        i = min(int(f), len(pts) - 2)
        k = f - i
        return (lerp(pts[i][0], pts[i + 1][0], k), lerp(pts[i][1], pts[i + 1][1], k))

    def crack_subpath(self, p):
        """Polyline of the crack grown to progress p (grows outward from the middle)."""
        n = len(self.crack) - 1
        lo = clamp(self.crack_m * (1 - p), 0, n)
        hi = clamp(self.crack_m + (self.crack_n - self.crack_m) * p, 0, n)
        out = [self._interp(self.crack, lo)]
        for i in range(int(math.floor(lo)) + 1, int(math.ceil(hi))):
            out.append(self.crack[i])
        out.append(self._interp(self.crack, hi))
        twigs = [(a, b) for i, a, b in self.twigs if lo <= i <= hi]
        return out, twigs

    def crack_overlay(self, p, glow=(60, 255, 150, 110), core=(235, 255, 242, 255), wscale=1.0):
        """RGBA overlay (sprite-sized) with the glowing seam drawn up to progress p (0..1)."""
        S = 2
        ov = Image.new("RGBA", (SW * S, SH * S), (0, 0, 0, 0))
        if p <= 0:
            return ov.resize((SW, SH), RS.BILINEAR)
        d = ImageDraw.Draw(ov)
        path, twigs = self.crack_subpath(p)
        path = [(x * S, y * S) for x, y in path]
        twigs = [[(a[0] * S, a[1] * S), (b[0] * S, b[1] * S)] for a, b in twigs]
        for w, col in ((11 * wscale, glow), (4 * wscale, core)):
            d.line(path, fill=col, width=int(w * S // 2 + 1), joint="curve")
            for t in twigs:
                d.line(t, fill=col, width=max(1, int((w // 2) * S // 2)))
        return ov.resize((SW, SH), RS.LANCZOS)

    def half_masks(self):
        S = 2
        path = [(SX, 0)] + self.crack + [(SX, SH)]
        L = Image.new("L", (SW * S, SH * S), 0)
        R = Image.new("L", (SW * S, SH * S), 0)
        pp = [(x * S, y * S) for x, y in path]
        ImageDraw.Draw(L).polygon([(0, 0)] + pp + [(0, SH * S)], fill=255)
        ImageDraw.Draw(R).polygon([(SW * S, 0)] + pp + [(SW * S, SH * S)], fill=255)
        return L.resize((SW, SH), RS.LANCZOS), R.resize((SW, SH), RS.LANCZOS)


# ===========================================================================
# Butterfly body (shared) and sprite helpers
# ===========================================================================
BODY_ELL = [("abd", 0, 72, 8, 70), ("thx", 0, -4, 11, 26), ("head", 0, -36, 10, 10)]


def antenna(sgn):
    p0, p1, p2 = (sgn * 4, -42), (sgn * 20, -130), (sgn * 72, -152)
    pts = [((1 - t) ** 2 * p0[0] + 2 * t * (1 - t) * p1[0] + t * t * p2[0],
            (1 - t) ** 2 * p0[1] + 2 * t * (1 - t) * p1[1] + t * t * p2[1]) for t in (i / 20 for i in range(21))]
    return pts, p2


def build_body_stock(c):
    """Default butterfly body. c: dict of colours (abd, abd_hi, thx, thx_hi, head, head_hi, ant, club, seg)."""
    S = 3
    im = Image.new("RGBA", (BW * S, BH * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def E(cx, cy, rx, ry, fill):
        d.ellipse([(BX + cx - rx) * S, (BY + cy - ry) * S, (BX + cx + rx) * S, (BY + cy + ry) * S], fill=fill)

    for sgn in (-1, 1):
        pts, tip = antenna(sgn)
        d.line([((BX + x) * S, (BY + y) * S) for x, y in pts], fill=c["ant"], width=2 * S, joint="curve")
        E(tip[0], tip[1], 4.5, 4.5, c["club"])
    E(0, 72, 8, 70, c["abd"])
    E(-2.5, 70, 3, 60, c["abd_hi"])
    for yy in range(22, 140, 13):
        w = 8 * math.sqrt(max(0.0, 1 - ((yy - 72) / 70) ** 2))
        d.line([((BX - w) * S, (BY + yy) * S), ((BX + w) * S, (BY + yy) * S)], fill=c["seg"], width=S)
    E(0, -4, 11, 26, c["thx"])
    E(-3, -8, 4, 16, c["thx_hi"])
    E(0, -36, 10, 10, c["head"])
    E(-3, -39, 3.5, 3.5, c["head_hi"])
    return im.resize((BW, BH), RS.LANCZOS)


PERSPECTIVE = 0.17                       # how much bigger the wing swinging toward the viewer gets during a spin


def yaw_factors(yaw):
    """(side, width, near_scale, far_scale) for a butterfly turned `yaw` degrees about its vertical axis."""
    a = math.radians(yaw)
    cs, sn = math.cos(a), math.sin(a)
    return (1 if cs >= 0 else -1), max(0.035, abs(cs)), 1 + PERSPECTIVE * sn, 1 - PERSPECTIVE * sn


def draw_butterfly_sprites(fr, wing, body, cx, cy, sc, f, alpha=1.0, yaw=0.0):
    """f = how open the wings are (0.05 folded .. 1 fully open); yaw = turn about the vertical axis (degrees)."""
    syf = 0.92 + 0.08 * f
    yaw %= 360.0
    if min(yaw, 360.0 - yaw) < 0.05:
        w = max(2, round(wing.width * sc * f))
        h = max(2, round(wing.height * sc * syf))
        wr = wing.resize((w, h), RS.BICUBIC)
        ax, ay = WAX * sc * f, WAY * sc * syf
        blit(fr, wr, (ax, ay), (cx, cy), alpha=alpha)
        blit(fr, ImageOps.mirror(wr), (w - ax, ay), (cx, cy), alpha=alpha)
        blit(fr, body, (BX, BY), (cx, cy), scale=sc, alpha=alpha)
        return
    side, wd, near, far = yaw_factors(yaw)
    for wside, ps in ((-side, far), (side, near)):                 # far wing first, then the near one
        w = max(2, round(wing.width * sc * f * wd * ps))
        h = max(2, round(wing.height * sc * syf * ps))
        wr = wing.resize((w, h), RS.BICUBIC)
        ax, ay = WAX * sc * f * wd * ps, WAY * sc * syf * ps
        if wside < 0:
            wr, ax = ImageOps.mirror(wr), w - ax
        blit(fr, wr, (ax, ay), (cx, cy), alpha=alpha)
    bw = max(2, round(body.width * sc * max(wd, 0.3)))
    bh = max(2, round(body.height * sc))
    blit(fr, body.resize((bw, bh), RS.BICUBIC), (BX * sc * max(wd, 0.3), BY * sc), (cx, cy), alpha=alpha)


def lit(spr, level, color=(70, 190, 100)):
    """Inner light shining through a sprite (additive tint inside its alpha)."""
    if level <= 0.01:
        return spr
    a = spr.getchannel("A")
    rgb = spr.convert("RGB")
    add = Image.new("RGB", spr.size, tuple(int(c * level) for c in color))
    out = Image.composite(ImageChops.add(rgb, add), rgb, a).convert("RGBA")
    out.putalpha(a)
    return out


# ===========================================================================
# Sparkles
# ===========================================================================
_rng = random.Random(11)
MOTES = [dict(x0=_rng.uniform(70, 650), y0=_rng.uniform(CY - 430, CY + 300),
              A=_rng.uniform(8, 26), B=_rng.uniform(10, 34),
              m=_rng.choice((1, 2)), n=_rng.choice((1, 2)), q=_rng.choice((1, 2, 3)),
              p1=_rng.uniform(0, 6.28), p2=_rng.uniform(0, 6.28), p3=_rng.uniform(0, 6.28),
              r=_rng.uniform(2.5, 6)) for _ in range(34)]
BURST = [dict(ang=_rng.uniform(0, 6.283), v=_rng.uniform(6, 16), life=_rng.randint(36, 70),
              size=_rng.uniform(3, 7)) for _ in range(52)]


def draw_motes(fr, T, k, color=(0.55, 1.0, 0.75), size=1.0):
    """Drifting sparkles. Whole cycles per LOOP_UNITS, so they loop seamlessly."""
    if k <= 0.01:
        return
    a = 2 * math.pi * T / LOOP_UNITS
    for m in MOTES:
        x = m["x0"] + m["A"] * math.sin(a * m["m"] + m["p1"])
        y = m["y0"] + m["B"] * math.cos(a * m["n"] + m["p2"])
        tw = 0.15 + 0.85 * (0.5 + 0.5 * math.sin(a * m["q"] + m["p3"])) ** 2
        r = m["r"] * 3 * size
        add_blob(fr, x, y, r, r, tw * k * 0.9, color)


def draw_burst(fr, tb, color=(0.7, 1.0, 0.85)):
    for b in BURST:
        if tb < 0 or tb > b["life"]:
            continue
        tau = tb / b["life"]
        dist = b["v"] * b["life"] * 0.35 * (1 - (1 - tau) ** 2)
        x = CX + math.cos(b["ang"]) * dist
        y = CY - 30 + math.sin(b["ang"]) * dist * 1.1 - 25 * tau
        add_blob(fr, x, y, b["size"] * 2.4, b["size"] * 2.4, (1 - tau) ** 1.5, color)


def heartbeat(t, beats=(60, 76, 90, 102, 112, 122)):
    v = 0.0
    for bt in beats:
        v += math.exp(-((t - bt) / 3.2) ** 2) + 0.5 * math.exp(-((t - bt - 6) / 3.2) ** 2)
    return clamp(v)


# ===========================================================================
# Timeline
# ===========================================================================
RISE_DIST = H - CY + L_MAX * 0.5 + 40        # chrysalis centre starts this far below rest (fully off-screen)


def centre_dy(t):
    """Vertical offset (px, from CY) of the blob / butterfly centre: hang, dip, leap, settle."""
    if t < T_DIP1:
        return 38.0 * smooth(T_HANG1, T_DIP1, t)                                  # anticipation dip
    if t < T_LEAP1:
        return lerp(38.0, -78.0, smooth(T_DIP1, T_LEAP1, t))                      # leap
    return lerp(-78.0, FINAL_Y - CY, smooth(T_LEAP1, T_SPIN1, t))                 # float back down


def ease_smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def wing_pump(u):
    """Wing opening factor during the spin (u = 0..1): fling out wide, then 3 shrinking pumps, ends at 1.0."""
    opening = smooth(0.0, 0.20, u)
    dip = math.exp(-2.4 * u) * (1 - math.cos(2 * math.pi * 3 * u)) / 2
    f = 0.05 + (1.0 + 0.16 * math.exp(-3.0 * u) - 0.62 * dip - 0.05) * opening
    return lerp(f, 1.0, smooth(0.86, 1.0, u))


def intro_state(t):
    """Everything the renderer needs at logical time t (units of 1/30 s)."""
    u = clamp(t / T_RISE)
    rise = ease_back(u)
    settle = smooth(T_RISE - 8, T_RISE + 12, t)
    st = SimpleNamespace(t=t, T=t, tb=None, loop=False, split=False, spin=0.0, spin_active=False)
    st.yoff = (1 - rise) * RISE_DIST
    st.melt = smooth(T_MELT0, T_MELT1, t)                       # 0..1: how far the melt front has travelled
    st.shell = st.melt < 0.999
    st.jy = 6 * math.sin(t / 8.5) * settle * (1 - st.melt)
    st.sway = 4 * (1 - u) ** 2 * math.sin(t / 3.5) + 2.0 * math.sin(t / 14.0) * settle * (1 - st.melt)
    st.beat = heartbeat(t, (58, 70, 82))
    shake = 2.6 * smooth(T_MELT0 - 6, T_MELT0 + 22, t) * (1 - st.melt)
    st.jx = shake * math.sin(t * 2.7) * math.cos(t * 1.3)
    st.scale = 1 + 0.012 * st.beat
    st.light = (0.02 + 0.07 * st.beat + 0.26 * st.melt) * smooth(10, 50, t)
    dy = centre_dy(t)
    st.dy = dy
    fade = smooth(0, 50, t)
    # aura follows whatever is at the centre
    if t < T_SPIN0:
        hang = smooth(T_MELT1 - 10, T_MELT1 + 10, t)
        st.aura = (0.30 + 0.35 * st.beat + 0.45 * st.melt + 0.25 * hang + 0.08 * hang * math.sin(t * 0.45)) * fade
        st.aura_x, st.aura_y = CX, CY + st.yoff + dy
    else:
        w = (t - T_SPIN0) / (T_SPIN1 - T_SPIN0)
        st.aura = 1.0 + 0.45 * math.sin(math.pi * clamp(w / 0.6)) ** 2 * (1 - smooth(0.6, 1.0, w))
        st.aura_x, st.aura_y = CX, CY + dy + 30
    st.mote_k = 1.0 * smooth(20, 70, t)
    # --- the blob: lives inside the shell, is revealed by the melt, bobs, then bursts into the butterfly
    st.blob = None
    if t < T_SPIN0 + 16:
        sx = sy = 1.0
        if t >= T_HANG1:
            sq = smooth(T_HANG1, T_DIP1, t)                      # squash on the way down
            sx, sy = 1 + 0.22 * sq, 1 - 0.22 * sq
            if t >= T_DIP1:
                lp = smooth(T_DIP1, T_DIP1 + 9, t)               # stretch on the way up
                sx, sy = lerp(1.22, 0.84, lp), lerp(0.78, 1.30, lp)
        hover = 5.0 * math.sin(t / 9.0) * smooth(T_MELT0, T_MELT1, t) if t < T_HANG1 else 0.0
        tremor = 2.2 * smooth(T_MELT1 + 14, T_HANG1, t) * math.sin(t * 3.1) if t < T_HANG1 else 0.0
        vis = lerp(0.30, 1.0, smooth(T_MELT0, T_MELT0 + 40, t)) * smooth(4, 40, t)
        breath = 1 + 0.035 * math.sin(t * 0.42) * smooth(T_MELT0, T_MELT1, t)
        st.blob = dict(x=CX + st.jx + tremor, y=CY + st.yoff + st.jy + dy + hover,
                       sx=sx * breath, sy=sy * breath, a=vis * (1 - smooth(T_SPIN0, T_SPIN0 + 14, t)), t=t)
    # --- the butterfly: bursts out of the blob during the leap and spins
    st.bf = None
    st.flash = st.ring = 0.0
    st.bloom_extra = 0.0
    if t >= T_SPIN0:
        w = (t - T_SPIN0) / (T_SPIN1 - T_SPIN0)
        st.spin = SPIN_DEG * (1 - (1 - w) ** 3) * smooth(0.0, 0.07, w) if w < 1 else SPIN_DEG   # fast, decelerating, lands at 720 = 0
        st.spin_active = t < T_SPIN1
        k = 0.42 + 0.58 * smooth(0.0, 0.35, w) + 0.14 * math.sin(math.pi * clamp(w / 0.7)) ** 2
        f = wing_pump(w)
        a = smooth(T_SPIN0, T_SPIN0 + 10, t)
        st.bf = (CX, CY + dy, FINAL_SC * k, f, a)
        tt = t - T_SPIN0
        st.flash = 0.55 * max(0.0, 1 - tt / 22) ** 2
        st.bloom_extra = 0.35 * max(0.0, 1 - tt / 26)
        st.ring = tt / 44 if tt < 44 else 0.0
    return st


def loop_state(j):
    T = INTRO_UNITS + j
    phi = 2 * math.pi * j / FLAP
    f = 0.42 + 0.58 * ((1 + math.cos(phi)) / 2) ** 0.7       # gentle idle flap: mostly open
    y = FINAL_Y + 12 * math.sin(2 * math.pi * j / LOOP_UNITS)
    x = CX + 7 * math.sin(4 * math.pi * j / LOOP_UNITS)
    st = SimpleNamespace(t=T, T=T, tb=None, loop=True, split=False, phi=phi, j=j, spin=0.0, spin_active=False)
    st.aura, st.aura_x, st.aura_y = 1.0 + 0.1 * math.sin(phi), x, y + 30
    st.mote_k, st.flash, st.bloom_extra, st.ring = 1.0, 0.0, 0.0, 0.0
    st.bf = (x, y, FINAL_SC, f, 1.0)
    st.blob, st.melt, st.shell, st.dy = None, 1.0, False, 0.0
    st.yoff, st.jy, st.jx, st.sway, st.scale = 0.0, 0.0, 0.0, 0.0, 1.0
    st.beat, st.light = 0.0, 0.0
    return st


def state_at(t):
    """Intro or loop state for an absolute time (used by afterimage ghosts that look back in time)."""
    t = max(0.0, t)
    return intro_state(t) if t < INTRO_UNITS else loop_state(t - INTRO_UNITS)


# ===========================================================================
# Style base classes
# ===========================================================================
# ===========================================================================
# Melt: the shell dissolves from the top down
# ===========================================================================
def melt_y(shape, x, m, t):
    """y (sprite coords) of the melt front at column x when the front has travelled m (0..1)."""
    y0 = SY - 60 + m * (shape.L + 190)
    wob = 12 * math.sin(x / 26 + t * 0.07 + 0.6) + 7 * math.sin(x / 10.5 - t * 0.05 + 2.1)
    return y0 + wob * (0.3 + 0.7 * min(1.0, m * 6)) + 0.10 * (x - SX)


_MASKS = {}


def melt_masks(shape):
    key = shape.name
    if key not in _MASKS:
        _MASKS[key] = shape.body_mask()
    return _MASKS[key]


def melt_sprite(spr, shape, m, t, rim_rgb, glow=1.0):
    """Cut the melted top off the shell sprite and add a hot, glowing rim along the melt front."""
    keep = Image.new("L", (SW, SH), 0)
    front = [(x, melt_y(shape, x, m, t)) for x in range(0, SW + 1, 5)]
    ImageDraw.Draw(keep).polygon(front + [(SW, SH), (0, SH)], fill=255)
    keep = keep.filter(ImageFilter.GaussianBlur(1.1))
    band = ImageChops.subtract(keep, ImageChops.offset(keep, 0, 15))
    band = ImageChops.multiply(band, melt_masks(shape)).filter(ImageFilter.GaussianBlur(2.2))
    band = band.point([min(255, int(v * 1.6)) for v in range(256)])
    r, g, b, a = spr.split()
    a = ImageChops.lighter(ImageChops.multiply(a, keep), band.point([int(v * 0.9) for v in range(256)]))
    tint = Image.merge("RGB", [band.point([min(255, int(v * c / 255 * glow)) for v in range(256)]) for c in rim_rgb])
    rgb = ImageChops.add(Image.merge("RGB", (r, g, b)), tint)
    out = rgb.convert("RGBA")
    out.putalpha(a)
    return out


def make_drips(shape, seed=5, n=11):
    """Rivulets that start at the melt front and run down the shell: (u across, t_start, speed, s_start)."""
    rng = random.Random(seed)
    out = []
    for i in range(n):
        u = rng.uniform(-0.8, 0.8)
        ts = T_MELT0 + 6 + (T_MELT1 - T_MELT0 - 22) * (i + rng.uniform(0, 0.8)) / n
        m = smooth(T_MELT0, T_MELT1, ts)
        x = SX + shape.c(0.5) + u * shape.R
        s0 = clamp((melt_y(shape, x, m, ts) - SY) / shape.L)
        out.append(dict(u=u, ts=ts, v=rng.uniform(4.5, 7.0), g=rng.uniform(0.07, 0.12), s0=s0, x0=x))
    return out


def drip_state(shape, d, t):
    """(head_xy, tail_xy) in sprite coords for drip d at time t, or None if not active.
    The streak runs from the melt front down to a head that accelerates along the shell's surface."""
    tau = t - d["ts"]
    if tau < 0 or d["s0"] > 0.97:
        return None
    dist = d["v"] * tau + 0.5 * d["g"] * tau * tau

    def at(dd):
        s = d["s0"] + dd / shape.L
        if s <= 1.0:
            return (SX + shape.c(s) + d["u"] * shape.r(s), SY + s * shape.L), s
        return (SX + shape.c(1.0) + d["u"] * shape.r(1.0), SY + shape.L + (s - 1.0) * shape.L), s
    head, sh = at(dist)
    tail, st_ = at(max(0.0, dist - 90))
    rim = clamp((melt_y(shape, d["x0"], smooth(T_MELT0, T_MELT1, t), t) - SY) / shape.L, 0, 1.5)
    if sh < rim or head[1] > SY + shape.L + 70:                  # the melt front overtook it, or it has fallen away
        return None
    if st_ < rim:                                                # keep the tail on the shell below the front
        tail = (SX + shape.c(min(rim, 1.0)) + d["u"] * shape.r(min(rim, 1.0)), SY + rim * shape.L)
    return head, tail


class Style:
    """A style decides how everything is drawn; the timeline is shared."""
    name = "base"
    label = ""
    blurb = ""
    bloom_gain = 0.75
    aura_color = (0.35, 1.0, 0.6)
    aura_k = 0.42
    mote_color = (0.55, 1.0, 0.75)
    mote_size = 1.0
    flash_color = (0.45, 1.0, 0.7)
    burst_color = (0.7, 1.0, 0.85)
    png_colors = 256
    global_palette = True            # one shared palette for every frame (no frame-to-frame colour flicker)
    shape_name = "default"           # which silhouette set (see shapes.py)
    glow = 1.0                       # overall glow multiplier (bloom, aura, flash, inner light); CLI --glow scales it
    ghosts = 3                       # afterimages trailing the butterfly
    ghost_dt = 1.6                   # logical units between afterimages
    ghost_alpha = 0.26
    ghosts_always = False            # False: only while spinning; True: also while flying in / idling

    def __init__(self):
        from .shapes import SHAPES
        self.shape = SHAPES[self.shape_name]

    def build(self):
        pass

    def background(self, fr, st):
        draw_motes(fr, st.T, st.mote_k, self.mote_color, self.mote_size)
        add_blob(fr, st.aura_x, st.aura_y, 320, 400, st.aura * self.aura_k * self.glow, self.aura_color)

    def chrysalis(self, fr, st):
        raise NotImplementedError

    def blob(self, fr, st):
        pass

    def draw_bf(self, fr, bf, st, main=True):
        """Draw the butterfly at bf = (x, y, scale, openness, alpha) on fr (screen or spin-layer)."""
        raise NotImplementedError

    def effects(self, fr, st):
        add_blob(fr, CX, st.aura_y - 30, 430, 540, st.flash * self.glow, self.flash_color)

    def post(self, fr, st):
        return bloom(fr, (self.bloom_gain + st.bloom_extra) * self.glow)


class SpriteStyle(Style):
    """Style whose art is pre-rendered into sprites (chrysalis, wing, body)."""
    light_color = (70, 190, 100)
    rim_color = (225, 255, 230)

    def build_chrysalis(self):
        raise NotImplementedError

    def build_wing(self):
        raise NotImplementedError

    def build_body(self):
        raise NotImplementedError

    def build(self):
        self.CHRY = self.build_chrysalis()
        self.WING = self.build_wing()
        self.BODY = self.build_body()

    def chrysalis(self, fr, st):
        if not st.shell:
            return
        spr = lit(self.CHRY, st.light * self.glow, self.light_color)
        if st.melt > 0:
            spr = melt_sprite(spr, self.shape, st.melt, st.t, self.rim_color, self.glow)
        blit(fr, spr, self.shape.anchor, (CX + st.jx, CY + st.yoff + st.jy), angle=st.sway, scale=st.scale)

    def draw_bf(self, fr, bf, st, main=True):
        cx, cy, sc, f, a = bf
        draw_butterfly_sprites(fr, self.WING, self.BODY, cx, cy, sc, f, a, st.spin)


# ===========================================================================
# Rendering / packaging
# ===========================================================================
def paint_bf(style, fr, st, bf, amul=1.0, main=True):
    """Draw the butterfly (turned about its vertical axis by st.spin degrees, see draw_bf)."""
    cx, cy, sc, f, a = bf
    a *= amul
    if a > 0.004:
        style.draw_bf(fr, (cx, cy, sc * style.shape.bf_scale, f, a), st, main)


def render_frame(style, i):
    st = intro_state(i * STEP) if i < N_INTRO else loop_state((i - N_INTRO) * STEP)
    fr = Image.new("RGB", (W, H), (0, 0, 0))
    style.background(fr, st)
    style.blob(fr, st)
    style.chrysalis(fr, st)
    if st.bf:
        n = style.ghosts if (style.ghosts_always or st.spin_active) else 0
        for k in range(n, 0, -1):                                   # afterimages: earlier states, fading out
            p = state_at(st.t - style.ghost_dt * k)
            if p.bf:
                paint_bf(style, fr, p, p.bf, amul=style.ghost_alpha * (1 - (k - 1) / (n + 1)), main=False)
        paint_bf(style, fr, st, st.bf)
    style.effects(fr, st)
    return style.post(fr, st)


def to_png(im, path, colors=256, palette=None):
    # Palette PNGs are ~2.5x smaller than RGB; the art is a narrow colour range so 256 is plenty.
    # (128 or fewer shows visible banding in smooth glows.)
    # With a shared `palette` every frame maps to the same colours, so smooth gradients can't flicker
    # from frame to frame (a per-frame median-cut palette shifts colours slightly each frame).
    if not colors:                                   # 0 = full-colour PNG: no banding, no palette shifts (bigger files)
        q = im
    elif palette is not None:
        q = im.quantize(palette=palette, dither=Image.Dither.NONE)
    else:
        q = im.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q.save(path, compress_level=9, optimize=True)


def make_palette(style, total, colors=256, samples=36):
    """One palette for the whole animation: median-cut over a mosaic of frames sampled across it."""
    ids = sorted({round(k * (total - 1) / (samples - 1)) for k in range(samples)})
    tw, th = W // 3, H // 3
    sheet = Image.new("RGB", (tw * 6, th * ((len(ids) + 5) // 6)))
    for n, i in enumerate(ids):
        sheet.paste(render_frame(style, i).resize((tw, th), RS.BOX), ((n % 6) * tw, (n // 6) * th))
    return sheet.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)


def build_zip(style, out_dir, preview=True, log=print):
    out = Path(out_dir)
    work = out / "build"
    if work.exists():
        shutil.rmtree(work)
    (work / "part0").mkdir(parents=True)
    (work / "part1").mkdir(parents=True)
    total = N_INTRO + N_LOOP
    prev = []
    pal = make_palette(style, total, style.png_colors) if (style.global_palette and style.png_colors) else None
    for i in range(total):
        im = render_frame(style, i)
        part, n = ("part0", i) if i < N_INTRO else ("part1", i - N_INTRO)
        to_png(im, work / part / f"{n:05d}.png", style.png_colors, pal)
        if preview and i % 2 == 0:
            prev.append(im.resize((W // 3, H // 3), RS.LANCZOS))
        if i % 40 == 0:
            log(f"  [{style.name}] frame {i}/{total}")
    # "p <loops> <pause> <dir>": loops 1 = once, 0 = until boot completes.
    (work / "desc.txt").write_text(f"{W} {H} {FPS}\np 1 0 part0\np 0 0 part1\n", newline="\n", encoding="ascii")
    zpath = out / "bootanimation.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:          # STORED is required
        z.write(work / "desc.txt", "desc.txt")
        for part in ("part0", "part1"):
            for f in sorted((work / part).iterdir()):
                z.write(f, f"{part}/{f.name}")
    shutil.rmtree(work)
    if preview and prev:
        prev[0].save(out / "preview.gif", save_all=True, append_images=prev[1:],
                     duration=int(2000 / FPS), loop=0, optimize=True)
    log(f"[{style.name}] wrote {zpath} ({zpath.stat().st_size / 1e6:.1f} MB, {total} frames)")
    return zpath


def stills(style, ids, out_dir):
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    tiles = []
    for i in ids:
        im = render_frame(style, i)
        im.save(d / f"{i:05d}.png")
        tiles.append(im.resize((W // 3, H // 3), RS.LANCZOS))
    sheet = Image.new("RGB", (len(tiles) * (W // 3 + 4), H // 3), (30, 30, 30))
    for k, tile in enumerate(tiles):
        sheet.paste(tile, (k * (W // 3 + 4), 0))
    sheet.save(d / "sheet.png")
    return d / "sheet.png"
