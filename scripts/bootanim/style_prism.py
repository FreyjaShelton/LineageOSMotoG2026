"""Style 5: PRISM - iridescent chrome.

Mirror-metal shell and wings whose colour slides through emerald -> teal ->
sapphire -> violet like an oil slick / Morpho wing, with white-hot specular
highlights. The whole frame also slowly shimmers in hue during the idle loop.
"""
import colorsys
import math

from PIL import Image

from .core import clamp
from .style_soft import SoftStyle


class PrismStyle(SoftStyle):
    name = "prism"
    label = "Prism (iridescent chrome)"
    blurb = "Mirror-chrome shell and wings with an oil-slick sheen: emerald, teal, sapphire and violet."
    bloom_gain = 0.60
    aura_color = (0.18, 0.85, 0.85)
    aura_k = 0.34
    mote_color = (0.75, 0.9, 1.0)
    flash_color = (0.6, 0.9, 1.0)
    burst_color = (0.8, 0.95, 1.0)
    crack_glow = (110, 220, 255, 110)
    crack_core = (240, 252, 255, 255)
    light_color = (14, 34, 44)
    dot_color = (235, 245, 255)
    rim_color = (150, 235, 255)
    border_t = 0.06

    body_colors = dict(abd=(14, 40, 70, 255), abd_hi=(120, 200, 235, 255), thx=(18, 60, 90, 255),
                       thx_hi=(170, 240, 255, 255), head=(20, 70, 100, 255), head_hi=(220, 250, 255, 255),
                       ant=(110, 190, 230, 255), club=(210, 245, 255, 255), seg=(8, 24, 45, 255))

    def shade(self, t, a, b):
        t = clamp(t)
        h = (0.41 + 0.07 * math.sin(a) + 0.03 * math.sin(a * 2.3 + 1.0) + 0.26 * t ** 3) % 1.0   # green/teal, violet only in highlights
        s = clamp(0.80 - 0.62 * t ** 2.2)
        v = clamp(0.07 + 1.05 * t ** 0.95)
        r, g, bl = colorsys.hsv_to_rgb(h, s, v)
        return (int(r * 255), int(g * 255), int(bl * 255))

    def post(self, fr, st):
        fr = super().post(fr, st)
        shift = 9 * math.sin(2 * math.pi * st.T / 120)      # one full hue cycle per loop => seamless
        if abs(shift) < 0.3:
            return fr
        h, s, v = fr.convert("HSV").split()
        h = h.point([(i + int(round(shift))) % 256 for i in range(256)])
        return Image.merge("HSV", (h, s, v)).convert("RGB")
