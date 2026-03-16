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
    clearance : float
        Radial gap between the unwound spring tip and the ring inner bore (mm).
    """

    def __init__(
        self,
        hub_r: float = 6.0,
        plate_thickness: float = 5.4,
        spring_count: int = 3,
        root_thickness: float = 1.2,
        tip_thickness: float = 0.5,
        sweep_angle: float | None = None,
        ring_inner_r: float = 10.0,
        clearance: float = 0.25,
        b_out: float | None = None,
        arm_rotation_offset: float = 0.0,
    ) -> None:
        self.hub_r           = hub_r
        self.plate_thickness = plate_thickness
        self.spring_count    = spring_count
        self.root_thickness  = root_thickness
        self.tip_thickness   = tip_thickness

        self.ring_inner_r    = ring_inner_r
        self.clearance       = clearance
        self.arm_rotation_offset = arm_rotation_offset

        # Target tip outermost radius
        self.r_max = self.ring_inner_r - self.clearance

        if self.r_max <= self.hub_r + self.root_thickness:
            raise ValueError("Hub + root thickness exceeds available outer radius.")

        if sweep_angle is None:
            if b_out is not None:
                # Force outer spiral pitch to match `b_out`
                a_out = self.hub_r + self.root_thickness

                # Math gives the exact sweep angle to reach the pocket_r.
                # However, the physical arm finishes with a rounded semi-circle cap across its
                # `tip_thickness`. This cap protrudes outwards radially beyond the mathematical stopping
                # point. If we don't subtract the angular equivalent of the cap, it will physically clip
                # into the vertical drop-off wall of the gear's ramp (the hook).
                # The radius of the cap is tip_thickness / 2.0. The angular overshoot is approx
                # cap_radius / (circumference roughly) but practically it's about 1.5 to 2.0 degrees on an 8mm gear.

                raw_sweep_rad = (self.r_max - a_out) / b_out
                cap_r = self.tip_thickness / 2.0
                # Using the angular approximation of that cap given the current radius
                angular_overshoot_rad = cap_r / self.r_max

                sweep_angle = math.degrees(raw_sweep_rad - angular_overshoot_rad)
            else:
                # Auto-calculate sweep angle to maintain consistent overlap proportions
                # For 3 arms (120 pitch), 160 deg was optimal (1.33x pitch)
                # This works out to (360 / count) + 40
                sweep_angle = (360.0 / spring_count) + 40.0

        self.sweep_angle = math.radians(sweep_angle)

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
            r_start=self.hub_r,
            r_end=self.r_max,
            width_start=self.root_thickness,
            width_end=self.tip_thickness,
            sweep_angle=self.sweep_angle,
            angle_start=0.0,
            n_points=n_points,
            r_start_draw=max(0.1, self.hub_r - 0.2)
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
        # We select the edges that connect the arms to the hub. Since CQ's edge
        # selection can be tricky, we select Z-aligned edges near the hub.
        z_edges = hub.edges("|Z")
        hub_r_min = self.hub_r - 0.2
        hub_r_max = self.hub_r + self.root_thickness + 0.2


        def is_root_edge(e) -> bool:
            c = e.Center()
            r = math.hypot(c.x, c.y)
            return (self.hub_r - 0.5) <= r <= (self.hub_r + 1.5)

        root_edge_objs = [e for e in z_edges.vals() if is_root_edge(e)]
        if root_edge_objs:
            try:
                hub = hub.objects([e for e in root_edge_objs]).fillet(0.8)
            except Exception:
                pass # skip if filleting fails

        return hub

if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
    from ocp_vscode import show

    p = SlipperSpring()
    show(p.solid, names=["Spiral SlipperSpring"])
