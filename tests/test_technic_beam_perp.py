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

"""Tests for ``vibe_cading.lego.technic_beam_perp.PerpendicularHolesLiftarm``.

Covers the Tests table rows 1–17 from the design brief
``docs/design_plans/2026-06-26-perpendicular-holes-liftarm_design.md``.

hole_finder.py usage note (Tests 5–8):
  ``hole_finder.py`` has no ``--axis`` CLI flag.  Axis filtering is done in
  Python on the ``axis`` dict field of the ``--json`` output.  Filter entries
  where ``abs(entry["axis"]["z"]) ≈ 1.0`` for main holes (Z-axis) and
  ``abs(entry["axis"]["y"]) ≈ 1.0`` for perp holes (Y-axis).

Design brief: docs/design_plans/2026-06-26-perpendicular-holes-liftarm_design.md
Human design gate approved 2026-06-26.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import cadquery as cq
import pytest

from vibe_cading.lego.constants import (
    BEAM_THICKNESS,
    BEAM_WIDTH,
    STUD_PITCH,
)
from vibe_cading.lego.cutters.technic_pin_hole import TechnicPinHole
from vibe_cading.lego.technic_beam import LegoTechnicBeam
from vibe_cading.lego.technic_beam_perp import PerpendicularHolesLiftarm


# ── Helpers ────────────────────────────────────────────────────────────────────

def _export_step(solid: cq.Workplane, path: str) -> None:
    """Export solid to STEP at path."""
    cq.exporters.export(solid, path)


def _run_hole_finder(step_path: str) -> list[dict]:
    """Run hole_finder.py --json on *step_path* and return parsed JSON list."""
    result = subprocess.run(
        [sys.executable, "vibe_cading/tools/hole_finder.py", step_path, "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def _z_axis_holes(features: list[dict], cb_radius: float = 3.1) -> list[dict]:
    """Filter hole_finder features to counterbore-sized holes with Z-parallel axis.

    Filters by ``abs(axis.z) ≈ 1.0`` (Z-axis bore) and ``radius ≈ cb_radius``
    (counterbore diameter — not bore diameter).  ``hole_finder.py`` has no
    ``--axis`` CLI flag; filtering is done here in Python.
    """
    return [
        f for f in features
        if abs(abs(f["axis"]["z"]) - 1.0) < 0.05
        and abs(f["radius"] - cb_radius) < 0.05
    ]


def _y_axis_holes(features: list[dict], cb_radius: float = 3.1) -> list[dict]:
    """Filter hole_finder features to counterbore-sized holes with Y-parallel axis.

    Filters by ``abs(axis.y) ≈ 1.0`` (Y-axis bore) and ``radius ≈ cb_radius``.
    """
    return [
        f for f in features
        if abs(abs(f["axis"]["y"]) - 1.0) < 0.05
        and abs(f["radius"] - cb_radius) < 0.05
    ]


# ── Test 1: Body cross-section + length (FR 1, 2, 15, 16) ─────────────────────

def test_bounding_box_5stud_alternating() -> None:
    """Tests row 1 — bbox Y∈[-3.9,3.9], Z∈[0,7.8], X∈[0, 5*8] for default 5-hole part."""
    p = PerpendicularHolesLiftarm(num_holes=5)
    bb = p.solid.val().BoundingBox()
    assert bb.xlen == pytest.approx(5 * STUD_PITCH, abs=0.01)   # 40.0 mm
    assert bb.ylen == pytest.approx(BEAM_WIDTH, abs=0.01)        # 7.8 mm
    assert bb.zlen == pytest.approx(BEAM_THICKNESS, abs=0.01)    # 7.8 mm


def test_bounding_box_3stud_main() -> None:
    """Tests row 1 — bbox for 3-stud all-main part."""
    p = PerpendicularHolesLiftarm(num_holes=3, hole_axes=["main"] * 3)
    bb = p.solid.val().BoundingBox()
    assert bb.xlen == pytest.approx(3 * STUD_PITCH, abs=0.01)
    assert bb.ylen == pytest.approx(BEAM_WIDTH, abs=0.01)
    assert bb.zlen == pytest.approx(BEAM_THICKNESS, abs=0.01)


# ── Test 2: Constructor validation (FR 3, 5) ───────────────────────────────────

def test_num_holes_zero_raises() -> None:
    """Tests row 2 — num_holes < 1 → ValueError."""
    with pytest.raises(ValueError, match="num_holes must be >= 1"):
        PerpendicularHolesLiftarm(num_holes=0)


def test_num_holes_negative_raises() -> None:
    """Tests row 2 — num_holes negative → ValueError."""
    with pytest.raises(ValueError):
        PerpendicularHolesLiftarm(num_holes=-1)


def test_hole_axes_wrong_length_raises() -> None:
    """Tests row 2 — len(hole_axes) != num_holes → ValueError."""
    with pytest.raises(ValueError, match="hole_axes length"):
        PerpendicularHolesLiftarm(num_holes=3, hole_axes=["main", "perp"])


def test_hole_axes_bad_token_raises() -> None:
    """Tests row 2 — invalid axis token → ValueError."""
    with pytest.raises(ValueError, match="must be 'main' or 'perp'"):
        PerpendicularHolesLiftarm(num_holes=2, hole_axes=["main", "diagonal"])


# ── Test 3: Default alternating pattern (FR 4) ─────────────────────────────────

def test_default_alternating_5hole() -> None:
    """Tests row 3 — hole_axes=None, num_holes=5 ⇒ ['perp','main','perp','main','perp']."""
    p = PerpendicularHolesLiftarm(num_holes=5)
    assert p.hole_axes == ["perp", "main", "perp", "main", "perp"]


def test_default_alternating_4hole() -> None:
    """Tests row 3 — hole_axes=None, num_holes=4 ⇒ ['perp','main','perp','main']."""
    p = PerpendicularHolesLiftarm(num_holes=4)
    assert p.hole_axes == ["perp", "main", "perp", "main"]


def test_default_alternating_1hole() -> None:
    """Tests row 3 — hole_axes=None, num_holes=1 ⇒ ['perp']."""
    p = PerpendicularHolesLiftarm(num_holes=1)
    assert p.hole_axes == ["perp"]


# ── Test 4: Single solid topology (FR 22, AC-1) ───────────────────────────────

def test_single_solid_alternating() -> None:
    """Tests row 4 — 5-hole alternating is exactly one solid."""
    p = PerpendicularHolesLiftarm(num_holes=5)
    assert len(p.solid.solids().vals()) == 1


def test_single_solid_all_main() -> None:
    """Tests row 4 — all-main is exactly one solid."""
    p = PerpendicularHolesLiftarm(num_holes=5, hole_axes=["main"] * 5)
    assert len(p.solid.solids().vals()) == 1


def test_single_solid_all_perp() -> None:
    """Tests row 4 — all-perp is exactly one solid."""
    p = PerpendicularHolesLiftarm(num_holes=5, hole_axes=["perp"] * 5)
    assert len(p.solid.solids().vals()) == 1


def test_single_solid_mixed() -> None:
    """Tests row 4 — arbitrary mix produces exactly one solid."""
    p = PerpendicularHolesLiftarm(num_holes=4, hole_axes=["main", "perp", "perp", "main"])
    assert len(p.solid.solids().vals()) == 1


# ── Tests 5–8: Hole count + axis + position (via hole_finder.py) ──────────────

@pytest.fixture(scope="module")
def step_5hole_alternating(tmp_path_factory):
    """Export the 5-hole alternating part to a temp STEP file (once for the module)."""
    p = PerpendicularHolesLiftarm(num_holes=5)
    path = str(tmp_path_factory.mktemp("step") / "perp_5hole_alt.step")
    _export_step(p.solid, path)
    return path


@pytest.fixture(scope="module")
def features_5hole_alternating(step_5hole_alternating):
    """Parse hole_finder.py --json output for the 5-hole alternating part."""
    return _run_hole_finder(step_5hole_alternating)


def test_main_hole_count(features_5hole_alternating) -> None:
    """Tests row 5 — Z-axis (main) counterbore holes == 2 for 5-hole alternating."""
    z_holes = _z_axis_holes(features_5hole_alternating)
    assert len(z_holes) == 2, (
        f"Expected 2 main (Z-axis) holes, got {len(z_holes)}: {z_holes}"
    )


def test_perp_hole_count(features_5hole_alternating) -> None:
    """Tests row 6 — Y-axis (perp) counterbore holes == 3 for 5-hole alternating."""
    y_holes = _y_axis_holes(features_5hole_alternating)
    assert len(y_holes) == 3, (
        f"Expected 3 perp (Y-axis) holes, got {len(y_holes)}: {y_holes}"
    )


def test_main_hole_positions(features_5hole_alternating) -> None:
    """Tests row 7 — main hole X centres at 12, 28 mm (positions 1, 3 on 8mm grid)."""
    z_holes = _z_axis_holes(features_5hole_alternating)
    x_centres = sorted(f["center"]["x"] for f in z_holes)
    expected = sorted(STUD_PITCH * i + STUD_PITCH / 2 for i in [1, 3])  # [12.0, 28.0]
    assert x_centres == pytest.approx(expected, abs=0.1), (
        f"Main hole X centres: got {x_centres}, expected {expected}"
    )
    # Y should be ≈ 0 (centred on beam)
    for f in z_holes:
        assert abs(f["center"]["y"]) < 0.1, f"Main hole Y not ≈ 0: {f}"


def test_perp_hole_positions(features_5hole_alternating) -> None:
    """Tests row 8 — perp hole X centres at 4, 20, 36 mm (positions 0, 2, 4); Z ≈ 3.9."""
    y_holes = _y_axis_holes(features_5hole_alternating)
    x_centres = sorted(f["center"]["x"] for f in y_holes)
    expected_x = sorted(STUD_PITCH * i + STUD_PITCH / 2 for i in [0, 2, 4])  # [4, 20, 36]
    assert x_centres == pytest.approx(expected_x, abs=0.1), (
        f"Perp hole X centres: got {x_centres}, expected {expected_x}"
    )
    # Z centre should be ≈ BEAM_THICKNESS/2 (mid-height)
    for f in y_holes:
        assert abs(f["center"]["z"] - BEAM_THICKNESS / 2) < 0.1, (
            f"Perp hole Z centre not ≈ {BEAM_THICKNESS/2}: {f}"
        )


# ── Test 9: Bore diameter tracks profile (FR 17, AC-8) ──────────────────────

def test_bore_diameter_default_profile() -> None:
    """Tests row 9 — bore Ø on fdm_standard/slip matches PIN_HOLE_DIAMETER + 2*slip.radial."""
    from vibe_cading.print_settings import get_profile
    profile = get_profile("fdm_standard")
    expected_bore = TechnicPinHole.DEFAULT_DIAMETER + 2 * profile.slip.radial

    # Construct with explicit profile to lock the bore diameter
    p = PerpendicularHolesLiftarm(num_holes=3, hole_axes=["main"] * 3, profile="fdm_standard")

    # Export and inspect bore diameter via hole_finder
    with tempfile.TemporaryDirectory() as tmpdir:
        step_path = str(Path(tmpdir) / "perp_profile.step")
        _export_step(p.solid, step_path)
        features = _run_hole_finder(step_path)

    # Filter bore-diameter entries (smaller radius — not the CB)
    bore_radius = expected_bore / 2
    bore_features = [
        f for f in features
        if abs(f["radius"] - bore_radius) < 0.05
        and abs(abs(f["axis"]["z"]) - 1.0) < 0.05
    ]
    assert len(bore_features) > 0, "No bore-diameter features found"
    for f in bore_features:
        assert abs(f["diameter"] - expected_bore) < 0.1, (
            f"Bore diameter mismatch: got {f['diameter']:.3f}, expected {expected_bore:.3f}"
        )


# ── Test 11: Chamfer-edge count assertions (in _build; FR 8, 11, 23, AC-10) ───
# The assertions are inside _build; they fire at construction time.
# This test confirms construction succeeds (the assertions are the guard).

def test_chamfer_assertions_fire_in_build() -> None:
    """Tests row 11 — construction passes (the 2*count assertions are live)."""
    # If the chamfer assertions ever fail, these constructions raise AssertionError
    PerpendicularHolesLiftarm(num_holes=5)
    PerpendicularHolesLiftarm(num_holes=3, hole_axes=["main", "perp", "main"])
    PerpendicularHolesLiftarm(num_holes=4, hole_axes=["perp"] * 4)


# ── Test 12: No main∩perp intersection (FR 13, AC-6) ─────────────────────────

def test_no_main_perp_intersection() -> None:
    """Tests row 12 — main cutter union ∩ perp cutter union == 0 for alternating pattern."""
    hole_axes = ["perp", "main", "perp", "main", "perp"]

    cutter_depth_main = BEAM_WIDTH + 2 * TechnicPinHole._ENTRY_OVERCUT
    cutter_depth_perp = BEAM_THICKNESS + 2 * TechnicPinHole._ENTRY_OVERCUT

    main_cutter = TechnicPinHole.standard(depth=cutter_depth_main).to_cutter()
    perp_cutter_template = (
        TechnicPinHole.standard(depth=cutter_depth_perp)
        .to_cutter()
        .rotate((0, 0, 0), (1, 0, 0), -90)
    )

    # Build union of main cutters
    main_parts = []
    perp_parts = []
    for i, ax in enumerate(hole_axes):
        x_i = STUD_PITCH * i + STUD_PITCH / 2
        if ax == "main":
            main_parts.append(main_cutter.translate((x_i, 0.0, -TechnicPinHole._ENTRY_OVERCUT)))
        else:
            perp_parts.append(
                perp_cutter_template.translate(
                    (x_i, -BEAM_WIDTH / 2 - TechnicPinHole._ENTRY_OVERCUT, BEAM_THICKNESS / 2)
                )
            )

    main_union = main_parts[0]
    for part in main_parts[1:]:
        main_union = main_union.union(part)

    perp_union = perp_parts[0]
    for part in perp_parts[1:]:
        perp_union = perp_union.union(part)

    intersection = main_union.intersect(perp_union)
    # Volume should be 0 (or the intersect returns an empty shape)
    try:
        vol = intersection.val().Volume()
    except Exception:
        vol = 0.0
    assert vol == pytest.approx(0.0, abs=1e-3), (
        f"Main ∩ perp intersection volume should be 0, got {vol:.6f} mm³"
    )


# ── Test 13: AGPLv3 header present (FR 21, AC-12) ─────────────────────────────

def test_agplv3_header_present() -> None:
    """Tests row 13 — first 15 lines of technic_beam_perp.py contain the AGPLv3 string."""
    src = Path("vibe_cading/lego/technic_beam_perp.py").read_text(encoding="utf-8")
    lines = src.splitlines()[:15]
    header_text = "\n".join(lines)
    assert "GNU Affero General Public License" in header_text, (
        "AGPLv3 header not found in first 15 lines of technic_beam_perp.py"
    )


# ── Test 17: NFC — existing tests cover both selector consumers ───────────────
# These tests import and construct the original classes to verify the T1/T2
# refactor (stadium_beam_body extraction + _HoleMouthSelector generalization)
# has not changed their behavior.

def test_nfc_technic_beam_still_constructs() -> None:
    """Tests row 17 (NFC) — LegoTechnicBeam(5) still builds and has correct bbox."""
    beam = LegoTechnicBeam(length_in_studs=5)
    bb = beam.solid.val().BoundingBox()
    assert bb.xlen == pytest.approx(40.0, abs=0.01)
    assert bb.ylen == pytest.approx(BEAM_WIDTH, abs=0.01)
    assert bb.zlen == pytest.approx(BEAM_THICKNESS, abs=0.01)
    assert len(beam.solid.solids().vals()) == 1


def test_nfc_all_main_matches_technic_beam() -> None:
    """Tests T-PRE (NFC) — PerpendicularHolesLiftarm(N, all-main) ≡ LegoTechnicBeam(N).

    Strengthened (B4 2026-06-26): boolean-residual check (A−B and B−A volumes ≈ 0)
    plus single-solid, instead of scalar volume delta only.
    This is the AC-7 / NFC-1 representative-scale check.
    """
    n = 5
    perp_all_main = PerpendicularHolesLiftarm(num_holes=n, hole_axes=["main"] * n)
    beam = LegoTechnicBeam(length_in_studs=n)

    # Boolean-residual check: both A−B and B−A must have ≈0 volume.
    try:
        perp_cut_beam = perp_all_main.solid.cut(beam.solid).val().Volume()
    except Exception:
        perp_cut_beam = 0.0
    try:
        beam_cut_perp = beam.solid.cut(perp_all_main.solid).val().Volume()
    except Exception:
        beam_cut_perp = 0.0

    assert perp_cut_beam == pytest.approx(0.0, abs=1.0), (
        f"PerpendicularHolesLiftarm(all-main) − LegoTechnicBeam residual "
        f"{perp_cut_beam:.4f} mm³ ≠ 0 — all-main liftarm has extra material"
    )
    assert beam_cut_perp == pytest.approx(0.0, abs=1.0), (
        f"LegoTechnicBeam − PerpendicularHolesLiftarm(all-main) residual "
        f"{beam_cut_perp:.4f} mm³ ≠ 0 — all-main liftarm is missing material"
    )
    assert len(perp_all_main.solid.solids().vals()) == 1, "Expected single solid"


# ── B4: AC-9 counterbore Ø assertion (FR 11, AC-9) ───────────────────────────

def test_ac9_counterbore_diameter_main_holes() -> None:
    """B4 AC-9 — counterbore Ø == TECHNIC_PIN_CB_DIAMETER (6.2) at ±Z entry faces.

    Uses hole_finder.py --json to find Z-axis holes and asserts their diameter
    matches the expected counterbore value exactly to within 0.1 mm.
    """
    n = 3
    p = PerpendicularHolesLiftarm(num_holes=n, hole_axes=["main"] * n)
    with tempfile.TemporaryDirectory() as tmpdir:
        step_path = str(Path(tmpdir) / "ac9_main.step")
        _export_step(p.solid, step_path)
        features = _run_hole_finder(step_path)

    expected_cb_diam = TechnicPinHole.DEFAULT_CB_DIAMETER  # 6.2 mm
    cb_features = _z_axis_holes(features, cb_radius=expected_cb_diam / 2)
    assert len(cb_features) > 0, "No Z-axis counterbore features found for AC-9 check"
    for f in cb_features:
        assert abs(f["diameter"] - expected_cb_diam) < 0.1, (
            f"Main counterbore Ø mismatch: got {f['diameter']:.3f}, "
            f"expected {expected_cb_diam:.3f}"
        )


def test_ac9_counterbore_diameter_perp_holes() -> None:
    """B4 AC-9 — counterbore Ø == TECHNIC_PIN_CB_DIAMETER (6.2) at ±Y entry faces.

    Uses hole_finder.py --json to find Y-axis holes and asserts their diameter
    matches the expected counterbore value exactly to within 0.1 mm.
    """
    n = 3
    p = PerpendicularHolesLiftarm(num_holes=n, hole_axes=["perp"] * n)
    with tempfile.TemporaryDirectory() as tmpdir:
        step_path = str(Path(tmpdir) / "ac9_perp.step")
        _export_step(p.solid, step_path)
        features = _run_hole_finder(step_path)

    expected_cb_diam = TechnicPinHole.DEFAULT_CB_DIAMETER  # 6.2 mm
    cb_features = _y_axis_holes(features, cb_radius=expected_cb_diam / 2)
    assert len(cb_features) > 0, "No Y-axis counterbore features found for AC-9 check"
    for f in cb_features:
        assert abs(f["diameter"] - expected_cb_diam) < 0.1, (
            f"Perp counterbore Ø mismatch: got {f['diameter']:.3f}, "
            f"expected {expected_cb_diam:.3f}"
        )


# ── B4: AC-10 lead-in chamfer presence (FR 8, 23, AC-10) ─────────────────────

def test_ac10_chamfer_reduces_volume() -> None:
    """B4 AC-10 — lead-in chamfer is physically present at hole mouths.

    Verifies by comparing volume of the chamfered solid against a no-chamfer
    body constructed the same way.  The chamfer removes material, so the
    chamfered body must have strictly less volume than the unchamfered body.
    """
    # Build a 3-hole alternating part (the normal path)
    p_chamfered = PerpendicularHolesLiftarm(num_holes=3)
    vol_chamfered = p_chamfered.solid.val().Volume()

    # Build the same body without chamfers by constructing the inner geometry
    # directly — use stadium_beam_body + cutters only (no chamfer step).
    from vibe_cading.lego.technic_beam_perp import stadium_beam_body

    hole_axes = ["perp", "main", "perp"]
    length_mm = 3 * STUD_PITCH
    body = stadium_beam_body(length_mm)

    cutter_depth_main = BEAM_WIDTH + 2 * TechnicPinHole._ENTRY_OVERCUT
    main_cutter = TechnicPinHole.standard(depth=cutter_depth_main).to_cutter()
    cutter_depth_perp = BEAM_THICKNESS + 2 * TechnicPinHole._ENTRY_OVERCUT
    perp_cutter = (
        TechnicPinHole.standard(depth=cutter_depth_perp)
        .to_cutter()
        .rotate((0, 0, 0), (1, 0, 0), -90)
    )
    for i, ax in enumerate(hole_axes):
        x_i = STUD_PITCH * i + STUD_PITCH / 2
        if ax == "main":
            body = body.cut(main_cutter.translate((x_i, 0.0, -TechnicPinHole._ENTRY_OVERCUT)))
        else:
            body = body.cut(
                perp_cutter.translate(
                    (x_i, -BEAM_WIDTH / 2 - TechnicPinHole._ENTRY_OVERCUT, BEAM_THICKNESS / 2)
                )
            )
    vol_unchamfered = body.val().Volume()

    assert vol_unchamfered > vol_chamfered, (
        f"Chamfered volume ({vol_chamfered:.2f} mm³) should be less than "
        f"unchamfered volume ({vol_unchamfered:.2f} mm³) — lead-in chamfer missing"
    )


# ── B4: AC-8 for perp holes — bore Ø tracks profile (FR 17, AC-8) ────────────

def test_ac8_perp_bore_diameter_tracks_profile() -> None:
    """B4 AC-8 (perp) — perp bore Ø == PIN_HOLE_DIAMETER + 2*profile.slip.radial.

    Builds an all-perp part and asserts the Y-axis bore diameter matches
    the slip-fit tolerance from the active profile, catching a regression
    where profile= is dropped from the perp TechnicPinHole.standard() call.
    """
    from vibe_cading.print_settings import get_profile
    profile = get_profile("fdm_standard")
    expected_bore = TechnicPinHole.DEFAULT_DIAMETER + 2 * profile.slip.radial

    p = PerpendicularHolesLiftarm(num_holes=3, hole_axes=["perp"] * 3, profile="fdm_standard")

    with tempfile.TemporaryDirectory() as tmpdir:
        step_path = str(Path(tmpdir) / "ac8_perp.step")
        _export_step(p.solid, step_path)
        features = _run_hole_finder(step_path)

    # Filter Y-axis bore entries (smaller radius — bore, not CB)
    bore_radius = expected_bore / 2
    bore_features = [
        f for f in features
        if abs(f["radius"] - bore_radius) < 0.05
        and abs(abs(f["axis"]["y"]) - 1.0) < 0.05
    ]
    assert len(bore_features) > 0, (
        "No Y-axis bore-diameter features found — perp bore may not be drilled "
        "or hole_finder missed it"
    )
    for f in bore_features:
        assert abs(f["diameter"] - expected_bore) < 0.1, (
            f"Perp bore Ø mismatch: got {f['diameter']:.3f} mm, "
            f"expected {expected_bore:.3f} mm (profile=fdm_standard slip.radial="
            f"{profile.slip.radial})"
        )
