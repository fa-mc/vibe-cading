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

"""Regression tests for ``vibe_cading.lego.technic_beam.LegoTechnicBeam``.

Per the design's T11 task — three minimal assertions guarding the FR5
bounding-box invariant, the FR3 input-validation contract, and the FR16
single-solid topological invariant.  Design reference:
``.agents/plans/2026-05-15-lego-technic-beam_design.md``.
"""

import pytest

from vibe_cading.lego.technic_beam import LegoTechnicBeam


def test_bounding_box_5stud() -> None:
    """FR5 / FR11 — N=5 beam has bb (40, 7.8, 7.8) mm."""
    bb = LegoTechnicBeam(length_in_studs=5).solid.val().BoundingBox()
    assert bb.xlen == pytest.approx(40.0, abs=0.01)
    assert bb.ylen == pytest.approx(7.8, abs=0.01)
    assert bb.zlen == pytest.approx(7.8, abs=0.01)


def test_zero_length_raises_valueerror() -> None:
    """FR3 — length_in_studs < 1 raises ValueError."""
    with pytest.raises(ValueError):
        LegoTechnicBeam(length_in_studs=0)


def test_single_solid_5stud() -> None:
    """FR16 — finished beam is exactly one solid (no wafers, no detached pieces)."""
    beam = LegoTechnicBeam(length_in_studs=5)
    assert len(beam.solid.solids().vals()) == 1
