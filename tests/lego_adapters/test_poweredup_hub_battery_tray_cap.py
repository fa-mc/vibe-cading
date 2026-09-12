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

"""PoweredUpHubBatteryTrayCap -- regression net for the round-55 strap
channel recorded in
docs/design_plans/2026-08-19-poweredup-hub-battery-box_reference-comparison.md.

The cap's whole job is one thing -- roof the tray's strap corridor from
above, flush, without adding to the stack under the battery -- so the tests
here are mostly about the JOINT, not about the plate in isolation. The
channel runs UNDER this plate: floored by the Cover's own face, roofed by
the cap.
"""

import pytest

from vibe_cading.cq_utils import rounded_box
from vibe_cading.lego_adapters.poweredup_hub.battery_tray import (
    PoweredUpHubBatteryTray,
)
from vibe_cading.lego_adapters.poweredup_hub.battery_tray_cap import (
    PoweredUpHubBatteryTrayCap,
)
from vibe_cading.lego_adapters.poweredup_hub.cover import PoweredUpHubCover
from vibe_cading.lego_adapters.poweredup_hub.housing import PoweredUpHubHousing
from vibe_cading.print_settings import get_profile


def test_single_solid():
    cap = PoweredUpHubBatteryTrayCap()
    solids = cap.solid.solids().vals()
    assert len(solids) == 1
    assert solids[0].isValid()


def _seated(profile="fdm_standard"):
    """The cap where it actually lives, in the Tray's own frame.

    ROUND 88 BUG FIX: this helper translated by ``SEAT_Z`` ONLY and omitted
    ``SEAT_Y``. The plate is built centred on its own Y = 0, while its rebate
    is centred on ``STRAP_Y_CENTER`` (2.000) -- round 72 centre-aligned the
    whole strap assembly with the side tabs, and ``SEAT_Y`` exists precisely
    so a placer does not miss it. ``assembly.assemble()`` applies both.

    Placed 2.000 mm off in Y, the plate overhangs its pocket wall by 1.850 mm
    and the interference test below reported a confident, reproducible
    **93.018 mm^3** -- of a collision that does not exist on the part. It had
    been doing so since at least round 83.

    The lesson is the one in vibe/INSTRUCTIONS.md under *Positive Control*:
    this helper's own placement was never itself checked, so a mis-seated
    probe and a real defect were indistinguishable. ``test_seated_cap_is_in
    _its_rebate`` below now pins the placement, so a future edit that drops
    a component of it fails loudly instead of manufacturing a fault.
    """
    return PoweredUpHubBatteryTrayCap(profile=profile).solid.translate(
        (0.0,
         PoweredUpHubBatteryTrayCap.SEAT_Y,
         PoweredUpHubBatteryTrayCap.SEAT_Z)
    )


def test_seated_cap_is_in_its_rebate():
    """The ``_seated()`` helper actually puts the plate in the pocket.

    Guards the round-88 bug directly: every other test in this module trusts
    ``_seated()``, so an error there does not fail *it* -- it silently
    corrupts all of them, and reports the corruption as a geometry defect.

    Falsifier: the seated plate's centre not matching the rebate's centre in
    X and Y, or its footprint not lying strictly inside the pocket.
    """
    prof = get_profile("fdm_standard")
    bb = _seated().val().BoundingBox()
    x_half, y_half = PoweredUpHubBatteryTray.cap_rebate_half_extents(prof)

    cx = (bb.xmin + bb.xmax) / 2.0
    cy = (bb.ymin + bb.ymax) / 2.0
    assert abs(cx - 0.0) < 1e-6, (
        f"seated plate is centred on X {cx:.3f}, not the rebate's 0.000"
    )
    assert abs(cy - PoweredUpHubBatteryTray.STRAP_Y_CENTER) < 1e-6, (
        f"seated plate is centred on Y {cy:.3f}, not the rebate's "
        f"{PoweredUpHubBatteryTray.STRAP_Y_CENTER:.3f} -- SEAT_Y was very "
        f"likely dropped from the placement (the round-88 bug)"
    )
    assert bb.xmin > -x_half and bb.xmax < x_half, (
        f"seated plate spans X {bb.xmin:.3f}..{bb.xmax:.3f}, outside its "
        f"rebate's +-{x_half:.3f}"
    )
    assert bb.ymin > PoweredUpHubBatteryTray.STRAP_Y_CENTER - y_half, (
        f"seated plate's -Y edge {bb.ymin:.3f} is outside its rebate"
    )
    assert bb.ymax < PoweredUpHubBatteryTray.STRAP_Y_CENTER + y_half, (
        f"seated plate's +Y edge {bb.ymax:.3f} is outside its rebate"
    )


@pytest.mark.parametrize(
    "profile_name", ["fdm_standard", "resin_precise", "petg", "cnc"])
def test_cap_finishes_at_or_below_flush_never_proud(profile_name):
    """Seated, the cap's top face must be level with the floor's top face or
    slightly below it -- never above.

    ROUND 88, RENAMED. Was ``test_thickness_is_the_rebate_depth_so_it_
    finishes_flush``, asserting EXACT equality on the premise that a plate
    dimensioned to exactly fill its pocket finishes flush. The owner printed
    it and reported the opposite: *"the plate does not sit flush in the
    tray"* -- it sat proud.

    The premise was wrong about the physical world, not about the arithmetic.
    This is a GLUED joint, and an exactly-filling plate has nowhere to put
    the glue except under itself; add a glue film, or an elephant's foot on
    the rebate floor, or a squished first layer on the plate, and every one
    of those departures pushes it the SAME way -- proud. The part gave the
    plate a running clearance on all four edges and none on its thickness.

    So the assertion becomes one-sided, which is what the requirement
    actually is: proud rocks the battery pack and is a real defect; a few
    tenths recessed is harmless, because the pack bears on the floor around
    the plate. The gap is ``profile.free.axial`` -- see the cap's
    :attr:`~PoweredUpHubBatteryTrayCap.thickness` property.

    Falsifier: a seated top face above FLOOR_THICKNESS, or a gap so large
    the plate no longer roofs the corridor meaningfully.

    ROUND 88, THIRD PASS -- swept over all four shipped profiles, having been
    hard-coded to ``fdm_standard`` while ``_seated`` already took a profile no
    caller passed. The sibling kinematic test gained a sweep earlier in this
    same PR on the stated principle that single-profile checks are what let
    errors through; leaving this one pinned contradicted that in the same
    breath. ``cnc`` is the interesting row and the reason the sweep is not
    cosmetic: its ``free.axial`` is 0.000, so there the glue gap is legitimately
    zero -- an exact fit is correct on a machined part -- which means the
    value-pinning assertion below passes identically on a fixed and a reverted
    part at that one profile. That is a real limit of the check and is stated
    at the assertion rather than left for someone to rediscover.
    """
    prof = get_profile(profile_name)
    cap = PoweredUpHubBatteryTrayCap(profile=prof)
    bb = cap.solid.val().BoundingBox()
    assert abs(bb.zmin) < 1e-6, f"cap's print datum is not Z = 0: {bb.zmin}"

    # Built solid vs. what the class computed -- catches a plate extruded the
    # wrong way or to the nominal despite the gap being taken.
    assert abs(bb.zmax - cap.thickness) < 1e-6, (
        f"built plate is {bb.zmax:.3f} thick, not the {cap.thickness:.3f} the "
        f"class computed"
    )
    # NOTE: a third assertion here checked
    #     |(FLOOR_THICKNESS - STRAP_CAP_Z) - cap.thickness| == free.axial
    # as "the glue gap still tracks its knob". It could not fail.
    # `STRAP_CAP_Z` is DEFINED as `FLOOR_THICKNESS - STRAP_CAP_THICKNESS`
    # (battery_tray.py:466), so that first term is identically
    # `Cap.THICKNESS` and the whole expression reduces to
    # |free.axial - free.axial| < 1e-9 -- true for every profile and every
    # geometry, including a plate built inside out.
    #
    # Deleting it was described as lossless. It was NOT, and the replacement
    # below is why. The seated pair further down bounds the gap to the
    # INTERVAL [0, free.axial]; the deleted line pinned its VALUE. A plate
    # with gap == 0 -- precisely the printed-part failure the owner reported
    # -- passes every one of them, verified by rebuilding that exact
    # regression as a subclass (tmp/r88m_cap_coverage_check.py): 4 of 4
    # surviving assertions PASS on the broken part.
    #
    # So the value IS pinned again, but measured off the BUILT seated solid
    # rather than restated from the constants that defined it. Falsifier:
    # revert `_thickness` to the nominal and this fails; the interval checks
    # below do not.

    bb_seated = _seated(profile_name).val().BoundingBox()
    measured_gap = PoweredUpHubBatteryTray.FLOOR_THICKNESS - bb_seated.zmax
    # On every profile with a nonzero axial allowance, a measured gap of 0.000
    # IS the round-88 printed-part failure: an exactly-filling plate has
    # nowhere to put the glue but under itself, so it sits proud and rocks the
    # pack. On `cnc` (free.axial 0.000) a zero gap is instead CORRECT -- an
    # exact fit is right on a machined part -- so this assertion cannot
    # distinguish a fixed part from a reverted one at that profile. It is not
    # vacuous there (a nonzero gap would still fail it), but it is not the
    # regression guard either; the other three rows are.
    assert abs(measured_gap - prof.free.axial) < 1e-9, (
        f"[{profile_name}] the seated plate's glue gap measures "
        f"{measured_gap:.4f} mm, not the profile's axial allowance "
        f"{prof.free.axial:.4f}"
    )
    floor = PoweredUpHubBatteryTray.FLOOR_THICKNESS
    assert bb_seated.zmax <= floor + 1e-9, (
        f"seated cap top at {bb_seated.zmax:.3f} stands PROUD of the floor's "
        f"{floor:.3f} -- it will rock the battery pack. This is the exact "
        f"failure the owner reported from a printed part in round 88."
    )
    assert bb_seated.zmax >= floor - prof.free.axial - 1e-9, (
        f"seated cap top at {bb_seated.zmax:.3f} is more than the glue gap "
        f"below the floor's {floor:.3f} -- it has stopped being a flush-ish "
        f"roof and is now a pocket the pack can drop into"
    )


def test_drops_into_the_rebate_from_above_with_a_glue_gap():
    """A glued joint, not a press fit -- a small positive gap all round is
    intended, so zero interference plus a strictly smaller footprint is
    the correct pair of assertions.

    Positive control: the cap must overlap the Tray's own Z span at all,
    so "no interference" is a real clearance rather than two parts that
    never met.
    """
    prof = get_profile("fdm_standard")
    tray = PoweredUpHubBatteryTray(profile="fdm_standard").solid
    cap = _seated()

    bb_c = cap.val().BoundingBox()
    bb_t = tray.val().BoundingBox()
    assert bb_c.zmin >= bb_t.zmin - 1e-9 and bb_c.zmax <= bb_t.zmax + 1e-9, (
        "positive control failed: the cap does not sit within the tray's Z span"
    )

    vol = sum(s.Volume() for s in cap.intersect(tray).solids().vals())
    assert vol < 1e-6, f"cap interferes with the tray by {vol:.4f} mm^3"

    # ROUND 88 -- these compare against the rebate's ABSOLUTE bounds, not
    # against bare half-extents. `bb_c` is the SEATED plate, so its Y is
    # offset by SEAT_Y (2.000); the previous form compared an absolute Y
    # against a half-width and only held while the plate was mis-seated at
    # Y = 0 by the `_seated()` bug this round fixed. Two errors were
    # cancelling: a wrong placement and a wrong frame in the check.
    x_half, y_half = PoweredUpHubBatteryTray.cap_rebate_half_extents(prof)
    yc = PoweredUpHubBatteryTray.STRAP_Y_CENTER
    assert -x_half < bb_c.xmin and bb_c.xmax < x_half, (
        f"cap spans X {bb_c.xmin:.3f}..{bb_c.xmax:.3f}, not strictly inside "
        f"its rebate's +-{x_half:.3f}"
    )
    assert yc - y_half < bb_c.ymin and bb_c.ymax < yc + y_half, (
        f"cap spans Y {bb_c.ymin:.3f}..{bb_c.ymax:.3f}, not strictly inside "
        f"its rebate's {yc - y_half:.3f}..{yc + y_half:.3f}"
    )


def test_it_roofs_the_corridor():
    """The point of the part. Across the corridor's own Y width and along
    its length, there must be cap material at the channel's roof level --
    otherwise the pack sits over a 20.500 mm slot and the strap has no
    roof to bear against.

    Positive control is the complementary probe directly BELOW it: that
    one must be empty (it is the channel). A cap that filled the corridor
    top-to-bottom would pass the first assertion and fail this one.
    """
    T = PoweredUpHubBatteryTray
    cap = _seated()

    for x in (0.0, T.STRAP_HOLDER_X - 3.0, -(T.STRAP_HOLDER_X - 3.0)):
        roof = rounded_box(
            width=1.0, depth=T.STRAP_WIDTH - 1.0, height=0.1, corner_r=0.0,
            center=(x, 0.0, T.STRAP_CAP_Z + T.STRAP_CAP_THICKNESS / 2.0),
        )
        assert cap.intersect(roof).solids().vals(), (
            f"the corridor has no roof at x={x}"
        )
        channel = rounded_box(
            width=1.0, depth=T.STRAP_WIDTH - 1.0, height=0.1, corner_r=0.0,
            center=(x, 0.0, T.STRAP_CAP_Z / 2.0),
        )
        assert not cap.intersect(channel).solids().vals(), (
            f"the cap hangs down into the channel at x={x} -- no room for the strap"
        )


def test_the_channel_under_the_cap_is_tall_enough_for_the_strap():
    """Measured on the built solids, not re-derived: the clear height in
    the corridor between the Cover's face (the channel floor, at the
    Tray's own Z = 0) and the underside of the seated cap must exceed the
    strap's own nominal thickness.

    Falsifier: a floor thinned, or a cap thickened, to the point where the
    strap cannot pass. Every other test in this file would still pass.
    """
    T = PoweredUpHubBatteryTray
    tray = PoweredUpHubBatteryTray(profile="fdm_standard").solid
    cap = _seated()

    # ROUND 88 -- the corridor probe is centred on STRAP_Y_CENTER, not Y = 0.
    # Round 72 centre-aligned the whole strap assembly with the side tabs
    # (Y = 2.000); this probe kept the old Y = 0 centre, so it straddled the
    # corridor's edge and struck tray material. Its positive control then
    # fired -- correctly, and that is the control doing precisely its job:
    # it refused to report a clear height from a probe that was not in the
    # channel, rather than returning a confident wrong number. Same root
    # cause as the `_seated()` bug this round fixed.
    corridor = rounded_box(
        width=1.0, depth=T.STRAP_WIDTH - 1.0, height=4 * T.FLOOR_THICKNESS,
        corner_r=0.0,
        center=(0.0, T.STRAP_Y_CENTER, -T.FLOOR_THICKNESS),
    )
    assert not tray.intersect(corridor).solids().vals(), (
        "positive control failed: the tray blocks the corridor, so the "
        "clear height measured below is not measuring what it claims to"
    )
    cap_bottom = min(
        s.BoundingBox().zmin for s in cap.intersect(corridor).solids().vals()
    )
    # ``>=``, not ``>``: the user sized the channel at 1.500 outright
    # against a strap measured "less than 1.5mm", i.e. at the strap's own
    # upper bound exactly, deliberately spending no extra headroom (the
    # housing pays for every 0.1 mm here). An earlier ``>`` encoded a
    # margin nobody asked for and failed the moment the real number
    # arrived.
    assert cap_bottom >= T.STRAP_THICKNESS_TARGET - 1e-6, (
        f"clear channel height {cap_bottom:.3f} mm (Cover face to cap "
        f"underside) is under the strap's own measured "
        f"{T.STRAP_THICKNESS_TARGET} mm"
    )
    assert abs(cap_bottom - T.STRAP_CHANNEL_HEIGHT) < 1e-6, (
        f"the built channel ({cap_bottom:.3f}) does not match the "
        f"declared STRAP_CHANNEL_HEIGHT ({T.STRAP_CHANNEL_HEIGHT})"
    )


def test_seats_against_housing_and_cover_with_zero_interference():
    """Seated per ``assembly.py``: the Tray's seat translate plus this
    part's own ``SEAT_Z``.
    """
    cap = _seated().translate((0.0, 0.0, PoweredUpHubCover.PLATE_THICKNESS))

    for name, other in (
        ("Housing", PoweredUpHubHousing(profile="fdm_standard").solid),
        ("Cover", PoweredUpHubCover(profile="fdm_standard").solid),
    ):
        vol = sum(s.Volume() for s in cap.intersect(other).solids().vals())
        assert vol < 1e-6, f"Cap interferes with {name} by {vol:.4f} mm^3"


def test_default_preserving_profile_kwarg():
    a = PoweredUpHubBatteryTrayCap(profile=get_profile("fdm_standard"))
    b = PoweredUpHubBatteryTrayCap(profile="fdm_standard")
    assert abs(a.solid.val().Volume() - b.solid.val().Volume()) < 1e-9
