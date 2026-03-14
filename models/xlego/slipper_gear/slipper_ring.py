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
    spring_count : int
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
        spring_count: int = 3,
        sag_r: float = 10.5,
        sag_depth: float = 1.2,
    ) -> None:
        self.module         = module
        self.teeth          = teeth
        self.face_width     = face_width
        self.pressure_angle = pressure_angle

        self.pocket_r       = pocket_r
        self.ramp_r         = ramp_r
        self.spring_count   = spring_count
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
        n_r = self.spring_count
        cycle = 2.0 * math.pi / n_r

        hook_angle   = math.radians(10.0)
        pocket_angle = math.radians(20.0)
        ramp_angle   = math.radians(70.0)
        ridge_angle  = cycle - pocket_angle - ramp_angle

        pocket_r = self.pocket_r
        ramp_r   = self.ramp_r

        n_pocket = max(3, int((pocket_angle + hook_angle) / (2 * math.pi) * 144))
        n_ramp   = max(10, int(ramp_angle / (2 * math.pi) * 144))
        n_ridge  = max(2, int(ridge_angle / (2 * math.pi) * 144))

        pts: list[tuple[float, float]] = []

        for i in range(n_r):
            base_angle = i * cycle

            # Calculate fillet for the concave pocket root
            A_theta = base_angle
            A = (ramp_r * math.cos(A_theta), ramp_r * math.sin(A_theta))
            B_theta = base_angle - hook_angle
            B = (pocket_r * math.cos(B_theta), pocket_r * math.sin(B_theta))

            # Use true tangent of the circle at B to prevent restricting the fillet distance 'd'
            T_x = -math.sin(B_theta) * 10.0 + B[0]
            T_y =  math.cos(B_theta) * 10.0 + B[1]
            C = (T_x, T_y)

            # Concave corner fillet R=0.35, high step count for smoothness
            fillet_arc, d_corner = self._fillet_corner(A, B, C, R=0.35, steps=12)
            pts.extend(fillet_arc)

            # 1. Pocket flat (extended backwards to form the hook)
            for j in range(1, n_pocket):
                frac = j / n_pocket
                theta = base_angle - hook_angle + (pocket_angle + hook_angle) * frac
                P = (pocket_r * math.cos(theta), pocket_r * math.sin(theta))
                # Skip points embedded inside the structural fillet to avoid zigzag artifacts
                if math.hypot(P[0] - B[0], P[1] - B[1]) < d_corner:
                    continue
                pts.append(P)

            # 2. Gradual ramp inward
            for j in range(n_ramp):
                frac = j / n_ramp
                theta = base_angle + pocket_angle + ramp_angle * frac
                r = pocket_r - (pocket_r - ramp_r) * frac
                pts.append((r * math.cos(theta), r * math.sin(theta)))

            # 3. Ridge flat
            for j in range(n_ridge):
                frac = j / n_ridge
                theta = base_angle + pocket_angle + ramp_angle + ridge_angle * frac
                pts.append((ramp_r * math.cos(theta), ramp_r * math.sin(theta)))

            # Sharp hook tip to be filleted in 3D
            theta_end = base_angle + cycle
            pts.append((ramp_r * math.cos(theta_end), ramp_r * math.sin(theta_end)))

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

        # Inner bore with directional ramp profile
        ramp_pts = self._ramp_profile_points()
        bore = (
            cq.Workplane("XY")
            .polyline(ramp_pts)
            .close()
            .extrude(self.face_width + 0.2)
        )

        ring = ring.cut(bore.translate((0, 0, -0.1)))

        # Fillet the sharp inward hook teeth tips
        tip_edges = []
        for e in ring.edges("|Z").vals():
            v = e.startPoint()
            r = math.hypot(v.x, v.y)
            if abs(r - self.ramp_r) < 0.05:
                ang = math.atan2(v.y, v.x) % (2 * math.pi)
                cycle_deg = 360.0 / self.spring_count
                for i in range(self.spring_count):
                    target = math.radians(i * cycle_deg)
                    diff = min(abs(ang - target), 2 * math.pi - abs(ang - target))
                    if diff < 0.05:
                        tip_edges.append(e)
                        break

        if tip_edges:
            try:
                ring = ring.newObject(tip_edges).fillet(0.4)
            except Exception as ex:
                print("Failed to fillet tip:", ex)

        # Add top and bottom counterbore sags for the plates
        if self.sag_depth > 0:
            sag_cut = cq.Workplane("XY").circle(self.sag_r).extrude(self.sag_depth + 0.1)
            # Bottom sag
            ring = ring.cut(sag_cut.translate((0, 0, -0.1)))
            # Top sag
            ring = ring.cut(sag_cut.translate((0, 0, self.face_width - self.sag_depth)))

        return ring


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
    from ocp_vscode import show

    r = SlipperRing(
        module=2.0, teeth=24, face_width=8.0, pressure_angle=20.0,
        n_flank=32, pocket_r=18.5, ramp_r=16.5, spring_count=3
    )
    show(r.solid, names=["SlipperRing Directional"])
