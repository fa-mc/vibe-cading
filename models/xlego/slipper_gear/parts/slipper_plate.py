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
    ) -> None:
        self.plate_r = plate_r
        self.plate_thickness = plate_thickness
        self.hub_r = hub_r
        self.hub_length = hub_length

        self._solid = self._build()

    @property
    def solid(self) -> cq.Workplane:
        return self._solid

    def _build(self) -> cq.Workplane:
        # 1. Base Disk
        base = cq.Workplane("XY").circle(self.plate_r).extrude(self.plate_thickness)

        # 2. Central Hub
        hub = cq.Workplane("XY").circle(self.hub_r).extrude(self.hub_length)

        # 3. Add dog-bone axle hole to the hub & base
        axle_fw = self.hub_length + 2.0
        axle_tool = TechnicAxleHole(depth=axle_fw).solid.translate((0, 0, -1.0))

        core = base.union(hub).cut(axle_tool)

        return core

if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
    from ocp_vscode import show

    p = SlipperPlate()
    show(p.solid, names=["SlipperPlate Stack"])
