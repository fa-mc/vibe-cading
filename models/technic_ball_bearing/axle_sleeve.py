import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cadquery as cq

from lego.cutters.technic_axle_hole import TechnicAxleHole


class AxleSleeve:
    """Sleeve that seats a Lego Technic axle inside a ball bearing.

    The sleeve slips onto the axle and sits inside the bearing inner race.
    A single thin flange on one end prevents the sleeve from passing through
    the bearing.

    The bore profile is sourced from :class:`TechnicAxleHole`, which uses
    the Technic axle hole dimensions for a correct sliding fit.

    Parameters
    ----------
    bearing_id:
        Inner diameter of the target ball bearing (mm).  The sleeve OD
        matches this value for a press / snug fit in the inner race.
    length:
        Axial length of the cylindrical sleeve body (mm).
    flange_od:
        Outer diameter of the retaining flange (mm).  Must be larger than
        ``bearing_id`` to prevent the sleeve from passing through.
    flange_thickness:
        Axial thickness of the retaining flange (mm).
    """

    def __init__(
        self,
        bearing_id: float = 5.0,
        length: float = 2.5,
        flange_od: float = 7.0,
        flange_thickness: float = 0.8,
    ):
        self.bearing_id = bearing_id
        self.length = length
        self.flange_od = flange_od
        self.flange_thickness = flange_thickness

        self._solid = self._build()

    def _build(self) -> cq.Workplane:
        """Construct the sleeve solid."""
        # 1. Retaining flange disc at the base
        part = (
            cq.Workplane("XY")
            .circle(self.flange_od / 2)
            .extrude(self.flange_thickness)
        )

        # 2. Cylindrical sleeve body on top of the flange
        part = (
            part
            .faces(">Z")
            .workplane()
            .circle(self.bearing_id / 2)
            .extrude(self.length)
        )

        # 3. Cut the cross-axle bore using TechnicAxleHole
        total_height = self.flange_thickness + self.length
        bore = TechnicAxleHole(depth=total_height)
        part = part.cut(bore.solid)

        return part

    @property
    def solid(self) -> cq.Workplane:
        return self._solid


if __name__ == "__main__":
    from ocp_vscode import show

    sleeve = AxleSleeve()
    show(sleeve.solid)
