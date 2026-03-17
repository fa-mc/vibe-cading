"""SlipperPlate — base disc + central hub + independent spiral leaf springs."""

from __future__ import annotations
import math
import cadquery as cq

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from models.lego.cutters.technic_axle_hole import TechnicAxleHole

try:
    from .slipper_spring import SlipperSpring
except ImportError:
    from slipper_spring import SlipperSpring

class SlipperPlate:
    """A Slipper Plate assembly consisting of a base disk, a central cross-axle hub,
    and a spiral leaf spring hovering above the base disk.

    Parameters
    ----------
    plate_r : float
        Radius of the outer base disk (mm).
    plate_thickness : float
        Axial thickness of the base disk (mm).
    hub_r : float
        Radius of the solid central core (mm).
    hub_length : float
        Total length of the central hub (mm).
    """

    def __init__(
        self,
        plate_r: float = 10.3,
        plate_thickness: float = 1.2,
        hub_r: float = 6.0,
        hub_length: float = 1.2,
        hole_d: float | None = None,
    ) -> None:
        self.plate_r = plate_r
        self.plate_thickness = plate_thickness
        self.hub_r = hub_r
        self.hub_length = hub_length
        self.hole_d = hole_d

        self._solid = self._build()

    @property
    def solid(self) -> cq.Workplane:
        return self._solid

    def _build(self) -> cq.Workplane:
        # If hub is taller than base, union them. Otherwise base covers it.
        overall_length = max(self.plate_thickness, self.hub_length)

        # 1. Base Disk
        core = cq.Workplane("XY").circle(self.plate_r).extrude(overall_length)

        # 3. Add axle hole or round clearance hole
        axle_fw = overall_length + 2.0
        
        if self.hole_d is not None:
            axle_tool = cq.Workplane("XY").circle(self.hole_d / 2.0).extrude(axle_fw).translate((0, 0, -1.0))
        else:
            axle_tool = TechnicAxleHole(depth=axle_fw).solid.translate((0, 0, -1.0))

        core = core.cut(axle_tool)

        return core

if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
    from ocp_vscode import show

    p = SlipperPlate()
    show(p.solid, names=["SlipperPlate Stack"])
