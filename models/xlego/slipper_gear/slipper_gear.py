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

        # 1. Instantiate the ring first. It intrinsically owns the geometric ramp mathematics.
        ring_obj = SlipperRing(**ring_params)

        # 2. Extract the systematic relationship. For flush contact, the spring's outer Archimedean
        # pitch (b_out) must perfectly match the computed pitch of the ring's ramps.
        spring_params.setdefault("b_out", ring_obj.b_out)
        spring_params.setdefault("ring_inner_r", ring_obj.pocket_r)

        # 3. Discover exact spring arm length.
        # Temp spring lets us query the derived sweep angle (automatically bounded short of the hook)
        temp_spring = SlipperSpring(**spring_params)

        # 4. Calculate alignment rot offset.
        # The arm starts its sweep at the ramp's root angle. We offset it so the tip mathematically
        # aligns with the end of the ramp span, ensuring the physical cap nests exactly into the pocket.
        tip_angle_deg = math.degrees(temp_spring.sweep_angle)
        ramp_span_deg = math.degrees(ring_obj.ramp_span)
        offset_deg = ramp_span_deg - tip_angle_deg + spring_rotation_offset

        # Pass the rotation natively so the inner axle shaft remains globally aligned at 0 degrees
        spring_params["arm_rotation_offset"] = math.radians(offset_deg)

        plate = SlipperPlate(**plate_params)
        spring_obj = SlipperSpring(**spring_params)

        ring = ring_obj.solid
        spring = spring_obj.solid.translate((0,0, 1.3))
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
        
        # Reduced Ramp Height (Drop-off): 
        # By bringing pocket_r from 10.0 -> 9.8, and ramp_r from 8.0 -> 8.8,
        # the cliff the arm must climb over drops from a massive 2.0mm down to just 1.0mm.
        # This cuts the bending fatigue during a "slip" event in half.
        ring_p.setdefault("pocket_r", 9.8)
        ring_p.setdefault("ramp_r", 8.8)

        spring_p.setdefault("spring_count", 3)
        
        # Increase Arm Curvy Radius (Hub base):
        # We increase the solid center hub`s radius from 6.0 -> 6.8. This shifts the entire
        # working bend mechanism further outwards from the axle centre. Together with the 
        # small 1.0mm ramp height, this forces the Archimedean math to spiral around 
        # a massive ~170 degrees before reaching the tip, maximizing flexibility length.
        spring_p.setdefault("hub_r", 6.8)
        spring_p.setdefault("root_thickness", 1.2)

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
