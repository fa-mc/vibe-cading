"""SlipperGear base assembly."""
from __future__ import annotations
import math
import cadquery as cq

from models.xlego.slipper_gear.directional.parts.slipper_spring import SlipperSpring
from models.xlego.slipper_gear.directional.parts.slipper_plate import SlipperPlate
from models.xlego.slipper_gear.directional.parts.slipper_ring import SlipperRing

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

        # Map correct parameters over
        spring_params.setdefault("ramp_end_r", ring_obj.ramp_end_r)

        temp_spring = SlipperSpring(**spring_params)

        # Calculate alignment offset
        tip_angle_deg = math.degrees(temp_spring.sweep_angle)
        ramp_span_deg = math.degrees(ring_obj.ramp_span)
        offset_deg = ramp_span_deg - tip_angle_deg + spring_rotation_offset

        spring_params["arm_rotation_offset"] = math.radians(offset_deg)

        plate = SlipperPlate(**plate_params)
        spring_obj = SlipperSpring(**spring_params)

        # Dynamically center the spring in the vertical gap to guarantee it never gets pinched.
        top_plate_z = ring_obj.face_width
        plate_fw = plate.plate_thickness
        gap_height = top_plate_z - (2 * plate_fw)
        spring_z_clearance = (gap_height - spring_obj.plate_thickness) / 2.0

        # Bottom plate ends at Z=plate_fw, plus bottom clearance = perfectly centered spring Z offset
        spring_z = plate_fw + spring_z_clearance

        ring = ring_obj.solid
        spring = spring_obj.solid.translate((0, 0, spring_z))
        plate_flip = SlipperPlate(**plate_params).solid.rotate((0,0,0), (1,0,0), 180).translate((0, 0, top_plate_z))

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
