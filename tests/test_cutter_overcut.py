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

"""Through-vs-blind cutter overcut regression test.

Design reference: §Tests T13, §Success Criteria 9 in
``.agents/plans/2026-05-13-pre-oss-models-structure_design.md``.

Phase 4 baked the through-vs-blind overcut policy into each cutter
class as a class-level ``_THROUGH`` constant:

* ``_THROUGH = True``  → ``to_cutter()`` extends past both faces by
  ``_THROUGH_OVERCUT`` (typically 100 mm).  Validated by asserting the
  Z bounding box overshoots the design depth on both ends.
* ``_THROUGH = False`` → ``to_cutter()`` ends exactly at the design
  bounds.  Validated by asserting the Z bounding box matches the design
  depth / thickness with no overcut on the terminal face.

This codifies the **Infinite Cutter Overcuts** rule structurally so a
future regression — e.g. someone "tightening" a through-hole bake from
100 mm to 0 — fails CI at the moment it lands.

Scope: every concrete class under ``vibe_cading/mechanical/holes.py``
that declares ``_THROUGH``.  Drives, ventilation, lego cutters, and
servo wrappers are validated in ``test_protocols.py`` (default-arg
callability) but their detailed Z-bake assertion belongs here when
they too declare a documented ``_THROUGH_OVERCUT`` policy.
"""

from __future__ import annotations

import pytest

from vibe_cading.mechanical.holes import (
    _THROUGH_OVERCUT,
    CaptiveNutPocket,
    ClearanceHole,
    CounterboreHole,
    SlottedHole,
    TaperedHole,
)


# Tolerance for bounding-box assertions (mm).  OCCT round-trip + lofts /
# polygon approximations introduce sub-mm wobble at the bounding-box
# extremes.  0.1 mm is loose enough to never false-positive while still
# catching a regression that drops overcut to 0 (off by 99.9 mm).
_BBOX_EPS = 0.1


def _bbox_z(workplane):
    """Return ``(zmin, zmax)`` of the resulting workplane's first solid."""
    bb = workplane.val().BoundingBox()
    return bb.zmin, bb.zmax


# --------------------------------------------------------------------------
# Through-hole cutters — must extend past both faces by ``_THROUGH_OVERCUT``
# --------------------------------------------------------------------------

def test_clearance_hole_through_overcut():
    """``ClearanceHole`` is a through-cutter — symmetric overcut on both faces.

    Design: entry at Z=0, terminal at Z=-depth, cutter bake extends both.
    """
    hole = ClearanceHole(diameter=3.2, depth=5.0)
    assert hole._THROUGH is True, "ClearanceHole must declare _THROUGH = True"
    zmin, zmax = _bbox_z(hole.to_cutter())
    assert zmax >= _THROUGH_OVERCUT - _BBOX_EPS, (
        f"Through cutter entry overcut missing: zmax={zmax}, "
        f"expected >= {_THROUGH_OVERCUT}"
    )
    assert zmin <= -hole.depth - _THROUGH_OVERCUT + _BBOX_EPS, (
        f"Through cutter terminal overcut missing: zmin={zmin}, "
        f"expected <= {-hole.depth - _THROUGH_OVERCUT}"
    )


def test_counterbore_hole_through_overcut():
    """``CounterboreHole`` is a through-cutter on the shaft side."""
    hole = CounterboreHole(
        shaft_diameter=3.2, shaft_depth=5.0,
        head_diameter=5.5, head_depth=3.0,
    )
    assert hole._THROUGH is True, "CounterboreHole must declare _THROUGH = True"
    zmin, _zmax = _bbox_z(hole.to_cutter())
    # Shaft extends through past terminal face at Z=-shaft_depth.
    assert zmin <= -hole.shaft_depth - _THROUGH_OVERCUT + _BBOX_EPS, (
        f"CounterboreHole shaft overcut missing: zmin={zmin}, "
        f"expected <= {-hole.shaft_depth - _THROUGH_OVERCUT}"
    )


def test_slotted_hole_through_overcut():
    """``SlottedHole`` extends through past both faces."""
    hole = SlottedHole(diameter=3.2, length=10.0, depth=5.0)
    assert hole._THROUGH is True
    zmin, zmax = _bbox_z(hole.to_cutter())
    assert zmax >= _THROUGH_OVERCUT - _BBOX_EPS
    assert zmin <= -hole.depth - _THROUGH_OVERCUT + _BBOX_EPS


def test_tapered_hole_through_overcut():
    """``TaperedHole`` extends straight cylinders past both faces."""
    hole = TaperedHole(
        top_diameter=5.5, bottom_diameter=3.2, depth=5.0,
    )
    assert hole._THROUGH is True
    zmin, zmax = _bbox_z(hole.to_cutter())
    assert zmax >= _THROUGH_OVERCUT - _BBOX_EPS
    assert zmin <= -hole.depth - _THROUGH_OVERCUT + _BBOX_EPS


# --------------------------------------------------------------------------
# Blind cutters — must NOT extend past the terminal face
# --------------------------------------------------------------------------

def test_captive_nut_pocket_blind_no_overcut():
    """``CaptiveNutPocket`` is the canonical blind cutter — no overcut either side.

    Per the docstring: the pocket sits exactly between Z=-thickness and
    Z=0; consumers translating the pocket into a host body own the
    overcut concern for whichever face exits the host.
    """
    pocket = CaptiveNutPocket(width_across_flats=5.5, thickness=2.4)
    assert pocket._THROUGH is False, (
        "CaptiveNutPocket must declare _THROUGH = False (blind)"
    )
    zmin, zmax = _bbox_z(pocket.to_cutter())
    assert abs(zmax - 0.0) <= _BBOX_EPS, (
        f"Blind pocket entry should sit at Z=0, got zmax={zmax}"
    )
    assert abs(zmin - (-pocket.thickness)) <= _BBOX_EPS, (
        f"Blind pocket terminal should sit at Z=-thickness "
        f"({-pocket.thickness}), got zmin={zmin}"
    )
    # Structural guard — the bounding box should be exactly the thickness,
    # NOT thickness + 2*overcut.  Catches a regression that bakes overcut
    # into a class declared as blind.
    assert (zmax - zmin) < pocket.thickness + 2 * _BBOX_EPS, (
        f"Blind pocket Z-extent {zmax - zmin} exceeds thickness "
        f"{pocket.thickness} — overcut leaked into a _THROUGH=False cutter"
    )


# --------------------------------------------------------------------------
# Policy invariant — every cutter class declares its overcut intent
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "cls",
    [
        ClearanceHole,
        CounterboreHole,
        SlottedHole,
        TaperedHole,
        CaptiveNutPocket,
    ],
    ids=lambda c: c.__name__,
)
def test_cutter_class_declares_through_policy(cls):
    """Every cutter class carries an explicit ``_THROUGH`` bool.

    Structural guard against the failure mode where a contributor adds
    a new cutter class without declaring its overcut intent — the
    project's documented through-vs-blind contract demands the bake
    decision happens at class-definition time, not call time.
    """
    assert hasattr(cls, "_THROUGH"), (
        f"{cls.__name__} missing class-level _THROUGH constant — "
        "the through-vs-blind policy must be baked per-class"
    )
    assert isinstance(cls._THROUGH, bool), (
        f"{cls.__name__}._THROUGH must be a bool, "
        f"got {type(cls._THROUGH).__name__}"
    )


def test_through_overcut_constant_is_substantial():
    """``_THROUGH_OVERCUT`` must be large enough to clear realistic host bodies.

    A regression to a tiny value (e.g. 0.1 mm or 0) would defeat the
    Infinite Cutter Overcuts rule and re-introduce the class of seam
    bugs the bake is designed to prevent.
    """
    assert _THROUGH_OVERCUT >= 10.0, (
        f"_THROUGH_OVERCUT = {_THROUGH_OVERCUT} is too small to clear "
        "any realistic host body — should be >= 10 mm (per design)"
    )
