"""Neon round 4: five drastic reworks of the clean (particle-free) neon style.

Each changes the silhouette, the palette, the interior pattern and adds an
animated extra, so they are genuinely different directions, not tweaks:

    circuit   angular gem-cut shapes, green + magenta, circuit-board traces, data pulses racing along them
    deco      ornate long-tailed shapes, gold + emerald, sunburst fans and chevrons, light glints on the edges
    aurora    swallowtail, lime->teal->violet->magenta, nested echo outlines with glowing fills, hue shimmer
    sonar     broad classic wings, ice blue, halftone dot-matrix shading, expanding ripple rings
"""
import math

from PIL import Image, ImageChops, ImageDraw

from .core import LOOP_UNITS, yaw_factors, RS, SH, SW, SX, SY, WAX, WAY, WCH, WCW, clamp, lerp, mixc, poly_mask
from .style_neon import NeonStyle, dot, tube


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def make_path(pts):
    cum, tot = [0.0], 0.0
    for a, b in zip(pts, pts[1:]):
        tot += math.hypot(b[0] - a[0], b[1] - a[1])
        cum.append(tot)
    return dict(pts=pts, cum=cum, total=tot)


def path_point(P, u):
    t = (u % 1.0) * P["total"]
    cum, pts = P["cum"], P["pts"]
    i = 0
    while i < len(pts) - 2 and cum[i + 1] < t:
        i += 1
    seg = cum[i + 1] - cum[i]
    f = (t - cum[i]) / seg if seg else 0
    return (lerp(pts[i][0], pts[i + 1][0], f), lerp(pts[i][1], pts[i + 1][1], f))


def centroid(poly):
    return (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))


def shrink(poly, c, k):
    return [(c[0] + (x - c[0]) * k, c[1] + (y - c[1]) * k) for x, y in poly]


def ramp_stops(stops, t):
    t = clamp(t)
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if t <= b:
            return mixc(ca, cb, (t - a) / (b - a))
    return stops[-1][1]


class NeonVariant(NeonStyle):
    """Template: base fill / clipped inner pattern / bold edge, for both chrysalis and wings."""
    particles = False
    PATHS = ()
    pulse_color = (255, 255, 255)
    pulse_hot = (255, 255, 255)
    pulse_tail, pulse_step, pulse_size = 5, 0.014, 4.5
    pulse_phases = ((0.0, 1),)               # (phase, laps per loop) per path

    # hooks (S = supersample factor; coordinates are sprite/canvas coords, multiply by S to draw)
    def chry_base(self, S):
        im = Image.new("RGBA", (SW * S, SH * S), (0, 0, 0, 0))
        ImageDraw.Draw(im).polygon([(x * S, y * S) for x, y in self.shape.outline()], fill=self.FILL)
        return im

    def chry_inner(self, d, S):
        pass

    def chry_edge(self, d, S):
        pts = [(x * S, y * S) for x, y in self.shape.outline()]
        tube(d, pts, self.C1, 7, S, closed=True)

    def wing_base(self, g, S):
        im = Image.new("RGBA", (WCW * S, WCH * S), (0, 0, 0, 0))
        ImageDraw.Draw(im).polygon([(x * S, y * S) for x, y in g["poly"]], fill=self.FILL)
        return im

    def wing_inner(self, d, g, S):
        pass

    def wing_edge(self, d, g, S):
        tube(d, [(x * S, y * S) for x, y in g["poly"]], self.C1, 6.5, S, closed=True)
        for x, y, r in g["dots"]:
            if r > 2:
                dot(d, x, y, r * 1.45, self.C1, S)

    # builders
    def build_chrysalis(self):
        S = 3
        mk = lambda: Image.new("RGBA", (SW * S, SH * S), (0, 0, 0, 0))
        base = self.chry_base(S)
        inner = mk()
        self.chry_inner(ImageDraw.Draw(inner), S)
        m = Image.new("L", (SW * S, SH * S), 0)
        ImageDraw.Draw(m).polygon([(x * S, y * S) for x, y in self.shape.outline()], fill=255)
        inner.putalpha(ImageChops.multiply(inner.getchannel("A"), m))
        edge = mk()
        self.chry_edge(ImageDraw.Draw(edge), S)
        return Image.alpha_composite(Image.alpha_composite(base, inner), edge).resize((SW, SH), RS.LANCZOS)

    def build_wing(self):
        S = 2
        self.PATHS = []
        wing = Image.new("RGBA", (WCW, WCH), (0, 0, 0, 0))
        for g in self.shape.wing_geom:
            base = self.wing_base(g, S)
            inner = Image.new("RGBA", (WCW * S, WCH * S), (0, 0, 0, 0))
            self.wing_inner(ImageDraw.Draw(inner), g, S)
            inner.putalpha(ImageChops.multiply(inner.getchannel("A"), poly_mask(g["poly"], S)))
            edge = Image.new("RGBA", (WCW * S, WCH * S), (0, 0, 0, 0))
            self.wing_edge(ImageDraw.Draw(edge), g, S)
            layer = Image.alpha_composite(Image.alpha_composite(base, inner), edge)
            wing = Image.alpha_composite(wing, layer.resize((WCW, WCH), RS.LANCZOS))
        return wing

    # animated pulses travelling along self.PATHS (right-wing coords relative to the thorax)
    def draw_pulses(self, fr, st, bf):
        if not self.PATHS:
            return
        cx, cy, sc, f, a = bf
        syf = 0.92 + 0.08 * f
        side, wd, near, far = yaw_factors(st.spin)
        d = ImageDraw.Draw(fr)
        for i, P in enumerate(self.PATHS):
            for ph, laps in self.pulse_phases:
                u0 = (st.T / LOOP_UNITS * laps + ph + i * 0.173) % 1.0
                for t in range(self.pulse_tail):
                    px, py = path_point(P, u0 - t * self.pulse_step)
                    k = (1 - t / self.pulse_tail) * a
                    col = tuple(int(c * k) for c in (self.pulse_hot if t == 0 else self.pulse_color))
                    r = max(1.5, self.pulse_size * (1 - 0.8 * t / self.pulse_tail) * (0.6 + 0.4 * sc / 0.8))
                    for wside, ps in ((-side, far), (side, near)):
                        x, y = cx + wside * px * sc * f * wd * ps, cy + py * sc * syf * ps
                        d.ellipse([x - r, y - r, x + r, y + r], fill=col)

    def draw_bf(self, fr, bf, st, main=True):
        super().draw_bf(fr, bf, st, main)
        if main:
            self.draw_pulses(fr, st, bf)


# ===========================================================================
# 1. CIRCUIT
# ===========================================================================
def circuit_path(B, E, lane):
    bx, by = B
    ex, ey = E
    dx, dy = ex - bx, ey - by
    sx, sy = (1 if dx >= 0 else -1), (1 if dy >= 0 else -1)
    y0 = by + lane
    x1 = bx + dx * 0.36
    t = min(abs(ey - y0) * 0.85, abs(ex - x1) * 0.7)
    p2 = (x1 + sx * t, y0 + sy * t)
    return [(bx, y0), (x1, y0), p2, (ex, p2[1]), (ex, ey)]


class NeonCircuit(NeonVariant):
    name = "circuit"
    label = "Circuit (angular, green + magenta)"
    blurb = "Gem-cut angular shapes with circuit-board traces and data pulses racing through them."
    shape_name = "crystal"
    C1, C2 = (120, 255, 70, 255), (255, 60, 200, 255)
    FILL = (0, 34, 18, 96)
    aura_color, aura_k = (0.35, 1.0, 0.3), 0.20
    flash_color = (0.8, 0.5, 0.9)
    crack_glow, crack_core = (255, 60, 200, 130), (255, 235, 250, 255)
    light_color = (60, 20, 70)
    pulse_color, pulse_hot = (255, 70, 210), (255, 240, 255)
    pulse_tail, pulse_step, pulse_size = 6, 0.012, 5.0
    pulse_phases = ((0.0, 1), (0.5, 2))

    def chry_inner(self, d, S):
        pt = self.shape.pt
        sc = lambda p: (p[0] * S, p[1] * S)
        for u in (-0.55, 0.0, 0.55):
            tube(d, [sc(pt(k / 40, u)) for k in range(5, 37)], self.C2[:3] + (210,), 2.8, S)
            for s in (0.2, 0.34, 0.48, 0.62, 0.76):
                x, y = pt(s, u)
                d.rectangle([(x - 5) * S, (y - 5) * S, (x + 5) * S, (y + 5) * S], fill=self.C1)
        for s, u0, u1 in ((0.27, -0.55, 0), (0.41, 0, 0.55), (0.55, -0.55, 0), (0.69, 0, 0.55), (0.83, -0.55, 0)):
            tube(d, [sc(pt(s, u0)), sc(pt(s, u1))], self.C1[:3] + (230,), 2.8, S)

    def chry_edge(self, d, S):
        super().chry_edge(d, S)
        pt = self.shape.pt
        for s, w in self.shape.profile:
            for u in (-1, 1):
                x, y = pt(s, u)
                d.rectangle([(x - 6) * S, (y - 6) * S, (x + 6) * S, (y + 6) * S], fill=self.C1)

    def wing_inner(self, d, g, S):
        B = g["base"]
        ends = [pl[-1] for pl in g["veins"] if len(pl) == 3]
        n = len(ends)
        for i, E in enumerate(ends):
            path = circuit_path(B, E, (i - n / 2) * 3.2)
            tube(d, [(x * S, y * S) for x, y in path], self.C2[:3] + (225,), 3.0, S)
            self.PATHS.append(make_path([(x - WAX, y - WAY) for x, y in path]))
            ex, ey = E
            d.ellipse([(ex - 7) * S, (ey - 7) * S, (ex + 7) * S, (ey + 7) * S], outline=self.C1, width=int(3 * S))

    def wing_edge(self, d, g, S):
        tube(d, [(x * S, y * S) for x, y in g["poly"]], self.C1, 6.5, S, closed=True)
        for x, y, r in g["dots"]:
            if r > 2:
                q = r * 1.5
                d.rectangle([(x - q) * S, (y - q) * S, (x + q) * S, (y + q) * S], fill=self.C1)


# ===========================================================================
# 2. DECO
# ===========================================================================
class NeonDeco(NeonVariant):
    name = "deco"
    label = "Deco (ornate, gold + emerald)"
    blurb = "Long-tailed ornate shapes in gold and emerald: double outlines, sunburst fans, chevrons, edge glints."
    shape_name = "stardust"
    C1, C2 = (255, 196, 60, 255), (40, 255, 170, 255)
    FILL = (0, 38, 26, 100)
    aura_color, aura_k = (1.0, 0.75, 0.25), 0.20
    flash_color = (1.0, 0.9, 0.5)
    crack_glow, crack_core = (255, 200, 60, 130), (255, 248, 215, 255)
    light_color = (60, 50, 8)
    pulse_color, pulse_hot = (255, 214, 110), (255, 255, 235)
    pulse_tail, pulse_step, pulse_size = 8, 0.008, 5.0
    pulse_phases = ((0.0, 1), (0.5, 1))

    def chry_inner(self, d, S):
        pt = self.shape.pt
        sc = lambda p: (p[0] * S, p[1] * S)
        for k in range(8):
            s = 0.22 + 0.085 * k
            tube(d, [sc(pt(s, -0.92)), sc(pt(s + 0.055, 0)), sc(pt(s, 0.92))], self.C1[:3] + (215,), 3.0, S)
        tube(d, [sc(pt(k / 40, 0)) for k in range(3, 38)], self.C2[:3] + (170,), 2.4, S)

    def chry_edge(self, d, S):
        pt = self.shape.pt
        out = [(x * S, y * S) for x, y in self.shape.outline()]
        tube(d, out, self.C1, 7, S, closed=True)
        inner = [pt(i / 100, -0.86) for i in range(6, 95)] + [pt(i / 100, 0.86) for i in range(94, 5, -1)]
        tube(d, [(x * S, y * S) for x, y in inner], self.C2[:3] + (230,), 2.6, S, closed=True)
        for k in range(-4, 5):
            x, y = pt(0.17 + 0.02 * (1 - (k * 0.2) ** 2), k * 0.2)
            q = 6
            d.polygon([(x * S, (y - q) * S), ((x + q) * S, y * S), (x * S, (y + q) * S), ((x - q) * S, y * S)], fill=self.C1)

    def wing_inner(self, d, g, S):
        bx, by = g["base"]
        angs = [math.atan2(y - by, x - bx) for x, y in g["poly"]]
        a0, a1 = min(angs) - 0.05, max(angs) + 0.05
        n = int((a1 - a0) / 0.085)
        for i in range(n + 1):
            a = a0 + (a1 - a0) * i / n
            tube(d, [((bx + math.cos(a) * 50) * S, (by + math.sin(a) * 50) * S),
                     ((bx + math.cos(a) * 520) * S, (by + math.sin(a) * 520) * S)], self.C1[:3] + (150,), 1.8, S)
        for j, r in enumerate(range(80, 520, 64)):
            arc = [((bx + math.cos(a0 + (a1 - a0) * i / 40) * r) * S, (by + math.sin(a0 + (a1 - a0) * i / 40) * r) * S)
                   for i in range(41)]
            tube(d, arc, self.C2[:3] + (205,), 2.8 if j % 2 else 2.0, S)

    def wing_edge(self, d, g, S):
        tube(d, [(x * S, y * S) for x, y in g["poly"]], self.C1, 6.5, S, closed=True)
        tube(d, [(x * S, y * S) for x, y in shrink(g["poly"], g["base"], 0.94)], self.C2[:3] + (235,), 2.6, S, closed=True)
        for x, y, r in g["dots"]:
            if r > 2:
                q = r * 1.9
                d.polygon([(x * S, (y - q) * S), ((x + q) * S, y * S), (x * S, (y + q) * S), ((x - q) * S, y * S)], fill=self.C1)
        self.PATHS.append(make_path([(x - WAX, y - WAY) for x, y in g["poly"]] + [(g["poly"][0][0] - WAX, g["poly"][0][1] - WAY)]))


# ===========================================================================
# 3. AURORA
# ===========================================================================
AURORA = [(0.0, (140, 255, 60)), (0.3, (0, 255, 190)), (0.55, (60, 170, 255)), (0.8, (170, 100, 255)), (1.0, (255, 80, 210))]
LEVELS = (1.0, 0.84, 0.69, 0.55, 0.42, 0.30)


class NeonAurora(NeonVariant):
    name = "aurora"
    label = "Aurora (gradient echo lines)"
    blurb = "Swallowtail drawn as nested echo outlines with a glowing lime-teal-violet-magenta gradient."
    shape_name = "neon"
    C1, C2 = (140, 255, 60, 255), (0, 255, 190, 255)
    aura_color, aura_k = (0.25, 0.8, 0.9), 0.24
    flash_color = (0.7, 0.8, 1.0)
    crack_glow, crack_core = (150, 140, 255, 130), (245, 240, 255, 255)
    light_color = (30, 30, 70)
    shimmer = 11                                    # hue shimmer amplitude (0..255 scale)

    @staticmethod
    def _level_color(k):
        return ramp_stops(AURORA, (1 - k) / 0.7)

    def _stack_fill(self, poly, c, S, size):
        base = Image.new("RGBA", size, (0, 0, 0, 0))
        for k in LEVELS:
            tmp = Image.new("RGBA", size, (0, 0, 0, 0))
            col = self._level_color(k)
            ImageDraw.Draw(tmp).polygon([(x * S, y * S) for x, y in shrink(poly, c, k)], fill=col + (44,))
            base = Image.alpha_composite(base, tmp)
        return base

    def _echo(self, d, poly, c, S, widths):
        for k, w in zip(LEVELS, widths):
            col = self._level_color(k)
            alpha = 255 if k == 1.0 else int(120 + 110 * k)
            tube(d, [(x * S, y * S) for x, y in shrink(poly, c, k)], col + (alpha,), w, S, closed=True)

    def chry_base(self, S):
        return self._stack_fill(self.shape.outline(), self.shape.anchor, S, (SW * S, SH * S))

    def chry_inner(self, d, S):
        self._echo(d, self.shape.outline(), self.shape.anchor, S, (0, 3.2, 3.0, 2.8, 2.6, 2.4))

    def chry_edge(self, d, S):
        tube(d, [(x * S, y * S) for x, y in self.shape.outline()], self._level_color(1.0) + (255,), 7, S, closed=True)

    def wing_base(self, g, S):
        return self._stack_fill(g["poly"], centroid(g["poly"]), S, (WCW * S, WCH * S))

    def wing_inner(self, d, g, S):
        self._echo(d, g["poly"], centroid(g["poly"]), S, (0, 3.4, 3.1, 2.8, 2.5, 2.2))

    def wing_edge(self, d, g, S):
        tube(d, [(x * S, y * S) for x, y in g["poly"]], self._level_color(1.0) + (255,), 6.5, S, closed=True)
        for x, y, r in g["dots"]:
            if r > 2:
                dot(d, x, y, r * 1.3, self._level_color(0.9) + (255,), S)

    def post(self, fr, st):
        fr = super().post(fr, st)
        sh = int(round(self.shimmer * math.sin(2 * math.pi * st.T / LOOP_UNITS)))
        if sh == 0:
            return fr
        h, s, v = fr.convert("HSV").split()
        h = h.point([(i + sh) % 256 for i in range(256)])
        return Image.merge("HSV", (h, s, v)).convert("RGB")


# ===========================================================================
# 4. SONAR
# ===========================================================================
class NeonSonar(NeonVariant):
    name = "sonar"
    label = "Sonar (ice blue halftone + ripples)"
    blurb = "Broad classic wings shaded with a dot-matrix halftone, ice-blue, with sonar ripples spreading out."
    shape_name = "default"
    glow = 0.42
    C1, C2 = (90, 235, 255, 255), (40, 130, 255, 255)
    FILL = (0, 20, 44, 100)
    aura_color, aura_k = (0.2, 0.6, 1.0), 0.22
    flash_color = (0.6, 0.85, 1.0)
    crack_glow, crack_core = (90, 200, 255, 130), (235, 250, 255, 255)
    light_color = (20, 60, 90)

    def _halftone(self, d, S, x0, x1, y0, y1, sp, rfun):
        j = 0
        y = y0
        while y < y1:
            off = sp / 2 if j % 2 else 0
            x = x0 + off
            while x < x1:
                r = rfun(x, y)
                if r > 1.2:
                    hot = (int(x / sp) + j) % 7 == 0
                    col = (225, 250, 255, 255) if hot else self.C1
                    d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=col)
                x += sp
            y += sp * 0.866
            j += 1

    def chry_inner(self, d, S):
        sh = self.shape
        sp = 19.0

        def r(x, y):
            xc = SX + sh.c((y - SY) / sh.L)
            return 8.5 * max(0.0, 1 - abs(x - xc) / sh.R) ** 0.7
        self._halftone(d, S, SX - sh.R - 20, SX + sh.R + 50, SY, SY + sh.L, sp, r)

    def wing_inner(self, d, g, S):
        bx, by = g["base"]

        def r(x, y):
            dist = math.hypot(x - bx, (y - by) * 0.9)
            return 11.5 * max(0.0, 1 - dist / 400) ** 0.85
        self._halftone(d, S, bx, WCW, 0, WCH, 25.0, r)

    def wing_edge(self, d, g, S):
        tube(d, [(x * S, y * S) for x, y in g["poly"]], self.C1, 6.5, S, closed=True)

    def background(self, fr, st):
        super().background(fr, st)
        k = st.mote_k
        if k <= 0.02:
            return
        d = ImageDraw.Draw(fr)
        for n in range(3):                                    # period 40 divides the 120-unit loop
            ph = ((st.T / 40.0) + n / 3.0) % 1.0
            rad = 70 + ph * 430
            a = (1 - ph) ** 1.6 * k * 0.95
            col = tuple(int(c * a) for c in (self.C1 if n % 2 == 0 else self.C2)[:3])
            d.ellipse([st.aura_x - rad, st.aura_y - rad, st.aura_x + rad, st.aura_y + rad], outline=col, width=3)
