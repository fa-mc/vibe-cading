"""SlipperGear — main assembly."""
from __future__ import annotations
import math
import cadquery as cq

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from models.xlego.slipper_gear.parts.slipper_spring import SlipperSpring
from models.xlego.slipper_gear.parts.slipper_plate import SlipperPlate
from models.xlego.slipper_gear.parts.slipper_ring import SlipperRing

class SlipperGearBase:
    """Base SlipperGear Assembly"""
    def __init__(
        self,
        ring_params: dict | None = None,
        plate_params: dict | None = None,
        spring_params: dict | None = None,
        show_top_plate: bool = True,
        spring_rotation_offset: float = 0.0
    ):
        ring_params = ring_params or {}
        plate_params = plate_params or {}
        spring_params = spring_params or {}

        # The assembly intrinsically knows the relationship of the spring sweep degree and the ramp parameters.
        # We evaluate the geometry of the ring gear's ramps to force the spring's Archimedean spirals to match perfectly.
        ramp_count = ring_params.get("ramp_count", 3)
        pocket_r = ring_params.get("pocket_r", 10.0)
        ramp_r = ring_params.get("ramp_r", 8.0)

        # Mathematical logic mapping ring teeth geometry to the spring parameter requirements
        cycle_deg = 360.0 / ramp_count
        cycle = math.radians(cycle_deg)
        scale = cycle / math.radians(120.0)
        hook_angle = math.radians(10.0) * scale
        ramp_span = cycle - hook_angle
        b_out = (pocket_r - ramp_r) / ramp_span

        # Force the spring to act correctly mathematically
        spring_params.setdefault("b_out", b_out)
        spring_params.setdefault("ring_inner_r", pocket_r)

        plate = SlipperPlate(**plate_params)
        ring_obj = SlipperRing(**ring_params)
        spring_obj = SlipperSpring(**spring_params)

        # Calculate automatic alignment offset so the spring arm tip lands directly in the ring's first pocket
        tip_angle_deg = math.degrees(spring_obj.sweep_angle)
        ramp_span_deg = math.degrees(ramp_span)
        offset = ramp_span_deg - tip_angle_deg + spring_rotation_offset

        ring = ring_obj.solid
        spring = spring_obj.solid.rotate((0,0,0), (0,0,1), offset).translate((0,0, 1.3))
        plate_flip = SlipperPlate(**plate_params).solid.rotate((0,0,0), (1,0,0), 180).translate((0,0, 8.0))

        parts = [
            plate.solid.val(),
            spring.val(),
            ring.val(),
        ]
        if show_top_plate:
            parts.append(plate_flip.val())

        # makeCompound natively returns cq.Compound (which already extends Shape), so we wrap it in Workplane to match the interface of other models
        compound = cq.Compound.makeCompound(parts)
        self._solid = cq.Workplane(obj=compound)

    @property
    def solid(self) -> cq.Workplane:
        return self._solid

class SlipperGearMatched(SlipperGearBase):
    """Option A (Matched Pitch): 3-ramps, 3-arms, perfectly matched spiral pitches.

    The spring will lay flush against the entire length of the ramp for maximum
    contact area and high torque, but engages only 3 times per revolution.
    """
    def __init__(self, **kwargs):
        ring_p = kwargs.pop("ring_params", {})
        spring_p = kwargs.pop("spring_params", {})

        ring_p.setdefault("ramp_count", 3)
        ring_p.setdefault("pocket_r", 10.0)
        ring_p.setdefault("ramp_r", 8.0)
        spring_p.setdefault("spring_count", 3)

        super().__init__(ring_params=ring_p, spring_params=spring_p, **kwargs)

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

        super().__init__(ring_params=ring_p, spring_params=spring_p, **kwargs)

# Keep the original SlipperGear name around for backwards compatibility with test scripts
class SlipperGear(SlipperGearSteep):
    pass

if __name__ == "__main__":
    from ocp_vscode import show
    g_matched = SlipperGearMatched(show_top_plate=False)
    g_steep = SlipperGearSteep(show_top_plate=False)
    show(g_matched.solid, names=["Matched (Option A)"])
    show(g_steep.solid, names=["Steep (Option C)"])
