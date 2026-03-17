"""
Reusable CadQuery geometry helpers.

All functions are pure (no side-effects) and return a new solid or a modified
Workplane.  Import selectively — nothing here depends on project-specific
constants.
"""

from __future__ import annotations

import cadquery as cq


# ── Primitives ────────────────────────────────────────────────────────────────

def rounded_box(
    width: float,
    depth: float,
    height: float,
    corner_r: float,
    center: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> cq.Workplane:
    """Axis-aligned box with vertical corner fillets, extruded from Z = 0.

    Parameters
    ----------
    width, depth:
        XY footprint (mm).
    height:
        Total extrusion height (mm).
    corner_r:
        Fillet radius on the four vertical (|Z) edges (mm).
    center:
        (x, y, z) offset applied *before* extrusion so the footprint centre
        lands at (center.x, center.y) and the base sits at center.z.
    """
    cx, cy, cz = center
    box = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, cz))
        .rect(width, depth)
        .extrude(height)
    )
    if corner_r > 0:
        box = box.edges("|Z").fillet(corner_r)
    return box


def cylinder(
    radius: float,
    height: float,
    center: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> cq.Workplane:
    """Cylinder extruded upward from *center* along +Z.

    Parameters
    ----------
    radius:
        Cylinder radius (mm).
    height:
        Extrusion height (mm).
    center:
        (x, y, z) position of the base centre.
    """
    cx, cy, cz = center
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, cz))
        .circle(radius)
        .extrude(height)
    )


def countersunk_hole(
    bore_r: float,
    bore_depth: float,
    cs_r: float,
    cs_depth: float,
    center: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> cq.Workplane:
    """Countersunk bore starting at *center* and going upward along +Z.

    The countersink tapers from *cs_r* at Z = center.z down to *bore_r* at
    Z = center.z + cs_depth.  A straight bore of *bore_r* then continues from
    there to Z = center.z + bore_depth.

    Parameters
    ----------
    bore_r:
        Radius of the straight bore (mm).
    bore_depth:
        Total depth including countersink (mm).
    cs_r:
        Countersink entry radius at Z = 0 (mm).
    cs_depth:
        Axial depth of the tapered countersink section (mm).
    center:
        (x, y, z) position of the entry face centre.
    """
    cx, cy, cz = center
    countersink = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, cz))
        .circle(cs_r)
        .workplane(offset=cs_depth)
        .circle(bore_r)
        .loft()
    )
    straight = cylinder(bore_r, bore_depth - cs_depth, (cx, cy, cz + cs_depth))
    return countersink.union(straight)


# ── Wall-hole helpers ─────────────────────────────────────────────────────────

def orient_to_neg_x(
    solid: cq.Workplane,
    wall_x: float,
    at_y: float,
    at_z: float,
) -> cq.Workplane:
    """Orient a +Z-extruded cutter so it enters the part through the −X wall.

    The solid's Z = 0 face is placed flush with the outer wall at *wall_x*
    (negative) and the bore axis points inward (+X direction).

    Parameters
    ----------
    solid:
        A cutter solid whose axis runs along +Z, centred at XY origin.
    wall_x:
        X coordinate of the outer face (negative value, e.g. −12.0).
    at_y, at_z:
        Y and Z position of the hole centre.
    """
    return solid.rotate((0, 0, 0), (0, 1, 0), 90).translate((wall_x, at_y, at_z))


def orient_to_pos_x(
    solid: cq.Workplane,
    wall_x: float,
    at_y: float,
    at_z: float,
) -> cq.Workplane:
    """Orient a +Z-extruded cutter so it enters the part through the +X wall.

    Parameters
    ----------
    solid:
        A cutter solid whose axis runs along +Z, centred at XY origin.
    wall_x:
        X coordinate of the outer face (positive value, e.g. +12.0).
    at_y, at_z:
        Y and Z position of the hole centre.
    """
    return solid.rotate((0, 0, 0), (0, 1, 0), -90).translate((wall_x, at_y, at_z))


# ── Cutter modifier ──────────────────────────────────────────────────────────

class WithAllowance:
    """Offset all faces of a solid outward by *allowance* mm.

    Useful when you need a slightly enlarged cutter without modifying the
    original object — works with any ``cq.Workplane`` or ``cq.Shape``, whether
    from a cutter class or built ad-hoc.

    .. note::
        Uses CadQuery's ``shell`` offset, which grows faces uniformly in all
        directions.  For directional allowance (e.g. radial-only on a Technic
        axle hole cross) prefer building allowance into the cutter class itself,
        as the concave inner corners of non-convex solids can cause ``shell``
        to fail.

    Parameters
    ----------
    solid:
        The base cutter solid (``cq.Workplane`` or ``cq.Shape``).
    allowance:
        Outward face offset in mm.  Positive = larger cutter.
        Zero is a no-op and returns the original solid unchanged.

    Examples
    --------
    ::

        from models.cq_utils import WithAllowance

        cutter = WithAllowance(TechnicPinHole(depth=8).solid, allowance=0.1).solid
        part = part.cut(cutter)

        loose_box = WithAllowance(cq.Workplane("XY").box(5, 5, 5), allowance=0.2).solid
        part = part.cut(loose_box)
    """

    def __init__(self, solid: cq.Workplane | cq.Shape, allowance: float):
        self._solid = self._apply(solid, allowance)

    @staticmethod
    def _apply(solid: cq.Workplane | cq.Shape, allowance: float) -> cq.Workplane:
        if allowance == 0.0:
            return solid if isinstance(solid, cq.Workplane) else cq.Workplane(solid)
        shape: cq.Shape = solid.val() if isinstance(solid, cq.Workplane) else solid
        return cq.Workplane(shape.shell(allowance))

    @property
    def solid(self) -> cq.Workplane:
        """The offset solid — cut this from any part."""
        return self._solid


# ── Grid cut helper ───────────────────────────────────────────────────────────

def cut_at_positions(
    part: cq.Workplane,
    cutter: cq.Workplane,
    positions: list[tuple[float, float]],
    z_offset: float = 0.0,
) -> cq.Workplane:
    """Subtract *cutter* (translated by (x, y, z_offset)) at each XY position.

    Parameters
    ----------
    part:
        The solid to cut into.
    cutter:
        Cutter solid already positioned at the XY origin.
    positions:
        List of (x, y) centres.
    z_offset:
        Additional Z translation applied to *cutter* before each cut.
    """
    base = cutter.translate((0, 0, z_offset)) if z_offset else cutter
    for x, y in positions:
        part = part.cut(base.translate((x, y, 0)))
    return part

import math

def get_corner(A, B, C, R, steps=10):
    import math
    ux = A[0] - B[0]; uy = A[1] - B[1]
    lu = math.hypot(ux, uy)
    if lu == 0: return [B]
    ux /= lu; uy /= lu
    vx = C[0] - B[0]; vy = C[1] - B[1]
    lv = math.hypot(vx, vy)
    if lv == 0: return [B]
    vx /= lv; vy /= lv
    dot = max(-1.0, min(1.0, ux * vx + uy * vy))
    theta_angle = math.acos(dot)
    if theta_angle < 0.01 or theta_angle > math.pi - 0.01: return [B]
    d = R / math.tan(theta_angle / 2.0)
    d = min(d, lu * 0.49, lv * 0.49)
    R = d * math.tan(theta_angle / 2.0)
    T1 = (B[0] + d * ux, B[1] + d * uy)
    T2 = (B[0] + d * vx, B[1] + d * vy)
    dc = R / math.sin(theta_angle / 2.0)
    dir_cx = (ux + vx); dir_cy = (uy + vy)
    ld = math.hypot(dir_cx, dir_cy); dir_cx /= ld; dir_cy /= ld
    Center = (B[0] + dc * dir_cx, B[1] + dc * dir_cy)
    a1 = math.atan2(T1[1] - Center[1], T1[0] - Center[0])
    a2 = math.atan2(T2[1] - Center[1], T2[0] - Center[0])
    diff = (a2 - a1) % (2 * math.pi)
    if diff > math.pi: diff -= 2 * math.pi
    out = []
    for i in range(steps + 1):
        f = i / steps
        out.append((Center[0] + R * math.cos(a1 + diff * f), Center[1] + R * math.sin(a1 + diff * f)))
    return out


def line_intersect(p1, v1, p2, v2):
    det = v1[0]*v2[1] - v1[1]*v2[0]
    if abs(det) < 1e-9:
        return None
    t1 = ((p2[0] - p1[0])*v2[1] - (p2[1] - p1[1])*v2[0]) / det
    return (p1[0] + t1*v1[0], p1[1] + t1*v1[1])

def tapered_arm_profile(
    r_start: float,
    r_end: float,
    width_start: float,
    width_end: float,
    sweep_angle: float,
    angle_start: float = 0.0,
    n_points: int = 50,
    r_start_draw: float | None = None,
    b_out: float | None = None,
) -> list[tuple[float, float]]:
    import math
    cap_r = width_end / 2.0
    # Stop early so we can fit the cap
    angular_overshoot_rad = cap_r / (r_end - cap_r) if (r_end - cap_r) > 0 else 0
    effective_sweep = max(0.01, sweep_angle - angular_overshoot_rad)

    a_in = r_start
    a_out = r_start + width_start
    if b_out is None:
        b_out = (r_end - a_out) / sweep_angle
    b_in = (r_end - width_end - a_in) / sweep_angle

    if r_start_draw is not None and b_in != 0:
        t_draw_start = (r_start_draw - a_in) / b_in
        t_min_in = (0.1 - a_in) / b_in if b_in > 0 else -10.0
        t_min_out = (0.1 - a_out) / b_out if b_out > 0 else -10.0
        t_draw_start = max(t_draw_start, t_min_in, t_min_out)
        t_draw_start = min(t_draw_start, effective_sweep)
    else:
        t_draw_start = 0.0

    inner_pts = []
    for i in range(n_points + 1):
        frac = i / n_points
        t = t_draw_start + (effective_sweep - t_draw_start) * frac
        r = a_in + b_in * t
        th = angle_start + t
        inner_pts.append((r * math.cos(th), r * math.sin(th)))

    outer_pts = []
    for i in range(n_points, -1, -1):
        frac = i / n_points
        t = t_draw_start + (effective_sweep - t_draw_start) * frac
        r = a_out + b_out * t
        th = angle_start + t
        outer_pts.append((r * math.cos(th), r * math.sin(th)))

    if width_end <= 0.01:
        return inner_pts + outer_pts

    # Calculate tangents at effective_sweep
    t_end = effective_sweep
    th_end = angle_start + t_end
    r_in_end = a_in + b_in*t_end
    r_out_end = a_out + b_out*t_end

    pin = (r_in_end*math.cos(th_end), r_in_end*math.sin(th_end))
    pout = (r_out_end*math.cos(th_end), r_out_end*math.sin(th_end))

    dx_in = b_in*math.cos(th_end) - r_in_end*math.sin(th_end)
    dy_in = b_in*math.sin(th_end) + r_in_end*math.cos(th_end)
    
    dx_out = b_out*math.cos(th_end) - r_out_end*math.sin(th_end)
    dy_out = b_out*math.sin(th_end) + r_out_end*math.cos(th_end)

    apex = line_intersect(pin, (dx_in, dy_in), pout, (dx_out, dy_out))
    
    if apex:
        # Check if apex is forward (dot product > 0)
        v_in_to_apex = (apex[0]-pin[0], apex[1]-pin[1])
        if (v_in_to_apex[0]*dx_in + v_in_to_apex[1]*dy_in) > 0:
            cap_pts = get_corner(inner_pts[-2], apex, outer_pts[1], R=cap_r, steps=10)
            return inner_pts[:-1] + cap_pts + outer_pts[1:]

    # Fallback to simple corner if lines are parallel or apex is backwards
    cap_pts = get_corner(inner_pts[-2], inner_pts[-1], outer_pts[1], R=cap_r, steps=10)
    return inner_pts[:-1] + cap_pts + outer_pts[1:]

def archimedean_spiral_arc(
    r_start: float,
    r_end: float,
    sweep_angle: float,
    angle_start: float = 0.0,
    n_points: int = 50,
    r_start_draw: float | None = None,
) -> list[tuple[float, float]]:
    b = (r_end - r_start) / sweep_angle
    
    if r_start_draw is not None and b != 0:
        t_start = (r_start_draw - r_start) / b
    else:
        t_start = 0.0

    pts = []
    for i in range(n_points + 1):
        frac = i / n_points
        t = t_start + (sweep_angle - t_start) * frac
        r = r_start + b * t
        th = angle_start + t
        pts.append((r * math.cos(th), r * math.sin(th)))
    return pts

def fillet_z_edges(wp: cq.Workplane, r_min: float, r_max: float, radius: float = 0.8) -> cq.Workplane:
    """Safely apply a fillet to all Z-aligned edges whose radial centroid falls between r_min and r_max"""
    import math
    z_edges = wp.edges("|Z")
    
    def match_edge(e) -> bool:
        c = e.Center()
        dist = math.hypot(c.x, c.y)
        return r_min <= dist <= r_max
        
    try:
        matched = [e for e in z_edges.vals() if match_edge(e)]
        if matched:
            return wp.objects(matched).fillet(radius)
    except Exception:
        pass
        
    return wp
