"""Vapor options (round 5). Four takes on the round pink/amber light-painting butterfly:

    vapor          original: hot pink + amber, round barrel shell, afterimage trails, RGB fringing, scanlines
    vapor-sunset   synthwave: a striped retro sun rises behind the butterfly over a scrolling perspective grid
    vapor-lilac    cyan + lilac swallowtail drawn as horizontal scan-bands, long trailing echoes
    vapor-vhs      worn tape: heavy RGB split, tearing strips, a rolling glow bar, tracking noise
"""
from PIL import ImageChops

from .core import CX, FINAL_Y, T_MELT0, T_MELT1, T_SPIN0, SH, SW, blit, intro_state, smooth
from .fx import chroma, perspective_grid, retro_sun, roll_bar, scanlines, tear
from .style_neon import NeonStyle, tube
from .style_neon2 import NeonVariant


class VaporMixin:
    particles = False
    ghosts, ghost_dt, ghost_alpha, ghosts_always = 5, 2.3, 0.30, True
    fringe = 5
    scan_depth = 50

    def build(self):
        super().build()
        self.scan = scanlines(self.scan_depth)

    def chrysalis(self, fr, st):
        if st.shell and st.yoff > 4:                                         # afterimages while rising
            for k in range(6, 0, -1):
                p = intro_state(st.t - 1.7 * k)
                if abs(p.yoff - st.yoff) < 3:
                    continue
                blit(fr, self.CHRY, self.shape.anchor, (CX + p.jx, 800 + p.yoff + p.jy), angle=p.sway, scale=p.scale,
                     alpha=0.20 * (1 - k / 7))
        super().chrysalis(fr, st)

    def glitch_seed(self, st):
        return None

    def post(self, fr, st):
        fr = super().post(fr, st)
        seed = self.glitch_seed(st)
        if seed is not None:
            fr = tear(fr, seed, **self.tear_args)
        fr = chroma(fr, self.fringe + (3 if seed is not None else 0))
        return ImageChops.multiply(fr, self.scan)

    tear_args = dict(strips=5, amp=40)


class VaporPink(VaporMixin, NeonStyle):
    name = "vapor"
    label = "Vapor (pink + amber)"
    blurb = "Round barrel shell and round wings in hot pink and amber, light-painting trails, RGB fringing, scanlines."
    shape_name = "vapor"
    C1, C2 = (255, 70, 190, 255), (255, 196, 60, 255)
    FILL = (44, 0, 30, 96)
    aura_color, aura_k = (1.0, 0.35, 0.7), 0.22
    flash_color = (1.0, 0.7, 0.8)
    light_color = (70, 20, 40)


class SunsetMixin:
    """Striped synthwave sun rising behind the butterfly, over a scrolling perspective grid."""
    glow = 0.5
    sun_k = 0.36
    grid_color = (255, 60, 190)
    sun_stops = None
    sun_top, sun_bot = (255, 214, 70), (255, 40, 150)
    grid_k = 0.55
    grid_thick = False                  # True: grid lines get thicker toward the bottom of the screen

    def background(self, fr, st):
        fade = smooth(0, 60, st.t)
        vis = smooth(T_MELT0 + 10, T_MELT1 + 14, st.t)
        perspective_grid(fr, st.T, 1190, self.grid_color, self.grid_k * fade, thick=self.grid_thick)
        retro_sun(fr, CX, FINAL_Y - 10, 270 * (0.82 + 0.18 * vis), st.T, self.sun_top, self.sun_bot, self.sun_k * vis, stops=self.sun_stops,
                  ramp=getattr(self, 'sun_color', None))
        super().background(fr, st)


class VaporSunset(VaporMixin, SunsetMixin, NeonStyle):
    name = "vapor-sunset"
    label = "Vapor: sunset (retro sun + grid)"
    blurb = "A striped synthwave sun rises behind the butterfly over a scrolling perspective grid."
    shape_name = "vapor"
    C1, C2 = (255, 80, 175, 255), (255, 178, 50, 255)
    FILL = (44, 0, 34, 100)
    aura_color, aura_k = (1.0, 0.45, 0.45), 0.16
    flash_color = (1.0, 0.75, 0.6)
    light_color = (70, 24, 30)
    ghost_alpha = 0.26


class VaporLilac(VaporMixin, NeonVariant):
    name = "vapor-lilac"
    label = "Vapor: lilac (cyan + lilac scan-bands)"
    blurb = "Swallowtail drawn as horizontal scan-bands in cyan and lilac, with long trailing echoes."
    shape_name = "stardust"
    C1, C2 = (70, 235, 255, 255), (200, 130, 255, 255)
    FILL = (10, 8, 40, 100)
    aura_color, aura_k = (0.55, 0.55, 1.0), 0.22
    flash_color = (0.8, 0.8, 1.0)
    light_color = (30, 30, 80)
    ghosts, ghost_dt, ghost_alpha = 7, 2.0, 0.28
    fringe = 4

    def chry_inner(self, d, S):
        pt = self.shape.pt
        for k in range(26):
            s = 0.05 + 0.036 * k
            col = (self.C1 if k % 2 == 0 else self.C2)[:3] + (170,)
            a, b = pt(s, -1.1), pt(s, 1.1)
            tube(d, [(a[0] * S, a[1] * S), (b[0] * S, b[1] * S)], col, 2.4, S)

    def chry_edge(self, d, S):
        pt = self.shape.pt
        tube(d, [(x * S, y * S) for x, y in self.shape.outline()], self.C1, 7, S, closed=True)
        inner = [pt(i / 100, -0.88) for i in range(7, 94)] + [pt(i / 100, 0.88) for i in range(93, 6, -1)]
        tube(d, [(x * S, y * S) for x, y in inner], self.C2[:3] + (235,), 2.6, S, closed=True)

    def wing_inner(self, d, g, S):
        bx, by = g["base"]
        for n, y in enumerate(range(0, 830, 19)):
            col = (self.C1 if n % 2 == 0 else self.C2)[:3] + (150,)
            tube(d, [(bx * S, y * S), (480 * S, y * S)], col, 2.2, S)

    def wing_edge(self, d, g, S):
        tube(d, [(x * S, y * S) for x, y in g["poly"]], self.C1, 6.5, S, closed=True)
        tube(d, [(x * S, y * S) for x, y in _shrunk(g["poly"], g["base"], 0.93)], self.C2[:3] + (235,), 2.6, S, closed=True)


def _shrunk(poly, c, k):
    return [(c[0] + (x - c[0]) * k, c[1] + (y - c[1]) * k) for x, y in poly]


class VaporVHS(VaporMixin, NeonStyle):
    name = "vapor-vhs"
    label = "Vapor: VHS (tape glitch)"
    blurb = "Worn tape: heavy RGB split, tearing strips, a rolling glow bar and tracking noise at the bottom."
    shape_name = "vapor"
    C1, C2 = (255, 120, 205, 255), (110, 205, 255, 255)
    FILL = (30, 0, 36, 100)
    aura_color, aura_k = (0.85, 0.5, 1.0), 0.20
    flash_color = (0.95, 0.8, 1.0)
    light_color = (50, 20, 70)
    fringe = 9
    scan_depth = 70
    tear_args = dict(strips=6, amp=54)

    def glitch_seed(self, st):
        if st.loop:
            j = int(st.j)
            return j if (j % 40 < 3 or 62 <= j <= 64) else None
        t = st.t
        if t % 40 < 3 or T_MELT1 - 4 <= t <= T_MELT1 + 3 or T_SPIN0 <= t <= T_SPIN0 + 16:
            return int(t * 2)
        return None

    def post(self, fr, st):
        roll_bar(fr, st.T, 0.12)
        fr = super().post(fr, st)
        return tear(fr, int(st.T * 2) + 77, strips=2, amp=26, y_lo=1480, y_hi=1560, hmin=4, hmax=14)


VAPOR_STYLES = [VaporPink, VaporSunset, VaporLilac, VaporVHS]
