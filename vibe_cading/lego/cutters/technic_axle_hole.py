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
from vibe_cading.print_settings import ToleranceProfile, get_profile
from vibe_cading.lego.constants import (
    AXLE_TIP_TO_TIP,
    AXLE_ARM_WIDTH,
)


class TechnicAxleHole:
    """Lego Technic cross axle hole profile.

    Builds a + cross solid sized to the Technic axle *hole* dimensions.
    Use the :pymeth:`to_cutter` method as a boolean cutter::

        from vibe_cading.lego.cutters.technic_axle_hole import TechnicAxleHole

        hole = TechnicAxleHole(depth=my_thickness, fit="slip")
        part = part.cut(hole.to_cutter())

    The legacy ``.solid`` accessor remains as an alias for backwards
    compatibility and is read-only.

    Through-vs-blind: this cutter is built flush — entry at Z=0 and
    terminal exactly at Z=depth.  Consumers that need a through-hole
    typically construct the cutter with ``depth`` already equal to the
    host body's full thickness, so no class-level overcut is required.

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

    # Cutter is built flush by construction; per-class through/blind policy
    # is degenerate for this class (no extra entry/terminal overcut).
    _THROUGH: bool = False

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
        # Pick the radial allowance off the requested fit grade.
        # ``fit`` is one of "free" / "slip" / "press" → maps directly to
        # the matching FitGrade on the new nested ``ToleranceProfile``.
        grade = getattr(profile, fit)
        clearance = grade.radial

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
                (half_arm + eps, half_arm + eps, self.depth + eps),
            )
            cross = cross.edges(inner_sel).fillet(self.concave_radius)

        # Fillet the remaining outer convex junction edges.
        # After the concave fillet above the only remaining |Z edges are
        # the 8 outer junctions where cylinder arc meets flat arm side.
        if self.convex_radius > 0:
            cross = cross.edges("|Z").fillet(self.convex_radius)

        return cross

    def to_cutter(self, profile: ToleranceProfile | None = None) -> cq.Workplane:
        """Return the + cross cutter solid for boolean subtraction.

        The tolerance profile is consulted at constructor time (via the
        ``fit`` argument) and baked into the geometry.  The call-time
        ``profile`` argument is accepted to satisfy
        :class:`vibe_cading.mechanical.protocols.CutterProtocol` but
        does not re-resolve clearance — pass a different ``profile``
        to ``__init__`` if you need a non-default machine profile.
        """
        return self._solid

    @property
    def solid(self) -> cq.Workplane:
        """Legacy alias for :pymeth:`to_cutter` — returns the cutter solid."""
        return self._solid

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Show a depth-8 axle hole cut into a small Ø8 cylinder."""
        depth = 8.0
        hole_cutter = cls(depth=depth).to_cutter()
        main_body = cq.Workplane("XY").circle(8.0 / 2).extrude(depth)
        part = main_body.cut(hole_cutter)
        return [(part, "TechnicAxleHole demo", "tan")]
