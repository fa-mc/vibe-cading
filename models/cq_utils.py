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
    cap_r = width_end / 2.0
    tip_center_r = r_end - cap_r
    angular_overshoot_rad = cap_r / tip_center_r
    effective_sweep = max(0.01, sweep_angle - angular_overshoot_rad)

    a_in = r_start
    a_out = r_start + width_start
    if b_out is None:
        b_out = (r_end - a_out) / sweep_angle
    # For a tapered arm, we infer b_in so the tip matches width_end
    # r_end_in = r_end - width_end. Since r_end_in = a_in + b_in * sweep_angle:
    b_in = (r_end - width_end - a_in) / sweep_angle

    if r_start_draw is not None and b_in != 0:
        t_draw_start = (r_start_draw - a_in) / b_in
        # Prevent going to negative radius
        t_min_in = (0.1 - a_in) / b_in if b_in > 0 else -10.0
        t_min_out = (0.1 - a_out) / b_out if b_out > 0 else -10.0
        t_draw_start = max(t_draw_start, t_min_in, t_min_out)
        t_draw_start = min(t_draw_start, effective_sweep)
    else:
        t_draw_start = 0.0

    pts = []
    
    # Inner curve
    for i in range(n_points + 1):
        frac = i / n_points
        t = t_draw_start + (effective_sweep - t_draw_start) * frac
        r = a_in + b_in * t
        th = angle_start + t
        pts.append((r * math.cos(th), r * math.sin(th)))

    # Semicircular Cap
    actual_r_out = a_out + b_out * effective_sweep
    actual_r_in  = a_in + b_in * effective_sweep
    cap_center_r = (actual_r_out + actual_r_in) / 2.0
    cap_r_actual = (actual_r_out - actual_r_in) / 2.0
    cap_angle = angle_start + effective_sweep
    cx = cap_center_r * math.cos(cap_angle)
    cy = cap_center_r * math.sin(cap_angle)

    cap_steps = 10
    for i in range(1, cap_steps):
        frac = i / cap_steps
        ang = cap_angle + math.pi - math.pi * frac
        pts.append((cx + cap_r_actual * math.cos(ang), cy + cap_r_actual * math.sin(ang)))

    # Outer curve
    for i in range(n_points, -1, -1):
        frac = i / n_points
        t = t_draw_start + (effective_sweep - t_draw_start) * frac
        r = a_out + b_out * t
        th = angle_start + t
        pts.append((r * math.cos(th), r * math.sin(th)))

    return pts

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
