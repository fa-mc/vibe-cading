"""SlipperRing — outer gear ring: involute spur teeth on OD, directional ramp bore on ID."""

from __future__ import annotations

import math
import cadquery as cq

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
    pocket_r : float
        Maximum inner radius (in the pocket) where the spring tip can expand (mm).
    ramp_r : float
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
        pocket_r: float = 10.0,
        ramp_r: float = 8.0,
        ramp_count: int = 12,
        sag_r: float = 10.5,
        sag_depth: float = 1.2,
    ) -> None:
        self.module         = module
        self.teeth          = teeth
        self.face_width     = face_width
        self.pressure_angle = pressure_angle

        self.pocket_r       = pocket_r
        self.ramp_r         = ramp_r
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
        if d > lu * 0.9 or d > lv * 0.9:
            d = min(lu * 0.9, lv * 0.9)
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
        cycle = 2.0 * math.pi / n_r

        # Scale angles depending on ramp count, assuming 3 ramps (120 deg cycle) as baseline
        scale = cycle / math.radians(120.0)
        hook_angle = math.radians(10.0) * scale

        pocket_r = self.pocket_r
        ramp_r   = self.ramp_r

        pts: list[tuple[float, float]] = []
        n_ramp = 90

        ramp_span = cycle - hook_angle
        b = (pocket_r - ramp_r) / ramp_span

        for i in range(n_r):
            theta_start = i * cycle                  # inner root
            theta_end   = theta_start + ramp_span    # outer pocket edge
            theta_next  = (i + 1) * cycle            # next inner root

            theta_prev_end = theta_start - hook_angle

            Root_curr = (ramp_r * math.cos(theta_start), ramp_r * math.sin(theta_start))
            Tip_curr  = (pocket_r * math.cos(theta_end), pocket_r * math.sin(theta_end))
            Root_next = (ramp_r * math.cos(theta_next), ramp_r * math.sin(theta_next))
            Tip_prev  = (pocket_r * math.cos(theta_prev_end), pocket_r * math.sin(theta_prev_end))

            dx_start = b * math.cos(theta_start) - ramp_r * math.sin(theta_start)
            dy_start = b * math.sin(theta_start) + ramp_r * math.cos(theta_start)
            Tang_start = (Root_curr[0] + dx_start, Root_curr[1] + dy_start)

            dx_end = b * math.cos(theta_end) - pocket_r * math.sin(theta_end)
            dy_end = b * math.sin(theta_end) + pocket_r * math.cos(theta_end)
            Tang_end = (Tip_curr[0] - dx_end, Tip_curr[1] - dy_end)

            spiral_pts = []
            for j in range(0, n_ramp + 1):
                frac = j / n_ramp
                theta_j = theta_start + ramp_span * frac
                r_j = ramp_r + b * (theta_j - theta_start)
                spiral_pts.append((r_j * math.cos(theta_j), r_j * math.sin(theta_j)))

            # Fillets with true geometric tangents matching the spiral equations
            root_arc, d_root = self._fillet_corner(Tip_prev, Root_curr, Tang_start, R=0.35, steps=24)
            tip_arc, d_tip   = self._fillet_corner(Tang_end, Tip_curr, Root_next, R=0.25, steps=24)

            pts.extend(root_arc)
            for pt in spiral_pts:
                # Exclude internal overlapping points covered by fillets
                if math.hypot(pt[0] - Root_curr[0], pt[1] - Root_curr[1]) < d_root:
                    continue
                if math.hypot(pt[0] - Tip_curr[0], pt[1] - Tip_curr[1]) < d_tip:
                    continue
                pts.append(pt)
            pts.extend(tip_arc)

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
        n_flank=32, pocket_r=18.5, ramp_r=16.5, ramp_count=12
    )
    show(r.solid, names=["SlipperRing Directional"])
