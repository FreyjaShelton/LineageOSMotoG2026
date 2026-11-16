"""Style 4: STARDUST - constellation / particle art.

Nothing is filled. The chrysalis and butterfly are made of thousands of
twinkling points of light joined by faint constellation lines. At the split
the shell's points scatter away like dust and the butterfly's points
condense into place. Palette is aurora: pale mint -> teal -> violet.
"""
import math
import random

from PIL import ImageDraw

from .core import (CX, CY, LOOP_UNITS, SY, WAX, WAY, WCH, WCW, Style, antenna, clamp, mixc, poly_mask, resample_closed,
                   resample_open)

MINT, TEAL, VIOLET = (205, 255, 238), (30, 228, 208), (176, 120, 255)


def wing_color(d):
    return mixc(MINT, TEAL, clamp(d / 0.5)) if d < 0.5 else mixc(TEAL, VIOLET, clamp((d - 0.5) / 0.5))


def chry_color(s):
    return mixc(MINT, TEAL, clamp(s * 1.1))


class StardustStyle(Style):
    name = "stardust"
    label = "Stardust (particles)"
    blurb = "Constellation of twinkling points: the shell scatters to dust and re-forms as the butterfly. Mint, teal, violet."
    shape_name = "stardust"
    glow = 0.6
    bloom_gain = 1.0
    aura_color = (0.22, 0.75, 0.95)
    aura_k = 0.26
    mote_color = (0.7, 0.8, 1.0)
    mote_size = 0.9
    flash_color = (0.6, 0.85, 1.0)
    burst_color = (0.75, 0.85, 1.0)

    def build(self):
        rng = random.Random(21)
        sh = self.shape
        chry_pt = sh.pt

        def pt(x, y, kind, d):
            return dict(x=x, y=y, ph=rng.uniform(0, 6.283), q=rng.choice((1, 2, 3)), sz=rng.choice((1.0, 1.0, 1.4, 2.0)),
                        rx=rng.uniform(-1, 1), ry=rng.uniform(-1, 1), kind=kind, d=d)

        # chrysalis points (sprite coordinates)
        self.C_OUT = resample_closed(sh.outline(), 6.5)
        self.CP = [pt(x, y, 0, (y - SY) / sh.L) for x, y in self.C_OUT]
        for k in range(8):                                                    # ribs
            s0 = 0.52 + 0.06 * k
            if s0 > 0.95:
                break
            arc = [chry_pt(s0 + 0.03 * (1 - u * u), u) for u in (i / 11.5 - 1 for i in range(24))]
            self.CP += [pt(x, y, 1, (y - SY) / sh.L) for x, y in resample_open(arc, 8)]
        band = [chry_pt(0.17 + 0.02 * (1 - u * u), u) for u in (i / 11.5 - 1 for i in range(24))]
        self.CP += [pt(x, y, 1, 0.17) for x, y in resample_open(band, 8)]
        for _ in range(260):
            x, y = chry_pt(rng.uniform(0.05, 0.95), rng.uniform(-0.9, 0.9))
            self.CP.append(pt(x, y, 2, (y - SY) / sh.L))

        # butterfly wing points (right wing, local coords relative to the thorax)
        self.WP, self.WOUT = [], []
        for g in sh.wing_geom:
            out = resample_closed(g["poly"], 7)
            self.WOUT.append([(x - WAX, y - WAY) for x, y in out])
            for x, y in out:
                self.WP.append(pt(x - WAX, y - WAY, 0, math.hypot(x - WAX, y - WAY) / 420))
            for pl in g["veins"]:
                for x, y in resample_open(pl, 11 if len(pl) == 3 else 14):
                    self.WP.append(pt(x - WAX, y - WAY, 1, math.hypot(x - WAX, y - WAY) / 420))
            m = poly_mask(g["poly"], 1)
            n = 0
            while n < 520:
                x, y = rng.uniform(0, WCW), rng.uniform(0, WCH)
                if m.getpixel((int(x), int(y))) > 128:
                    self.WP.append(pt(x - WAX, y - WAY, 2, math.hypot(x - WAX, y - WAY) / 420))
                    n += 1

        # body points (local coords)
        self.BP = []
        for y in range(-30, 142, 7):
            self.BP.append(pt(0, y, 1, 0.1))
        for a in range(0, 360, 40):
            self.BP.append(pt(math.cos(math.radians(a)) * 9, -36 + math.sin(math.radians(a)) * 9, 1, 0.1))
        for sgn in (-1, 1):
            pts, tip = antenna(sgn)
            for x, y in resample_open(pts, 7):
                self.BP.append(pt(x, y, 1, 0.1))
            self.BP.append(pt(tip[0], tip[1], 0, 0.1))
            self.BP[-1]["sz"] = 2.4

    # -- helpers --------------------------------------------------------------
    @staticmethod
    def _dot(d, x, y, r, col, k):
        if k <= 0.02:
            return
        c = (int(col[0] * k), int(col[1] * k), int(col[2] * k))
        d.ellipse([x - r, y - r, x + r, y + r], fill=c)

    def _tw(self, p, T):
        return 0.5 + 0.5 * math.sin(2 * math.pi * T * p["q"] / LOOP_UNITS + p["ph"])

    # -- chrysalis ------------------------------------------------------------
    def _chry_xform(self, st):
        ang = math.radians(st.sway)
        ca, sa = math.cos(ang), math.sin(ang)
        ox, oy = CX + st.jx, CY + st.yoff + st.jy
        sc = st.scale

        def f(x, y):
            dx, dy = x - self.shape.anchor[0], y - self.shape.anchor[1]
            return ox + (dx * ca + dy * sa) * sc, oy + (-dx * sa + dy * ca) * sc
        return f

    def chrysalis(self, fr, st):
        d = ImageDraw.Draw(fr)
        f = self._chry_xform(st)
        boost = 0.75 + 0.5 * st.beat + 0.5 * st.crack_p
        line = [f(x, y) for x, y in self.C_OUT]
        d.line(line + [line[0]], fill=(18, 84, 82), width=1)
        for p in self.CP:
            x, y = f(p["x"], p["y"])
            k = (0.35 + 0.65 * self._tw(p, st.T)) * boost
            r = (0.9 + 0.45 * p["sz"]) * (1.2 if p["kind"] == 0 else 1.0)
            self._dot(d, x, y, r, chry_color(p["d"]), min(1.0, k))
        if st.crack_p > 0:                                                    # glowing seam
            path, twigs = self.shape.crack_subpath(st.crack_p)
            segs = [path] + [[a, b] for a, b in twigs]
            for sg in segs:
                for x, y in resample_open(sg, 5):
                    X, Y = f(x, y)
                    fl = 0.7 + 0.3 * math.sin(st.t * 1.7 + x * 0.3)
                    self._dot(d, X, Y, 2.0, (235, 255, 250), fl)

    def halves(self, fr, st):                       # the shell turns to dust
        d = ImageDraw.Draw(fr)
        e, al = st.e, st.halfa
        for p in self.CP:
            dx, dy = p["x"] - self.shape.anchor[0], p["y"] - self.shape.anchor[1]
            x = CX + dx * (1 + 1.3 * e) + p["rx"] * 110 * e
            y = CY + dy * (1 + 1.3 * e) + p["ry"] * 110 * e - 90 * e * e
            k = al * (0.4 + 0.6 * self._tw(p, st.T))
            self._dot(d, x, y, 0.9 + 0.45 * p["sz"], chry_color(p["d"]), k)

    # -- butterfly ------------------------------------------------------------
    def butterfly(self, fr, st):
        cx, cy, sc, f, a = st.bf
        d = ImageDraw.Draw(fr)
        syf = 0.92 + 0.08 * f
        off = (1 - st.asm) ** 1.5 * 140               # points start scattered, then condense
        T = st.T
        for side in (1, -1):
            for ol in self.WOUT:
                pts = [(cx + side * x * sc * f, cy + y * sc * syf) for x, y in ol]
                d.line(pts + [pts[0]], fill=tuple(int(c * a) for c in (24, 96, 118)), width=1)
            for p in self.WP:
                x = cx + side * p["x"] * sc * f + p["rx"] * off
                y = cy + p["y"] * sc * syf + p["ry"] * off
                k = (0.35 + 0.65 * self._tw(p, T + side * 7)) * a
                r = (0.9 + 0.45 * p["sz"]) * (1.25 if p["kind"] == 0 else 1.0) * (0.6 + 0.4 * sc / 0.8)
                self._dot(d, x, y, r, wing_color(p["d"]), min(1.0, k * (1.25 if p["kind"] == 0 else 1.0)))
        for p in self.BP:
            x = cx + p["x"] * sc + p["rx"] * off
            y = cy + p["y"] * sc + p["ry"] * off
            self._dot(d, x, y, (1.0 + 0.5 * p["sz"]) * sc / 0.8, (225, 255, 245), min(1.0, (0.55 + 0.45 * self._tw(p, T)) * a))
