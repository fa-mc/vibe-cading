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

"""Tests for the RC hex hub + MR85 bearing housing family.

Covers the Tests table from the design brief
``docs/design_plans/2026-08-25-rc-hex-hub-bearing_design.md``.
"""

from __future__ import annotations

import math

import cadquery as cq
import pytest

from vibe_cading.print_settings import get_profile
from vibe_cading.rc.hex_hub_bearing.bearing_hex_housing import BearingHexHousing
from vibe_cading.rc.hex_hub_bearing.hex_hub_nut import HexHubNut
from vibe_cading.rc.hex_hub_bearing.hex_hub_with_bearing import HexHubWithBearing


# ── Test 1 / 2 — HexHubNut single-solid topology + bounding box ───────────

def test_hex_hub_nut_single_solid() -> None:
    nut = HexHubNut()
    assert len(nut.solid.solids().vals()) == 1


def test_hex_hub_nut_bounding_box() -> None:
    nut = HexHubNut()
    bb = nut.solid.val().BoundingBox()
    # The vertex-aligned X extent (circumdiameter) is trimmed by the
    # chamfer, which cuts the sharp hex corners; the flat-aligned Y extent
    # (across-flats, mid-edge) is untouched by a corner chamfer.
    expected_circumdia = 12.0 / math.cos(math.radians(30)) - nut.hex_chamfer
    assert bb.xlen == pytest.approx(expected_circumdia, abs=1e-6)
    assert bb.ylen == pytest.approx(12.0, abs=1e-6)
    assert bb.zlen == pytest.approx(6.0, abs=1e-6)


# ── Test 3 — HexHubNut bore reflects `free` fit grade, not bare nominal ───

def test_hex_hub_nut_bore_is_free_fit() -> None:
    prof = get_profile()
    nut = HexHubNut()
    expected_radius = 6.0 / 2.0 + prof.free.radial
    assert expected_radius != pytest.approx(3.0), (
        "test is not falsifiable if free.radial resolves to 0.0"
    )
    assert nut._bore_dia / 2.0 == pytest.approx(expected_radius, abs=1e-9)


# ── Test 13 — hex-nut wall thickness (bore edge to nearest hex flat) ──────
# (new, D8 Round 4 — the larger 6 mm bore must not thin the wall to a
# print-failure risk; the brief's Dimension Table computes 2.85 mm on
# fdm_standard: hex inradius (across_flats / 2 = 6.0 mm) minus printed bore
# radius (6.30 / 2 = 3.15 mm).)

def test_hex_hub_nut_wall_thickness_not_thin() -> None:
    prof = get_profile()
    nut = HexHubNut()
    hex_inradius = nut.hex_across_flats / 2.0
    bore_radius = nut._bore_dia / 2.0
    wall = hex_inradius - bore_radius
    expected_wall = 12.0 / 2.0 - (6.0 + 2.0 * prof.free.radial) / 2.0
    assert wall == pytest.approx(expected_wall, abs=1e-9)
    # Comfortably clear of a typical multi-perimeter FDM thin-wall minimum
    # (well under 1 mm would be a real risk); this is a floor, not a bare
    # existence check -- see the design brief's D8 wall-thickness check.
    assert wall > 1.5


# ── Test 4 — BearingHexHousing single-solid topology ──────────────────────

def test_bearing_hex_housing_single_solid() -> None:
    housing = BearingHexHousing()
    assert len(housing.solid.solids().vals()) == 1


# ── Test 7 — Falsifiable clearance: nominal bearing OD fits, oversized doesn't

def test_bearing_hex_housing_pocket_admits_nominal_bearing() -> None:
    """A real 8.000 mm nominal-OD bearing cylinder must NOT interfere with
    the printed pocket cavity -- proving the printed bore is larger than
    nominal, not merely equal to it."""
    housing = BearingHexHousing().solid
    nominal = cq.Workplane("XY").circle(8.000 / 2.0).extrude(2.5)
    inter = housing.intersect(nominal)
    vol = sum(s.Volume() for s in inter.solids().vals()) if inter.solids().vals() else 0.0
    assert vol == pytest.approx(0.0, abs=1e-6)


def test_bearing_hex_housing_pocket_rejects_oversized_probe() -> None:
    """Positive control for the above: an oversized (8.10 mm) cylinder MUST
    show interference, proving the probe can actually detect a collision."""
    housing = BearingHexHousing().solid
    oversized = cq.Workplane("XY").circle(8.10 / 2.0).extrude(2.5)
    inter = housing.intersect(oversized)
    vol = sum(s.Volume() for s in inter.solids().vals()) if inter.solids().vals() else 0.0
    assert vol > 0.0


# ── Test 9 / 10 — HexHubWithBearing fused single-solid + bounding box ─────

def test_hex_hub_with_bearing_single_solid() -> None:
    fused = HexHubWithBearing()
    assert len(fused.solid.solids().vals()) == 1, (
        "HexHubWithBearing: union between HexHubNut and BearingHexHousing "
        "did not produce a single contiguous body"
    )


def test_hex_hub_with_bearing_bounding_box_height() -> None:
    fused = HexHubWithBearing()
    bb = fused.solid.val().BoundingBox()
    expected_height = (
        fused.hex_nut.thickness + fused.housing.bearing_width - fused.overlap_eps
    )
    assert bb.zlen == pytest.approx(expected_height, abs=1e-6)
    assert bb.zmin == pytest.approx(
        -(fused.housing.bearing_width - fused.overlap_eps), abs=1e-6
    )
    assert bb.zmax == pytest.approx(fused.hex_nut.thickness, abs=1e-6)


# ── Fused-body bearing-seat clearance (TL review follow-up) ───────────────
#
# Test 7 above only probes the *standalone* BearingHexHousing, where the
# pocket is a plain through-cut and the nominal-OD check is trivially
# satisfied. The actual printed deliverable is the *fused* HexHubWithBearing,
# where HexHubNut's own solid caps the pocket at global Z = 0 rather than at
# the housing's own (translated) nominal top plane at Z = overlap_eps -- so
# the real, usable seating depth is `bearing_width - overlap_eps`, not
# `bearing_width`. Below print resolution (0.02mm on fdm_standard) and an
# inherent consequence of the overlap-epsilon boolean-robustness technique
# (see module docstring / BearingHexHousing docstring), not a defect -- but
# it must be *characterized*, not silently assumed away by only testing the
# standalone part.

def test_hex_hub_with_bearing_fused_pocket_admits_bearing_at_achievable_depth() -> None:
    """A nominal 8.000mm-OD bearing, seated flush against the fused body's
    *actual* open face and sized to the *achievable* depth
    (`bearing_width - overlap_eps`), must show zero interference -- this is
    the true usable seating depth of the printed part."""
    fused = HexHubWithBearing()
    achievable_depth = fused.housing.bearing_width - fused.overlap_eps
    z0 = -achievable_depth
    probe = cq.Workplane("XY").workplane(offset=z0).circle(8.000 / 2.0).extrude(achievable_depth)
    inter = fused.solid.intersect(probe)
    vol = sum(s.Volume() for s in inter.solids().vals()) if inter.solids().vals() else 0.0
    assert vol == pytest.approx(0.0, abs=1e-6)


def test_hex_hub_with_bearing_fused_pocket_nominal_width_bearing_is_bounded_proud() -> None:
    """Positive control + regression guard for the above: a nominal
    8.000mm x 2.500mm bearing (the bearing's own true dimensions, not the
    achievable depth) seated flush against the open face MUST show
    interference -- it does NOT sit fully flush in the fused body, per the
    module docstring's overlap-epsilon tradeoff. The interference volume
    must be bounded near the expected `overlap_eps`-thin proud slice, so a
    future change that grows this gap unexpectedly larger fails loudly
    instead of silently."""
    fused = HexHubWithBearing()
    bearing_width = fused.housing.bearing_width
    achievable_depth = bearing_width - fused.overlap_eps
    z0 = -achievable_depth
    probe = cq.Workplane("XY").workplane(offset=z0).circle(8.000 / 2.0).extrude(bearing_width)
    inter = fused.solid.intersect(probe)
    vol = sum(s.Volume() for s in inter.solids().vals()) if inter.solids().vals() else 0.0
    assert vol > 0.0, (
        "expected the nominal-width bearing to sit proud by overlap_eps in "
        "the fused body -- if this is now 0.0, the known cosmetic gap may "
        "have been fixed; update this test's docstring/assertions instead "
        "of leaving a stale positive-control expectation"
    )
    # A loose ceiling rather than an exact formula: the true cross-section
    # at this Z-slice is a thin annulus (bounded by the nut's own bore,
    # itself widened by its Z=0 edge chamfer) far smaller than a full
    # bearing-OD disc -- computing that exactly would couple this test to
    # unrelated chamfer geometry. The full-disc volume is a safe, generous
    # upper bound: this only fails if the proud gap grows far past a single
    # `overlap_eps` sliver.
    full_disc_ceiling = math.pi * (8.000 / 2.0) ** 2 * fused.overlap_eps
    assert vol < full_disc_ceiling
