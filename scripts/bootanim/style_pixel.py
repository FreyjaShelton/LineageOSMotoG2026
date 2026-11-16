"""Style 3: PIXEL - handheld LCD.

The shaded art is thrown through a 4-pixel grid, a 4-shade olive-green
palette with ordered (Bayer) dithering, and an LCD pixel-gap mask, so it
looks like a game running on an old handheld. Motion snaps to the pixel grid.
"""
from PIL import Image, ImageChops

from .core import H, RS, W, bloom, clamp
from .style_soft import SoftStyle, make_ramp

BLOCK = 4
GW, GH = W // BLOCK, -(-H // BLOCK)                 # 120 x 268 pixel grid
PALETTE = [(0, 0, 0), (15, 56, 15), (48, 98, 48), (139, 172, 15), (205, 232, 90)]
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def _grid_mask():
    m = Image.new("L", (W, GH * BLOCK), 255)
    px = m.load()
    for y in range(GH * BLOCK):
        for x in range(W):
            if x % BLOCK == 0 or y % BLOCK == 0:
                px[x, y] = 205
    return m.crop((0, 0, W, H))


class PixelStyle(SoftStyle):
    name = "pixel"
    label = "Pixel (handheld LCD)"
    blurb = "Chunky 4px pixel art in four olive-green shades with dithering and an LCD grid."
    bloom_gain = 0.55
    aura_color = (0.45, 0.75, 0.15)
    aura_k = 0.40
    mote_color = (0.7, 0.9, 0.3)
    mote_size = 1.4
    flash_color = (0.8, 0.95, 0.4)
    burst_color = (0.85, 1.0, 0.5)
    crack_glow = (139, 172, 15, 140)
    crack_core = (230, 250, 130, 255)
    light_color = (6, 10, 2)
    png_colors = 16
    ramp = make_ramp([(0.0, (0, 0, 0)), (0.5, (110, 150, 20)), (1.0, (235, 255, 140))])
    dot_color = (230, 250, 130)
    rim_color = (180, 220, 60)
    border_t = 0.08
    body_colors = dict(abd=(30, 70, 15, 255), abd_hi=(139, 172, 15, 255), thx=(40, 90, 20, 255),
                       thx_hi=(190, 225, 70, 255), head=(48, 98, 48, 255), head_hi=(205, 232, 90, 255),
                       ant=(139, 172, 15, 255), club=(205, 232, 90, 255), seg=(15, 40, 15, 255))

    def build(self):
        super().build()
        self.grid = _grid_mask()

    def post(self, fr, st):
        fr = bloom(fr, self.bloom_gain + st.bloom_extra)
        pad = Image.new("RGB", (W, GH * BLOCK), (0, 0, 0))
        pad.paste(fr, (0, 0))
        small = pad.resize((GW, GH), RS.BOX)
        data = list(small.get_flattened_data())
        out = []
        for i, (r, g, b) in enumerate(data):
            x, y = i % GW, i // GW
            v = clamp(max(r, g, b) / 255) ** 1.5
            if v < 0.035:
                out.append(0)
                continue
            lv = v * 4.4 + (BAYER[y % 4][x % 4] / 16 - 0.5) * 1.0
            out.append(int(clamp(lv, 0, 4.999)) if lv >= 0.5 else 0)
        idx = Image.new("P", (GW, GH))
        idx.putpalette([c for p in PALETTE for c in p])
        idx.putdata(out)
        big = idx.convert("RGB").resize((W, GH * BLOCK), RS.NEAREST).crop((0, 0, W, H))
        return ImageChops.multiply(big, Image.merge("RGB", [self.grid] * 3))
