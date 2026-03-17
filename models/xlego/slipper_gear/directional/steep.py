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
        ring_p.setdefault("ramp_end_r", 10.0)
        # ring_p.setdefault("ramp_start_r", 8.0)
        ring_p.setdefault("ramp_start_r", 9.0)

        spring_p.setdefault("spring_count", 3)
        spring_p.setdefault("hub_r", 3.6)

        # Anchor strictly at origin (0 width) and use pure mathematical spiral to reach tip
        spring_p.setdefault("arm_base_width", 2.0)
        spring_p.setdefault("clearance", 0.1)

        # Thinner Spring to guarantee it avoids pinching in the assembly gap
        spring_p.setdefault("plate_thickness", 5.2)

        # Allow the spring arms to be independent short pawls instead of perfectly matching
        # the ring's steep pitch (which causes them to over-extend and collide with the next tooth).
        # A very steep pitch (22.0) means it will reach r=9.75 in just ~25 degrees of sweep.
        spring_p.setdefault("arm_pitch", 2.4)

        super().__init__(ring_params=ring_p, spring_params=spring_p, **kwargs)

if __name__ == "__main__":
    from ocp_vscode import show
    # Set to False to easily see inside the mechanism during interactive preview
    g_steep = SlipperGearSteep(show_top_plate=False)
    show(g_steep.solid, names=["Steep (Option C)"])
