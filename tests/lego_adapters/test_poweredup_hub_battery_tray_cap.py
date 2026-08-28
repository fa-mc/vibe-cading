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
    """The cap where it actually lives, in the Tray's own frame: its print
    datum is its bottom face at Z = 0, so placing it means adding SEAT_Z.
    """
    return PoweredUpHubBatteryTrayCap(profile=profile).solid.translate(
        (0.0, 0.0, PoweredUpHubBatteryTrayCap.SEAT_Z)
    )


def test_thickness_is_the_rebate_depth_so_it_finishes_flush():
    """Seated, the cap's top face must be level with the floor's own top
    face: the pack lands on both, so a proud cap rocks the battery and a
    sunk one leaves a step.

    Asserted against ``PoweredUpHubBatteryTray``'s constants rather than
    literals precisely so that changing the floor thickness cannot break
    the joint silently.
    """
    cap = PoweredUpHubBatteryTrayCap().solid
    bb = cap.val().BoundingBox()
    assert abs(bb.zmin) < 1e-6, f"cap's print datum is not Z = 0: {bb.zmin}"
    assert abs(bb.zmax - PoweredUpHubBatteryTray.STRAP_CAP_THICKNESS) < 1e-6

    bb_seated = _seated().val().BoundingBox()
    assert abs(bb_seated.zmax - PoweredUpHubBatteryTray.FLOOR_THICKNESS) < 1e-6, (
        f"seated cap top at {bb_seated.zmax} is not flush with the floor's "
        f"own {PoweredUpHubBatteryTray.FLOOR_THICKNESS}"
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

    x_half, y_half = PoweredUpHubBatteryTray.cap_rebate_half_extents(prof)
    assert bb_c.xmax < x_half, "cap is not narrower than its rebate in X"
    assert bb_c.ymax < y_half, "cap is not narrower than its rebate in Y"


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

    corridor = rounded_box(
        width=1.0, depth=T.STRAP_WIDTH - 1.0, height=4 * T.FLOOR_THICKNESS,
        corner_r=0.0, center=(0.0, 0.0, -T.FLOOR_THICKNESS),
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
