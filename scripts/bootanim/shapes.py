"""Silhouettes. Each style picks one (Style.shape_name).

Wing points are the RIGHT wing relative to the thorax: x grows outward, y grows
DOWN (so -y is toward the head). The left wing is a mirror image.
Canvas limits: x up to ~450, y from about -400 to +400.
"""
from .core import Shape

# --- original (kept for pixel / prism) --------------------------------------
_DEFAULT = Shape(
    "default", length=400, radius=112, bow=16,
    profile=[(0.0, 0.40), (0.04, 0.60), (0.12, 0.88), (0.22, 1.0), (0.34, 1.0), (0.48, 0.92),
             (0.62, 0.74), (0.76, 0.52), (0.88, 0.30), (0.96, 0.14), (1.0, 0.05)],
    fore=[(4, -12), (50, -80), (120, -165), (205, -240), (285, -282), (350, -285), (380, -255),
          (375, -200), (350, -135), (312, -80), (250, -38), (160, -10), (70, 4), (4, 6)],
    hind=[(4, 8), (90, 2), (180, 14), (255, 48), (292, 108), (285, 172), (248, 228),
          (190, 262), (130, 252), (85, 212), (52, 150), (22, 82)],
)

# --- NEON: sleek, elongated capsule; long swallowtail butterfly --------------
_NEON = Shape(
    "neon", length=450, radius=90, bow=22, bf_scale=0.88,
    profile=[(0.0, 0.30), (0.05, 0.55), (0.14, 0.85), (0.26, 1.0), (0.40, 0.98), (0.55, 0.84),
             (0.70, 0.62), (0.84, 0.38), (0.94, 0.18), (1.0, 0.04)],
    fore=[(4, -10), (60, -72), (140, -152), (230, -226), (320, -276), (392, -292), (424, -264),
          (410, -206), (372, -142), (326, -86), (260, -44), (170, -14), (80, 2), (4, 6)],
    hind=[(4, 8), (95, 0), (185, 16), (255, 52), (288, 110), (276, 176), (246, 236), (222, 300),
          (214, 376), (192, 318), (158, 266), (112, 234), (68, 190), (40, 128), (20, 70)],
)

# --- CRYSTAL: cut-gem shard, straight edges; angular, origami-like wings -----
_CRYSTAL = Shape(
    "crystal", length=430, radius=102, bow=0, smooth_body=False, smooth_wings=False,
    profile=[(0.0, 0.16), (0.10, 0.62), (0.30, 1.0), (0.55, 0.92), (0.78, 0.52), (1.0, 0.0)],
    fore=[(4, -12), (55, -88), (130, -172), (215, -244), (300, -292), (346, -302), (374, -264),
          (364, -202), (340, -132), (300, -72), (226, -34), (140, -10), (60, 4)],
    hind=[(4, 8), (90, 2), (180, 12), (262, 46), (306, 102), (300, 162), (262, 216), (218, 262),
          (192, 336), (162, 262), (112, 238), (66, 190), (36, 126), (18, 70)],
)

# --- STARDUST: plump bulb with a long wisp; luna-moth wings with curling tails
_STARDUST = Shape(
    "stardust", length=470, radius=104, bow=28, bf_scale=0.92,
    profile=[(0.0, 0.38), (0.05, 0.62), (0.14, 0.92), (0.26, 1.0), (0.38, 0.96), (0.52, 0.78),
             (0.66, 0.54), (0.80, 0.30), (0.92, 0.12), (1.0, 0.02)],
    fore=[(4, -10), (50, -70), (110, -150), (190, -225), (280, -275), (360, -288), (406, -258),
          (408, -200), (382, -140), (336, -86), (266, -46), (176, -16), (80, 0), (4, 6)],
    hind=[(4, 8), (85, 0), (172, 12), (244, 48), (280, 108), (268, 172), (240, 236), (226, 300),
          (236, 352), (262, 396), (222, 362), (196, 300), (160, 258), (110, 232), (66, 190),
          (40, 128), (20, 70)],
)

# --- VAPOR: round barrel chrysalis; big round-lobed wings ----------------------
_VAPOR = Shape(
    "vapor", length=410, radius=118, bow=0, bf_scale=0.92,
    profile=[(0.0, 0.50), (0.06, 0.80), (0.18, 1.0), (0.50, 1.0), (0.72, 0.80), (0.88, 0.50), (1.0, 0.18)],
    fore=[(4, -10), (60, -80), (140, -170), (230, -235), (320, -250), (380, -215), (385, -150), (350, -90),
          (290, -50), (200, -20), (100, 0), (4, 6)],
    hind=[(4, 8), (110, 10), (210, 40), (280, 95), (300, 165), (270, 230), (210, 270), (140, 265), (80, 220),
          (40, 150), (20, 80)],
)

# --- BOLT: stealth-fighter butterfly; hexagonal pod, long swept forewings, small delta hindwings
_BOLT = Shape(
    "bolt", length=440, radius=96, bow=0, smooth_body=False, smooth_wings=False, bf_scale=0.9,
    profile=[(0.0, 0.10), (0.10, 0.70), (0.26, 1.0), (0.52, 1.0), (0.76, 0.58), (1.0, 0.0)],
    fore=[(4, -12), (80, -78), (170, -170), (270, -262), (380, -332), (428, -340), (404, -262), (360, -180),
          (310, -112), (230, -56), (130, -18), (50, 2)],
    hind=[(4, 8), (100, 6), (200, 28), (300, 84), (356, 160), (322, 212), (250, 206), (176, 176),
          (112, 132), (58, 84), (22, 40)],
)

# --- SHARD: kite-shaped pod; huge sharp forewings and two spear-point tails
_SHARD = Shape(
    "shard", length=450, radius=100, bow=0, smooth_body=False, smooth_wings=False, bf_scale=0.88,
    profile=[(0.0, 0.0), (0.30, 1.0), (0.62, 0.62), (1.0, 0.0)],
    fore=[(4, -12), (110, -112), (250, -285), (400, -352), (372, -198), (290, -108), (170, -40), (56, 0)],
    hind=[(4, 8), (120, 26), (250, 70), (322, 168), (292, 330), (214, 236), (146, 296), (98, 186), (40, 106)],
)

# --- round 7: angular butterflies whose top wings are bigger than the bottom ones -------------------
# SHARD2: the shard, reworked: bigger forewings, shorter, sturdier tails
_SHARD2 = Shape(
    "shard2", length=450, radius=100, bow=0, smooth_body=False, smooth_wings=False, bf_scale=0.86,
    profile=[(0.0, 0.0), (0.30, 1.0), (0.62, 0.62), (1.0, 0.0)],
    fore=[(4, -12), (100, -120), (230, -300), (410, -380), (430, -250), (360, -140), (240, -60), (110, -14)],
    hind=[(4, 8), (110, 22), (220, 64), (268, 150), (232, 262), (172, 196), (112, 226), (74, 150), (36, 90)],
)

# HAWK: enormous forewings, small triangular hindwings
_HAWK = Shape(
    "hawk", length=440, radius=96, bow=0, smooth_body=False, smooth_wings=False, bf_scale=0.84,
    profile=[(0.0, 0.0), (0.22, 0.9), (0.40, 1.0), (0.70, 0.55), (1.0, 0.0)],
    fore=[(4, -12), (90, -130), (200, -300), (330, -395), (440, -410), (420, -290), (380, -190), (310, -110),
          (200, -50), (80, -8)],
    hind=[(4, 8), (110, 20), (210, 62), (240, 150), (170, 200), (96, 160), (50, 100), (22, 50)],
)

# BLADE: forewings swept up and back like knife blades, hindwings reduced to two spurs
_BLADE = Shape(
    "blade", length=470, radius=82, bow=0, smooth_body=False, smooth_wings=False, bf_scale=0.84,
    profile=[(0.0, 0.0), (0.18, 0.7), (0.38, 1.0), (0.75, 0.5), (1.0, 0.0)],
    fore=[(4, -12), (70, -170), (170, -340), (290, -430), (410, -400), (392, -310), (336, -214), (262, -130),
          (160, -60), (60, -6)],
    hind=[(4, 8), (90, 40), (188, 112), (240, 214), (170, 196), (122, 232), (72, 150), (34, 80)],
)

# KITE: top wings are big kite-shaped quadrilaterals, bottom wings small rhombi
_KITE = Shape(
    "kite", length=420, radius=108, bow=0, smooth_body=False, smooth_wings=False, bf_scale=0.84,
    profile=[(0.0, 0.0), (0.35, 1.0), (0.70, 0.70), (1.0, 0.0)],
    fore=[(4, -14), (130, -210), (310, -410), (450, -290), (420, -170), (250, -70), (100, -10)],
    hind=[(4, 8), (130, 40), (240, 120), (190, 232), (110, 176), (46, 104)],
)

SHAPES = {s.name: s for s in (_DEFAULT, _NEON, _CRYSTAL, _STARDUST, _VAPOR, _BOLT, _SHARD, _SHARD2, _HAWK, _BLADE, _KITE)}
