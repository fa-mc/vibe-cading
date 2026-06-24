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

"""Tests for ``vibe_cading.lego.technic_l_liftarm.LegoTechnicLLiftarm``.

Covers the Tests table from the design brief (tests 1–9; tests 10–11 are
CI/Developer validation steps, not pytest rows).

Design brief: docs/design_plans/2026-06-24-lego-technic-l-liftarm_design.md
Human design gate approved 2026-06-24.
"""

import pytest

from vibe_cading.lego.technic_l_liftarm import LegoTechnicLLiftarm
from vibe_cading.lego.constants import STUD_PITCH, BEAM_END_RADIUS


# ── Helper ─────────────────────────────────────────────────────────────────────

def _unique_hole_centres(part) -> list[tuple[float, float]]:
    """Return unique (x, y) centres of pin-hole cylinder faces.

    Filters CYLINDER faces to those whose radius is smaller than the arm
    end-cap radius (BEAM_END_RADIUS = 3.9 mm), which excludes the convex
    end-cap cylindrical faces and retains only bore and counterbore cylinders.

    The upper radius bound is set to BEAM_END_RADIUS - 0.1 mm so that a
    3.9 mm arm-end-cap cylinder cannot accidentally be classified as a hole.
    The counterbore max radius is TechnicPinHole.DEFAULT_CB_DIAMETER / 2
    = 3.1 mm, well below BEAM_END_RADIUS.

    Returns a deduplicated list of (cx, cy) rounded to 2 dp.  Multiple
    cylinder faces per hole (bore + counterbores) all share the same (cx, cy)
    axis centre and collapse to one entry.
    """
    # OCP is the OCCT wrapper used by cadquery (import path is OCP.*, not OCC.*).
    from OCP.BRep import BRep_Tool
    from OCP.GeomAdaptor import GeomAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder

    max_r = BEAM_END_RADIUS - 0.1  # < 3.9 mm; excludes end-cap arc cylinders
    centres: dict[tuple[float, float], None] = {}
    for face in part.faces().vals():
        try:
            if face.geomType() != "CYLINDER":
                continue
            surf = BRep_Tool.Surface_s(face.wrapped)
            adaptor = GeomAdaptor_Surface(surf)
            if adaptor.GetType() != GeomAbs_Cylinder:
                continue
            r = adaptor.Cylinder().Radius()
            if r >= max_r:
                continue  # skip end-cap arc cylinders (r = BEAM_END_RADIUS = 3.9)
            cx = round(face.Center().x, 2)
            cy = round(face.Center().y, 2)
            centres[(cx, cy)] = None
        except Exception:
            continue
    return list(centres.keys())


# ── Test 1 — Default 3×5 construction ─────────────────────────────────────────

def test_default_construction() -> None:
    """Test 1 — Default 3×5 construction returns a non-None Workplane."""
    part = LegoTechnicLLiftarm()
    assert part.solid is not None


# ── Test 2 — Single-solid topology (3×5) ──────────────────────────────────────

def test_single_solid_3x5() -> None:
    """Test 2 — 3×5 L-liftarm is a single contiguous solid."""
    part = LegoTechnicLLiftarm(arm_a_studs=3, arm_b_studs=5)
    assert len(part.solid.solids().vals()) == 1


# ── Test 3 — Hole count (3×5) ─────────────────────────────────────────────────

def test_hole_count_3x5() -> None:
    """Test 3 — 3×5 has exactly 7 unique hole positions (3 + 5 − 1)."""
    part = LegoTechnicLLiftarm(arm_a_studs=3, arm_b_studs=5)
    centres = _unique_hole_centres(part.solid)
    assert len(centres) == 7, (
        f"Expected 7 hole centres for 3×5, got {len(centres)}: {centres}"
    )


# ── Test 4 — Grid alignment (3×5) ─────────────────────────────────────────────

def test_grid_alignment_3x5() -> None:
    """Test 4 — All hole centres lie on the 8 mm stud grid."""
    part = LegoTechnicLLiftarm(arm_a_studs=3, arm_b_studs=5)
    centres = _unique_hole_centres(part.solid)
    half = STUD_PITCH / 2
    for cx, cy in centres:
        # X must be STUD_PITCH/2 + k×STUD_PITCH for some non-negative integer k.
        x_offset = cx - half
        assert abs(x_offset % STUD_PITCH) < 0.01 or abs(x_offset % STUD_PITCH - STUD_PITCH) < 0.01, (
            f"Hole at ({cx}, {cy}) has x not on 8 mm grid"
        )
        # Y must be −(STUD_PITCH/2 + k×STUD_PITCH) for some non-negative integer k.
        y_offset = abs(cy) - half
        assert abs(y_offset % STUD_PITCH) < 0.01 or abs(y_offset % STUD_PITCH - STUD_PITCH) < 0.01, (
            f"Hole at ({cx}, {cy}) has y not on 8 mm grid"
        )


# ── Test 5 — Corner hole shared (not duplicated) ──────────────────────────────

def test_corner_hole_not_duplicated() -> None:
    """Test 5 — Exactly one hole centre at (4.0, −4.0)."""
    part = LegoTechnicLLiftarm(arm_a_studs=3, arm_b_studs=5)
    centres = _unique_hole_centres(part.solid)
    corner_matches = [
        (cx, cy) for cx, cy in centres
        if abs(cx - 4.0) < 0.05 and abs(cy - (-4.0)) < 0.05
    ]
    assert len(corner_matches) == 1, (
        f"Expected exactly one hole at (4, −4), found {len(corner_matches)}: {corner_matches}"
    )


# ── Test 6 — Bounding box (3×5) ───────────────────────────────────────────────

def test_bounding_box_3x5() -> None:
    """Test 6 — 3×5 bounding box ≈ X∈[0, 24], Y∈[−40, 0], Z∈[0, 7.8]."""
    part = LegoTechnicLLiftarm(arm_a_studs=3, arm_b_studs=5)
    bb = part.solid.val().BoundingBox()
    assert bb.xmin == pytest.approx(0.0, abs=0.1)
    assert bb.xmax == pytest.approx(24.0, abs=0.1)
    assert bb.ymin == pytest.approx(-40.0, abs=0.1)
    assert bb.ymax == pytest.approx(0.0, abs=0.1)
    assert bb.zmin == pytest.approx(0.0, abs=0.1)
    assert bb.zmax == pytest.approx(7.8, abs=0.1)


# ── Test 7 — Parametric minimal 1×1 ──────────────────────────────────────────

def test_parametric_1x1() -> None:
    """Test 7 — arm_a=1, arm_b=1: 1 unique hole; single solid; bbox ≈ 8×8 footprint."""
    part = LegoTechnicLLiftarm(arm_a_studs=1, arm_b_studs=1)
    solid = part.solid
    assert len(solid.solids().vals()) == 1
    centres = _unique_hole_centres(solid)
    assert len(centres) == 1, f"Expected 1 hole for 1×1, got {len(centres)}: {centres}"
    bb = solid.val().BoundingBox()
    # Arm-A and Arm-B both span 8 mm; bounding box should cover ~8×8 in XY.
    assert bb.xmax == pytest.approx(8.0, abs=0.1)
    assert bb.ymin == pytest.approx(-8.0, abs=0.1)


# ── Test 8 — Parametric large 5×7 ────────────────────────────────────────────

def test_parametric_5x7() -> None:
    """Test 8 — arm_a=5, arm_b=7: 11 unique holes; bbox ≈ X∈[0,40], Y∈[−56,0]."""
    part = LegoTechnicLLiftarm(arm_a_studs=5, arm_b_studs=7)
    solid = part.solid
    assert len(solid.solids().vals()) == 1
    centres = _unique_hole_centres(solid)
    assert len(centres) == 11, (
        f"Expected 11 holes for 5×7, got {len(centres)}: {centres}"
    )
    bb = solid.val().BoundingBox()
    assert bb.xmax == pytest.approx(40.0, abs=0.1)
    assert bb.ymin == pytest.approx(-56.0, abs=0.1)


# ── Test 9 — Symmetric 3×3 ────────────────────────────────────────────────────

def test_parametric_3x3() -> None:
    """Test 9 — arm_a=3, arm_b=3: 5 unique holes; bbox ≈ X∈[0,24], Y∈[−24,0]."""
    part = LegoTechnicLLiftarm(arm_a_studs=3, arm_b_studs=3)
    solid = part.solid
    assert len(solid.solids().vals()) == 1
    centres = _unique_hole_centres(solid)
    assert len(centres) == 5, (
        f"Expected 5 holes for 3×3, got {len(centres)}: {centres}"
    )
    bb = solid.val().BoundingBox()
    assert bb.xmax == pytest.approx(24.0, abs=0.1)
    assert bb.ymin == pytest.approx(-24.0, abs=0.1)


# ── Validation tests — invalid inputs ─────────────────────────────────────────

def test_invalid_arm_a_raises() -> None:
    """Arm-A < 1 must raise ValueError."""
    with pytest.raises(ValueError):
        LegoTechnicLLiftarm(arm_a_studs=0)


def test_invalid_arm_b_raises() -> None:
    """Arm-B < 1 must raise ValueError."""
    with pytest.raises(ValueError):
        LegoTechnicLLiftarm(arm_b_studs=0)
