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
