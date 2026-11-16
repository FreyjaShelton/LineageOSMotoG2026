"""Round 9: vibrant, saturated sunset shards (the muted dusk palettes were too quiet).

Same shard silhouette, solid fills, crisp outlines and full-colour frames as the dusk styles, but fully saturated
multi-hue gradients, a brighter sun and less bloom, so the wings keep their colour instead of washing out.

    vivid-sunset    yellow -> orange -> hot pink: the original sunset, saturated and solid
    vivid-miami     yellow -> hot pink -> electric blue, sun runs on into violet and blue
    vivid-tropical  coral -> hot pink -> violet
"""
from .style_dusk import Dusk


class Vivid(Dusk):
    shape_name = "shard2"
    blob_poly = 4
    glow = 0.30
    sun_k = 0.62
    grid_k = 0.95
    light_color = (40, 12, 10)


class VividSunset(Vivid):
    name = "vivid-sunset"
    label = "Vivid: sunset (yellow -> orange -> hot pink)"
    blurb = "The original pink-and-amber sunset, saturated and solid."
    RAMP = [(255, 205, 40), (255, 112, 70), (255, 40, 150)]
    SUN_RAMP = [(255, 214, 70), (255, 120, 60), (255, 40, 150), (170, 30, 150)]
    C1, C2 = (255, 246, 248, 255), (255, 210, 130, 255)
    blob_c1 = (255, 150, 50, 255)
    aura_color, aura_k = (1.0, 0.5, 0.4), 0.15
    grid_color = (255, 60, 190)


class VividMiami(Vivid):
    name = "vivid-miami"
    label = "Vivid: miami (yellow -> hot pink -> electric blue)"
    blurb = "Yellow top wings, hot pink middle, electric blue below; the sun runs on into violet and blue."
    RAMP = [(255, 226, 60), (255, 56, 150), (80, 120, 255)]
    SUN_RAMP = [(255, 226, 70), (255, 80, 150), (160, 60, 255), (40, 120, 255)]
    C1, C2 = (255, 255, 255, 255), (170, 230, 255, 255)
    blob_c1 = (255, 100, 170, 255)
    aura_color, aura_k = (1.0, 0.5, 0.8), 0.15
    grid_color = (110, 100, 255)


class VividTropical(Vivid):
    name = "vivid-tropical"
    label = "Vivid: tropical (coral -> hot pink -> violet)"
    blurb = "Coral-orange top wings fading through hot pink into violet."
    RAMP = [(255, 112, 52), (255, 50, 140), (190, 60, 255)]
    SUN_RAMP = [(255, 174, 50), (255, 70, 100), (230, 40, 170), (130, 40, 210)]
    C1, C2 = (255, 244, 250, 255), (255, 190, 220, 255)
    blob_c1 = (255, 110, 70, 255)
    aura_color, aura_k = (1.0, 0.45, 0.6), 0.15
    grid_color = (200, 70, 230)


VIVID_STYLES = [VividSunset, VividMiami, VividTropical]
