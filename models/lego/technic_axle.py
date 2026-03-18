import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cadquery as cq
from models.lego.constants import (
    AXLE_TIP_TO_TIP,
    AXLE_ARM_WIDTH,
    AXLE_ARM_PROTRUSION,
    AXLE_LENGTH_PER_STUD,
    DEFAULT_LEAD_IN,
    DEFAULT_CORNER_RADIUS,
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

    # ── Dimensions sourced from models.lego.constants ─────────────────────────────
    TIP_TO_TIP: float = AXLE_TIP_TO_TIP
    ARM_WIDTH: float = AXLE_ARM_WIDTH
    ARM_PROTRUSION: float = AXLE_ARM_PROTRUSION
    LENGTH_PER_STUD: float = AXLE_LENGTH_PER_STUD
    DEFAULT_CLEARANCE: float = 0.0
    DEFAULT_LEAD_IN: float = DEFAULT_LEAD_IN
    DEFAULT_CORNER_RADIUS: float = DEFAULT_CORNER_RADIUS

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

        # Cylinder gives the rounded outer boundary (arm tips curve with radius = TIP_TO_TIP/2)
        cylinder = (
            cq.Workplane("XY")
            .circle(self.tip_to_tip / 2)
            .extrude(length)
        )

        # Two rectangular prisms form the + cross mask
        arm_h = (
            cq.Workplane("XY")
            .rect(self.tip_to_tip, self.arm_width)
            .extrude(length)
        )
        arm_v = (
            cq.Workplane("XY")
            .rect(self.arm_width, self.tip_to_tip)
            .extrude(length)
        )

        # Intersect cylinder with cross mask → curved-tip + cross (like the real axle)
        cross = cylinder.intersect(arm_h.union(arm_v))

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


if __name__ == "__main__":
    from ocp_vscode import show

    axle = TechnicAxle(studs=3)
    show(axle.solid)
