"""Matched (Option A) slipper gear variant."""

from models.xlego.slipper_gear.directional.base import SlipperGearBase

class SlipperGearMatched(SlipperGearBase):
    """Option A (Matched Pitch): 3-ramps, 3-arms, perfectly matched spiral pitches.

    The spring will lay flush against the entire length of the ramp for maximum
    contact area and high torque, but engages only 3 times per revolution.
    """
    def __init__(self, **kwargs):
        ring_p = kwargs.pop("ring_params", {})
        spring_p = kwargs.pop("spring_params", {})

        ring_p.setdefault("ramp_count", 3)

        # Reduced Ramp Height (Drop-off): 1.0mm drop cuts bending fatigue.
        ring_p.setdefault("pocket_r", 9.8)
        ring_p.setdefault("ramp_r", 8.8)

        spring_p.setdefault("spring_count", 3)

        # Reduced Hub Core (Weight Savings & Base Truss):
        # We shrink the solid disk hub back to 4.0mm (safe minimum for 3D printing walls),
        # but increase `root_thickness` to 4.0mm. Mathematical a_out
        # is preserved identically at 8.0, meaning the sweeping curve stays the exact same.
        spring_p.setdefault("hub_r", 4.0)
        spring_p.setdefault("root_thickness", 4.0)

        # Thinner Spring to guarantee it avoids pinching in the assembly gap
        # The ring creates a 5.6mm internal gap. 5.2mm thickness gives a comfortable 0.2mm anti-pinch clearance top & bottom.
        spring_p.setdefault("plate_thickness", 5.2)

        super().__init__(ring_params=ring_p, spring_params=spring_p, **kwargs)

if __name__ == "__main__":
    from ocp_vscode import show
    # Set to False to easily see inside the mechanism during interactive preview
    g_matched = SlipperGearMatched(show_top_plate=False)
    show(g_matched.solid, names=["Matched (Option A)"])
