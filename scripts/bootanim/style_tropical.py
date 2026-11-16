"""Round 10: variations on vivid-tropical with the white outline replaced by palette colours.

Shape, fills, sun, grid and timing are the same as vivid-tropical (coral -> hot pink -> violet); what changes is the
colour of every line that used to be white (outlines, ribs, studs, antennae, melt rim) and small palette nudges.

    trop-pink       hot-pink outline
    trop-lilac      lilac outline, violet grid
    trop-gold       amber outline over a more orange top half
    trop-gradient   outline follows the wing's gradient, shifted toward the next colour (pink on top, violet below)
    trop-duo        two-tone: amber on the big top wings, lilac on the small bottom wings, pink shell
"""
from .core import mixc
from .style_dusk import _ramp
from .style_flag import FlagFacet
from .style_neon import tube
from .style_vivid import VividTropical


class Tropical(VividTropical):
    """Base for the variants. edge_color(y, fore) may vary the wing outline colour; default is the single C1."""

    def edge_color(self, y, fore):
        return self.C1[:3]

    uniform_edge = True

    def wing_edge(self, d, g, S):
        if self.uniform_edge:
            return FlagFacet.wing_edge(self, d, g, S)
        fore = g is self.shape.wing_geom[1]
        poly = g["poly"]
        pts = poly + [poly[0]]
        w = 6.5
        r = w * S / 2
        for a, b in zip(pts, pts[1:]):
            col = self.edge_color((a[1] + b[1]) / 2, fore) + (255,)
            tube(d, [(a[0] * S, a[1] * S), (b[0] * S, b[1] * S)], col, w, S)
            d.ellipse([a[0] * S - r, a[1] * S - r, a[0] * S + r, a[1] * S + r], fill=col)
        for x, y in g["ctrl"][1:-1]:
            self._stud(d, x, y, 7, S, self.edge_color(y, fore) + (255,))


class TropPink(Tropical):
    name = "trop-pink"
    label = "Tropical: hot-pink outline"
    blurb = "Vivid tropical with a hot-pink outline."
    C1, C2 = (255, 178, 218, 255), (255, 205, 232, 255)


class TropLilac(Tropical):
    name = "trop-lilac"
    label = "Tropical: lilac outline"
    blurb = "Vivid tropical with a lilac outline and a violet floor grid."
    C1, C2 = (232, 192, 255, 255), (245, 215, 255, 255)
    grid_color = (150, 90, 255)


class TropGold(Tropical):
    name = "trop-gold"
    label = "Tropical: amber outline"
    blurb = "A more orange top half with an amber outline."
    RAMP = [(255, 150, 40), (255, 50, 140), (190, 60, 255)]
    SUN_RAMP = [(255, 200, 60), (255, 90, 80), (230, 40, 170), (130, 40, 210)]
    C1, C2 = (255, 200, 90, 255), (255, 225, 150, 255)
    blob_c1 = (255, 150, 40, 255)


class TropGradient(Tropical):
    name = "trop-gradient"
    label = "Tropical: gradient outline"
    blurb = "The outline follows the wing gradient, shifted toward the next colour: pink on top, violet below."
    C1, C2 = (255, 170, 215, 255), (255, 205, 232, 255)
    uniform_edge = False

    def edge_color(self, y, fore):
        return mixc(_ramp(self.RAMP, y / 700 + 0.5), (255, 255, 255), 0.42)


class TropDuo(Tropical):
    name = "trop-duo"
    label = "Tropical: two-tone outline"
    blurb = "Amber outline on the big top wings, lilac on the small bottom wings, pink on the shell."
    C1, C2 = (255, 178, 218, 255), (255, 205, 232, 255)
    uniform_edge = False

    def edge_color(self, y, fore):
        return (255, 205, 100) if fore else (232, 192, 255)


TROPICAL_STYLES = [TropPink, TropLilac, TropGold, TropGradient, TropDuo]
