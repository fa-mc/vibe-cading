"""Shaft — Rigid, single-piece servo-to-Lego axle adapter.

This component is a "dumb" equivalent of the compliant servo-saver assembly.
It merges the geometry of ShaftCrown and ShaftBody (and the envelope of the
spring) into a single solid part for applications where break-away torque
protection is not needed.

Assembled dimensions identical to the saver:
- Total height: 12.0 mm
- Outer diameter: matches the AX31009 saver spring OD (10.03 mm)
- Bottom face: SG90 press-fit spline socket
- Top face: 8.0 mm deep Lego Technic axle bore

Printed orientation: bottom (spline-socket face) flat on the bed.
No supports needed.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

import cadquery as cq

from models.xlego.servos.cam_utils import SPRING_OD
from models.lego.cutters.technic_axle_hole import TechnicAxleHole


class Shaft:
    """Rigid servo-to-Lego axle adapter."""

    HEIGHT: float              = 12.0                 # mm
    OUTER_R: float             = SPRING_OD / 2.0      # ~5.015 mm
    SPLINE_SOCKET_DEPTH: float = 2.75                 # mm
    SPLINE_BORE_R: float       = 2.3                  # Ø 4.6 mm
    SHAFT_BORE_R: float        = 1.5                  # central through-bore
    AXLE_HOLE_DEPTH: float     = 8.0                  # mm

    def __init__(
        self,
        height: float              = HEIGHT,
        outer_r: float             = OUTER_R,
        spline_socket_depth: float = SPLINE_SOCKET_DEPTH,
        spline_bore_r: float       = SPLINE_BORE_R,
        shaft_bore_r: float        = SHAFT_BORE_R,
        axle_hole_depth: float     = AXLE_HOLE_DEPTH,
    ) -> None:
        self.height              = height
        self.outer_r             = outer_r
        self.spline_socket_depth = spline_socket_depth
        self.spline_bore_r       = spline_bore_r
        self.shaft_bore_r        = shaft_bore_r
        self.axle_hole_depth     = axle_hole_depth

        self._solid = self._build()

    def _build(self) -> cq.Workplane:
        # Full solid main cylinder
        part = (
            cq.Workplane("XY")
            .circle(self.outer_r)
            .extrude(self.height)
        )

        # Bottom spline socket
        spline_socket = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -0.1))
            .circle(self.spline_bore_r)
            .extrude(self.spline_socket_depth + 0.1)
        )
        part = part.cut(spline_socket)

        # Central screw clearance bore
        screw_bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -0.1))
            .circle(self.shaft_bore_r)
            .extrude(self.height + 0.2)
        )
        part = part.cut(screw_bore)

        # Top Lego cross-axle hole
        axle_hole = TechnicAxleHole(depth=self.axle_hole_depth)
        cutter = (
            axle_hole.solid
            .rotate((0, 0, 0), (0, 0, 1), 45)
            .translate((0, 0, self.height - self.axle_hole_depth))
        )
        part = part.cut(cutter)

        return part

    @property
    def solid(self) -> cq.Workplane:
        return self._solid

    def to_cutter(self, clearance: float = 0.15, extend_up: float = 0.0, extend_down: float = 0.0) -> cq.Workplane:
        """Return a simplified solid for boolean cuts, expanded by clearance.
        
        This omits the internal spline socket and axle hole so that cutting
        from a mount leaves a clean, hollow cylindrical bore. The cutter is
        extended slightly along Z to ensure clean boolean operations.
        """
        return (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -0.1 - extend_down))
            .circle(self.outer_r + clearance)
            .extrude(self.height + 0.2 + extend_up + extend_down)
        )


if __name__ == "__main__":
    from ocp_vscode import show

    shaft = Shaft()
    bb = shaft.solid.val().BoundingBox()
    print(f"Rigid Shaft: Z[{bb.zmin:.2f}, {bb.zmax:.2f}]  "
          f"R: {shaft.outer_r:.3f} mm")

    show(shaft.solid, names=["Rigid Shaft"], colors=["silver"])
