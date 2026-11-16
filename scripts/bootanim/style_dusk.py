"""Round 8: the sunset shard in subtle, muted pink-and-amber palettes.

Same angular shard silhouette as flag-shard (big forewings, sturdy tails), solid fills and crisp outlines, full-colour
frames (no flicker or banding), but a soft vertical gradient instead of stripes: warm on the big top wings, rose on
the small bottom wings, with the sun and floor grid toned to match. The grid lines thicken toward the bottom.

    dusk-rose    amber -> coral -> rose, closest to the original sunset
    dusk-peach   peach -> blush -> mauve, the softest
    dusk-gold    rose gold -> dusty rose -> deep rose, the warmest
"""
from PIL import Image, ImageChops, ImageDraw

from .core import SH, SW, WCH, WCW, mixc, poly_mask
from .style_flag import FlagFacet, _composite


def _ramp(stops, t):
    t = min(1.0, max(0.0, t))
    n = len(stops) - 1
    i = min(n - 1, int(t * n))
    return mixc(stops[i], stops[i + 1], t * n - i)


class Dusk(FlagFacet):
    RAMP = [(246, 176, 92), (236, 132, 120), (214, 92, 150)]      # top -> bottom of the butterfly
    sun_stops = None
    grid_thick = True
    grid_k = 0.8
    sun_k = 0.46

    SUN_RAMP = None

    def sun_color(self, f):
        return _ramp(self.SUN_RAMP or self.RAMP, f)

    def chry_base(self, S):
        size = (SW * S, SH * S)
        im = Image.new("RGBA", size, (0, 0, 0, 0))
        pt = self.shape.pt
        n, steps = 36, 8
        for i in range(n):
            s0, s1 = i / n, (i + 1) / n + 0.004
            left = [pt(s0 + (s1 - s0) * k / steps, -1) for k in range(steps + 1)]
            right = [pt(s0 + (s1 - s0) * k / steps, 1) for k in range(steps + 1)]
            im = _composite(im, left + right[::-1], _ramp(self.RAMP, (i + 0.5) / n) + (240,), S, size)
        half = [pt(k / 60, 0) for k in range(61)] + [pt(k / 60, 1) for k in range(60, -1, -1)]
        shade = _composite(Image.new("RGBA", size, (0, 0, 0, 0)), half, (0, 0, 0, 58), S, size)
        shade.putalpha(ImageChops.multiply(shade.getchannel("A"), im.getchannel("A")))
        return Image.alpha_composite(im, shade)

    def wing_base(self, g, S):
        size = (WCW * S, WCH * S)
        mask = poly_mask(g["poly"], S)
        grad = Image.new("RGBA", size, (0, 0, 0, 0))
        d = ImageDraw.Draw(grad)
        for y in range(0, WCH, 3):
            d.rectangle([0, y * S, WCW * S, (y + 3) * S], fill=_ramp(self.RAMP, y / 700) + (240,))
        grad.putalpha(ImageChops.multiply(grad.getchannel("A"), mask))
        shade = Image.new("RGBA", size, (0, 0, 0, 0))
        ds = ImageDraw.Draw(shade)
        bx, by = g["base"]
        c = g["ctrl"]
        for i in range(len(c) - 1):
            if i % 2:
                ds.polygon([(bx * S, by * S), (c[i][0] * S, c[i][1] * S), (c[i + 1][0] * S, c[i + 1][1] * S)], fill=(0, 0, 0, 58))
        shade.putalpha(ImageChops.multiply(shade.getchannel("A"), mask))
        return Image.alpha_composite(grad, shade)


class DuskRose(Dusk):
    name = "dusk-rose"
    label = "Dusk: rose (amber -> coral -> rose)"
    blurb = "Muted version of the original pink-and-amber sunset on the shard butterfly."
    shape_name = "shard2"
    blob_poly = 4
    RAMP = [(246, 176, 92), (236, 132, 120), (214, 92, 150)]
    C1, C2 = (255, 232, 236, 255), (244, 176, 178, 255)
    blob_c1 = (240, 140, 96, 255)
    aura_color, aura_k = (1.0, 0.55, 0.5), 0.14
    sun_top, sun_bot = (244, 186, 96), (196, 76, 136)
    grid_color = (200, 90, 160)


class DuskPeach(Dusk):
    name = "dusk-peach"
    label = "Dusk: peach (peach -> blush -> mauve)"
    blurb = "The softest: peach and blush fading into mauve."
    shape_name = "shard2"
    blob_poly = 4
    RAMP = [(250, 190, 140), (226, 140, 150), (170, 110, 176)]
    C1, C2 = (255, 238, 232, 255), (240, 190, 200, 255)
    blob_c1 = (240, 160, 120, 255)
    aura_color, aura_k = (1.0, 0.65, 0.55), 0.13
    sun_top, sun_bot = (248, 196, 140), (150, 86, 160)
    grid_color = (160, 100, 170)


class DuskGold(Dusk):
    name = "dusk-gold"
    label = "Dusk: rose gold (rose gold -> dusty rose -> deep rose)"
    blurb = "The warmest: rose gold on top, dusty rose below, a deeper rose sun."
    shape_name = "shard2"
    blob_poly = 4
    RAMP = [(236, 170, 128), (214, 130, 132), (176, 92, 130)]
    C1, C2 = (255, 230, 222, 255), (232, 168, 160, 255)
    blob_c1 = (228, 150, 108, 255)
    aura_color, aura_k = (1.0, 0.55, 0.45), 0.14
    sun_top, sun_bot = (232, 168, 124), (140, 60, 100)
    grid_color = (170, 84, 130)


DUSK_STYLES = [DuskRose, DuskPeach, DuskGold]
