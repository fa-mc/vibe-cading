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

"""
Reusable CadQuery geometry helpers.

All functions are pure (no side-effects) and return a new solid or a modified
Workplane.  Import selectively — nothing here depends on project-specific
constants.

Post Round 6.1 single-caller audit (see
``.agents/plans/2026-05-13-pre-oss-models-structure_design.md``) this module
intentionally exposes a small set of generic primitives: :func:`rounded_box`,
:func:`cylinder`, :func:`cut_at_positions`, and :func:`axle_cross_section`.
:func:`axle_cross_section` was promoted here once a third caller materialised
(``TechnicAxle``, ``TechnicAxleHole`` and ``AxleCrossHoleGauge`` all build the
identical cylinder∩cross construction — a clear DRY trigger).  Helpers that
served exactly one caller have moved closer to their consumer:

* ``countersunk_hole`` removed — superseded by
  :class:`vibe_cading.mechanical.holes.CounterboreHole` with
  ``head_type='cone'``.  The 3 SG90-mount call sites now wrap that class via
  a private ``_build_countersunk_screw_cutter`` adapter.
* ``orient_to_neg_x`` / ``orient_to_pos_x`` moved to
  :mod:`vibe_cading.lego_adapters._wall_helpers` (private — only the SG90
  servo-mount classes consume them).
* ``WithAllowance`` removed — replaced by the profile-aware cutter
  protocol implementations introduced in Phase 4 of the same plan.
* ``tapered_arm_profile``, ``archimedean_spiral_arc``, ``fillet_z_edges``
  moved to ``experiments/slipper_gear/curves.py`` alongside their only
  consumers.

Promote a helper back here (with the AGPL header) if a generic-purpose
second caller materialises.
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


# ── Lego Technic cross profile ────────────────────────────────────────────────

def axle_cross_section(
    tip_to_tip: float,
    arm_width: float,
    length: float,
) -> cq.Workplane:
    """Extruded ``+`` cross solid with curved arm tips — the Lego Technic
    axle / axle-hole envelope.

    The cross is the intersection of a bounding cylinder (radius
    ``tip_to_tip / 2``) with the union of two perpendicular rectangular
    prisms (``tip_to_tip × arm_width`` and ``arm_width × tip_to_tip``).
    The cylinder constrains the four arm tips to arcs of radius
    ``tip_to_tip / 2``; the rectangles give the flat arm sides.  No
    corner fillets and no lead-in chamfers are applied — callers layer
    those on top (e.g. :class:`TechnicAxle`'s concave fillet and end
    chamfers, :class:`TechnicAxleHole`'s convex/concave fillets, or the
    cross-hole gauge's dog-bone corner relief).

    The solid is plan-centred (XY centroid at the origin) and extrudes
    upward from Z = 0 to Z = ``length``.

    Parameters
    ----------
    tip_to_tip:
        Tip-to-tip diameter of the cross (mm) — the bounding-cylinder
        diameter and the long dimension of each arm rectangle.
    arm_width:
        Flat slot-wall width of each arm (mm) — the short dimension of
        each arm rectangle.
    length:
        Axial extrusion length along +Z (mm).
    """
    # Cylinder constrains the outer boundary → curved arm tips.
    cylinder = (
        cq.Workplane("XY")
        .circle(tip_to_tip / 2)
        .extrude(length)
    )
    # Two rectangular prisms form the + cross mask → flat arm sides.
    arm_h = (
        cq.Workplane("XY")
        .rect(tip_to_tip, arm_width)
        .extrude(length)
    )
    arm_v = (
        cq.Workplane("XY")
        .rect(arm_width, tip_to_tip)
        .extrude(length)
    )
    return cylinder.intersect(arm_h.union(arm_v))


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
