"""Style 2: CRYSTAL - faceted cut-gem / low-poly.

Chrysalis and wings are meshes of flat-shaded triangles in deep emerald
with a few gold facets, cut-glass facet edges, gold wing borders and gold
dust. Same shapes, completely different surface.
"""
import math
import random

from PIL import Image, ImageChops, ImageDraw

from .core import RS, SH, SW, WCH, WCW, SpriteStyle, build_body_stock, clamp, mixc, poly_mask

# emerald ramp (dark -> pale mint) and gold ramp
EMERALD = [(3, 28, 20), (6, 70, 48), (14, 130, 84), (40, 200, 130), (150, 250, 200), (235, 255, 240)]
GOLD = [(60, 36, 4), (150, 100, 14), (225, 170, 40), (255, 215, 100), (255, 245, 190)]


def ramp(stops, t):
    t = clamp(t) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    return mixc(stops[i], stops[i + 1], t - i)


def edge(c):
    return tuple(min(255, int(v * 1.25 + 28)) for v in c)


class CrystalStyle(SpriteStyle):
    name = "crystal"
    label = "Crystal (faceted gem)"
    blurb = "Low-poly cut-emerald with gold facets and gold-dust sparkles."
    shape_name = "crystal"
    glow = 0.5
    bloom_gain = 0.55
    aura_color = (0.2, 0.95, 0.55)
    aura_k = 0.30
    mote_color = (1.0, 0.82, 0.38)
    mote_size = 0.9
    flash_color = (1.0, 0.9, 0.55)
    burst_color = (1.0, 0.88, 0.5)
    crack_glow = (255, 205, 90, 120)
    crack_core = (255, 248, 210, 255)
    light_color = (40, 56, 16)

    def build_chrysalis(self):
        S = 2
        rng = random.Random(5)
        im = Image.new("RGBA", (SW * S, SH * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        rows = [0, 0.03, 0.08, 0.15, 0.23, 0.32, 0.42, 0.52, 0.62, 0.71, 0.79, 0.86, 0.92, 0.97, 1.0]
        cols = [-1, -0.66, -0.33, 0, 0.33, 0.66, 1]
        V = {}
        for i, s in enumerate(rows):
            for j, u in enumerate(cols):
                x, y = self.shape.pt(s, u)
                if 0 < i < len(rows) - 1 and 0 < j < len(cols) - 1:
                    x += rng.uniform(-6, 6)
                    y += rng.uniform(-5, 5)
                V[i, j] = (x * S, y * S)
        for i in range(len(rows) - 1):
            for j in range(len(cols) - 1):
                um = (cols[j] + cols[j + 1]) / 2
                nz = math.sqrt(max(0.0, 1 - um * um))
                lam = clamp(-0.55 * um + 0.85 * nz)
                quad = [V[i, j], V[i, j + 1], V[i + 1, j + 1], V[i + 1, j]]
                tris = ([quad[0], quad[1], quad[2]], [quad[0], quad[2], quad[3]]) if rng.random() < 0.5 else \
                       ([quad[0], quad[1], quad[3]], [quad[1], quad[2], quad[3]])
                for tri in tris:
                    t = clamp(0.10 + 0.62 * lam + rng.uniform(-0.13, 0.13) + 0.06 * math.sin(rows[i] * 9))
                    c = ramp(GOLD, t * 0.9 + 0.05) if rng.random() < 0.11 else ramp(EMERALD, t)
                    d.polygon(tri, fill=c + (255,), outline=edge(c) + (255,))
        spr = im.resize((SW, SH), RS.LANCZOS)
        spr.putalpha(ImageChops.multiply(spr.getchannel("A"), self.shape.body_mask()))
        # gold collar
        d2 = ImageDraw.Draw(spr)
        band = [self.shape.pt(0.17 + 0.02 * (1 - u * u), u) for u in (i / 11.5 - 1 for i in range(24))]
        d2.line(band, fill=(255, 215, 100, 255), width=3, joint="curve")
        return spr

    def build_wing(self):
        S = 2
        rng = random.Random(9)
        wing = Image.new("RGBA", (WCW, WCH), (0, 0, 0, 0))
        for g in self.shape.wing_geom:
            bx, by = g["base"]
            ang = [math.atan2(y - by, x - bx) for x, y in g["poly"]]
            a0, a1 = min(ang) - 0.15, max(ang) + 0.15
            n_a = max(6, int((a1 - a0) / 0.115))
            rings = [k * 34 for k in range(0, 13)]
            V = {}
            for k, r in enumerate(rings):
                for j in range(n_a + 1):
                    a = a0 + (a1 - a0) * j / n_a
                    rr = r + (rng.uniform(-6, 6) if 0 < k else 0)
                    aa = a + (rng.uniform(-0.03, 0.03) if 0 < j < n_a else 0)
                    V[k, j] = ((bx + math.cos(aa) * rr) * S, (by + math.sin(aa) * rr) * S)
            im = Image.new("RGBA", (WCW * S, WCH * S), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            for k in range(len(rings) - 1):
                for j in range(n_a):
                    quad = [V[k, j], V[k, j + 1], V[k + 1, j + 1], V[k + 1, j]]
                    tris = ([quad[0], quad[1], quad[2]], [quad[0], quad[2], quad[3]]) if rng.random() < 0.5 else \
                           ([quad[0], quad[1], quad[3]], [quad[1], quad[2], quad[3]])
                    rr = rings[k] / 400
                    for tri in tris:
                        t = 0.78 - 0.45 * rr + rng.uniform(-0.17, 0.17) + 0.10 * math.sin((j / n_a) * 9 + k * 0.7)
                        c = ramp(GOLD, 0.35 + t * 0.6) if (rr > 0.3 and rng.random() < 0.09) else ramp(EMERALD, t)
                        d.polygon(tri, fill=c + (255,), outline=edge(c) + (255,))
            for pl in g["veins"]:
                if len(pl) == 3:
                    d.line([(x * S, y * S) for x, y in pl], fill=(200, 255, 225, 90), width=2, joint="curve")
            poly = [(x * S, y * S) for x, y in g["poly"]]
            d.line(poly + [poly[0]], fill=(255, 210, 90, 255), width=5, joint="curve")
            for x, y, r in g["dots"]:
                if r > 2:
                    d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=(255, 245, 200, 255))
            part = im.resize((WCW, WCH), RS.LANCZOS)
            m = poly_mask(g["poly"], 2).resize((WCW, WCH), RS.LANCZOS)
            part.putalpha(ImageChops.multiply(part.getchannel("A"), m.point([int(v * 0.96) for v in range(256)])))
            wing = Image.alpha_composite(wing, part)
        return wing

    def build_body(self):
        return build_body_stock(dict(
            abd=(5, 60, 40, 255), abd_hi=(40, 180, 120, 255), thx=(8, 80, 52, 255), thx_hi=(150, 250, 200, 255),
            head=(10, 100, 64, 255), head_hi=(255, 225, 130, 255), ant=(225, 170, 40, 255),
            club=(255, 225, 130, 255), seg=(3, 30, 20, 255)))
