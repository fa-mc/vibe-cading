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

"""Regression tests for ``vibe_cading.lego.block.LegoBlock``.

Guards the studded-System block generator: footprint / height formulas,
single-solid topology across the degenerate matrix, the underside clutch-tube
presence rule, factory equivalence, and the profile-driven clutch bore.
Design reference: ``docs/design_plans/2026-06-17-lego-brick-2x3_design.md``.
"""

import dataclasses
import math

import pytest

from vibe_cading.lego.block import LegoBlock
from vibe_cading.lego.constants import (
    BLOCK_PLAY,
    BLOCK_ROOF,
    BLOCK_WALL,
    CLUTCH_TUBE_OD,
    PLATE_HEIGHT,
    STUD_DIAMETER,
    STUD_HEIGHT,
    STUD_PITCH,
)
from vibe_cading.print_settings import get_profile

PLAY = 0.2


def _bbox(block: LegoBlock):
    return block.solid.val().BoundingBox()


def test_default_is_2x3_brick() -> None:
    """Default constructor = the requested 2x3 brick: 15.8 x 23.8 x 11.4 mm."""
    bb = _bbox(LegoBlock(2, 3))
    assert bb.xlen == pytest.approx(15.8, abs=0.01)
    assert bb.ylen == pytest.approx(23.8, abs=0.01)
    assert bb.zlen == pytest.approx(11.4, abs=0.01)


@pytest.mark.parametrize("plates", [1, 3, 6])
@pytest.mark.parametrize("studded", [True, False])
def test_height_formula(plates: int, studded: bool) -> None:
    """Height = plates*PLATE_HEIGHT, plus STUD_HEIGHT only when studded."""
    bb = _bbox(LegoBlock(2, 3, plates=plates, studded=studded))
    expected = plates * PLATE_HEIGHT + (STUD_HEIGHT if studded else 0.0)
    assert bb.zlen == pytest.approx(expected, abs=0.01)


@pytest.mark.parametrize("sx,sy", [(1, 1), (2, 3), (1, 4), (3, 5)])
def test_footprint_formula(sx: int, sy: int) -> None:
    """Footprint per axis = n*STUD_PITCH - PLAY (real-Lego pack gap)."""
    bb = _bbox(LegoBlock(sx, sy))
    assert bb.xlen == pytest.approx(sx * STUD_PITCH - PLAY, abs=0.01)
    assert bb.ylen == pytest.approx(sy * STUD_PITCH - PLAY, abs=0.01)


@pytest.mark.parametrize("sx,sy", [(1, 1), (1, 4), (4, 1), (2, 2), (2, 3), (8, 8)])
@pytest.mark.parametrize("plates", [1, 3])
@pytest.mark.parametrize("studded", [True, False])
def test_single_solid_matrix(sx: int, sy: int, plates: int, studded: bool) -> None:
    """Every configuration — incl. the no-tube 1xN / 1x1 cases — is one solid."""
    block = LegoBlock(sx, sy, plates=plates, studded=studded)
    assert len(block.solid.solids().vals()) == 1


@pytest.mark.parametrize(
    "sx,sy,expect_tube",
    [(2, 2, True), (2, 3, True), (3, 5, True), (1, 1, False), (1, 4, False), (4, 1, False)],
)
def test_tube_presence_rule(sx: int, sy: int, expect_tube: bool) -> None:
    """Clutch tubes exist iff a 2x2 stud cluster exists (both dims >= 2)."""
    block = LegoBlock(sx, sy)
    xs = block._grid_centres(sx)
    ys = block._grid_centres(sy)
    has_interior_vertex = bool(xs[:-1]) and bool(ys[:-1])
    assert has_interior_vertex is expect_tube


def _analytic_volume(b: LegoBlock) -> float:
    """Closed-form volume: outer box − cavity + clutch-tube annuli + studs.

    The tube-annulus term is non-zero iff a 2×2 cluster exists, so matching the
    built solid's volume to this formula asserts — on the actual geometry — that
    the underside tubes are present exactly where the rule says and absent
    elsewhere (a missing/extra tube shifts the volume out of tolerance)."""
    foot_x = b.studs_x * STUD_PITCH - BLOCK_PLAY
    foot_y = b.studs_y * STUD_PITCH - BLOCK_PLAY
    height = b.plates * PLATE_HEIGHT
    cavity_h = height - BLOCK_ROOF
    box = foot_x * foot_y * height
    cavity = (foot_x - 2 * BLOCK_WALL) * (foot_y - 2 * BLOCK_WALL) * cavity_h
    n_tubes = max(0, b.studs_x - 1) * max(0, b.studs_y - 1)
    tube = n_tubes * math.pi / 4 * (CLUTCH_TUBE_OD ** 2 - b.clutch_bore_diameter ** 2) * cavity_h
    n_studs = b.studs_x * b.studs_y if b.studded else 0
    studs = n_studs * math.pi / 4 * STUD_DIAMETER ** 2 * STUD_HEIGHT
    return box - cavity + tube + studs


@pytest.mark.parametrize(
    "sx,sy,plates,studded",
    [(2, 3, 3, True), (2, 2, 3, True), (1, 4, 3, True), (4, 1, 1, True), (2, 3, 1, False)],
)
def test_volume_matches_analytic(sx: int, sy: int, plates: int, studded: bool) -> None:
    """Built-solid volume equals the analytic model incl. the tube-annulus term."""
    b = LegoBlock(sx, sy, plates=plates, studded=studded)
    assert b.solid.val().Volume() == pytest.approx(_analytic_volume(b), rel=1e-3)


def test_factory_equivalence() -> None:
    """.brick / .plate / .tile match the explicit constructor configurations."""
    assert LegoBlock.brick(2, 3).plates == 3 and LegoBlock.brick(2, 3).studded
    assert LegoBlock.plate(2, 3).plates == 1 and LegoBlock.plate(2, 3).studded
    assert LegoBlock.tile(2, 3).plates == 1 and not LegoBlock.tile(2, 3).studded


def test_clutch_bore_is_profile_driven() -> None:
    """Clutch bore = STUD_DIAMETER + 2*slip.radial, decoupled from the stud Ø."""
    prof = get_profile()
    block = LegoBlock(2, 3)
    assert block.clutch_bore_diameter == pytest.approx(
        STUD_DIAMETER + 2 * prof.slip.radial, abs=1e-9
    )
    # A tightened profile must flow through the factories, proving the knob works.
    loose = dataclasses.replace(prof, slip=dataclasses.replace(prof.slip, radial=0.25))
    assert LegoBlock.brick(2, 3, profile=loose).clutch_bore_diameter == pytest.approx(
        STUD_DIAMETER + 0.5, abs=1e-9
    )


@pytest.mark.parametrize("args", [(0, 2), (2, 0)])
def test_invalid_footprint_raises(args) -> None:
    with pytest.raises(ValueError):
        LegoBlock(*args)


def test_invalid_plates_raises() -> None:
    with pytest.raises(ValueError):
        LegoBlock(2, 2, plates=0)
