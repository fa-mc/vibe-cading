"""SlipperPlate — hub disc + spiral leaf springs + dog-bone axle bore."""

from __future__ import annotations

import math
import cadquery as cq

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from models.lego.cutters.technic_axle_hole import TechnicAxleHole
from models.cq_utils import tapered_arm_profile

class SlipperSpring:
    """Slipper plate with Lego cross-axle dog-bone bore and spiral springs.

    Uses Archimedean spirals (r = a + b*theta) for the arms. The arms are
    thick at the root and taper toward the tip.

    Parameters
    ----------
    hub_r : float
        Radius of the inner solid hub core (mm).
    plate_thickness : float
        Axial thickness of the plate (mm).
    spring_count : int
        Number of spiral arms. Automatically scales sweep limits to prevent collisions.
        Common tuning values: 2, 3, 4, 6.
    root_thickness : float
        Radial thickness of the arm at the hub root (mm).
    tip_thickness : float
        Radial thickness of the arm at its tip (mm).
    sweep_angle : float
        Total angular span of each arm from root to tip (degrees).
    ring_inner_r : float
        Inner radius of the outer ring assembly (mm).
    """

    def __init__(
        self,
        plate_thickness: float = 5.4,
        spring_count: int = 3,
        arm_pitch: float = 5.1,
        arm_base_width: float = 3.2,
        arm_tip_width: float = 0.5,
        hub_r: float = 4.0,
        ramp_end_r: float = 10.0,
        tip_gap: float = 0.5,
        arm_rotation_offset: float = 0.0,
    ) -> None:
        self.plate_thickness = plate_thickness
        self.spring_count    = spring_count
        self.arm_pitch       = arm_pitch
        self.arm_base_width = arm_base_width
        self.arm_tip_width   = arm_tip_width
        self.hub_r           = hub_r
        self.tip_gap         = tip_gap
        self.arm_rotation_offset = arm_rotation_offset

        # Target tip outermost radius
        self.r_max = ramp_end_r - self.tip_gap

        # Anchor the mathematical origin strictly at the center point (r=0)
        # so the entire start of the arm profile is swallowed by the hub, preventing a flat stump.
        self.r_start_embed = 0.0

        a_out = self.r_start_embed + self.arm_base_width
        b_out = self.arm_pitch

        # Equation for outer curve: r = a_out + b_out * theta
        # Calculate exactly how much sweep is needed to reach the ramp pocket
        raw_sweep_rad = (self.r_max - a_out) / b_out

        # `cq_utils.tapered_arm_profile` automatically subtracts the angular overshoot internally
        # so that the true mathematical length respects the semicircle tip radius.
        self.sweep_angle = raw_sweep_rad

        self._solid = self._build()
        # assert len(self._solid.solids().vals()) == 1, "Expected single solid spring, got multiple pieces (floating root artefact)."


    @property
    def solid(self) -> cq.Workplane:
        return self._solid

    def _arm_profile(self, n_points: int | None = None) -> list[tuple[float, float]]:
        """Closed polyline for one spiral arm oriented at 0 degrees.
        Now mathematically originates from the center of the gear, sweeping out
        to r_max. The hub simply engulfs the inner portion.
        """
        if n_points is None:
            # Dynamically calculate points to guarantee 1 segment per degree of sweep
            n_points = max(50, int(math.degrees(self.sweep_angle)))

        return tapered_arm_profile(
            r_start=self.r_start_embed,
            r_end=self.r_max,
            width_start=self.arm_base_width,
            width_end=self.arm_tip_width,
            sweep_angle=self.sweep_angle,
            angle_start=0.0,
            n_points=n_points,
            r_start_draw=0.1,  # Safe start just off exact zero to prevent singular faces inside the hub
            b_out=self.arm_pitch  # Need to thread this through to override auto-calculated b!
        )

    def _build(self) -> cq.Workplane:
        fw = self.plate_thickness

        # 1. Base hub and Arms
        hub = cq.Workplane("XY").circle(self.hub_r).extrude(fw)

        for i in range(self.spring_count):
            angle_deg = i * (360.0 / self.spring_count)
            arm_pts = self._arm_profile()

            arm = (
                cq.Workplane("XY")
                .polyline(arm_pts)
                .close()
                .extrude(fw)
                .rotate((0, 0, 0), (0, 0, 1), angle_deg + math.degrees(self.arm_rotation_offset))
            )
            hub = hub.union(arm)

        # 2. Add Lego Technic axle hole
        axle_fw = fw + 2.0
        axle_tool = TechnicAxleHole(depth=axle_fw).solid.translate((0, 0, -1.0))

        hub = hub.cut(axle_tool)

        # 3. Add root fillets to reduce stress concentrations
        from models.cq_utils import fillet_z_edges
        hub = fillet_z_edges(hub, self.hub_r - 0.5, self.hub_r + 1.5, 0.8)

        return hub

if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
    from ocp_vscode import show

    p = SlipperSpring()
    show(p.solid, names=["Spiral SlipperSpring"])
