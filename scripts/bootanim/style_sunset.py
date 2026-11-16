"""Sunset options with angular butterflies (round 6): the vapor-sunset sun and grid behind gem-cut shapes.

    sunset-crystal   cut-gem silhouette, faceted wings
    sunset-bolt      stealth-fighter silhouette with a swept, hexagonal-pod look
    sunset-shard     kite pod, huge spear-point wings and tails
    circuit-sunset   the circuit butterfly (traces + data pulses + glitch) in sunset pink and amber
"""
from PIL import Image, ImageDraw

from .core import SH, SW, WAX, WAY, WCH, WCW, mixc
from .style_circuit import CircuitGlitch
from .style_neon import tube
from .style_neon2 import NeonCircuit, NeonVariant, shrink
from .style_vapor import SunsetMixin, VaporMixin


class SunsetFacet(VaporMixin, SunsetMixin, NeonVariant):
    """Faceted gem look: triangle fills fanned from the thorax, chevron-ribbed shell, studs on every corner."""
    C1, C2 = (255, 80, 175, 255), (255, 178, 50, 255)
    FILL = (44, 0, 34, 100)
    aura_color, aura_k = (1.0, 0.45, 0.45), 0.16
    flash_color = (1.0, 0.75, 0.6)
    light_color = (70, 24, 30)
    blob_poly = 7

    def _stud(self, d, x, y, q, S, col):
        d.polygon([(x * S, (y - q) * S), ((x + q) * S, y * S), (x * S, (y + q) * S), ((x - q) * S, y * S)], fill=col)

    def chry_base(self, S):
        im = super().chry_base(S)
        d = ImageDraw.Draw(im)
        pt = self.shape.pt
        for k in range(10):                                                  # alternating facet bands
            s0, s1 = 0.04 + 0.095 * k, 0.04 + 0.095 * (k + 1)
            col = mixc(self.FILL[:3], (self.C1, self.C2)[k % 2][:3], 0.30) + (125,)
            d.polygon([(x * S, y * S) for x, y in (pt(s0, 0), pt(s1, -1), pt(s1, 0))], fill=col)
            d.polygon([(x * S, y * S) for x, y in (pt(s0, 0), pt(s1, 0), pt(s1, 1))], fill=col[:3] + (95,))
        return im

    def chry_inner(self, d, S):
        pt = self.shape.pt
        for k in range(8):
            s = 0.16 + 0.085 * k
            tube(d, [(x * S, y * S) for x, y in (pt(s, -1.05), pt(s + 0.07, 0), pt(s, 1.05))], self.C2[:3] + (210,), 2.6, S)
        tube(d, [(pt(k / 40, 0)[0] * S, pt(k / 40, 0)[1] * S) for k in range(2, 39)], self.C1[:3] + (190,), 2.4, S)

    def chry_edge(self, d, S):
        super().chry_edge(d, S)
        pt = self.shape.pt
        for s, w in self.shape.profile:
            for u in (-1, 1):
                x, y = pt(s, u)
                self._stud(d, x, y, 7, S, self.C2)

    def wing_base(self, g, S):
        im = super().wing_base(g, S)
        d = ImageDraw.Draw(im)
        bx, by = g["base"]
        c = g["ctrl"]
        for i in range(len(c) - 1):
            col = mixc(self.FILL[:3], (self.C1, self.C2)[i % 2][:3], 0.32) + (125,)
            d.polygon([(bx * S, by * S), (c[i][0] * S, c[i][1] * S), (c[i + 1][0] * S, c[i + 1][1] * S)], fill=col)
        return im

    def wing_inner(self, d, g, S):
        bx, by = g["base"]
        c = g["ctrl"]
        for x, y in c[1:-1]:
            tube(d, [(bx * S, by * S), (x * S, y * S)], self.C1[:3] + (175,), 2.4, S)
        tube(d, [(x * S, y * S) for x, y in shrink(c, g["base"], 0.62)], self.C2[:3] + (215,), 2.6, S, closed=True)
        tube(d, [(x * S, y * S) for x, y in shrink(c, g["base"], 0.82)], self.C2[:3] + (150,), 2.2, S, closed=True)

    def wing_edge(self, d, g, S):
        tube(d, [(x * S, y * S) for x, y in g["poly"]], self.C1, 6.5, S, closed=True)
        for x, y in g["ctrl"][1:-1]:
            self._stud(d, x, y, 8, S, self.C2)


class SunsetCrystal(SunsetFacet):
    name = "sunset-crystal"
    label = "Sunset: crystal"
    blurb = "Retro sun and grid behind a cut-gem butterfly with faceted wings."
    shape_name = "crystal"


class SunsetBolt(SunsetFacet):
    name = "sunset-bolt"
    label = "Sunset: bolt"
    blurb = "Retro sun and grid behind a stealth-fighter butterfly with a swept, hexagonal pod."
    shape_name = "bolt"


class SunsetShard(SunsetFacet):
    name = "sunset-shard"
    label = "Sunset: shard"
    blurb = "Retro sun and grid behind a kite pod and huge spear-point wings with long tails."
    shape_name = "shard"
    blob_poly = 4


class CircuitSunset(VaporMixin, SunsetMixin, NeonCircuit):
    name = "circuit-sunset"
    label = "Circuit: sunset (traces + glitch over the sun)"
    blurb = "The circuit butterfly in sunset pink and amber over the retro sun and grid, with glitch tearing."
    C1, C2 = (255, 90, 170, 255), (255, 190, 60, 255)
    FILL = (44, 0, 30, 100)
    aura_color, aura_k = (1.0, 0.45, 0.5), 0.16
    flash_color = (1.0, 0.75, 0.6)
    light_color = (70, 24, 30)
    pulse_color, pulse_hot = (255, 200, 90), (255, 250, 230)
    sun_k = 0.32
    ghost_alpha = 0.26
    glitch_seed = CircuitGlitch._glitch_seed
    tear_args = dict(strips=7, amp=46)


SUNSET_STYLES = [SunsetCrystal, SunsetBolt, SunsetShard, CircuitSunset]
