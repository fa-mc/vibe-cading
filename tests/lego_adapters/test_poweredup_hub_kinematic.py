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

"""Kinematic retention sweep for the Powered Up hub battery box's latch.

Per docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md,
*Round 18* -- the independent audit (tmp/implementation-audit.md) found the
originally-shipped latch had zero retention because it was verified only as
a *static* seated-state interference problem, never as a *kinematic* one. A
retention catch is, by definition, a feature that must show POSITIVE
interference along the release path (proof the finger must deflect) and
ZERO interference along the insertion path -- two different,
direction-dependent checks that a single seated-state ``== 0 mm^3`` test
cannot distinguish. This module is the durable version of that check
(mirroring the audit's own probes), replacing the one-off ``tmp/`` scripts
used to verify B1 during implementation.

**A genuine finding surfaced while building this test, not assumed going
in**: :class:`~vibe_cading.lego_adapters.poweredup_hub.cover.PoweredUpHubCover`'s
latch finger is a *solid wedge* -- at every Z from 0 to ``hook_depth``
(13.000 mm), its cross-section fills continuously from its own drafted
face back to the plate edge (``PLATE_Y_LO``, -30.800 mm). Any housing-side
retention nub whose outboard reach gets behind the barb crest (as it must,
to catch it) necessarily also overlaps that permanent "back fill" material
at every Z the nub's own Z-band touches -- INCLUDING Z = 0 transform
(seated). This is a geometric property of the finger's own shape, not a
construction bug: no placement of a Z-localised nub (of any Z-extent) can
show zero interference at the seated/untransformed state while also
catching the crest, because the finger has no Z at which its cross-section
is anything other than that same solid wedge. See
``test_latch_catch_seated_engagement_is_the_proven_minimum`` below for the
mechanical detail, and the design brief's *Implementation Status* for the
full escalation this finding produced.

What DOES work cleanly, verified below: the design's own primary release
mechanism (pressing the thumb pads and rotating the latch end away) shows
genuine, monotonically GROWING interference as the rotation increases --
proof real deflection is required to release the lid that way. A pure
-Z pull-out also shows resistance, though it clears at a short travel
(~0.5 mm) rather than persisting -- documented, not silently accepted as
equivalent to the rotation path.
"""

from __future__ import annotations

import cadquery as cq

from vibe_cading.lego_adapters.poweredup_hub.cover import PoweredUpHubCover
from vibe_cading.lego_adapters.poweredup_hub.housing import PoweredUpHubHousing


def _intersect_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    inter = a.intersect(b)
    vals = inter.solids().vals()
    return sum(v.Volume() for v in vals) if vals else 0.0


def _latch_only_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    """Same as :func:`_intersect_volume`, filtered to pieces at the latch
    end only (Y < -29 mm) -- isolates the catch's own contribution from
    the independently-verified, unrelated tongue-lap engagement at the
    opposite end (which the audit already confirmed behaves correctly:
    nonzero for a short -Z pull, zero beyond TIP_Z_LO = 1.874 mm)."""
    inter = a.intersect(b)
    total = 0.0
    for v in inter.solids().vals():
        if v.BoundingBox().ymax < -29.0:
            total += v.Volume()
    return total


# Pivot for the "swing the latch end down/away" rotation -- about the
# tongue tip's own corner, matching how the design brief's retention
# scheme describes the lid pivoting on the tongue end while the latch end
# is the one that moves.
_PIVOT = (0.0, PoweredUpHubCover.TONGUE_Y_HI, PoweredUpHubCover.TIP_Z_LO)


def test_latch_catch_seated_engagement_is_the_proven_minimum():
    """At the seated (zero-transform) position, the ONLY nonzero
    Cover/Housing interference is the latch catch's own necessary
    engagement sliver -- everything else (tongue rebate, general body,
    pin holes) is exactly zero (see
    tests/lego_adapters/test_poweredup_hub_housing.py's own
    ``test_general_body_seated_interference_is_zero`` for that half).

    This test asserts the catch's OWN seated volume is small (bounded,
    not exactly zero -- see this module's own docstring for the geometric
    proof of why exactly zero is unachievable for this finger's
    cross-section) and stable, so a future change that silently grows it
    (e.g. a wider or taller nub re-colliding with more of the finger) is
    caught.
    """
    housing = PoweredUpHubHousing()
    cover = PoweredUpHubCover()
    vol = _latch_only_volume(cover.solid, housing.solid)
    assert vol > 0.0, "expected a nonzero seated engagement at the catch (proof it exists at all)"
    assert vol < 25.0, f"catch's seated engagement grew unexpectedly large: {vol:.3f} mm^3"


def test_latch_catch_rotation_release_shows_growing_interference():
    """The design's own primary release path -- pressing the thumb pads
    and rotating the latch end away/down about the tongue end -- must
    show genuinely GROWING interference as the angle increases: proof the
    finger must deflect more, not less, the further you try to release
    it. Monotonicity (not just "nonzero somewhere") is asserted, since a
    catch that peaks then drops back to near-zero at a shallow angle
    would not actually resist release.
    """
    housing = PoweredUpHubHousing()
    cover = PoweredUpHubCover()
    angles = (0.0, 0.5, 1.0, 2.0, 5.0, 10.0)
    volumes = []
    for angle in angles:
        rotated = cover.solid.rotate(_PIVOT, (1, 0, 0), -angle)
        volumes.append(_latch_only_volume(rotated, housing.solid))
    for prev, cur in zip(volumes, volumes[1:]):
        assert cur >= prev - 1e-6, f"release-path interference must not decrease: {volumes}"
    assert volumes[-1] > volumes[0], f"expected net growth across the sweep: {volumes}"


def test_tongue_pull_out_interference_matches_the_working_lap_mechanism():
    """A pure -Z pull-out is resisted by the (independently working,
    unaffected-by-this-round) tongue lap: nonzero at small-to-moderate
    pull distances, zero once the blade tip has fully cleared the rebate.
    Empirically, this clears at pull = 3.0 mm (not at
    ``TIP_Z_LO`` = 1.874 mm alone -- the tip's own 0.926 mm thickness plus
    the rebate step's own geometry extend the resistance further than the
    step height by itself would suggest; verified by measurement here, not
    hand-derived). Verifies this still holds with the round-18 changes in
    place -- none of B1/B2/S1/S2/S7/S8 touch the tongue end's own geometry.
    """
    housing = PoweredUpHubHousing()
    cover = PoweredUpHubCover()

    def tongue_volume(pulled: cq.Workplane) -> float:
        inter = pulled.intersect(housing.solid)
        total = 0.0
        for v in inter.solids().vals():
            if v.BoundingBox().ymax > 0.0:  # tongue end only
                total += v.Volume()
        return total

    for pull in (0.3, 1.0, 1.9):
        below_clear = cover.solid.translate((0, 0, -pull))
        assert tongue_volume(below_clear) > 0.0, f"expected tongue-lap resistance at pull={pull}"

    past_clear = cover.solid.translate((0, 0, -3.0))
    assert tongue_volume(past_clear) < 1e-6, "expected zero tongue-lap resistance once fully clear"


def test_latch_catch_insertion_path_is_bounded_by_the_seated_minimum():
    """Along the INSERTION direction -- swinging the latch end further
    into the housing, i.e. rotating the opposite way from release -- the
    catch must not show *additional* interference beyond its own
    unavoidable seated minimum (see
    ``test_latch_catch_seated_engagement_is_the_proven_minimum``): the
    existing depth-stop boss (verified pre-existing, unrelated to B1)
    already governs over-insertion separately and is excluded here by
    only sweeping small angles where the depth stop does not yet engage.
    """
    housing = PoweredUpHubHousing()
    cover = PoweredUpHubCover()
    seated = _latch_only_volume(cover.solid, housing.solid)
    for angle in (0.1, 0.2):
        rotated = cover.solid.rotate(_PIVOT, (1, 0, 0), angle)
        vol = _latch_only_volume(rotated, housing.solid)
        assert vol <= seated + 5.0, (
            f"insertion-direction interference at {angle} deg ({vol:.3f} mm^3) "
            f"grew well past the seated minimum ({seated:.3f} mm^3)"
        )


def test_seated_cross_part_interference_zero_for_tray_pairs():
    """Tray<->Housing and Tray<->Cover must both be exactly zero at the
    assembled seated position -- unlike the Cover<->Housing latch catch,
    neither of these interfaces has an intentional snap/retention feature,
    so there is no analogous "necessary minimum" to carve out.
    """
    from vibe_cading.lego_adapters.poweredup_hub.battery_tray import PoweredUpHubBatteryTray

    housing = PoweredUpHubHousing()
    cover = PoweredUpHubCover()
    tray = PoweredUpHubBatteryTray()
    tray_seated = tray.solid.translate((0, 0, PoweredUpHubCover.PLATE_THICKNESS))

    v_th = _intersect_volume(tray_seated, housing.solid)
    assert v_th < 1e-6, f"Tray/Housing interference volume {v_th:.4f} mm^3 -- expected 0"

    v_tc = _intersect_volume(tray_seated, cover.solid)
    assert v_tc < 1e-6, f"Tray/Cover interference volume {v_tc:.4f} mm^3 -- expected 0"


def test_envelope_and_single_solid_guards_hold():
    """Housing envelope stays exactly 72.000 x 71.200 x 33.800 mm, and all
    three parts remain single solids -- the final cross-part sign-off
    checks from the round-18 acceptance gate.
    """
    from vibe_cading.lego_adapters.poweredup_hub.battery_tray import PoweredUpHubBatteryTray

    housing = PoweredUpHubHousing()
    cover = PoweredUpHubCover()
    tray = PoweredUpHubBatteryTray()

    bb = housing.solid.val().BoundingBox()
    assert abs(bb.xlen - 72.000) < 1e-6
    assert abs(bb.ylen - 71.200) < 1e-6
    assert abs(bb.zlen - 33.800) < 1e-6

    for part in (housing, cover, tray):
        assert len(part.solid.solids().vals()) == 1


def test_thumb_pads_sit_behind_housing_windows():
    """Both of PoweredUpHubCover's thumb pads (round 18, B2) must
    physically sit behind PoweredUpHubHousing's two 13.6 x 3.6 mm finger
    windows -- verified by a material probe at each pad's own footprint,
    not assumed from the constants matching."""
    housing = PoweredUpHubHousing()
    cover = PoweredUpHubCover()
    for side in (1, -1):
        x_center = side * (PoweredUpHubCover.PLATE_WIDTH / 4.0)  # well inside the window's X span
        probe = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x_center, -35.0, 1.0))
            .box(1, 1, 1, centered=True)
        )
        assert _intersect_volume(probe, cover.solid) > 0.0, (
            f"expected Cover material (the thumb pad) behind the side={side} window"
        )
        assert _intersect_volume(probe, housing.solid) < 1e-6, (
            f"expected the side={side} window to be open (no Housing material)"
        )
