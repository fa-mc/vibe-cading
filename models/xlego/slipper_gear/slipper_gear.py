"""SlipperGear — main assembly."""
from __future__ import annotations
import cadquery as cq

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from models.xlego.slipper_gear.slipper_spring import SlipperSpring
from models.xlego.slipper_gear.slipper_plate import SlipperPlate
from models.xlego.slipper_gear.slipper_ring import SlipperRing

class SlipperGear:
    """
    SlipperGear Assembly

    A torque-limiting, directional slip gear compatible with Lego Technic.
    The internal core dimensions are structurally optimized for anything from 24T to 40T.

    Defaults:
      Module: 1.0 (Lego standard)
      Face width: 8.0mm (1 stud)
      Ratch: 3-arm Spring engaging with a 12-ramp SlipperRing
    """
    def __init__(
        self,
        ring_params: dict | None = None,
        plate_params: dict | None = None,
        spring_params: dict | None = None
    ):
        # The ring is 8.0mm wide, with 1.2mm sags on both sides.
        # This leaves 5.6mm of inner space for the spring.
        ring_params = ring_params or {}
        plate_params = plate_params or {}
        spring_params = spring_params or {}

        plate = SlipperPlate(**plate_params)
        ring = SlipperRing(**ring_params)
        spring = SlipperSpring(**spring_params).solid.translate((0,0, 1.3))
        plate_flip = SlipperPlate(**plate_params).solid.rotate((0,0,0), (1,0,0), 180).translate((0,0, 8.0))

        self._solid = cq.Compound.makeCompound([
            plate.solid.val(),
            spring.val(),
            ring.solid.val(),
            plate_flip.val()
        ])

    @property
    def solid(self):
        return self._solid

if __name__ == "__main__":
    from ocp_vscode import show
    g = SlipperGear()
    show(g.solid, names=["Full Assembly"])
