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
from vibe_cading.cq_utils import axle_cross_section
from vibe_cading.lego.constants import (
    AXLE_TIP_TO_TIP,
    AXLE_ARM_WIDTH,
    AXLE_ARM_PROTRUSION,
    AXLE_LENGTH_PER_STUD,
    LEAD_IN,
    CORNER_RADIUS,
)


class TechnicAxle:
    """Lego Technic cross axle.

    Parameters
    ----------
    studs:
        Length of the axle expressed in stud units (e.g. 3 → 24 mm).
        When omitted the axle object carries profile dimensions only
        and no CadQuery solid is built.
    clearance:
        Clearance deducted from the profile for a sliding fit in 
        tight assemblies. Defaults to 0 mm.
    lead_in:
        Chamfer size on both end faces for easy sliding. Defaults to 0.3 mm.
    corner_radius:
        Fillet radius for inner concave corners. Defaults to 0.4 mm.
    """

    # ── Dimensions sourced from vibe_cading.lego.constants ─────────────────────────────
    TIP_TO_TIP: float = AXLE_TIP_TO_TIP
    ARM_WIDTH: float = AXLE_ARM_WIDTH
    ARM_PROTRUSION: float = AXLE_ARM_PROTRUSION
    LENGTH_PER_STUD: float = AXLE_LENGTH_PER_STUD
    DEFAULT_CLEARANCE: float = 0.0
    DEFAULT_LEAD_IN: float = LEAD_IN
    DEFAULT_CORNER_RADIUS: float = CORNER_RADIUS

    def __init__(self, studs: int | None = None, clearance: float = DEFAULT_CLEARANCE, lead_in: float = DEFAULT_LEAD_IN, corner_radius: float = DEFAULT_CORNER_RADIUS):
        self.studs = studs
        self.clearance = clearance
        self.lead_in = lead_in
        self.corner_radius = corner_radius

        # Apply clearance directly to the profile dimensions so the solid shrinks
        self.tip_to_tip: float = self.TIP_TO_TIP - clearance
        self.arm_width: float = self.ARM_WIDTH - clearance
        self.length: float | None = (
            studs * self.LENGTH_PER_STUD if studs is not None else None
        )

        self._solid: cq.Workplane | None = None
        if studs is not None:
            self._solid = self._build()

    # ── Clearance-adjusted profile ───────────────────────────────────────────
    @property
    def bore_tip_to_tip(self) -> float:
        """Tip-to-tip with clearance applied."""
        return self.tip_to_tip

    @property
    def bore_arm_width(self) -> float:
        """Arm width with clearance applied."""
        return self.arm_width

    # ── CadQuery solid ────────────────────────────────────────────────────────
    def _build(self) -> cq.Workplane:
        """Build the + cross-section axle solid with lead-in chamfers on both ends."""
        length = self.length  # guaranteed non-None when _build is called

        # Curved-tip + cross (like the real axle): cylinder ∩ cross mask.
        # Shared construction — see vibe_cading.cq_utils.axle_cross_section.
        cross = axle_cross_section(self.tip_to_tip, self.arm_width, length)

        # Fillet the 4 inner concave corners (the only remaining vertical edges after intersect)
        if self.corner_radius > 0:
            cross = cross.edges("|Z").fillet(self.corner_radius)

        # Chamfer the perimeter edges on both end faces for easy sliding
        if self.lead_in > 0:
            cross = (
                cross
                .faces(">Z").edges().chamfer(self.lead_in)
                .faces("<Z").edges().chamfer(self.lead_in)
            )

        return cross

    @property
    def solid(self) -> cq.Workplane:
        """The CadQuery solid. Raises if no stud length was specified."""
        if self._solid is None:
            raise ValueError(
                "No solid: create TechnicAxle with a studs argument to build geometry."
            )
        return self._solid
