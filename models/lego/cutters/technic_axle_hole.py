import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cadquery as cq
from lego.constants import (
    AXLE_HOLE_TIP_TO_TIP,
    AXLE_HOLE_ARM_WIDTH,
)


class TechnicAxleHole:
    """Lego Technic cross axle hole profile.

    Builds a + cross solid sized to the Technic axle *hole* dimensions.
    Use the :pymeth:`solid` property as a boolean cutter to bore a correctly
    shaped axle hole into any part::

        from lego.technic_axle_hole import TechnicAxleHole

        hole = TechnicAxleHole(depth=my_thickness)
        part = part.cut(hole.solid)

    Parameters
    ----------
    depth:
        Axial depth of the hole (mm).
    convex_radius:
        Fillet radius on the 8 outer convex junction edges — where the
        curved arm tip meets the flat arm side (mm).  Set to 0 to skip.
    concave_radius:
        Fillet radius on the 4 inner concave corners — the valleys between
        perpendicular arms (mm).  Set to 0 to skip.
    """

    # ── Dimensions sourced from lego.constants ─────────────────────────────
    TIP_TO_TIP: float = AXLE_HOLE_TIP_TO_TIP
    ARM_WIDTH: float = AXLE_HOLE_ARM_WIDTH

    # ── Hole-specific corner radius defaults ───────────────────────────────
    DEFAULT_CONVEX_RADIUS: float = 0  # Convex junction (arm tip meets flat side)
    DEFAULT_CONCAVE_RADIUS: float = 0.6  # Concave inner corner (valley between arms)

    def __init__(
        self,
        depth: float,
        convex_radius: float = DEFAULT_CONVEX_RADIUS,
        concave_radius: float = DEFAULT_CONCAVE_RADIUS,
    ):
        self.depth = depth
        self.convex_radius = convex_radius
        self.concave_radius = concave_radius
        self._solid = self._build()

    def _build(self) -> cq.Workplane:
        """Build the + cross solid using the axle hole dimensions."""
        tip = self.TIP_TO_TIP
        arm = self.ARM_WIDTH
        half_arm = arm / 2

        # Cylinder constrains the outer boundary → curved arm tips
        cylinder = (
            cq.Workplane("XY")
            .circle(tip / 2)
            .extrude(self.depth)
        )

        # Two rectangular prisms form the + cross mask → flat sides
        arm_h = (
            cq.Workplane("XY")
            .rect(tip, arm)
            .extrude(self.depth)
        )
        arm_v = (
            cq.Workplane("XY")
            .rect(arm, tip)
            .extrude(self.depth)
        )

        cross = cylinder.intersect(arm_h.union(arm_v))

        # Fillet the 4 inner concave corners first (larger radius).
        # These sit at (±half_arm, ±half_arm) in XY — select via a tight
        # central box that excludes the outer junction edges.
        if self.concave_radius > 0:
            eps = 0.01
            inner_sel = cq.selectors.BoxSelector(
                (-half_arm - eps, -half_arm - eps, -eps),
                ( half_arm + eps,  half_arm + eps,  self.depth + eps),
            )
            cross = cross.edges(inner_sel).fillet(self.concave_radius)

        # Fillet the remaining outer convex junction edges.
        # After the concave fillet above the only remaining |Z edges are
        # the 8 outer junctions where cylinder arc meets flat arm side.
        if self.convex_radius > 0:
            cross = cross.edges("|Z").fillet(self.convex_radius)

        return cross

    @property
    def solid(self) -> cq.Workplane:
        """The + cross solid — cut this from any part to bore an axle hole."""
        return self._solid


if __name__ == "__main__":
    from ocp_vscode import show

    hole = TechnicAxleHole(depth=4)
    show(hole.solid)
