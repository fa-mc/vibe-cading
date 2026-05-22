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

"""Tests for the cross-profile axle-hole arm-width gauge task.

Covers the design's Tests 1-5 (see
``.agents/plans/2026-05-21-axle-cross-hole-gauge_design.md``): the new
``AxleCrossHoleGauge`` model class — a row of ``+`` cross axle-hole
cutters at a fixed profile-derived tip-to-tip, with the arm-slot width
swept and a dog-bone relief at each of the four inner concave corners.

Hole topology, per ``+`` cross through-hole, used as the test oracle:

* 8 PLANE faces  — the eight flat arm walls (two per arm, four arms).
  A plain round hole would contribute 0 PLANE walls; the 8 distinguish
  a ``+`` cross from a cylinder (Test 2).
* 8 CYLINDER faces — four curved arm tips + four dog-bone relief pocket
  arcs.  A ``+`` cross *without* the relief has only 4; the extra 4
  prove the dog-bone is present at all 4 concave corners (Test 5).

All interior hole-wall faces span the full block depth in Z — that is
the through-hole check.
"""

import math

import pytest

from vibe_cading.lego.axle_cross_hole_gauge import AxleCrossHoleGauge
from vibe_cading.lego.constants import AXLE_HOLE_TIP_TO_TIP
from vibe_cading.print_settings import FitGrade, ToleranceProfile


# ── Topology helper ──────────────────────────────────────────────────────────
def _hole_wall_faces(
    gauge: AxleCrossHoleGauge,
) -> dict[float, list]:
    """Group interior hole-wall faces by hole X centre.

    A face belongs to a hole wall iff it spans the full block depth in Z
    and its XY centre lands inside one hole cell (excludes the block's
    own top / bottom / perimeter faces and the shallow label glyphs).
    Returns ``{hole_x: [Face, ...]}`` — the raw faces, so callers can
    count surface types or read bounding boxes as needed.
    """
    solid = gauge.solid
    depth = gauge.depth
    hole_xs = [gauge._hole_x(i) for i in range(len(gauge.arm_widths))]

    per_hole: dict[float, list] = {}
    for face in solid.faces().vals():
        bb = face.BoundingBox()
        if abs(bb.zlen - depth) > 1e-6:
            continue  # not a through-hole wall (label glyph or flat face)
        cx = (bb.xmin + bb.xmax) / 2.0
        cy = (bb.ymin + bb.ymax) / 2.0
        # Skip the four outer block walls.
        if abs(cx) > gauge.length / 2.0 - 0.5:
            continue
        if abs(cy - gauge._hole_row_y) > gauge.tip_to_tip:
            continue
        hx = min(hole_xs, key=lambda h: abs(h - cx))
        if abs(hx - cx) > gauge.hole_pitch / 2.0:
            continue
        per_hole.setdefault(round(hx, 3), []).append(face)
    return per_hole


def _type_counts(faces: list) -> dict[str, int]:
    """Count faces by surface (geomType) name."""
    counts: dict[str, int] = {}
    for face in faces:
        counts[face.geomType()] = counts.get(face.geomType(), 0) + 1
    return counts


def _xy_bbox(faces: list) -> tuple[float, float, float, float]:
    """Combined XY bounding box ``(xmin, xmax, ymin, ymax)`` of *faces*."""
    xs_min = min(f.BoundingBox().xmin for f in faces)
    xs_max = max(f.BoundingBox().xmax for f in faces)
    ys_min = min(f.BoundingBox().ymin for f in faces)
    ys_max = max(f.BoundingBox().ymax for f in faces)
    return xs_min, xs_max, ys_min, ys_max


# ── Test 1 — AxleCrossHoleGauge builds a single solid ────────────────────────
def test_gauge_builds_single_solid() -> None:
    """Default AxleCrossHoleGauge is exactly one contiguous solid."""
    gauge = AxleCrossHoleGauge()
    assert len(gauge.solid.solids().vals()) == 1


def test_gauge_rejects_empty_sweep() -> None:
    """An empty ``arm_widths`` sequence raises ValueError."""
    with pytest.raises(ValueError):
        AxleCrossHoleGauge(arm_widths=())


def test_gauge_rejects_non_positive_corner_relief() -> None:
    """A non-positive ``corner_relief`` raises ValueError."""
    with pytest.raises(ValueError):
        AxleCrossHoleGauge(corner_relief=0.0)


# ── Test 2 — one cross hole per swept arm width; holes are + not round ───────
def test_gauge_hole_count_matches_sweep() -> None:
    """Each swept arm width yields exactly one ``+`` cross through-hole."""
    gauge = AxleCrossHoleGauge()
    per_hole = _hole_wall_faces(gauge)
    assert len(per_hole) == len(gauge.arm_widths)


def test_gauge_holes_are_cross_not_round() -> None:
    """Every hole is a ``+`` cross — it has the eight flat arm walls a
    plain round hole would lack."""
    gauge = AxleCrossHoleGauge()
    per_hole = _hole_wall_faces(gauge)
    for hole_x, faces in per_hole.items():
        planes = _type_counts(faces).get("PLANE", 0)
        assert planes == 8, (
            f"hole at X={hole_x} has {planes} flat walls, "
            "expected 8 (a + cross, not a cylinder)"
        )


def test_gauge_holes_are_through() -> None:
    """Every hole-wall face spans the full block depth (through-hole)."""
    gauge = AxleCrossHoleGauge()
    # _hole_wall_faces already filters to depth-spanning faces; a non-empty
    # result with 8 walls per hole proves the holes are through.
    per_hole = _hole_wall_faces(gauge)
    assert per_hole, "no through-hole wall faces detected"
    for faces in per_hole.values():
        assert len(faces) > 0


def test_gauge_holes_form_single_row() -> None:
    """All hole centres share one Y coordinate (single row along X).

    A hole's centre is the midpoint of the combined XY bounding box of
    its interior wall faces; every hole's centre-Y must coincide.
    """
    gauge = AxleCrossHoleGauge()
    per_hole = _hole_wall_faces(gauge)
    centre_ys = set()
    for faces in per_hole.values():
        _, _, ymin, ymax = _xy_bbox(faces)
        centre_ys.add(round((ymin + ymax) / 2.0, 3))
    assert len(centre_ys) == 1


# ── Test 3 — tip-to-tip is profile-derived and fixed across the row ──────────
def test_gauge_tip_to_tip_is_profile_derived() -> None:
    """Tip-to-tip = AXLE_HOLE_TIP_TO_TIP + 2 * profile.slip.radial."""
    profile = ToleranceProfile(
        name="calibrated",
        free=FitGrade(radial=0.15, axial=0.20),
        slip=FitGrade(radial=0.10, axial=0.20),
        press=FitGrade(radial=0.04, axial=0.20),
    )
    gauge = AxleCrossHoleGauge(profile=profile)
    assert gauge.tip_to_tip == pytest.approx(
        AXLE_HOLE_TIP_TO_TIP + 2 * 0.10, abs=1e-9
    )


def test_gauge_tip_to_tip_fixed_across_all_holes() -> None:
    """Every hole shares one tip-to-tip — the curved arm tips of all
    holes lie on the same bounding circle.

    The ``+`` cross is the intersection of a ``tip_to_tip`` bounding
    cylinder with the arm rectangles; its four curved tips reach exactly
    ``tip_to_tip`` corner-to-corner, so the combined XY bounding box of
    each hole's interior wall faces equals ``tip_to_tip`` in *both* X and
    Y — regardless of the swept arm width.
    """
    gauge = AxleCrossHoleGauge()
    per_hole = _hole_wall_faces(gauge)
    assert len(per_hole) == len(gauge.arm_widths)
    for hole_x, faces in per_hole.items():
        xmin, xmax, ymin, ymax = _xy_bbox(faces)
        assert (xmax - xmin) == pytest.approx(gauge.tip_to_tip, abs=1e-6), (
            f"hole at X={hole_x}: X envelope {xmax - xmin:.4f} "
            f"!= tip_to_tip {gauge.tip_to_tip:.4f}"
        )
        assert (ymax - ymin) == pytest.approx(gauge.tip_to_tip, abs=1e-6), (
            f"hole at X={hole_x}: Y envelope {ymax - ymin:.4f} "
            f"!= tip_to_tip {gauge.tip_to_tip:.4f}"
        )


def test_gauge_profile_changes_tip_to_tip() -> None:
    """A profile with a larger ``slip.radial`` widens the fixed
    tip-to-tip."""
    tight = ToleranceProfile(
        name="tight",
        free=FitGrade(radial=0.15), slip=FitGrade(radial=0.05),
        press=FitGrade(radial=0.04),
    )
    loose = ToleranceProfile(
        name="loose",
        free=FitGrade(radial=0.20), slip=FitGrade(radial=0.12),
        press=FitGrade(radial=0.04),
    )
    assert (
        AxleCrossHoleGauge(profile=loose).tip_to_tip
        > AxleCrossHoleGauge(profile=tight).tip_to_tip
    )


# ── Test 4 — arm-slot width varies as swept ──────────────────────────────────
def test_gauge_arm_width_varies_as_swept() -> None:
    """Each hole's flat arm-slot width matches its ``arm_widths`` entry.

    The eight flat arm walls of a ``+`` cross are PLANE faces; the two
    walls of one arm are separated across the slot by exactly the arm
    width.  Per hole, the *smallest* gap between a parallel PLANE-face
    pair is the arm-slot width — it must track the swept sequence.
    """
    arm_widths = (1.85, 2.05, 2.35)
    gauge = AxleCrossHoleGauge(arm_widths=arm_widths)
    hole_xs = [gauge._hole_x(i) for i in range(len(gauge.arm_widths))]

    # Collect the PLANE wall faces of each hole, keyed by hole X.
    walls: dict[float, list] = {hx: [] for hx in hole_xs}
    for face in gauge.solid.faces().vals():
        if face.geomType() != "PLANE":
            continue
        bb = face.BoundingBox()
        if abs(bb.zlen - gauge.depth) > 1e-6:
            continue
        cx = (bb.xmin + bb.xmax) / 2.0
        if abs(cx) > gauge.length / 2.0 - 0.5:
            continue
        cy = (bb.ymin + bb.ymax) / 2.0
        if abs(cy - gauge._hole_row_y) > gauge.tip_to_tip:
            continue
        hx = min(hole_xs, key=lambda h: abs(h - cx))
        if abs(hx - cx) > gauge.hole_pitch / 2.0:
            continue
        walls[hx].append(face)

    # For each hole, the arm-slot width is the smallest centre-to-centre
    # gap between two parallel, opposed flat walls.  The vertical arm's
    # two long walls are planes whose normal is ~X; their X-centres are
    # half_arm apart on each side of the hole centre -> separation = arm.
    for index, expected_arm in enumerate(arm_widths):
        hx = hole_xs[index]
        faces = walls[hx]
        assert len(faces) == 8, f"hole {hx}: expected 8 walls, got {len(faces)}"
        # X-facing walls (vertical arm sides): bbox xlen ~ 0 (thin in X).
        x_walls = sorted(
            ((f.BoundingBox().xmin + f.BoundingBox().xmax) / 2.0 - hx)
            for f in faces
            if f.BoundingBox().xlen < f.BoundingBox().ylen
        )
        # The two innermost X-facing walls straddle the hole centre and
        # are arm_width apart.
        inner = [x for x in x_walls if abs(x) < gauge.tip_to_tip / 2.0]
        gap = max(inner) - min(inner)
        assert gap == pytest.approx(expected_arm, abs=1e-6), (
            f"hole {index}: arm-slot width {gap:.4f}, expected {expected_arm}"
        )


# ── Test 5 — dog-bone relief present at all four concave corners ─────────────
def test_gauge_dogbone_relief_present() -> None:
    """Each cross hole carries a dog-bone relief at all four concave
    corners.

    A plain ``+`` cross hole has 4 CYLINDER wall faces (the arm tips).
    The dog-bone adds one circular pocket per concave corner — 4 more
    CYLINDER faces — so a relieved hole has exactly 8.
    """
    gauge = AxleCrossHoleGauge()
    per_hole = _hole_wall_faces(gauge)
    assert per_hole, "no holes detected"
    for hole_x, faces in per_hole.items():
        cylinders = _type_counts(faces).get("CYLINDER", 0)
        assert cylinders == 8, (
            f"hole at X={hole_x} has {cylinders} cylinder faces, "
            "expected 8 (4 arm tips + 4 dog-bone reliefs)"
        )


def test_gauge_dogbone_leaves_flat_slot_wall() -> None:
    """A defined flat slot wall survives along each arm — even on the
    widest swept hole, whose flat wall is the shortest.

    The dog-bone pocket passes through the concave corner point, eating
    ``corner_relief * sqrt(2)`` of flat wall along each arm.  The flat
    wall runs from the corner to where the bounding-cylinder arc cuts in
    at ``x = sqrt((tip/2)^2 - half_arm^2)``.  The remainder must stay
    strictly positive (a measurable surface) across the whole sweep.
    """
    gauge = AxleCrossHoleGauge()
    eaten = gauge.corner_relief * math.sqrt(2.0)
    for arm in gauge.arm_widths:
        half_arm = arm / 2.0
        junction_x = math.sqrt((gauge.tip_to_tip / 2.0) ** 2 - half_arm ** 2)
        flat_wall = junction_x - half_arm
        remaining = flat_wall - eaten
        assert remaining > 0.0, (
            f"arm {arm}: dog-bone eats the whole flat wall "
            f"(flat_wall={flat_wall:.4f}, eaten={eaten:.4f})"
        )
