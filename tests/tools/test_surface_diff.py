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

"""Tests for :mod:`vibe_cading.tools.surface_diff`.

The behaviour under test is mostly *refusal*: this tool exists because
comparison probes fail silently, reporting a clean result for a reason
unrelated to the geometry. So the tests that matter are the ones asserting it
declines to answer rather than answering wrongly.
"""
from __future__ import annotations

import cadquery as cq
import numpy as np
import pytest

from vibe_cading.tools.surface_diff import (
    InconclusiveRegion,
    compare,
    ray_surfaces,
    sweep_stations,
)


def _box_tris(w=10.0, d=10.0, h=10.0, offset=(0.0, 0.0, 0.0)):
    shape = cq.Workplane("XY").box(w, d, h).translate(offset).val()
    verts, faces = shape.tessellate(0.03)
    v = np.array([[p.x, p.y, p.z] for p in verts])
    return v[np.array(faces)]


def test_identical_shapes_agree_completely():
    a = _box_tris()
    c = compare(a, _box_tris(), tol=0.05)
    assert c.conclusive
    assert c.agreement == pytest.approx(100.0)
    assert c.a_to_b.max == pytest.approx(0.0, abs=1e-6)


def test_directions_are_reported_separately_and_mean_opposite_things():
    """A big A against a small B is MISSING material, not EXTRA."""
    big, small = _box_tris(20, 20, 20), _box_tris(10, 10, 10)
    c = compare(big, small, a_name="big", b_name="small", tol=0.05)
    # points on the big shape are far from the small one ...
    assert c.a_to_b.max > 4.0
    # ... but every point of the small shape lies on or inside the big one,
    # so the reverse direction is much tighter. Collapsing these into one
    # symmetric number would hide which way the error runs.
    assert c.b_to_a.max < c.a_to_b.max


def test_empty_region_raises_instead_of_reporting_agreement():
    """The positive control: absence of samples is NOT absence of difference.

    This is the failure this tool was built to make impossible -- a probe
    that reports a clean result because it was aimed at the wrong place.
    """
    a, b = _box_tris(), _box_tris()
    c = compare(a, b, region=(100.0, 110.0, 100.0, 110.0, 100.0, 110.0))
    assert not c.conclusive
    with pytest.raises(InconclusiveRegion):
        _ = c.agreement


def test_region_empty_on_one_side_only_still_raises():
    """One-sided emptiness is the subtler trap and must also refuse."""
    a = _box_tris(10, 10, 10)
    b = _box_tris(10, 10, 10, offset=(100.0, 0.0, 0.0))
    c = compare(a, b, a_name="a", b_name="b", region=(-6.0, 6.0, -6.0, 6.0, -6.0, 6.0))
    assert c.a_to_b.n > 0 and c.b_to_a.n == 0
    with pytest.raises(InconclusiveRegion) as exc:
        _ = c.agreement
    assert "b" in str(exc.value)


def test_scoping_to_a_region_changes_the_verdict():
    """Whole-shape statistics wash out a small local difference.

    A 0.5 mm bump on a 40 mm box is negligible globally and dominant locally
    -- which is the entire reason ``--region`` exists.
    """
    plain = _box_tris(40, 40, 10)
    bumped = np.vstack([plain, _box_tris(2, 2, 1, offset=(0.0, 0.0, 5.5))])
    whole = compare(plain, bumped, tol=0.2)
    local = compare(plain, bumped, tol=0.2, region=(-2.0, 2.0, -2.0, 2.0, 5.0, 6.5))
    assert local.b_to_a.within < whole.b_to_a.within


def test_sweep_ranks_worst_station_first():
    plain = _box_tris(40, 40, 10)
    bumped = np.vstack([plain, _box_tris(2, 2, 1, offset=(12.0, 0.0, 5.5))])
    rows = sweep_stations(plain, bumped, "x", (-20.0, 20.0, -20.0, 20.0, 0.0, 6.5),
                          step=2.0, tol=0.2)
    conclusive = [(at, c) for at, c in rows if c.conclusive]
    assert conclusive, "sweep produced no conclusive station"
    assert abs(conclusive[0][0] - 12.0) <= 2.0


def test_ray_reports_raw_crossings_without_a_parity_assumption():
    """Works on open meshes, where inside/outside is undefined."""
    a = _box_tris(10, 10, 10)
    hits = ray_surfaces(a, "z", {"x": 0.0, "y": 0.0})
    assert min(hits) == pytest.approx(-5.0, abs=1e-6)
    assert max(hits) == pytest.approx(5.0, abs=1e-6)
