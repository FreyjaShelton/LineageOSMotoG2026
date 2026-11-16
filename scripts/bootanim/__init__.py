"""Boot-animation generator: shared engine in core.py, one module per art style.

Round 5 replaced the crack-and-split intro with melt -> blob -> bob -> spin -> idle. Only the neon-family styles
(everything built on style_neon.NeonStyle) were ported; the older crystal / pixel / stardust / prism modules
still exist on disk but use the old crack/halves hooks, so they are not registered.
"""


def styles():
    """name -> Style class."""
    from .style_circuit import CIRCUIT_STYLES
    from .style_neon import NeonCleanStyle, NeonStyle
    from .style_neon2 import NeonAurora, NeonCircuit, NeonDeco, NeonSonar
    from .style_dusk import DUSK_STYLES
    from .style_flag import FLAG_STYLES
    from .style_sunset import SUNSET_STYLES
    from .style_tropical import TROPICAL_STYLES
    from .style_vapor import VAPOR_STYLES
    from .style_vivid import VIVID_STYLES
    classes = [NeonStyle, NeonCleanStyle, NeonCircuit, NeonDeco, NeonAurora, NeonSonar] + CIRCUIT_STYLES + VAPOR_STYLES + SUNSET_STYLES + FLAG_STYLES + DUSK_STYLES + VIVID_STYLES + TROPICAL_STYLES
    return {c.name: c for c in classes}
