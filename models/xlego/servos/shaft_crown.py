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

"""ShaftCrown — Part 1 of the servo-saver shaft assembly.

Design is based on the sinusoidal helical-ramp cam found in the AX31009
servo-saver kit.  The cam is a continuous annular ramp: its top surface
traces a sinusoid as a function of angle, with two peaks at 90° and 270°.

Printed orientation: spline-socket face (Z=0) on the print bed.
No supports needed.

Run directly to preview in OCP Viewer::

    python3 shaft_crown.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

import cadquery as cq

from models.xlego.servos.cam_utils import (  # noqa: F401 — re-exported
    cut_sinusoidal_cam,
    SPRING_OD, SPRING_ID, SPRING_FREE_HEIGHT, SPRING_PRELOAD, SPRING_GAP,
    CAM_LIFT, CAM_R_INNER, CAM_R_OUTER, CAM_STEPS,
)


# ── ShaftCrown ────────────────────────────────────────────────────────────────

class ShaftCrown:
    """Part 1 — Crown: press-fits onto the SG90 21T servo spline; drives the
    sinusoidal cam joint.

    The spline socket is a smooth cylindrical bore (Ø 4.6 mm) slightly smaller
    than the 4.8 mm spline OD.  When pressed onto the servo, the metal spline
    self-taps into the printed plastic for a secure, zero-backlash grip.

    The cam surface is the **annular top face** of the disc — an annular ring
    (r = CAM_R_INNER → CAM_R_OUTER) whose height varies sinusoidally::

        Z_top(θ) = DISC_HEIGHT + (CAM_LIFT / 2) · (1 − cos(2θ))

    Peaks at θ = 90° and 270°; troughs (Z = DISC_HEIGHT) at θ = 0° and 180°.

    Axial layout (Z = 0 at servo spline tip plane, +Z toward Lego axle):

    =========  ========  ====================================================
    Z range    Height    Zone
    =========  ========  ====================================================
    0 → 2.75   2.75 mm   Spline socket (cylindrical press-fit bore Ø 4.6 mm)
    0 → 4.05   4.05 mm   Solid inner base (r < 3.5 mm)
    2.0 → 4.5  2.5 mm    Sinusoidal cam ramp (annular, r = 3.5 → 5.0 mm)
    =========  ========  ====================================================

    Total assembly height = DISC_HEIGHT (2.0) + ShaftBody height (10.0) = **12.0 mm**.

    Parameters
    ----------
    disc_r
        Outer radius of the disc (mm). Default 5.0.
    inner_disk_height
        Z of the solid inner boss over the socket (mm). Default 4.05.
    disc_height
        Z of the cam trough = top of solid base (mm). Default 2.0.
    spline_socket_depth
        Depth of the cylindrical press-fit socket from Z=0 (mm). Default 2.75.
    spline_bore_r
        Radius of the press-fit bore (mm). Default 2.3 (Ø 4.6 mm).
    shaft_bore_r
        Central through-bore radius (mm). Default 1.5.
    cam_lift
        Peak-to-trough height of the sinusoidal cam ramp (mm). Default 2.5.
    cam_r_inner
        Inner radius of the cam annular zone (mm). Default 3.5.
    cam_r_outer
        Outer radius of the cam annular zone (mm). Default 5.0.
    cam_steps
        Angular segments for the BSpline point grid. Default 72 (= 5°).
    """

    DISC_R: float              = CAM_R_OUTER          # 5.0 mm
    INNER_DISK_HEIGHT: float   = 4.05                 # Z of solid inner boss
    DISC_HEIGHT: float         = 2.0                  # cam trough Z = assembly offset
    SPLINE_SOCKET_DEPTH: float = 2.75                 # socket depth (mm)
    DEFAULT_SPLINE_BORE_R: float = 2.3                # Ø 4.6 mm press-fit bore
    SHAFT_BORE_R: float        = 1.5                  # central through-bore
    CAM_LIFT: float            = CAM_LIFT             # 2.5 mm
    CAM_R_INNER: float         = CAM_R_INNER          # 3.5 mm
    CAM_R_OUTER: float         = CAM_R_OUTER          # 5.0 mm
    CAM_STEPS: int             = CAM_STEPS            # 72 wedges

    SERVO_PROFILES = {
        "SG90": 2.3,            # Generic 9g micro servo (21T, ~4.8mm OD) -> Ø 4.6 mm bore
        "SPMSA370": 2.25,       # Spektrum A370 (20T, ~3.9mm OD) calibrated to Ø 4.5 mm bore for PETG tolerance
    }

    def __init__(
        self,
        servo_profile: str | None  = "SG90",
        spline_bore_r: float | None= None,
        disc_r: float              = DISC_R,
        inner_disk_height: float   = INNER_DISK_HEIGHT,
        disc_height: float         = DISC_HEIGHT,
        spline_socket_depth: float = SPLINE_SOCKET_DEPTH,
        shaft_bore_r: float        = SHAFT_BORE_R,
        cam_lift: float            = CAM_LIFT,
        cam_r_inner: float         = CAM_R_INNER,
        cam_r_outer: float         = CAM_R_OUTER,
        cam_steps: int             = CAM_STEPS,
    ) -> None:
        self.disc_r              = disc_r
        self.inner_disk_height   = inner_disk_height
        self.disc_height         = disc_height
        self.spline_socket_depth = spline_socket_depth

        # Resolve spline bore radius
        if spline_bore_r is not None:
            self.spline_bore_r = spline_bore_r
        elif servo_profile and servo_profile in self.SERVO_PROFILES:
            self.spline_bore_r = self.SERVO_PROFILES[servo_profile]
        else:
            self.spline_bore_r = self.DEFAULT_SPLINE_BORE_R

        self.shaft_bore_r        = shaft_bore_r
        self.cam_lift            = cam_lift
        self.cam_r_inner         = cam_r_inner
        self.cam_r_outer         = cam_r_outer
        self.cam_steps           = cam_steps
        self._solid = self._build()

    # ── build pipeline ─────────────────────────────────────────────────────────

    def _build(self) -> cq.Workplane:
        part = self._full_body()
        part = self._cut_cam_ramp(part)
        part = self._cut_cam_bore(part)
        part = self._restore_inner_disk(part)
        part = self._cut_spline_socket(part)
        part = self._cut_shaft_bore(part)
        return part

    # ── 1. Full cylinder ───────────────────────────────────────────────────────

    def _full_body(self) -> cq.Workplane:
        """Solid cylinder from Z = 0 to cam peak height."""
        # Only extrude up to the top of the cam. The inner disk is added later.
        return (
            cq.Workplane("XY")
            .circle(self.disc_r)
            .extrude(self.disc_height + self.cam_lift)
        )

    # ── 2. Sinusoidal cam ramp (carved from top) ──────────────────────────────

    def _cut_cam_ramp(self, part: cq.Workplane) -> cq.Workplane:
        """Carve the sinusoidal ramp from the cylinder top face.

        Removes material **above** the sinusoidal surface (cut_upward=True),
        leaving peaks at 90° / 270° and troughs at 0° / 180°.
        """
        return cut_sinusoidal_cam(
            part,
            face_z=self.disc_height + self.cam_lift,
            r_inner=self.cam_r_inner,
            r_outer=self.cam_r_outer,
            cam_lift=self.cam_lift,
            steps=self.cam_steps,
            phase=0.0,
            cut_upward=True,
            profile="linear-smoothed",
        )

    # ── 3. Inner bore above inner_disk_height ──────────────────────────────────

    def _restore_inner_disk(self, part: cq.Workplane) -> cq.Workplane:
        """Restore the inner disk area that may have been overcut by the cam ramp."""
        inner_core = (
            cq.Workplane("XY")
            .circle(2.9)  # Small enough to fit inside the ShaftBody shaft
            .extrude(self.inner_disk_height)
        )
        return part.union(inner_core)

    def _cut_cam_bore(self, part: cq.Workplane) -> cq.Workplane:
        """Remove centre material above disc_height (r < cam_r_inner).

        This carves away the solid center down to the disc_height, leaving only the
        inner_disk (r=2.9) up to inner_disk_height.
        """
        # First, remove EVERYTHING inside cam_r_inner down to disc_height
        cut_depth = (self.disc_height + self.cam_lift) - self.disc_height
        if cut_depth > 0:
            bore = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, 0, self.disc_height))
                .circle(self.cam_r_inner)
                .extrude(cut_depth + 1.0)
            )
            part = part.cut(bore)

        return part
    def _cut_spline_socket(self, part: cq.Workplane) -> cq.Workplane:
        """Cylindrical press-fit bore from the bottom face (Z=0)."""
        socket = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -0.1))
            .circle(self.spline_bore_r)
            .extrude(self.spline_socket_depth + 0.1)
        )
        return part.cut(socket)

    # ── 5. Central through-bore ────────────────────────────────────────────────

    def _cut_shaft_bore(self, part: cq.Workplane) -> cq.Workplane:
        """Thin central through-bore through the full height of the crown."""
        max_h = max(self.disc_height + self.cam_lift, self.inner_disk_height)
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -0.1))
            .circle(self.shaft_bore_r)
            .extrude(max_h + 0.2)
        )
        return part.cut(bore)

    # ── public API ─────────────────────────────────────────────────────────────

    @property
    def solid(self) -> cq.Workplane:
        return self._solid


# ── Standalone OCP preview ────────────────────────────────────────────────────

if __name__ == "__main__":
    from ocp_vscode import show

    crown = ShaftCrown()
    bb = crown._solid.val().BoundingBox()
    print(f"ShaftCrown  Z[{bb.zmin:.2f}, {bb.zmax:.2f}]  "
          f"X[{bb.xmin:.2f}, {bb.xmax:.2f}]  Y[{bb.ymin:.2f}, {bb.ymax:.2f}]")

    show(crown.solid, names=["ShaftCrown"], colors=["gold"])
