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

"""SlipperRing — outer gear ring: involute spur teeth on OD, directional ramp bore on ID."""

from __future__ import annotations

import math
import cadquery as cq
from models.cq_utils import archimedean_spiral_arc

class SlipperRing:
    """Outer gear ring: involute spur teeth on OD, directional ramp bore on ID.

    Parameters
    ----------
    module : float
        Gear module m (pitch diameter / teeth).
    teeth : int
        Number of teeth.
    face_width : float
        Axial height (mm).
    pressure_angle : float
        Pressure angle (degrees).
    n_flank : int
        Involute flank sample points per side.
    ramp_end_r : float
        Maximum inner radius (in the pocket) where the spring tip can expand (mm).
    ramp_start_r : float
        Minimum inner radius (on the ridges) that compresses the spring arm (mm).
    ramp_count : int
        Number of directional saw-tooth ramps matching the spring arms.
    sag_r : float
        Radius of the recessed counterbore for the plate to sink into (mm).
    sag_depth : float
        Depth of the counterbore on each side (mm).
    """

    def __init__(
        self,
        module: float = 1.0,
        teeth: int = 24,
        face_width: float = 8.0,
        pressure_angle: float = 20.0,
        n_flank: int = 32,
        ramp_end_r: float = 10.0,
        ramp_curve_type: str = "archimedean",
        ramp_start_r: float = 8.0,
        ramp_count: int = 12,
        sag_r: float = 10.5,
        sag_depth: float = 1.2,
    ) -> None:
        self.module         = module
        self.teeth          = teeth
        self.face_width     = face_width
        self.pressure_angle = pressure_angle

        self.ramp_end_r     = ramp_end_r
        self.ramp_curve_type = ramp_curve_type
        self.ramp_start_r   = ramp_start_r
        self.ramp_count     = ramp_count
        self.sag_r          = sag_r
        self.sag_depth      = sag_depth
        self._n_flank       = n_flank

        phi = math.radians(pressure_angle)
        m, z = module, teeth
        self.pitch_radius = m * z / 2.0
        self.base_radius  = self.pitch_radius * math.cos(phi)
        self.tip_radius   = self.pitch_radius + m
        self.root_radius  = self.pitch_radius - 1.25 * m

        self._solid = self._build()

    @property
    def solid(self) -> cq.Workplane:
        return self._solid

    # --- Systematic Ramp Mathematics ---
    @property
    def cycle_angle(self) -> float:
        """Total angular span of one tooth cycle in radians."""
        return 2.0 * math.pi / int(self.ramp_count)

    @property
    def hook_angle(self) -> float:
        """Angular span of the steep drop-off hook.

        Scales dynamically with ramp_count. Base baseline is 10 degrees at 3 ramps (120 degree cycle).
        """
        scale = self.cycle_angle / math.radians(120.0)
        return math.radians(10.0) * scale

    @property
    def ramp_span(self) -> float:
        """Angular span of the actual sloped ramp contact area in radians."""
        return self.cycle_angle - self.hook_angle

    @property
    def b_out(self) -> float:
        """The calculated Archimedean pitch (delta Radius / delta Theta) for the ramp cut.

        Used by the main assembly to perfectly synchronize the spring arm's outer profile (r = a + b_out * theta).
        """
        return (self.ramp_end_r - self.ramp_start_r) / self.ramp_span

    # ── Involute helpers (identical to SpurGear) ──────────────────────────────

    @staticmethod
    def _involute(t: float, r_base: float) -> tuple[float, float]:
        return (
            r_base * (math.cos(t) + t * math.sin(t)),
            r_base * (math.sin(t) - t * math.cos(t)),
        )

    @staticmethod
    def _rotate_pt(pt: tuple[float, float], angle: float) -> tuple[float, float]:
        c, s = math.cos(angle), math.sin(angle)
        return (c * pt[0] - s * pt[1], s * pt[0] + c * pt[1])

    def _gear_profile_points(
        self, n_flank: int, n_tip: int = 6, n_root: int = 6
    ) -> list[tuple[float, float]]:
        """Full CCW gear cross-section matching SpurGear algorithm."""
        z   = self.teeth
        phi = math.radians(self.pressure_angle)
        r_b = self.base_radius
        r_a = self.tip_radius
        r_f = self.root_radius

        inv_phi     = math.tan(phi) - phi
        t_tip       = math.sqrt((r_a / r_b) ** 2 - 1)
        inv_at_tip  = t_tip - math.atan(t_tip)
        pitch_angle = 2.0 * math.pi / z
        half_base   = math.pi / (2.0 * z) + inv_phi

        if r_f >= r_b:
            t_root   = math.sqrt((r_f / r_b) ** 2 - 1)
            use_stub = False
        else:
            t_root   = 0.0
            use_stub = True

        pts: list[tuple[float, float]] = []

        for i in range(z):
            tc       = i * pitch_angle
            theta_rb = tc - half_base
            theta_lb = tc + half_base
            theta_rt = tc - half_base + inv_at_tip
            theta_lt = tc + half_base - inv_at_tip
            theta_nr = tc + pitch_angle - half_base

            if use_stub:
                pts.append((r_f * math.cos(theta_rb), r_f * math.sin(theta_rb)))

            for j in range(n_flank):
                t = t_root + (t_tip - t_root) * j / (n_flank - 1)
                pts.append(self._rotate_pt(self._involute(t, r_b), tc - half_base))

            for j in range(1, n_tip + 1):
                theta = theta_rt + (theta_lt - theta_rt) * j / n_tip
                pts.append((r_a * math.cos(theta), r_a * math.sin(theta)))

            for j in range(1, n_flank):
                t = t_tip - (t_tip - t_root) * j / (n_flank - 1)
                p = self._involute(t, r_b)
                pts.append(self._rotate_pt((p[0], -p[1]), tc + half_base))

            if use_stub:
                pts.append((r_f * math.cos(theta_lb), r_f * math.sin(theta_lb)))

            for j in range(1, n_root):
                theta = theta_lb + (theta_nr - theta_lb) * j / n_root
                pts.append((r_f * math.cos(theta), r_f * math.sin(theta)))

        return pts

    # ── Ramp bore profile ─────────────────────────────────────────────────────

    @staticmethod
    def _fillet_corner(A: tuple[float, float], B: tuple[float, float], C: tuple[float, float], R: float, steps: int = 5):
        ux = A[0] - B[0]; uy = A[1] - B[1]
        lu = math.hypot(ux, uy)
        if lu == 0: return [B], 0.0
        ux /= lu; uy /= lu

        vx = C[0] - B[0]; vy = C[1] - B[1]
        lv = math.hypot(vx, vy)
        if lv == 0: return [B], 0.0
        vx /= lv; vy /= lv

        dot = max(-1.0, min(1.0, ux * vx + uy * vy))
        theta_angle = math.acos(dot)
        if theta_angle < 0.01 or theta_angle > math.pi - 0.01:
            return [B], 0.0

        d = R / math.tan(theta_angle / 2.0)
        if d > lu * 0.49 or d > lv * 0.49:
            d = min(lu * 0.49, lv * 0.49)
            R = d * math.tan(theta_angle / 2.0)

        T1 = (B[0] + d * ux, B[1] + d * uy)
        T2 = (B[0] + d * vx, B[1] + d * vy)

        dc = R / math.sin(theta_angle / 2.0)
        dir_cx = (ux + vx); dir_cy = (uy + vy)
        ld = math.hypot(dir_cx, dir_cy)
        dir_cx /= ld; dir_cy /= ld

        Center = (B[0] + dc * dir_cx, B[1] + dc * dir_cy)

        a1 = math.atan2(T1[1] - Center[1], T1[0] - Center[0])
        a2 = math.atan2(T2[1] - Center[1], T2[0] - Center[0])

        diff = (a2 - a1) % (2 * math.pi)
        if diff > math.pi:
            diff -= 2 * math.pi

        out = []
        for i in range(steps + 1):
            frac = i / steps
            a = a1 + diff * frac
            out.append((Center[0] + R * math.cos(a), Center[1] + R * math.sin(a)))
        return out, d

    def _ramp_profile_points(self) -> list[tuple[float, float]]:
        """CCW closed profile for the ring bore with directional saw-tooth ramps
        and an angled hook to prevent the rounded spring tip from slipping.
        """
        n_r = int(self.ramp_count)

        # Systematically pull math from class properties to guarantee sync with the spring
        cycle = self.cycle_angle
        hook_angle = self.hook_angle
        ramp_span = self.ramp_span
        b = self.b_out

        ramp_end_r = self.ramp_end_r
        ramp_start_r = self.ramp_start_r

        pts: list[tuple[float, float]] = []
        n_ramp = max(90, int(math.degrees(ramp_span)))

        for i in range(n_r):
            theta_start = i * cycle                  # inner root
            theta_end   = theta_start + ramp_span    # outer pocket edge
            theta_next  = (i + 1) * cycle            # next inner root

            theta_prev_end = theta_start - hook_angle

            # Introduce an undercut "hook" by burying the pocket bottom
            undercut_angle = 0.0  # Explicitly zeroed to prevent backward hooks
            theta_pocket_curr = theta_end - undercut_angle
            theta_pocket_prev = theta_prev_end - undercut_angle

            Root_curr = (ramp_start_r * math.cos(theta_start), ramp_start_r * math.sin(theta_start))
            Tip_curr  = (ramp_end_r * math.cos(theta_end), ramp_end_r * math.sin(theta_end))
            Pocket_curr = (ramp_start_r * math.cos(theta_pocket_curr), ramp_start_r * math.sin(theta_pocket_curr))
            Root_next = (ramp_start_r * math.cos(theta_next), ramp_start_r * math.sin(theta_next))

            # The 'prev' values are used to compute the incoming fillet for Root_curr
            Pocket_prev = (ramp_start_r * math.cos(theta_pocket_prev), ramp_start_r * math.sin(theta_pocket_prev))

            dx_start = b * math.cos(theta_start) - ramp_start_r * math.sin(theta_start)
            dy_start = b * math.sin(theta_start) + ramp_start_r * math.cos(theta_start)
            Tang_start = (Root_curr[0] + dx_start, Root_curr[1] + dy_start)

            dx_end = b * math.cos(theta_end) - ramp_end_r * math.sin(theta_end)
            dy_end = b * math.sin(theta_end) + ramp_end_r * math.cos(theta_end)
            Tang_end = (Tip_curr[0] - dx_end, Tip_curr[1] - dy_end)

            global_sweep = (ramp_end_r - 0.1) / b
            t_draw_start = (ramp_start_r - 0.1) / b

            spiral_pts = archimedean_spiral_arc(
                r_start=0.1,
                r_end=ramp_end_r,
                angle_start=theta_start - t_draw_start,
                sweep_angle=global_sweep,
                n_points=n_ramp,
                r_start_draw=ramp_start_r
            )

            # Fillets with true geometric tangents matching the spiral equations
            # For root, we arrive from Pocket_prev
            root_arc, d_root = self._fillet_corner(Pocket_prev, Root_curr, Tang_start, R=0.6, steps=24)
            # For tip, we depart to Pocket_curr. Make it slightly more rounded.
            tip_arc, d_tip   = self._fillet_corner(Tang_end, Tip_curr, Pocket_curr, R=0.5, steps=24)

            # For the pocket bottom, we arrive from Tip_curr and depart along the ramp_start_r arc
            # We use Root_next as the tangency guide so _fillet_corner can accurately bound the geometry without overshooting
            pocket_arc, d_pocket = self._fillet_corner(Tip_curr, Pocket_curr, Root_next, R=0.6, steps=24)

            pts.extend(root_arc)
            for pt in spiral_pts:
                # Exclude internal overlapping points covered by fillets
                if math.hypot(pt[0] - Root_curr[0], pt[1] - Root_curr[1]) < d_root:
                    continue
                if math.hypot(pt[0] - Tip_curr[0], pt[1] - Tip_curr[1]) < d_tip:
                    continue
                pts.append(pt)
            pts.extend(tip_arc)
            pts.extend(pocket_arc)

            # Now we add the flat hook pocket bottom connecting Pocket_curr to Root_next
            pocket_steps = 12
            for j in range(0, pocket_steps):
                f = j / pocket_steps
                th = theta_pocket_curr + f * (theta_next - theta_pocket_curr)
                px, py = ramp_start_r * math.cos(th), ramp_start_r * math.sin(th)
                if math.hypot(px - Pocket_curr[0], py - Pocket_curr[1]) < d_pocket:
                    continue
                if math.hypot(px - Root_next[0], py - Root_next[1]) < d_root:
                    continue
                pts.append((px, py))

        return pts

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build(self) -> cq.Workplane:
        n_tip  = max(2, self._n_flank // 8)
        n_root = max(3, self._n_flank // 8)
        gear_pts = self._gear_profile_points(self._n_flank, n_tip, n_root)

        ring = (
            cq.Workplane("XY")
            .polyline(gear_pts)
            .close()
            .extrude(self.face_width)
        )

        # Add top and bottom counterbore sags for the plates FIRST, it avoids complicated OCC boolean edge cases
        # with the intricate bore cut.
        if self.sag_depth > 0:
            sag_cut_bot = cq.Workplane("XY").circle(self.sag_r).extrude(self.sag_depth + 1.0)
            sag_cut_top = cq.Workplane("XY").circle(self.sag_r).extrude(self.sag_depth + 1.0)

            # Bottom sag (cut upwards from below z=0)

            ring = ring.cut(sag_cut_bot.translate((0, 0, -1.0)))
            # Top sag (cut upwards intersecting top face)
            ring = ring.cut(sag_cut_top.translate((0, 0, self.face_width - self.sag_depth)))

        # Inner bore with directional ramp profile
        ramp_pts = self._ramp_profile_points()
        bore = (
            cq.Workplane("XY")
            .polyline(ramp_pts)
            .close()
            .extrude(self.face_width + 2.0)
        )


        ring = ring.cut(bore.translate((0, 0, -1.0)))

        return ring


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
    from ocp_vscode import show

    r = SlipperRing(
        module=2.0, teeth=24, face_width=8.0, pressure_angle=20.0,
        n_flank=32, ramp_end_r=18.5, ramp_start_r=16.5, ramp_count=12
    )
    show(r.solid, names=["SlipperRing Directional"])
