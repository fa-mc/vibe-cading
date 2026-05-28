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

"""Regression tests for ``TechnicAxleHole`` (concave-radius default).

Covers the 2026-05-28 design
(``.agents/plans/2026-05-28-concave-radius-default_design.md``):

* **FR-5 enforcement** — ``DEFAULT_CONCAVE_RADIUS`` is pinned at the
  current shipped value (``0.3 mm``) AND the constructor honours it
  when ``concave_radius=`` is omitted.  Catches both constant drift
  and signature-default regression in a single test.
* **Buildability smoke** — exercises the cutter across 5 representative
  radii spanning the realistic-use range (``0.0`` skip-fillet boundary,
  through the new default, up to ``0.8`` — well below the
  ``AXLE_HOLE_ARM_WIDTH / 2 = 0.915 mm`` upper buildability bound).
  Each variant must yield a single contiguous solid (``len(.solids()) == 1``).
  Guards a future maintainer changing the default from accidentally
  landing on an OCCT-unbuildable corner radius.
"""

import pytest

from vibe_cading.lego.cutters.technic_axle_hole import TechnicAxleHole


def test_default_concave_radius_pinned_at_0_3():
    """FR-5: shipped default is 0.3 mm and the constructor honours it.

    Two distinct regressions guarded:
        (a) class constant drift — someone edits the file and flips
            ``DEFAULT_CONCAVE_RADIUS`` without realising it is the
            default-fillet anchor.
        (b) signature-default regression — someone refactors
            ``__init__`` and accidentally hard-codes a different
            default value into the kwarg signature.
    """
    assert TechnicAxleHole.DEFAULT_CONCAVE_RADIUS == 0.3
    assert TechnicAxleHole(depth=8.0).concave_radius == 0.3


@pytest.mark.parametrize("radius", [0.0, 0.1, 0.3, 0.5, 0.8])
def test_axle_hole_builds_single_solid_across_radii(radius):
    """Smoke: cutter builds a single contiguous solid across the realistic range.

    Values chosen to span the skip-fillet boundary (``0.0``), the
    sweep low-water-mark (``0.1``), the new shipped default (``0.3``),
    the legacy ballpark (``0.5`` as a buildable proxy for the pre-2026-05-28
    ``0.6``), and a higher-radius point (``0.8``).  ``0.8`` sits only
    ``0.115 mm`` below ``AXLE_HOLE_ARM_WIDTH / 2 = 0.915 mm``, the
    upper buildability bound — chosen deliberately to exercise the
    near-edge buildability path.
    """
    cutter = TechnicAxleHole(depth=8.0, concave_radius=radius).to_cutter()
    solids = cutter.solids().vals()
    assert len(solids) == 1, (
        f"Expected single contiguous solid at concave_radius={radius}, "
        f"got {len(solids)} solids."
    )
