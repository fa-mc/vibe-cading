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

"""Tests for the axle-hole tip-to-tip gauge task.

Covers the design's Tests 1-5 (see
``.agents/plans/2026-05-20-axle-hole-tip-to-tip-gauge_design.md``):
the new ``AxleHoleGauge`` model class and the re-sourced
``TechnicAxleHole`` cutter.  Test 6 (existing consumers unaffected) is
covered by the rest of the suite passing unchanged.
"""

import pytest

from vibe_cading.lego.axle_hole_gauge import AxleHoleGauge
from vibe_cading.lego.cutters.technic_axle_hole import TechnicAxleHole
from vibe_cading.print_settings import FitGrade, ToleranceProfile, get_profile


def _xy_bbox(workplane):
    bb = workplane.val().BoundingBox()
    return bb.xlen, bb.ylen


# ── Test 1 — AxleHoleGauge builds a single solid ─────────────────────────────
def test_gauge_builds_single_solid() -> None:
    """Default AxleHoleGauge is exactly one contiguous solid."""
    gauge = AxleHoleGauge()
    assert len(gauge.solid.solids().vals()) == 1


# ── Test 2 — one through-hole per swept diameter ─────────────────────────────
def test_gauge_hole_count_matches_sweep() -> None:
    """Each swept diameter yields one round through-hole.

    A round through-hole contributes exactly one CYLINDER face whose XY
    bounding box equals its diameter and whose Z span equals the block
    depth (Face has no ``.radius()`` — bbox is the verified wire format).
    """
    gauge = AxleHoleGauge()
    hole_dias = []
    for face in gauge.solid.faces().vals():
        if face.geomType() == "CYLINDER":
            bb = face.BoundingBox()
            assert bb.zlen == pytest.approx(gauge.depth, abs=1e-6), (
                "hole does not span the full block depth (not through)"
            )
            hole_dias.append(round(bb.xlen, 3))
    assert sorted(hole_dias) == sorted(round(d, 3) for d in gauge.diameters)


def test_gauge_holes_form_single_row() -> None:
    """All hole centres share one Y coordinate (single row along X)."""
    gauge = AxleHoleGauge()
    centre_ys = set()
    for face in gauge.solid.faces().vals():
        if face.geomType() == "CYLINDER":
            bb = face.BoundingBox()
            centre_ys.add(round((bb.ymin + bb.ymax) / 2.0, 3))
    assert len(centre_ys) == 1


def test_gauge_rejects_empty_sweep() -> None:
    """An empty ``diameters`` sequence raises ValueError."""
    with pytest.raises(ValueError):
        AxleHoleGauge(diameters=())


# ── Test 3 — TechnicAxleHole default (slip) cutter dimensions ────────────────
def test_axle_hole_slip_cutter_dimensions() -> None:
    """fdm_standard slip cutter is 4.90 x 4.90 mm.

    The cutter is sized ``nominal + 2 * grade.radial``: the 4.80 mm
    real-Lego nominal plus twice the shipped ``fdm_standard`` slip
    radial (0.05) = 4.90 mm.

    The ``fdm_standard`` profile is passed explicitly so the assertion is
    independent of whatever ``VIBE_PRINT_PROFILE`` the contributor's
    ``.env`` resolves to — a bare ``TechnicAxleHole(depth=8.0)`` picks up
    the ambient default profile, which is not deterministic across hosts.
    """
    fdm = get_profile("fdm_standard")
    xlen, ylen = _xy_bbox(
        TechnicAxleHole(depth=8.0, fit="slip", profile=fdm).to_cutter()
    )
    assert xlen == pytest.approx(4.90, abs=1e-6)
    assert ylen == pytest.approx(4.90, abs=1e-6)


# ── Test 4 — fit grade ordering (tip-to-tip monotonic) ───────────────────────
def test_axle_hole_fit_grade_ordering() -> None:
    """free cutter wider than slip wider than press."""
    free_x, _ = _xy_bbox(TechnicAxleHole(depth=8.0, fit="free").to_cutter())
    slip_x, _ = _xy_bbox(TechnicAxleHole(depth=8.0, fit="slip").to_cutter())
    press_x, _ = _xy_bbox(TechnicAxleHole(depth=8.0, fit="press").to_cutter())
    assert free_x > slip_x > press_x


# ── Test 5 — profile override moves the cutter ───────────────────────────────
def test_axle_hole_profile_override_moves_cutter() -> None:
    """A ToleranceProfile with a larger ``slip.radial`` widens the cutter.

    Printer calibration lives in the ``ToleranceProfile`` (not an env
    constant): the cutter is ``AXLE_HOLE_TIP_TO_TIP + 2 * slip.radial``,
    so a profile whose ``slip.radial`` is 0.10 mm yields a 5.00 mm cutter
    (4.80 + 0.20), confirming the profile drives the dimension.
    """
    calibrated = ToleranceProfile(
        name="calibrated",
        free=FitGrade(radial=0.15, axial=0.20),
        slip=FitGrade(radial=0.10, axial=0.20),
        press=FitGrade(radial=0.04, axial=0.20),
    )
    xlen, ylen = _xy_bbox(
        TechnicAxleHole(depth=8.0, fit="slip", profile=calibrated).to_cutter()
    )
    assert xlen == pytest.approx(5.00, abs=1e-6)
    assert ylen == pytest.approx(5.00, abs=1e-6)


# ── Stage 2b — FitGrade.slot widens the arm slot ─────────────────────────────
def test_axle_hole_slot_widens_arm_only() -> None:
    """``slip.slot`` widens ``ARM_WIDTH`` by ``2 * slot``; ``TIP_TO_TIP``
    is untouched.

    Stage 2b Test #4: the narrow ``+`` cross slot prints tighter on FDM
    than the round envelope, so ``slot`` is an *additional* allowance
    applied only to the arm width. Two profiles identical but for
    ``slip.slot`` must produce the same ``TIP_TO_TIP`` and an
    ``ARM_WIDTH`` differing by exactly ``2 * (slot_b - slot_a)``.
    """
    no_slot = ToleranceProfile(
        name="no_slot",
        free=FitGrade(radial=0.15, axial=0.20),
        slip=FitGrade(radial=0.05, axial=0.20, slot=0.0),
        press=FitGrade(radial=0.04, axial=0.20),
    )
    with_slot = ToleranceProfile(
        name="with_slot",
        free=FitGrade(radial=0.15, axial=0.20),
        slip=FitGrade(radial=0.05, axial=0.20, slot=0.10),
        press=FitGrade(radial=0.04, axial=0.20),
    )
    base = TechnicAxleHole(depth=8.0, fit="slip", profile=no_slot)
    widened = TechnicAxleHole(depth=8.0, fit="slip", profile=with_slot)

    # TIP_TO_TIP (round envelope) is identical — slot does not touch it.
    assert widened.TIP_TO_TIP == pytest.approx(base.TIP_TO_TIP, abs=1e-9)
    # ARM_WIDTH grows by exactly 2 * slot.
    assert widened.ARM_WIDTH - base.ARM_WIDTH == pytest.approx(2 * 0.10, abs=1e-9)


def test_axle_hole_shipped_fdm_standard_arm() -> None:
    """Shipped ``fdm_standard`` slip → arm 2.13 mm, tip-to-tip 4.90 mm.

    Stage 2b Test #5 (Amendment): the shipped ``fdm_standard`` profile
    carries ``slip.slot = 0.10``, so the arm slot is
    ``1.83 + 2*0.05 + 2*0.10 = 2.13 mm`` — the *tight half* of the proven
    2.15-2.35 working band. The round tip-to-tip is unchanged at
    ``4.80 + 2*0.05 = 4.90 mm``.
    """
    fdm = get_profile("fdm_standard")
    hole = TechnicAxleHole(depth=8.0, fit="slip", profile=fdm)
    assert hole.ARM_WIDTH == pytest.approx(2.13, abs=1e-6)
    assert hole.TIP_TO_TIP == pytest.approx(4.90, abs=1e-6)


def test_axle_hole_legacy_flat_profile_arm() -> None:
    """A legacy-flat profile migrates with ``slot=0.0`` → arm 1.93 mm.

    Stage 2b new test: a stale legacy-flat ``print_profiles_user.json`` (or
    the legacy-named ``machine_profiles_user.json``) has no narrow-slot
    concept; it migrates to ``slip.slot = 0.0``, so the
    arm is ``1.83 + 2*0.05 = 1.93 mm`` — pre-Stage-2b behaviour. This pins
    the intentional legacy/nested divergence (nested ``fdm_standard``
    ships 2.13) against a silent regression.
    """
    legacy_slip = FitGrade(radial=0.05, axial=0.20)  # no slot → 0.0
    legacy = ToleranceProfile(
        name="legacy_flat",
        free=FitGrade(radial=0.15, axial=0.20),
        slip=legacy_slip,
        press=FitGrade(radial=0.04, axial=0.20),
    )
    hole = TechnicAxleHole(depth=8.0, fit="slip", profile=legacy)
    assert hole.ARM_WIDTH == pytest.approx(1.93, abs=1e-6)


def test_axle_hole_calibrated_bambu_arm() -> None:
    """Calibrated ``bambu_p1s`` (nested, ``slip.slot 0.10``) → arm 2.25 mm.

    Stage 2b Test #6: the user's migrated profile has
    ``slip.radial = 0.11`` and ``slip.slot = 0.10``, so the arm is
    ``1.83 + 2*0.11 + 2*0.10 = 2.25 mm`` — exactly the Stage-2 ``W_good``.
    Tip-to-tip is ``4.80 + 2*0.11 = 5.02 mm``.
    """
    bambu = ToleranceProfile(
        name="bambu_p1s",
        free=FitGrade(radial=0.15, axial=0.20),
        slip=FitGrade(radial=0.11, axial=0.20, slot=0.10),
        press=FitGrade(radial=0.04, axial=0.20),
    )
    hole = TechnicAxleHole(depth=8.0, fit="slip", profile=bambu)
    assert hole.ARM_WIDTH == pytest.approx(2.25, abs=1e-6)
    assert hole.TIP_TO_TIP == pytest.approx(5.02, abs=1e-6)
