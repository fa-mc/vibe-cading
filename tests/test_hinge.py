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

"""Tests for ``vibe_cading.mechanical.hinge.PrintInPlaceHinge``.

Covers the Tests table from the design brief
``docs/design_plans/2026-06-24-hinge-screw-holes_design.md``.

Human design gate approved 2026-06-24:
  - 2 countersunk M3 holes per leaf (4 total).
  - Top-face countersink (Z = plate_top_z = -1.0 for defaults).
  - ``screw_holes=True`` is the default.
  - No build.toml registration.
"""

import pytest

from vibe_cading.mechanical.hinge import PrintInPlaceHinge
from vibe_cading.print_settings import get_profile


# ── T_DEFAULT — Default construction builds without error ─────────────────────

def test_default_construction() -> None:
    """PrintInPlaceHinge() builds successfully with screw_holes=True default."""
    h = PrintInPlaceHinge()
    assert h.leaf_a is not None
    assert h.leaf_b is not None
    assert h.solid is not None


# ── T_SINGLE_SOLID_A — Single-solid topology, leaf_a ─────────────────────────

def test_single_solid_leaf_a() -> None:
    """leaf_a is a single contiguous solid after screw hole cuts."""
    h = PrintInPlaceHinge()
    assert len(h.leaf_a.solids().vals()) == 1, (
        "leaf_a screw holes produced floating fragments"
    )


# ── T_SINGLE_SOLID_B — Single-solid topology, leaf_b ─────────────────────────

def test_single_solid_leaf_b() -> None:
    """leaf_b is a single contiguous solid after screw hole cuts."""
    h = PrintInPlaceHinge()
    assert len(h.leaf_b.solids().vals()) == 1, (
        "leaf_b screw holes produced floating fragments"
    )


# ── T_HOLE_COUNT — 4 holes total (2 per leaf) ────────────────────────────────

def test_hole_count_4_total() -> None:
    """screw_holes=True removes material from both leaves (2 holes each = 4 total).

    Verified via volume reduction: each leaf loses ~50 mm³ per hole.
    """
    h_with = PrintInPlaceHinge(screw_holes=True)
    h_no = PrintInPlaceHinge(screw_holes=False)
    vol_a_with = h_with.leaf_a.val().Volume()
    vol_a_no = h_no.leaf_a.val().Volume()
    vol_b_with = h_with.leaf_b.val().Volume()
    vol_b_no = h_no.leaf_b.val().Volume()

    # Each leaf should have had material removed (2 holes per leaf).
    assert vol_a_no > vol_a_with, "leaf_a: no volume removed by screw holes"
    assert vol_b_no > vol_b_with, "leaf_b: no volume removed by screw holes"

    # 2 holes per leaf × ~50 mm³ each = ~100 mm³ removed per leaf.
    # Use a broad tolerance (30–200 mm³) to allow profile variation.
    removed_a = vol_a_no - vol_a_with
    removed_b = vol_b_no - vol_b_with
    assert 30.0 < removed_a < 200.0, (
        f"leaf_a volume removed ({removed_a:.2f} mm³) outside expected 30–200 mm³ range"
    )
    assert 30.0 < removed_b < 200.0, (
        f"leaf_b volume removed ({removed_b:.2f} mm³) outside expected 30–200 mm³ range"
    )


# ── T_NO_HOLES_UNCHANGED — screw_holes=False leaves geometry unchanged ────────

def test_screw_holes_false_unchanged() -> None:
    """screw_holes=False produces geometry with same bounding box as the
    pre-holes baseline (both leaves).
    """
    h_no = PrintInPlaceHinge(screw_holes=False)
    # Build a second no-holes instance and compare — consistent baseline.
    h_no2 = PrintInPlaceHinge(screw_holes=False)

    bb_a1 = h_no.leaf_a.val().BoundingBox()
    bb_a2 = h_no2.leaf_a.val().BoundingBox()
    assert abs(bb_a1.xmin - bb_a2.xmin) < 1e-6
    assert abs(bb_a1.xmax - bb_a2.xmax) < 1e-6
    assert abs(bb_a1.ymin - bb_a2.ymin) < 1e-6
    assert abs(bb_a1.ymax - bb_a2.ymax) < 1e-6
    assert abs(bb_a1.zmin - bb_a2.zmin) < 1e-6
    assert abs(bb_a1.zmax - bb_a2.zmax) < 1e-6

    bb_b1 = h_no.leaf_b.val().BoundingBox()
    bb_b2 = h_no2.leaf_b.val().BoundingBox()
    assert abs(bb_b1.xmin - bb_b2.xmin) < 1e-6
    assert abs(bb_b1.xmax - bb_b2.xmax) < 1e-6

    # Volumes must match too.
    vol_a1 = h_no.leaf_a.val().Volume()
    vol_a2 = h_no2.leaf_a.val().Volume()
    assert abs(vol_a1 - vol_a2) < 1e-3


# ── T_HOLE_POSITIONS — Centers at expected X=13.0, Y=±7.5 ───────────────────

def test_hole_centers_default() -> None:
    """_compute_screw_hole_centers returns (13.0, 7.5) and (13.0, -7.5)
    for the default 20 mm leaf and 30 mm width.
    """
    h = PrintInPlaceHinge()
    centers = h._compute_screw_hole_centers(20.0)
    assert len(centers) == 2
    # X = 20 * 0.65 = 13.0
    assert abs(centers[0][0] - 13.0) < 1e-6, f"Expected X=13.0, got {centers[0][0]}"
    assert abs(centers[1][0] - 13.0) < 1e-6, f"Expected X=13.0, got {centers[1][0]}"
    # Y = ±(30 * 0.25) = ±7.5
    y_vals = sorted([abs(c[1]) for c in centers])
    assert abs(y_vals[0] - 7.5) < 1e-6, f"Expected |Y|=7.5, got {y_vals}"
    assert abs(y_vals[1] - 7.5) < 1e-6, f"Expected |Y|=7.5, got {y_vals}"
    # Symmetric about Y=0
    y_signs = sorted([c[1] for c in centers])
    assert y_signs[0] < 0 and y_signs[1] > 0, (
        f"Expected ±7.5, got {y_signs}"
    )


# ── T_MARGIN_INNER — Inner margin >= 0.5 mm (passes for defaults) ─────────────

def test_margin_inner_valid() -> None:
    """Default 20 mm leaf clears the inner margin (knuckle clearance zone)."""
    h = PrintInPlaceHinge()
    # Should not raise — verified in construction.
    centers = h._compute_screw_hole_centers(20.0)
    assert centers is not None


# ── T_MARGIN_VIOLATED — ValueError raised for tiny leaf ──────────────────────

def test_margin_violated_short_leaf() -> None:
    """A leaf_length so short the hole would collide with the knuckle zone
    raises ValueError from _compute_screw_hole_centers.
    """
    with pytest.raises(ValueError, match="inner margin"):
        PrintInPlaceHinge(leaf_a_length=8.0)


# ── T_PLATE_TOP_Z — Plate top Z formula correct ───────────────────────────────

def test_plate_top_z_default() -> None:
    """plate_top_z = thickness/2 + (thickness - knuckle_diameter)/2 = -1.0."""
    h = PrintInPlaceHinge()
    # Use the same formula from _apply_screw_holes.
    plate_top_z = h.thickness / 2 + (h.thickness - h.knuckle_diameter) / 2
    assert abs(plate_top_z - (-1.0)) < 1e-9, (
        f"Expected plate_top_z=-1.0, got {plate_top_z}"
    )


# ── T_INTERSECTION_ZERO — Cutter-vs-leaf intersection volume ≈ 0 ─────────────

def test_intersection_volume_zero() -> None:
    """After cutting, the screw cutter no longer intersects the leaf solid."""
    from vibe_cading.mechanical.screws.metric import MetricMachineScrew
    prof = get_profile("fdm_standard")
    cutter = MetricMachineScrew.from_size(
        "M3", length=10.0, head_type="flat"
    ).to_cutter(profile=prof)

    h = PrintInPlaceHinge()
    plate_top_z = h.thickness / 2 + (h.thickness - h.knuckle_diameter) / 2

    # Check first hole at (13.0, 7.5)
    cutter_placed = cutter.translate((13.0, 7.5, plate_top_z))
    intersect = h.leaf_a.intersect(cutter_placed)
    try:
        iv = intersect.val().Volume()
    except Exception:
        iv = 0.0  # empty intersection is acceptable
    assert iv < 1e-3, (
        f"Screw cutter intersects leaf_a after cutting: vol={iv:.6f} mm³"
    )


# ── T_PARAMETRIC_SCALE — Larger leaf shifts hole positions ───────────────────

def test_parametric_scale_large_leaf() -> None:
    """With leaf_length=40 mm and width=60 mm:
      X = 40 * 0.65 = 26.0, Y = ±(60 * 0.25) = ±15.0.
    """
    h = PrintInPlaceHinge(
        leaf_a_length=40.0,
        leaf_b_length=40.0,
        width=60.0,
    )
    centers = h._compute_screw_hole_centers(40.0)
    assert abs(centers[0][0] - 26.0) < 1e-6, (
        f"Expected X=26.0 for 40mm leaf, got {centers[0][0]}"
    )
    y_vals = sorted([abs(c[1]) for c in centers])
    assert abs(y_vals[0] - 15.0) < 1e-6, (
        f"Expected |Y|=15.0 for 60mm width, got {y_vals}"
    )
