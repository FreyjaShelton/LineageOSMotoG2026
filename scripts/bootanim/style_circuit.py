"""Circuit options (round 5). Four takes on the angular circuit-board butterfly:

    circuit        original: acid green + magenta, gem-cut shapes, data pulses racing along the traces
    circuit-term   terminal green: columns of binary on the shell and wings, dense bus lines, white-green pulses
    circuit-tron   cyan + orange, stealth-fighter "bolt" silhouette, lattice grid with long light-cycle pulses
    circuit-glitch the original with chromatic fringing, scanlines, tape-tear glitches and afterimage trails
"""
import random

from PIL import ImageChops, ImageFont

from .core import T_MELT1, T_SPIN0, WAX, WAY
from .fx import chroma, scanlines, tear
from .style_neon import tube
from .style_neon2 import NeonCircuit, circuit_path, make_path


def _digits(d, S, boxes, rng, col, size):
    font = ImageFont.load_default(size=int(size * S))
    for x, y in boxes:
        d.text((x * S, y * S), rng.choice("01"), font=font, fill=col)


class CircuitTerm(NeonCircuit):
    name = "circuit-term"
    label = "Circuit: terminal (mono green, binary)"
    blurb = "All green. Columns of binary scroll through the shell and wings; dense bus lines; white-green pulses."
    C1, C2 = (110, 255, 120, 255), (30, 215, 100, 255)
    FILL = (0, 30, 12, 100)
    aura_color, aura_k = (0.30, 1.0, 0.40), 0.20
    flash_color = (0.6, 1.0, 0.7)
    light_color = (10, 60, 20)
    pulse_color, pulse_hot = (150, 255, 170), (255, 255, 255)
    pulse_tail, pulse_step, pulse_size = 8, 0.010, 4.6
    pulse_phases = ((0.0, 1), (0.33, 2), (0.66, 1))

    def chry_inner(self, d, S):
        pt = self.shape.pt
        rng = random.Random(4)
        boxes = []
        for u in (-0.62, -0.31, 0.0, 0.31, 0.62):
            for k in range(16):
                x, y = pt(0.10 + k * 0.055, u)
                boxes.append((x - 5, y - 8))
        _digits(d, S, boxes, rng, self.C2[:3] + (200,), 17)
        tube(d, [(pt(k / 40, 0)[0] * S, pt(k / 40, 0)[1] * S) for k in range(4, 37)], self.C1[:3] + (120,), 2.2, S)

    def wing_inner(self, d, g, S):
        rng = random.Random(9)
        bx, by = g["base"]
        boxes = [(x, y) for x in range(int(bx) + 40, 470, 34) for y in range(8, 830, 30)]
        _digits(d, S, boxes, rng, self.C2[:3] + (95,), 15)
        super().wing_inner(d, g, S)
        # second, shorter bus layer between the main traces
        ends = [pl[-1] for pl in g["veins"] if len(pl) == 3]
        for i, E in enumerate(ends):
            mid = (bx + (E[0] - bx) * 0.72, by + (E[1] - by) * 0.72)
            path = circuit_path((bx, by), mid, (i - len(ends) / 2) * 3.2 + 9)
            tube(d, [(x * S, y * S) for x, y in path], self.C1[:3] + (150,), 2.2, S)
            self.PATHS.append(make_path([(x - WAX, y - WAY) for x, y in path]))


class CircuitTron(NeonCircuit):
    name = "circuit-tron"
    label = "Circuit: tron (cyan + orange, bolt)"
    blurb = "Stealth-fighter silhouette, cyan outline over an orange lattice, long light-cycle pulses."
    shape_name = "bolt"
    C1, C2 = (40, 225, 255, 255), (255, 140, 30, 255)
    FILL = (0, 16, 34, 100)
    aura_color, aura_k = (0.10, 0.65, 1.0), 0.20
    flash_color = (0.7, 0.9, 1.0)
    light_color = (10, 40, 60)
    pulse_color, pulse_hot = (255, 170, 60), (255, 245, 220)
    pulse_tail, pulse_step, pulse_size = 13, 0.0085, 4.4
    pulse_phases = ((0.0, 1), (0.5, 1), (0.25, 2))
    blob_poly = 6

    def chry_inner(self, d, S):
        pt = self.shape.pt
        sc = lambda p: (p[0] * S, p[1] * S)
        for k in range(1, 9):                                              # rungs
            s = k / 9
            tube(d, [sc(pt(s, -1.1)), sc(pt(s, 1.1))], self.C1[:3] + (110,), 2.0, S)
        for u in (-0.5, 0.5):
            tube(d, [sc(pt(k / 40, u)) for k in range(3, 38)], self.C2[:3] + (230,), 3.0, S)
        tube(d, [sc(pt(k / 40, 0)) for k in range(2, 39)], self.C1[:3] + (200,), 2.4, S)

    def chry_edge(self, d, S):
        super().chry_edge(d, S)
        pt = self.shape.pt
        inner = [pt(i / 100, -0.86) for i in range(8, 93)] + [pt(i / 100, 0.86) for i in range(92, 7, -1)]
        tube(d, [(x * S, y * S) for x, y in inner], self.C2[:3] + (230,), 2.6, S, closed=True)

    def wing_inner(self, d, g, S):
        bx, by = g["base"]
        for x in range(int(bx) + 30, 460, 36):                              # lattice
            tube(d, [(x * S, 0), (x * S, 830 * S)], self.C1[:3] + (95,), 1.8, S)
        for y in range(0, 830, 36):
            tube(d, [(bx * S, y * S), (470 * S, y * S)], self.C1[:3] + (95,), 1.8, S)
        super().wing_inner(d, g, S)


class CircuitGlitch(NeonCircuit):
    name = "circuit-glitch"
    label = "Circuit: glitch (fringing, tearing, trails)"
    blurb = "The original, run through a corrupted display: RGB fringing, scanlines, tape-tear glitches, afterimages."
    ghosts, ghost_dt, ghost_alpha, ghosts_always = 5, 2.2, 0.30, True
    fringe = 5

    def build(self):
        super().build()
        self.scan = scanlines()

    def _glitch_seed(self, st):
        """Frame seed when a glitch burst is due (a deterministic function of time), else None."""
        if st.loop:
            j = int(st.j)
            return j if (30 <= j <= 34 or 84 <= j <= 87) else None
        t = st.t
        if T_MELT1 - 4 <= t <= T_MELT1 + 3 or T_SPIN0 <= t <= T_SPIN0 + 14 or T_SPIN0 + 40 <= t <= T_SPIN0 + 43:
            return int(t * 2)
        return None

    def post(self, fr, st):
        fr = super().post(fr, st)
        seed = self._glitch_seed(st)
        if seed is not None:
            fr = tear(fr, seed, strips=7, amp=46)
        fr = chroma(fr, self.fringe + (4 if seed is not None else 0))
        return ImageChops.multiply(fr, self.scan)


CIRCUIT_STYLES = [NeonCircuit, CircuitTerm, CircuitTron, CircuitGlitch]
