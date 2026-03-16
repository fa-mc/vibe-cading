"""Steep (Option C) slipper gear variant."""

from models.xlego.slipper_gear.directional.base import SlipperGearBase

class SlipperGearSteep(SlipperGearBase):
    """Option C (Hybrid/Steep): Variable ramps, dynamically matched short arms.

    The ramp is steep (default 12 ramps). The assembly base class auto-calculates
    the arm pitch to dynamically match the tooth pitch to act as a clean pawl.
    """
    def __init__(self, **kwargs):
        ring_p = kwargs.pop("ring_params", {})
        spring_p = kwargs.pop("spring_params", {})

        ring_p.setdefault("ramp_count", 12)
        ring_p.setdefault("pocket_r", 10.0)
        ring_p.setdefault("ramp_r", 8.0)
        
        spring_p.setdefault("spring_count", 3)
        spring_p.setdefault("hub_r", 4.0)
        
        # Maintain default a_out of 7.2 (6.0 + 1.2) while shrinking hub to 4.0
        spring_p.setdefault("root_thickness", 3.2)
        
        # Thinner Spring to guarantee it avoids pinching in the assembly gap
        spring_p.setdefault("plate_thickness", 5.2)

        super().__init__(ring_params=ring_p, spring_params=spring_p, **kwargs)

if __name__ == "__main__":
    from ocp_vscode import show
    # Set to False to easily see inside the mechanism during interactive preview
    g_steep = SlipperGearSteep(show_top_plate=False)
    show(g_steep.solid, names=["Steep (Option C)"])
