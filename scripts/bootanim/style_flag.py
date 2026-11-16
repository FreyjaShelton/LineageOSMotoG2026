"""Round 7: solid, flag-coloured sunset butterflies with angular shapes and big top wings.

The palette is the lesbian-flag stripes without the white one (dark orange, orange, light orange, orchid, rose, dark rose).
The sun is striped with them, the shell is six stripes down its length, and the wings carry the stripes top
to bottom (so the large forewings are the warm half and the small hindwings the pink half).
No fringing, scanlines or permanent trails: fills are opaque, outlines crisp, trails only during the spin.

    flag-shard   the shard, reworked: bigger forewings, sturdier tails
    flag-hawk    enormous forewings, small triangular hindwings
    flag-blade   forewings swept up and back like blades, hindwings reduced to two spurs
    flag-kite    big kite-shaped forewings over small rhombus hindwings
"""
from PIL import Image, ImageChops, ImageDraw

from .core import SH, SW, WCH, WCW, poly_mask
from .style_neon import tube
from .style_neon2 import NeonVariant, shrink
from .style_vapor import SunsetMixin

FLAG = [(213, 45, 0), (239, 118, 39), (255, 154, 86), (209, 98, 164), (181, 86, 144), (163, 2, 98)]
SOLID = 0.88                                    # stripe brightness (keeps the white outline reading as the brightest line)


def _dim(col, k=SOLID):
    return tuple(int(c * k) for c in col)


def _composite(base, poly, rgba, S, size):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).polygon([(x * S, y * S) for x, y in poly], fill=rgba)
    return Image.alpha_composite(base, layer)


class FlagFacet(SunsetMixin, NeonVariant):
    C1, C2 = (255, 240, 248, 255), (255, 170, 215, 255)
    aura_color, aura_k = (1.0, 0.55, 0.45), 0.14
    flash_color = (1.0, 0.85, 0.8)
    light_color = (30, 10, 8)
    body_fill = (44, 8, 30, 240)
    blob_c1 = (239, 118, 39, 255)
    blob_poly = 7
    png_colors = 0                                  # full-colour frames: smooth glows without banding or flicker
    glow = 0.36
    sun_k = 0.30
    sun_stops = FLAG
    grid_color = (181, 86, 144)
    ghosts, ghost_dt, ghost_alpha, ghosts_always = 3, 1.6, 0.22, False

    @staticmethod
    def _stud(d, x, y, q, S, col):
        d.polygon([(x * S, (y - q) * S), ((x + q) * S, y * S), (x * S, (y + q) * S), ((x - q) * S, y * S)], fill=col)

    # -- shell: six stripes down its length, right half shaded for a cut-gem look -----------------------------
    def chry_base(self, S):
        size = (SW * S, SH * S)
        im = Image.new("RGBA", size, (0, 0, 0, 0))
        pt = self.shape.pt
        n, steps = len(FLAG), 24
        for i, col in enumerate(FLAG):
            s0, s1 = i / n, (i + 1) / n
            left = [pt(s0 + (s1 - s0) * k / steps, -1) for k in range(steps + 1)]
            right = [pt(s0 + (s1 - s0) * k / steps, 1) for k in range(steps + 1)]
            im = _composite(im, left + right[::-1], _dim(col) + (240,), S, size)
        half = [pt(k / 60, 0) for k in range(61)] + [pt(k / 60, 1) for k in range(60, -1, -1)]
        shade = _composite(Image.new("RGBA", size, (0, 0, 0, 0)), half, (0, 0, 0, 62), S, size)
        shade.putalpha(ImageChops.multiply(shade.getchannel("A"), im.getchannel("A")))
        return Image.alpha_composite(im, shade)

    def chry_inner(self, d, S):
        pt = self.shape.pt
        for k in range(8):
            s = 0.14 + 0.095 * k
            tube(d, [(x * S, y * S) for x, y in (pt(s, -1.05), pt(s + 0.07, 0), pt(s, 1.05))], self.C1[:3] + (150,), 2.4, S)
        tube(d, [(pt(k / 40, 0)[0] * S, pt(k / 40, 0)[1] * S) for k in range(2, 39)], self.C1[:3] + (130,), 2.2, S)

    def chry_edge(self, d, S):
        super().chry_edge(d, S)
        pt = self.shape.pt
        for s, w in self.shape.profile:
            for u in (-1, 1):
                x, y = pt(s, u)
                self._stud(d, x, y, 6.5, S, self.C1)

    # -- wings: flag stripes top to bottom across the whole butterfly, fan facets shaded --------------------------
    def wing_base(self, g, S):
        size = (WCW * S, WCH * S)
        mask = poly_mask(g["poly"], S)
        stripes = Image.new("RGBA", size, (0, 0, 0, 0))
        d = ImageDraw.Draw(stripes)
        h = 700 / len(FLAG)
        for i, col in enumerate(FLAG):
            y0 = 0 if i == 0 else i * h
            y1 = WCH if i == len(FLAG) - 1 else (i + 1) * h
            d.rectangle([0, y0 * S, WCW * S, y1 * S], fill=_dim(col) + (240,))
        stripes.putalpha(ImageChops.multiply(stripes.getchannel("A"), mask))
        shade = Image.new("RGBA", size, (0, 0, 0, 0))
        ds = ImageDraw.Draw(shade)
        bx, by = g["base"]
        c = g["ctrl"]
        for i in range(len(c) - 1):
            if i % 2:
                ds.polygon([(bx * S, by * S), (c[i][0] * S, c[i][1] * S), (c[i + 1][0] * S, c[i + 1][1] * S)], fill=(0, 0, 0, 66))
        shade.putalpha(ImageChops.multiply(shade.getchannel("A"), mask))
        return Image.alpha_composite(stripes, shade)

    def wing_inner(self, d, g, S):
        bx, by = g["base"]
        c = g["ctrl"]
        for x, y in c[1:-1]:
            tube(d, [(bx * S, by * S), (x * S, y * S)], self.C1[:3] + (150,), 2.2, S)
        tube(d, [(x * S, y * S) for x, y in shrink(c, g["base"], 0.70)], self.C1[:3] + (120,), 2.2, S, closed=True)

    def wing_edge(self, d, g, S):
        tube(d, [(x * S, y * S) for x, y in g["poly"]], self.C1, 6.5, S, closed=True)
        for x, y in g["ctrl"][1:-1]:
            self._stud(d, x, y, 7, S, self.C1)


class FlagShard(FlagFacet):
    name = "flag-shard"
    label = "Flag sunset: shard"
    blurb = "Sunset shard, reworked: bigger forewings, sturdier tails, solid flag-stripe fills, no flicker."
    shape_name = "shard2"
    blob_poly = 4


class FlagHawk(FlagFacet):
    name = "flag-hawk"
    label = "Flag sunset: hawk"
    blurb = "Enormous forewings over small triangular hindwings."
    shape_name = "hawk"


class FlagBlade(FlagFacet):
    name = "flag-blade"
    label = "Flag sunset: blade"
    blurb = "Forewings swept up and back like blades; hindwings reduced to two spurs."
    shape_name = "blade"
    blob_poly = 5


class FlagKite(FlagFacet):
    name = "flag-kite"
    label = "Flag sunset: kite"
    blurb = "Big kite-shaped forewings over small rhombus hindwings."
    shape_name = "kite"
    blob_poly = 4


FLAG_STYLES = [FlagShard, FlagHawk, FlagBlade, FlagKite]
