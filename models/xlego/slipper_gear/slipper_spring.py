"""SlipperPlate — hub disc + spiral leaf springs + dog-bone axle bore."""

from __future__ import annotations

import math
import cadquery as cq

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from models.lego.cutters.technic_axle_hole import TechnicAxleHole

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
        Number of spiral arms.
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
        sweep_angle: float = 160.0,
        ring_inner_r: float = 10.0,
        clearance: float = 0.25,
    ) -> None:
        self.hub_r           = hub_r
        self.plate_thickness = plate_thickness
        self.spring_count    = spring_count
        self.root_thickness  = root_thickness
        self.tip_thickness   = tip_thickness
        self.sweep_angle     = math.radians(sweep_angle)
        self.ring_inner_r    = ring_inner_r
        self.clearance       = clearance

        # Target tip outermost radius
        self.r_max = self.ring_inner_r - self.clearance

        if self.r_max <= self.hub_r + self.root_thickness:
            raise ValueError("Hub + root thickness exceeds available outer radius.")

        self._solid = self._build()

    @property
    def solid(self) -> cq.Workplane:
        return self._solid

    def _arm_profile(self, n_points: int = 50) -> list[tuple[float, float]]:
        """Closed polyline for one spiral arm oriented at 0 degrees."""
        # Inner curve: r_in(t)  = a_in + b_in * t
        # Outer curve: r_out(t) = a_out + b_out * t
        a_in  = self.hub_r
        a_out = self.hub_r + self.root_thickness

        # Outer curve reaches exactly r_max at the tip
        b_out = (self.r_max - a_out) / self.sweep_angle
        # Inner curve reaches r_max - tip_thickness at the tip
        b_in  = ((self.r_max - self.tip_thickness) - a_in) / self.sweep_angle

        pts = []

        # Start sweeping from a negative angle to cleanly embed the base into the hub
        t_start = - (self.root_thickness + 0.5) / b_out

        # Inner curve: from embedded base to tip (CCW)
        for i in range(n_points + 1):
            t = t_start + (self.sweep_angle - t_start) * i / n_points
            r = max(a_in + b_in * t, 0.1) # protect against negative radius crossing origin
            pts.append((r * math.cos(t), r * math.sin(t)))

        # Approximate outward semi-circle cap at the tip
        tip_center_r = self.r_max - (self.tip_thickness / 2.0)
        cap_r = self.tip_thickness / 2.0

        cap_steps = 10
        base_angle = self.sweep_angle
        cx = tip_center_r * math.cos(base_angle)
        cy = tip_center_r * math.sin(base_angle)

        # Cap sweeps from inner curve end (base_angle + pi) outwards to outer curve (base_angle)
        for i in range(1, cap_steps):
            frac = i / cap_steps
            ang = base_angle + math.pi - math.pi * frac
            pts.append((cx + cap_r * math.cos(ang), cy + cap_r * math.sin(ang)))

        # Outer curve: from tip back to embedded base (CW)
        for i in range(n_points, -1, -1):
            t = t_start + (self.sweep_angle - t_start) * i / n_points
            r = max(a_out + b_out * t, 0.1)
            pts.append((r * math.cos(t), r * math.sin(t)))

        return pts

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
                .rotate((0, 0, 0), (0, 0, 1), angle_deg)
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
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
    from ocp_vscode import show

    p = SlipperSpring()
    show(p.solid, names=["Spiral SlipperSpring"])
