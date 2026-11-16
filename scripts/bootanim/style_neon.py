"""Style 1: NEON - glowing tube line-art.

No shading at all: the chrysalis and butterfly are bold electric-lime outlines
with cyan contour lines and veins over a nearly clear body. Every line is drawn
as a neon tube (coloured stroke + white-hot core) and the bloom pass lights it.

Variants (same art, different ambience):
    neon        floating particles are crisp neon glyphs (rings, four-point sparkles, glowing beads)
    neon-clean  no floating particles at all
"""
import math

from PIL import Image, ImageChops, ImageDraw

from .core import (poly_mask, BH, BW, BX, BY, CX, CY, LOOP_UNITS, MOTES, RS, SH, SW, SX, SY, T_MELT0, T_MELT1, WCH, WCW,
                   BODY_ELL, SpriteStyle, add_blob, antenna, blit, clamp, drip_state, ease_out, lerp, make_drips, mixc, smooth)

LIME = (185, 255, 40, 255)
CYAN = (0, 255, 205, 255)
FILL = (0, 40, 22, 90)


def _hot(col, k=0.55):
    """Lighten toward white: the bright core of the tube."""
    return tuple(int(c + (255 - c) * k) for c in col[:3]) + (col[3],)


def tube(d, pts, col, w, S, closed=False):
    """Neon tube: coloured stroke of w px (at final scale) with a white-hot core."""
    if closed:
        pts = list(pts) + [pts[0]]
    d.line(pts, fill=col, width=max(1, round(w * S)), joint="curve")
    d.line(pts, fill=_hot(col), width=max(1, round(w * S * 0.36)), joint="curve")


def dot(d, x, y, r, col, S):
    d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=col)
    r2 = r * 0.5
    d.ellipse([(x - r2) * S, (y - r2) * S, (x + r2) * S, (y + r2) * S], fill=_hot(col, 0.7))


class NeonStyle(SpriteStyle):
    name = "neon"
    label = "Neon (bold line art)"
    blurb = "Bold neon-tube outlines in lime and cyan; floating particles are crisp neon glyphs."
    shape_name = "neon"
    glow = 0.55
    bloom_gain = 1.25
    aura_color = (0.30, 1.0, 0.35)
    aura_k = 0.22
    mote_color = (0.4, 1.0, 0.7)
    flash_color = (0.55, 1.0, 0.45)
    burst_color = (0.6, 1.0, 0.7)
    crack_glow = (120, 255, 60, 120)
    crack_core = (250, 255, 215, 255)
    crack_wscale = 1.9
    light_color = (30, 110, 50)
    particles = True
    C1 = LIME            # main line colour
    C2 = CYAN            # accent line colour
    FILL = FILL          # faint body fill

    # -- sprites --------------------------------------------------------------
    def build_chrysalis(self):
        S = 3
        im = Image.new("RGBA", (SW * S, SH * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        sc = lambda pts: [(x * S, y * S) for x, y in pts]
        pt = self.shape.pt
        outline = self.shape.outline()
        d.polygon(sc(outline), fill=self.FILL)
        for u in (-0.42, 0.42):                                           # long ridges
            tube(d, sc([pt(s / 40, u) for s in range(3, 38)]), self.C1[:3] + (150,), 3, S)
        for k in range(8):                                                # abdominal ribs
            s0 = 0.52 + 0.06 * k
            if s0 > 0.95:
                break
            pts = [pt(s0 + 0.03 * (1 - u * u), u) for u in (i / 11.5 - 1 for i in range(24))]
            tube(d, sc(pts), self.C2[:3] + (230,), 4, S)
        band = [pt(0.17 + 0.02 * (1 - u * u), u) for u in (i / 11.5 - 1 for i in range(24))]
        tube(d, sc(band), self.C2, 4, S)
        tube(d, sc(outline), self.C1, 7, S, closed=True)                     # the big outline, on top
        for k in range(-4, 5):                                            # jewelled band
            x, y = pt(0.17 + 0.02 * (1 - (k * 0.2) ** 2), k * 0.2)
            dot(d, x, y, 5.5, self.C1, S)
        return im.resize((SW, SH), RS.LANCZOS)

    def build_wing(self):
        S = 2
        wing = Image.new("RGBA", (WCW, WCH), (0, 0, 0, 0))
        for g in self.shape.wing_geom:
            poly = [(x * S, y * S) for x, y in g["poly"]]
            base = Image.new("RGBA", (WCW * S, WCH * S), (0, 0, 0, 0))
            ImageDraw.Draw(base).polygon(poly, fill=self.FILL)
            inner = Image.new("RGBA", (WCW * S, WCH * S), (0, 0, 0, 0))
            d = ImageDraw.Draw(inner)
            bx, by = g["base"]
            for k, col, w in ((0.80, self.C2[:3] + (190,), 3.2), (0.58, self.C2[:3] + (130,), 2.6)):   # inner contours
                pts = [((bx + (x - bx) * k) * S, (by + (y - by) * k) * S) for x, y in g["poly"]]
                tube(d, pts, col, w, S, closed=True)
            for pl in g["veins"]:
                main = len(pl) == 3
                tube(d, [(x * S, y * S) for x, y in pl], self.C2[:3] + (225 if main else 170,), 3.2 if main else 2.2, S)
            # keep veins/contours inside the wing (no stubs poking past the outline)
            inner.putalpha(ImageChops.multiply(inner.getchannel("A"), poly_mask(g["poly"], S)))
            edge = Image.new("RGBA", (WCW * S, WCH * S), (0, 0, 0, 0))
            d = ImageDraw.Draw(edge)
            tube(d, poly, self.C1, 6.5, S, closed=True)
            for x, y, r in g["dots"]:
                if r > 2:
                    dot(d, x, y, r * 1.45, self.C1, S)
            layer = Image.alpha_composite(Image.alpha_composite(base, inner), edge)
            wing = Image.alpha_composite(wing, layer.resize((WCW, WCH), RS.LANCZOS))
        return wing

    def build_body(self):
        S = 3
        im = Image.new("RGBA", (BW * S, BH * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for sgn in (-1, 1):
            pts, tip = antenna(sgn)
            tube(d, [((BX + x) * S, (BY + y) * S) for x, y in pts], self.C1, 4, S)
            dot(d, BX + tip[0], BY + tip[1], 6.5, self.C1, S)
        for kind, cx, cy, rx, ry in BODY_ELL:
            box = [(BX + cx - rx - 1) * S, (BY + cy - ry - 1) * S, (BX + cx + rx + 1) * S, (BY + cy + ry + 1) * S]
            d.ellipse(box, fill=self.body_fill)
            ring = [((BX + cx + (rx + 1) * math.cos(a / 40 * 6.2832)) * S, (BY + cy + (ry + 1) * math.sin(a / 40 * 6.2832)) * S) for a in range(40)]
            tube(d, ring, self.C1, 4, S, closed=True)
        for yy in range(30, 132, 18):
            w = 8 * math.sqrt(max(0.0, 1 - ((yy - 72) / 70) ** 2))
            tube(d, [((BX - w) * S, (BY + yy) * S), ((BX + w) * S, (BY + yy) * S)], self.C2, 2.4, S)
        return im.resize((BW, BH), RS.LANCZOS)

    # -- floating particles -----------------------------------------------------
    @staticmethod
    def _glyph(d, kind, x, y, r, rot, col, w):
        """kind 0 = ring, 1 = four-point sparkle, 2 = glowing bead."""
        c, s = math.cos(rot), math.sin(rot)

        def P(px, py):
            return (x + px * c - py * s, y + px * s + py * c)
        if kind == 0:
            d.ellipse([x - r, y - r, x + r, y + r], outline=col, width=w)
        elif kind == 1:
            q = 0.2
            pts = [P(0, -r), P(q * r, -q * r), P(r, 0), P(q * r, q * r), P(0, r), P(-q * r, q * r), P(-r, 0), P(-q * r, -q * r)]
            d.line(pts + [pts[0]], fill=col, width=w, joint="curve")
        else:
            rb = r * 0.55
            d.ellipse([x - rb, y - rb, x + rb, y + rb], fill=col)
            hot = tuple(min(255, int(v + (255 - v) * 0.6)) for v in col)
            d.ellipse([x - rb * 0.5, y - rb * 0.5, x + rb * 0.5, y + rb * 0.5], fill=hot)

    @staticmethod
    def _glyph_r(kind, base):
        return (4.5 + base * 0.9, 8 + base * 1.7, 5 + base * 0.8)[kind]

    def _draw_glyphs(self, fr, st):
        if st.mote_k <= 0.01:
            return
        d = ImageDraw.Draw(fr)
        a = 2 * math.pi * st.T / LOOP_UNITS
        for i, m in enumerate(MOTES[:22]):
            x = m["x0"] + m["A"] * math.sin(a * m["m"] + m["p1"])
            y = m["y0"] + m["B"] * math.cos(a * m["n"] + m["p2"])
            tw = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(a * m["q"] + m["p3"])) ** 1.5
            k = tw * st.mote_k
            base = self.C1 if i % 2 == 0 else self.C2
            col = tuple(int(c * k) for c in base[:3])
            rot = a * (1 if i % 2 else -1) + m["p3"]
            self._glyph(d, i % 3, x, y, self._glyph_r(i % 3, m["r"]), rot, col, 3)

    def background(self, fr, st):
        add_blob(fr, st.aura_x, st.aura_y, 320, 400, st.aura * self.aura_k * self.glow, self.aura_color)
        if self.particles:
            self._draw_glyphs(fr, st)

    # -- melt / blob / spin effects ---------------------------------------------
    @property
    def rim_color(self):
        return _hot(self.C1, 0.6)[:3]

    body_fill = (0, 40, 24, 235)        # butterfly body ellipse fill
    blob_c1 = None                      # blob colour if different from C1
    blob_poly = 0                       # 0 = smooth wobbling blob; n > 2 = faceted n-gon blob

    def build(self):
        super().build()
        self.drips = make_drips(self.shape)

    def _blob_ring(self, k, cx, cy, rx, ry, t, S):
        n = self.blob_poly or 72
        wob = 0.4 if self.blob_poly else 1.0
        pts = []
        for a in range(n):
            th = a / n * 2 * math.pi + (0.3 if self.blob_poly else 0.0)
            r = 1 + wob * (0.07 * math.sin(3 * th + t * 0.21) + 0.045 * math.sin(5 * th - t * 0.33)
                           + 0.03 * math.sin(2 * th + t * 0.13 + 1))
            pts.append((cx + math.cos(th) * rx * k * r * S, cy + math.sin(th) * ry * k * r * S))
        return pts

    def blob(self, fr, st):
        b = st.blob
        if not b or b["a"] <= 0.01:
            return
        rx, ry = 0.78 * self.shape.R, 0.36 * self.shape.L
        S = 2
        w, h = int(2 * rx * 1.3), int(2 * ry * 1.3)
        tile = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(tile)
        cx, cy = w * S / 2, h * S / 2
        bc = self.blob_c1 or self.C1
        dark = tuple(int(c * 0.14) for c in bc[:3])
        top = _hot(bc, 0.32)[:3]
        for j, k in enumerate((1.0, 0.82, 0.64, 0.46, 0.28)):             # glowing core: dark rim -> white-hot centre
            d.polygon(self._blob_ring(k, cx, cy, rx, ry, b["t"], S), fill=mixc(dark, top, (j / 4) ** 1.1) + (255,))
        tube(d, self._blob_ring(1.0, cx, cy, rx, ry, b["t"], S), bc, 6, S, closed=True)
        tube(d, self._blob_ring(0.62, cx, cy, rx, ry, b["t"] * 1.3 + 2, S), self.C2[:3] + (200,), 2.6, S, closed=True)
        spr = tile.resize((max(2, round(w * b["sx"])), max(2, round(h * b["sy"]))), RS.LANCZOS)
        blit(fr, spr, (spr.width / 2, spr.height / 2), (b["x"], b["y"]), alpha=min(1.0, b["a"]))

    def melt_fx(self, fr, st):
        """Rivulets running down the shell, the puddle at its foot, beads drawn up into the blob."""
        t = st.t
        if t < T_MELT0 or t > T_MELT1 + 40:
            return
        sh = self.shape
        ax, ay = sh.anchor
        ox, oy = CX + st.jx - ax, CY + st.yoff + st.jy - ay
        d = ImageDraw.Draw(fr)
        for dr in self.drips:
            s = drip_state(sh, dr, t)
            if not s:
                continue
            (hx, hy), (tx, ty) = s
            fade = clamp((SY + sh.L + 70 - hy) / 70)
            col = tuple(int(c * (0.35 + 0.65 * fade)) for c in self.C1[:3])
            d.line([(tx + ox, ty + oy), (hx + ox, hy + oy)], fill=col, width=4)
            d.line([(tx + ox, ty + oy), (hx + ox, hy + oy)], fill=tuple(int(c * 0.9) for c in _hot(self.C1, 0.7)[:3]), width=2)
            dot(d, hx + ox, hy + oy, 6.5, col + (255,), 1)
        pool_y = CY + sh.L * 0.5 + 18
        amount = smooth(T_MELT0 + 18, T_MELT1, t) * (1 - smooth(T_MELT1 + 4, T_MELT1 + 30, t))
        if amount > 0.02:
            wd = 30 + 130 * amount
            add_blob(fr, CX, pool_y, wd * 1.7, 40, 0.75 * amount * self.glow, self.aura_color)
            col = tuple(int(c * amount) for c in self.C1[:3])
            d.ellipse([CX - wd, pool_y - 11, CX + wd, pool_y + 11], outline=col, width=4)
            d.ellipse([CX - wd * 0.55, pool_y - 5, CX + wd * 0.55, pool_y + 5], outline=tuple(int(c * amount) for c in self.C2[:3]), width=2)
        if st.blob:                                                 # the pool is drawn up into the blob
            bx, by = st.blob["x"], st.blob["y"]
            for i in range(9):
                p = clamp((t - (T_MELT1 - 2 + 3.2 * i)) / 28)
                if p <= 0 or p >= 1:
                    continue
                sx0, sgn = CX + (i - 4) * 16, (1 if i % 2 else -1)
                for q in range(4):
                    pp = clamp(p - 0.035 * q)
                    mx, my = lerp(sx0, bx, pp) + sgn * 110 * math.sin(math.pi * pp), lerp(pool_y, by, ease_out(pp))
                    k = (1 - pp) ** 0.5 * (1 - q * 0.22)
                    col = tuple(int(c * k) for c in (self.C1 if i % 2 else self.C2)[:3])
                    dot(d, mx, my, 4.6 - q * 0.8, col + (255,), 1)

    def effects(self, fr, st):
        super().effects(fr, st)
        self.melt_fx(fr, st)
        if st.ring > 0:                                             # shock rings flung out at the start of the spin
            ring = Image.new("RGB", (fr.width, fr.height), (0, 0, 0))
            d = ImageDraw.Draw(ring)
            cy = st.aura_y - 30
            for k, (delay, col, wd) in enumerate(((0.0, self.C1, 6), (0.16, self.C2, 4))):
                p = clamp((st.ring - delay) / (1 - delay))
                if p <= 0:
                    continue
                r = 70 + ease_out(p) * (520 - 90 * k)
                c = tuple(int(v * (1 - p) ** 1.3 * self.glow * 1.5) for v in col[:3])
                d.ellipse([CX - r, cy - r, CX + r, cy + r], outline=c, width=wd)
            fr.paste(ImageChops.add(fr, ring))


class NeonCleanStyle(NeonStyle):
    name = "neon-clean"
    label = "Neon clean (no particles)"
    blurb = "Same bold neon art with nothing floating around it."
    particles = False
