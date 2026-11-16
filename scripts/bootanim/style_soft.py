"""Shaded 'soft metal' sprites. Base for the pixel and prism styles.

Per-pixel lit chrysalis (chrome banding, specular streaks, segment ribs,
jewelled band) and veined, bordered wings. Subclasses change the colour
mapping via shade(t, a, b) and the post-processing.
"""
import math

from PIL import Image, ImageChops, ImageFilter

from .core import (RS, SH, SW, SX, SY, WAX, WAY, WCH, WCW, SpriteStyle,
                   build_body_stock, clamp, poly_mask)
from PIL import ImageDraw

GREEN_STOPS = [
    (0.00, (2, 22, 14)),
    (0.25, (6, 90, 52)),
    (0.50, (16, 185, 105)),
    (0.75, (90, 245, 165)),
    (1.00, (225, 255, 235)),
]


def make_ramp(stops):
    out = []
    for i in range(256):
        t = i / 255
        for (a, ca), (b, cb) in zip(stops, stops[1:]):
            if t <= b:
                k = (t - a) / (b - a)
                out.append(tuple(int(ca[j] + (cb[j] - ca[j]) * k) for j in range(3)))
                break
        else:
            out.append(stops[-1][1])
    return out


class SoftStyle(SpriteStyle):
    ramp = make_ramp(GREEN_STOPS)
    dot_color = (215, 255, 228)
    rim_color = (90, 255, 160)
    border_t = 0.10                    # ramp position of the dark wing border

    def shade(self, t, a, b):
        """Map brightness t (0..1) to colour. a, b are free 'phase' variables for iridescence."""
        return self.ramp[int(clamp(t) * 255)]

    # -- chrysalis ----------------------------------------------------------
    def _chry_pixel(self, x, y):
        sh = self.shape
        s = clamp((y - SY) / sh.L)
        r = sh.r(s)
        u = clamp((x - SX - sh.c(s)) / r, -1, 1)
        nz = math.sqrt(1 - u * u)
        diff = max(0.0, -0.5 * u + 0.85 * nz)
        env = 0.5 + 0.5 * math.sin(s * 15.0 + u * 2.4 + 0.7)                  # chrome-like banding
        spec = max(0.0, 1 - abs(u + 0.40) * 5.5) ** 2 * (0.55 + 0.45 * math.sin(s * 8 + 1.2))
        spec2 = max(0.0, 1 - abs(u - 0.55) * 9) ** 2 * 0.4
        rim = (1 - nz) ** 3 * 0.40
        t = 0.10 + 0.34 * diff + 0.26 * env * nz + rim
        if s > 0.48:                                                           # abdominal segments
            ph = (s + 0.03 * (1 - u * u)) * 14.0
            t *= 1 - 0.55 * math.exp(-(((ph % 1.0) - 0.5) / 0.10) ** 2)
        c = self.shade(clamp(t + 0.55 * spec + 0.25 * spec2), s * 9 + u * 2.5, u)
        sb = 0.17                                                              # jewelled band near the top
        if abs(s - sb) < 0.05:
            if abs(s - sb - 0.02 * (1 - u * u)) < 0.006:
                c = (c[0] // 4, c[1] // 3, c[2] // 3)
            for k in range(-4, 5):
                uc = k * 0.2
                dx = (u - uc) * r
                dy = (s - sb - 0.02 * (1 - uc * uc)) * sh.L
                if dx * dx + dy * dy < 10:
                    c = (min(255, c[0] + 190), 255, min(255, c[2] + 120))
        return c

    def build_chrysalis(self):
        mask = self.shape.body_mask()
        x0, x1 = SX - int(self.shape.R) - 60, SX + int(self.shape.R) + 60
        y0, y1 = SY - 3, SY + int(self.shape.L) + 4
        px = [self._chry_pixel(x, y) for y in range(y0, y1) for x in range(x0, x1)]
        patch = Image.new("RGB", (x1 - x0, y1 - y0))
        patch.putdata(px)
        body = Image.new("RGB", (SW, SH), (0, 0, 0))
        body.paste(patch, (x0, y0))
        spr = body.convert("RGBA")
        spr.putalpha(mask)
        return spr

    # -- wings ----------------------------------------------------------------
    def _wing_part(self, g):
        S = 2
        m2 = poly_mask(g["poly"], S)
        inner2 = m2.filter(ImageFilter.GaussianBlur(16)).point([255 if v > 237 else 0 for v in range(256)])
        veins = Image.new("L", (WCW * S, WCH * S), 0)
        dots = Image.new("L", (WCW * S, WCH * S), 0)
        rim = Image.new("L", (WCW * S, WCH * S), 0)
        vd, dd, rd = ImageDraw.Draw(veins), ImageDraw.Draw(dots), ImageDraw.Draw(rim)
        for pl in g["veins"]:
            vd.line([(x * S, y * S) for x, y in pl], fill=255, width=3 if len(pl) == 3 else 2, joint="curve")
        for x, y, r in g["dots"]:
            dd.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=255)
        p2 = [(x * S, y * S) for x, y in g["poly"]]
        rd.line(p2 + [p2[0]], fill=255, width=3)

        mask = m2.resize((WCW, WCH), RS.LANCZOS)
        inner = inner2.resize((WCW, WCH), RS.LANCZOS).get_flattened_data()
        vein = veins.resize((WCW, WCH), RS.LANCZOS).get_flattened_data()
        dot = dots.resize((WCW, WCH), RS.LANCZOS).get_flattened_data()
        rimm = rim.resize((WCW, WCH), RS.LANCZOS).get_flattened_data()
        mdat = mask.get_flattened_data()
        bc = self.ramp[int(self.border_t * 255)]
        out = []
        for idx in range(WCW * WCH):
            if mdat[idx] == 0:
                out.append((0, 0, 0))
                continue
            x, y = idx % WCW, idx // WCW
            dx, dy = x - WAX, y - WAY
            d = math.hypot(dx, dy * 0.85) / 330
            ang = math.atan2(dy, dx)
            t = (0.80 - 0.50 * d) + 0.14 * math.sin(ang * 6.0 + d * 7.0) + 0.08 * math.sin(d * 22)
            t += 0.25 * math.exp(-((dx - 170) ** 2 + (dy + 150) ** 2) / (2 * 70 * 70))
            c = self.shade(clamp(t), ang * 3 + d * 6, d)
            bi = inner[idx] / 255
            c = tuple(bc[j] + (c[j] - bc[j]) * bi for j in range(3))                 # dark border band
            v = vein[idx] / 255 * 0.78
            c = tuple(c[j] * (1 - v) for j in range(3))                              # dark veins
            dv = dot[idx] / 255
            c = tuple(c[j] + (self.dot_color[j] - c[j]) * dv for j in range(3))      # pale dots
            rv = rimm[idx] / 255 * 0.7
            c = tuple(c[j] + (self.rim_color[j] - c[j]) * rv for j in range(3))      # glowing rim
            out.append((int(c[0]), int(c[1]), int(c[2])))
        rgb = Image.new("RGB", (WCW, WCH))
        rgb.putdata(out)
        spr = rgb.convert("RGBA")
        spr.putalpha(mask.point([int(v * 0.94) for v in range(256)]))
        return spr

    def build_wing(self):
        wing = Image.new("RGBA", (WCW, WCH), (0, 0, 0, 0))
        for g in self.shape.wing_geom:
            wing = Image.alpha_composite(wing, self._wing_part(g))
        return wing

    body_colors = dict(abd=(8, 70, 44, 255), abd_hi=(60, 200, 130, 255), thx=(10, 90, 56, 255),
                       thx_hi=(120, 255, 190, 255), head=(14, 110, 70, 255), head_hi=(190, 255, 220, 255),
                       ant=(60, 200, 130, 255), club=(140, 255, 195, 255), seg=(4, 40, 26, 255))

    def build_body(self):
        return build_body_stock(self.body_colors)
