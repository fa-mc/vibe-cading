"""ShaftBody — Part 2 of the servo-saver shaft assembly.

Printed orientation: cam-valley face (bottom) flat on the print bed.
No supports needed.

The spring (Ø 10.03 OD / Ø 6.9 ID / 6 mm free height, AX31009) wraps
around the thin shaft section, pre-compressed 1 mm between the flange and
the underside of the servo case wall.

The cam valleys on the bottom face are the exact inverse of the sinusoidal
ramp on ShaftCrown: when deflected, the crown peaks slide into the body's
valleys, compressing the spring; on release the spring restores alignment.

Run directly to preview in OCP Viewer::

    python3 shaft_body.py
"""

from __future__ import annotations

import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

import cadquery as cq

from xlego.servos.shaft_crown import ShaftCrown
from xlego.servos.cam_utils import (
    cut_sinusoidal_cam,
    CAM_LIFT,
    CAM_R_INNER,
    CAM_R_OUTER,
    CAM_STEPS,
    SPRING_ID,
    SPRING_GAP,
)
from lego.cutters.technic_axle_hole import TechnicAxleHole


class ShaftBody:
    """Part 2 — Body: driven by the sinusoidal cam joint; outputs a Lego axle.

    The bottom face carries sinusoidal valley recesses that are the exact
    complement of the ShaftCrown ramp — both use the same depth function
    (``phase=0``).  The crown cuts downward from its top face; the body cuts
    upward from its bottom face.  This ensures the two surfaces nest flush
    at every angle with zero gap.

    The valley annular zone matches the crown ramp zone exactly
    (r = CAM_R_INNER → CAM_R_OUTER).

    Axial layout (Z = 0 at bottom face = cam-valley opening):

    =========  =======  =====================================================
    Z range    Height   Zone
    =========  =======  =====================================================
    0 → 5.0    5.0 mm   Cam base disc / spring seat (r = 5.0 mm)
    5.0 → 10.0 5.0 mm   Thin shaft (spring wraps here)
    =========  =======  =====================================================

    Total body height: 10.0 mm.
    Cam valleys are carved downward from the cam-base top (Z = cam_lift)
    toward the bottom face (Z = 0) using ``cut_sinusoidal_cam``.

    Assembled offset: ShaftBody Z = 0 sits at world Z = ShaftCrown.DISC_HEIGHT
    (2.0 mm).  Assembly total = 2.0 + 10.0 = **12.0 mm**.

    Parameters
    ----------
    shaft_r
        Radius of the thin shaft (mm). Default 3.4 (clears AX31009 spring ID).
    shaft_height
        Height of the thin shaft section (mm). Default 5.0.
    cam_lift
        Peak-to-trough cam lift (mm). Must match ShaftCrown. Default 2.5.
        Also determines the valley cutout height.
    cam_base_thickness
        Minimum thickness of the cam base disc at the valley thorough (mm). Default 2.5.
    cam_r_inner
        Inner radius of the cam annular zone (mm). Default 3.5.
    cam_r_outer
        Outer radius of the cam annular zone / disc (mm). Default 5.0.
    cam_steps
        Angular segments for the BSpline point grid. Default 72.
    """

    SHAFT_R: float            = 3.4
    SHAFT_HEIGHT: float       = 5.0
    CAM_LIFT: float           = CAM_LIFT
    CAM_BASE_THICKNESS: float = 2.5
    CAM_R_INNER: float        = CAM_R_INNER
    CAM_R_OUTER: float        = CAM_R_OUTER
    CAM_STEPS: int            = CAM_STEPS

    def __init__(
        self,
        shaft_r: float            = SHAFT_R,
        shaft_height: float       = SHAFT_HEIGHT,
        cam_lift: float           = CAM_LIFT,
        cam_base_thickness: float = CAM_BASE_THICKNESS,
        cam_r_inner: float        = CAM_R_INNER,
        cam_r_outer: float        = CAM_R_OUTER,
        cam_steps: int            = CAM_STEPS,
    ) -> None:
        self.shaft_r            = shaft_r
        self.shaft_height       = shaft_height
        self.cam_lift           = cam_lift
        self.cam_base_thickness = cam_base_thickness
        self.cam_r_inner        = cam_r_inner
        self.cam_r_outer        = cam_r_outer
        self.cam_steps          = cam_steps
        self._solid = self._build()

    # ── derived Z positions ────────────────────────────────────────────────────

    @property
    def _shaft_base_z(self) -> float:
        return self.cam_lift + self.cam_base_thickness               # 2.5 + 2.5 = 5.0

    @property
    def _total_height(self) -> float:
        return self._shaft_base_z + self.shaft_height                # 5.0 + 5.0 = 10.0

    # ── build pipeline ─────────────────────────────────────────────────────────

    def _build(self) -> cq.Workplane:
        part = self._main_body()
        part = self._cut_cam_valleys(part)
        part = self._cut_clearance_bore(part)
        part = self._cut_axle_hole(part)
        return part

    # ── 1. Main body (cam base + shaft) ──────────────────────────────────────

    def _main_body(self) -> cq.Workplane:
        """Build the body as stacked cylinders unioned together.

        The cam base disc (r = cam_r_outer, h = cam_lift + cam_base_thickness) doubles as the
        spring-seat flange.  The sinusoidal valleys are carved from it in
        the next step.
        """
        # Cam base disc (also the spring seat)
        body = (
            cq.Workplane("XY")
            .circle(self.cam_r_outer)
            .extrude(self._shaft_base_z)
        )
        # Thin shaft (spring wraps around this)
        shaft = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, self._shaft_base_z))
            .circle(self.shaft_r)
            .extrude(self.shaft_height)
        )
        return body.union(shaft)

    # ── 2. Sinusoidal cam valleys (bottom face) ───────────────────────────────

    def _cut_cam_valleys(self, part: cq.Workplane) -> cq.Workplane:
        """Carve sinusoidal valleys into the cam base disc.

        Uses ``phase=0`` (same as the crown) so the valley profile is the
        exact complement of the crown ramp — surfaces nest flush at every
        angle.  ``cut_upward=False`` removes material **below** the
        sinusoidal surface, carving valleys that open downward.
        """
        return cut_sinusoidal_cam(
            part,
            face_z=self.cam_lift,
            r_inner=self.cam_r_inner,
            r_outer=self.cam_r_outer,
            cam_lift=self.cam_lift,
            steps=self.cam_steps,
            phase=0.0,
            cut_upward=False,
            profile="linear-smoothed",
        )

    # ── 3. Clearance bore for Crown inner disk ───────────────────────────

    def _cut_clearance_bore(self, part: cq.Workplane) -> cq.Workplane:
        """Remove the central cylinder to avoid collision with Crown's inner disk.

        The ShaftCrown now has an inner disk up to Z=4.05 mm (in its coords).
        Given the base offset of 2.0 mm, this sticks up 2.05 mm into the body.
        The bore has radius 3.0 (sufficient for Crown's r=2.9 disk) and reaches a bit above Z=2.05.
        """
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -0.1))
            .circle(3.0)
            .extrude(2.05 + 0.2)
        )
        return part.cut(bore)

    # ── 4. Lego Technic axle cross-hole ───────────────────────────────────────

    def _cut_axle_hole(self, part: cq.Workplane) -> cq.Workplane:
        """Bore a Lego Technic cross-axle hole along −Z from the top face.

        The Lego axle inserts from the top face of the shaft downward. The hole
        is 8 mm deep (= 1 Lego stud), reaching Z = 0.0 mm.  The cutter is
        rotated 45° about Z so its cross arms land at 45°/135°/225°/315°,
        between the cam valleys which peak at 90°/270°.  The 45° arms and the
        90°/270° valleys are 45° apart — no interference with the cam surface.
        """
        hole_depth = 8.0   # mm — 1 Lego stud
        top_z = self._total_height  # 8.0 mm

        axle_hole = TechnicAxleHole(depth=hole_depth)
        # 45° rotation → arms at 45°/135°/225°/315°, clear of cam valleys at 90°/270°
        cutter = (
            axle_hole.solid
            .rotate((0, 0, 0), (0, 0, 1), 45)
            .translate((0, 0, top_z - hole_depth))
        )
        return part.cut(cutter)

    # ── public API ─────────────────────────────────────────────────────────────

    @property
    def solid(self) -> cq.Workplane:
        return self._solid


# ── Standalone OCP preview ────────────────────────────────────────────────────

if __name__ == "__main__":
    from ocp_vscode import show

    body = ShaftBody()
    bb = body._solid.val().BoundingBox()
    print(f"ShaftBody  Z[{bb.zmin:.2f}, {bb.zmax:.2f}]  "
          f"X[{bb.xmin:.2f}, {bb.xmax:.2f}]  Y[{bb.ymin:.2f}, {bb.ymax:.2f}]")

    show(body.solid, names=["ShaftBody"], colors=["royalblue"])
