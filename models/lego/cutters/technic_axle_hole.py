# This file is part of vibe-cading.
#
# vibe-cading is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# vibe-cading is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import cadquery as cq
from models.print_settings import ToleranceProfile, get_profile
from models.lego.constants import (
    AXLE_TIP_TO_TIP,
    AXLE_ARM_WIDTH,
)


class TechnicAxleHole:
    """Lego Technic cross axle hole profile.

    Builds a + cross solid sized to the Technic axle *hole* dimensions.
    Use the :pymeth:`solid` property as a boolean cutter to bore a correctly
    shaped axle hole into any part::

        from models.lego.cutters.technic_axle_hole import TechnicAxleHole

        hole = TechnicAxleHole(depth=my_thickness, fit="slip")
        part = part.cut(hole.solid)

    Parameters
    ----------
    depth:
        Axial depth of the hole (mm).
    fit:
        Tolerance fit type: "press", "slip", or "free".
    profile:
        Manufacturing tolerance profile. Defaults to global profile.
    convex_radius:
        Fillet radius on the 8 outer convex junction edges — where the
        curved arm tip meets the flat arm side (mm).  Set to 0 to skip.
    concave_radius:
        Fillet radius on the 4 inner concave corners — the valleys between
        perpendicular arms (mm).  Set to 0 to skip.
    """

    # ── Hole-specific corner radius defaults ───────────────────────────────
    DEFAULT_CONVEX_RADIUS: float = 0  # Convex junction (arm tip meets flat side)
    DEFAULT_CONCAVE_RADIUS: float = 0.6  # Concave inner corner (valley between arms)

    def __init__(
        self,
        depth: float,
        fit: str = "slip",
        profile: ToleranceProfile | None = None,
        convex_radius: float = DEFAULT_CONVEX_RADIUS,
        concave_radius: float = DEFAULT_CONCAVE_RADIUS,
    ):
        self.depth = depth
        self.convex_radius = convex_radius
        self.concave_radius = concave_radius

        profile = profile or get_profile()
        clearance = getattr(profile, f"{fit}_fit")

        # The profile tolerance is a radial clearance, so diametrical/width
        # features expand by 2 * clearance.
        self.TIP_TO_TIP = AXLE_TIP_TO_TIP + (2 * clearance)
        self.ARM_WIDTH = AXLE_ARM_WIDTH + (2 * clearance)

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
    import cadquery as cq

    depth = 8.0
    hole_cutter = TechnicAxleHole(depth=depth).solid
    main_body = cq.Workplane("XY").circle(8.0 / 2).extrude(depth)
    part = main_body.cut(hole_cutter)
    cq.exporters.export(part, "tmp/technic_axle_hole.step")
    show(part)
