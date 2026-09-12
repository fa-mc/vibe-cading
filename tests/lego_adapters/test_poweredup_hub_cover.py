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

"""PoweredUpHubCover — regression net per
docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md,
*Multi-part structure -> Cover* and *Success Criteria*.
"""

import cadquery as cq

from vibe_cading.cq_utils import rounded_box

from vibe_cading.lego_adapters.poweredup_hub.cover import PoweredUpHubCover
from vibe_cading.lego_adapters.poweredup_hub.latch_geometry import get_latch_geometry
from vibe_cading.print_settings import get_profile
# ROUND 88 -- the xfail_cross_datum import is gone with the last marker in
# this module. Both of its uses started XPASSing once the Housing's re-datum
# (round 74) made the marker's premise false, so they were removed per the
# marker's own strict=True contract. This file now has no suppressed tests.


def test_single_solid():
    c = PoweredUpHubCover()
    assert len(c.solid.solids().vals()) == 1
    assert c.solid.val().isValid()


def test_plate_envelope():
    """Overall X/Z envelope matches the measured lid, per SS1.1/SS1.4 of
    docs/design_plans/2026-08-19-poweredup-hub-battery-box_ldraw-parts-geometry.md: 54.4 mm wide, 13.0 mm deep (hook tip).

    **Round 51**: the side handles that widened this envelope (round 22,
    re-homed from the deleted BatteryTray) moved back onto
    :class:`~vibe_cading.lego_adapters.poweredup_hub.battery_tray.PoweredUpHubBatteryTray`,
    so the plate's own width was the whole envelope again.

    **Round 55**: the window sill (``_build_window_sill``) puts material
    back outboard of the plate edge -- deliberately, to fill the bottom of
    the housing's side window. So X is measured against the sill's own
    reach now, and the plate's width is asserted separately at a Z above
    the sill, where nothing else contributes. Asserting only the outer
    number would let the sill silently swallow a plate-width regression.
    """
    c = PoweredUpHubCover()
    bbox = c.solid.val().BoundingBox()
    assert abs(bbox.zmin - 0.0) < 1e-9
    prof = get_profile()
    lg = get_latch_geometry(prof)
    assert abs(bbox.zmax - lg.hook_depth) < 1e-6

    # Round 64: the sill is now FLUSH with the housing wall's outer face
    # per the owner's measurement, where it used to stop one running
    # clearance short. Read from the class's own knob rather than restated, so
    # flipping WINDOW_SILL_FLUSH moves the expectation with the part.
    sill_recess = 0.0 if PoweredUpHubCover.WINDOW_SILL_FLUSH else prof.free.radial
    assert abs(
        bbox.xlen
        - 2 * (PoweredUpHubCover.HOUSING_WALL_X_OUTER - sill_recess)
    ) < 1e-6

    # The plate itself, sampled above the sill's own Z extent.
    above_sill = c.solid.intersect(
        rounded_box(
            width=4 * PoweredUpHubCover.PLATE_WIDTH, depth=2.0, height=0.2,
            corner_r=0.0,
            center=(0.0, 0.0, PoweredUpHubCover.PLATE_THICKNESS + 0.1),
        )
    )
    assert not above_sill.solids().vals(), (
        "positive control failed: expected nothing but the sill out here, "
        "so this probe cannot distinguish plate from sill"
    )
    plate_only = c.solid.intersect(
        rounded_box(
            width=4 * PoweredUpHubCover.PLATE_WIDTH, depth=2.0, height=0.2,
            corner_r=0.0, center=(0.0, 20.0, PoweredUpHubCover.PLATE_THICKNESS / 2.0),
        )
    )
    bb_p = plate_only.val().BoundingBox()
    # The plate is one running clearance per side narrower than the
    # reference's own PLATE_WIDTH. Round 61: taken from the class's own
    # fit_clearance() seam rather than re-derived here as prof.free.radial.
    # That duplication is exactly what broke when round 60 re-datumed the lid
    # from calipers on a real MATING pair -- the clearance became 0.000
    # because it is already inside the measurement, and this test went on
    # demanding a second subtraction the part must not have.
    #
    # Still a real check, and the falsifier is unchanged: it fails if the
    # plate stops tracking fit_clearance() in either direction -- clearance
    # silently dropped, applied twice, or applied to the wrong edge.
    expected_plate = (
        PoweredUpHubCover.PLATE_WIDTH - 2 * PoweredUpHubCover.fit_clearance(prof)
    )
    assert abs(bb_p.xlen - expected_plate) < 1e-6, (
        f"plate width {bb_p.xlen:.3f} is not the reference "
        f"{PoweredUpHubCover.PLATE_WIDTH} less one running clearance per "
        f"side ({expected_plate:.3f})"
    )


def test_outer_face_is_z_zero():
    """The Z = 0 datum is the plate's outer/mating face — see class
    docstring, 'The Z = 0 datum, resolved'.

    Compared to a tolerance rather than for exact float equality, matching
    its sibling `test_plate_envelope` (which already asserts this same
    quantity as `abs(bbox.zmin - 0.0) < 1e-9`). An OCCT boolean's bounding
    box carries float noise at machine epsilon for the part's own magnitude
    — ~1e-16 mm on a 35.6 mm envelope — so an exact compare tests the
    boolean kernel's rounding, not the datum. 1e-9 mm still catches a real
    datum error by six orders of magnitude.
    """
    c = PoweredUpHubCover()
    bbox = c.solid.val().BoundingBox()
    assert abs(bbox.zmin - 0.0) < 1e-9


def test_no_third_rib_survives():
    """The one named deletion (design brief O1): the three AA-cell divider
    ribs must not appear anywhere in the built solid. A crude but durable
    guard: the plate's own cross-section at Z = 1.2 + 1.0 (comfortably
    inside the old 3.6 mm-tall rib zone) must be empty over the plate's
    general span, away from the latch/tongue end features."""
    c = PoweredUpHubCover()
    section = c.solid.section(height=2.2)
    wires = section.wires().vals()
    # Any wire found here would be rib material at a height only a rib
    # (or the removed rib's gussets) would occupy over the plate's flat span.
    plate_half = PoweredUpHubCover.PLATE_WIDTH / 2.0
    for w in wires:
        bb = w.BoundingBox()
        # Ribs sat at Y in [-23.6, 22.8] (SS1.3) -- exclude the latch/tongue
        # end features which legitimately have material at this height.
        if not -23.0 < (bb.ymin + bb.ymax) / 2 < 22.0:
            continue
        # Round 22: the side handles legitimately occupy this Z at the
        # plate's own X edges. Excluded by X band only -- a rib would sit
        # INBOARD of the plate edge, so the rib zone this test actually
        # guards (|X| < plate_half) is untouched by the carve-out.
        if min(abs(bb.xmin), abs(bb.xmax)) >= plate_half - 1e-6:
            continue
        raise AssertionError(
            f"Unexpected material at Z=2.2 in the former rib zone: {bb}"
        )


def test_latch_hooks_present_and_mirrored():
    """Both cantilever latch fingers exist, are mirrored about X = 0, and
    each carries the shared LatchGeometry's hook width."""
    c = PoweredUpHubCover()
    lg = get_latch_geometry(get_profile())
    # Slice through the barb's own engagement band -- both hooks must show
    # material there, symmetric about X = 0.
    section = c.solid.section(height=lg.barb_axis_z)
    wires = section.wires().vals()
    assert len(wires) >= 2, "expected at least two disjoint hook cross-sections"
    x_centers = sorted((w.BoundingBox().xmin + w.BoundingBox().xmax) / 2 for w in wires)
    assert abs(x_centers[0] + x_centers[-1]) < 1e-6, "hooks are not mirrored about X=0"


def test_tongue_present_at_insertion_end():
    """The tongue tip (0.926 mm thick, recessed from the outer face) exists
    at the +Y insertion end, per K2."""
    c = PoweredUpHubCover()
    section = c.solid.section(height=(PoweredUpHubCover.TIP_Z_LO + PoweredUpHubCover.RISER_Z_HI) / 2)
    wires = section.wires().vals()
    assert any(
        w.BoundingBox().ymax > PoweredUpHubCover.TONGUE_STEP_Y for w in wires
    ), "expected the tongue tip to extend beyond the riser step"


def _occupied_x_bands(solid, y, z, x_lo=-28.0, x_hi=28.0, step=0.05):
    """Return [(x_start, x_end), ...] of material along a ray in +X."""
    bands, run, x = [], None, x_lo
    while x <= x_hi + 1e-9:
        if solid.isInside(cq.Vector(x, y, z), tolerance=1e-6):
            if run is None:
                run = x
        elif run is not None:
            bands.append((round(run, 3), round(x - step, 3)))
            run = None
        x += step
    if run is not None:
        bands.append((round(run, 3), round(x_hi, 3)))
    return bands


def test_tongue_is_segmented_into_the_reference_four_blades():
    """The tongue is four separate blades with 1.600 mm gaps, not one slab
    (round 45; ldraw-housing-geometry.md SS12.2 T1/T2/T3 -- the gaps are
    where the housing's own locating ribs sit).

    Falsifier: a continuous tongue returns ONE band per station instead of
    four (riser) / two (tip), and the test fails. It also fails if a gap
    lands at the wrong X -- the band edges are compared to the reference
    values, not merely counted.

    Positive control: the same ray at a station inside the PLATE, which the
    reference leaves continuous and this change must not touch, must come
    back as a single full-width band. Without it, a probe that reported
    'no material anywhere' would pass the segmentation assertions.
    """
    solid = PoweredUpHubCover().solid.val()

    plate = _occupied_x_bands(solid, y=31.800, z=0.600)
    assert len(plate) == 1, f"positive control failed: plate is not continuous ({plate})"
    # Derived from PLATE_WIDTH, not the literal +-27.0 this used to carry:
    # that number was written when the plate was 54.400 wide, and round 60's
    # measured 52.330 made the control fail on a plate that is perfectly
    # continuous. A positive control that breaks when the part legitimately
    # changes size is a control that will be edited away next time.
    edge = PoweredUpHubCover.PLATE_WIDTH / 2.0 - 0.100
    assert plate[0][0] < -edge and plate[0][1] > edge, (
        f"positive control failed: plate band {plate[0]} is not full width "
        f"(expected to span at least +-{edge:.3f})"
    )

    # Round 59: the blades are one running clearance narrower and the centre
    # gap one clearance wider than the reference's own figures -- male faces
    # shrink, female voids grow, which is why the sign differs per edge here.
    # The reference constants stay the reference; these are what is printed.
    fit = PoweredUpHubCover.fit_clearance(get_profile())
    inner = PoweredUpHubCover.TONGUE_GAP_X_INNER + fit
    x_half = PoweredUpHubCover.TONGUE_X_HALF - fit
    # Both walls of the rib gap move outward, not just the inner one: a
    # version that widened only the TONGUE_X_HALF side left the housing's
    # locating rib butting this face at zero clearance.
    rib = PoweredUpHubCover.TONGUE_RIB_X_HI + fit
    riser_half = PoweredUpHubCover.RISER_X_HALF - fit

    # Riser: all four blades (Tongue A inner pair + Tongue B outer pair).
    #
    # Round 66: probed OUTBOARD of TONGUE_GAP_Y_INSET. The gaps no longer run
    # back to the plate edge -- the blades are joined at their root by design
    # -- so the old y = 32.200 station now sits in solid tongue and would
    # report one band, reading as "the segmentation is gone" when the opposite
    # is true. Both stations are past the inset and inside the riser.
    y_root = PoweredUpHubCover.PLATE_Y_HI + PoweredUpHubCover.TONGUE_GAP_Y_INSET
    for y, z in ((y_root + 0.400, 0.600), (33.800, 0.600)):
        bands = _occupied_x_bands(solid, y=y, z=z)
        assert len(bands) == 4, f"expected 4 blades at y={y}, z={z}, got {bands}"
        expected = [
            (-riser_half, -rib), (-x_half, -inner), (inner, x_half), (rib, riser_half),
        ]
        for got, want in zip(bands, expected):
            assert abs(got[0] - want[0]) <= 0.05 and abs(got[1] - want[1]) <= 0.05, (
                f"blade {got} does not match reference band {want} at y={y}, z={z}"
            )

    # Tip / ledge: only Tongue A reaches here, so two blades with the
    # centre gap between them -- Tongue B stops at TONGUE_STEP_Y (T5).
    #
    # Round 67: both stations derived from y_root rather than written as
    # literals. y = 33.000 used to sit safely inside the gap; when the body
    # grew 0.200 at this end the gap's start face moved onto exactly that
    # station, and a probe sitting on a boundary face reports material. It
    # failed as "the centre gap is missing" -- a datum move masquerading as a
    # geometry defect, and the third time this round of literals has done it.
    for y, z in ((y_root + 0.400, 2.400), (y_root + 1.300, 2.300)):
        bands = _occupied_x_bands(solid, y=y, z=z)
        assert len(bands) == 2, f"expected 2 tip blades at y={y}, z={z}, got {bands}"
        assert abs(bands[0][1] + inner) <= 0.05 and abs(bands[1][0] - inner) <= 0.05, (
            f"centre gap is not at |X| = {inner} at y={y}, z={z}: {bands}"
        )


def test_default_preserving_profile_kwarg():
    """Passing an explicit profile object vs. the same profile by name
    produces byte-identical geometry (volume as a cheap proxy)."""
    prof = get_profile("fdm_standard")
    a = PoweredUpHubCover(profile=prof)
    b = PoweredUpHubCover(profile="fdm_standard")
    assert abs(a.solid.val().Volume() - b.solid.val().Volume()) < 1e-9




def test_window_sill_fills_the_bottom_of_the_side_window():
    """Round 55. Until round 51 the extraction tab lived on the Cover and
    was rooted at the plate, filling the housing's side window from
    ``Z = 0``. Moving the tab to the Tray raised its root to
    ``PLATE_THICKNESS``, leaving a 1.200 mm slot straight through the side
    wall, open to daylight.

    Assert the whole ``Z`` extent of the window is occupied by SOMETHING:
    the sill below, the tab above. Falsifier: remove
    ``_build_window_sill`` and the band from 0 to 1.200 goes empty. That
    is exactly the state this repo shipped for four rounds, undetected --
    the window is cut to the tab's outline and the tab fits it perfectly,
    so no single-part test could see it.
    """
    from vibe_cading.lego_adapters.poweredup_hub.battery_tray import (
        PoweredUpHubBatteryTray,
    )
    from vibe_cading.lego_adapters.poweredup_hub.housing import PoweredUpHubHousing

    housing = PoweredUpHubHousing(profile="fdm_standard").solid
    cover = PoweredUpHubCover(profile="fdm_standard").solid
    seat = PoweredUpHubCover.PLATE_THICKNESS
    tray = PoweredUpHubBatteryTray(profile="fdm_standard").solid.translate(
        (0.0, 0.0, seat)
    )

    # ROUND 88 -- this scans the wall's FULL thickness instead of sampling one
    # hand-picked X, and asserts the property the docstring actually states:
    # you cannot see THROUGH the wall.
    #
    # The old probe sat at `28.000 - WALL_THICKNESS / 2`, which was stale
    # twice over: 28.000 was the wall's outer face before the owner
    # re-measured it to 27.800 (round 81b), and WALL_THICKNESS (0.800) is the
    # UPPER band's figure while this window is cut through the LOWER wall
    # (WALL_THICKNESS_LOWER, 1.400). It landed at X 27.600.
    #
    # More importantly it was the wrong SHAPE of check. Measured across the
    # wall, the tray's extraction tab fills the window from the inner face out
    # to 27.050-27.370 and stops there -- deliberately recessed 0.43-0.75 mm
    # so it does not stand proud of the housing's outer surface. X 27.600 sits
    # inside that intended recess, so the old probe reported a design feature
    # as a hole. Nothing was ever open to daylight.
    #
    # The falsifier the docstring names is PRESERVED: over Z 0..1.2 the Cover's
    # sill is the only thing occupying the wall at any X, so deleting
    # _build_window_sill still empties that band completely and still fails
    # here. That is the regression this test exists for.
    x_in = PoweredUpHubHousing.CAVITY_X_HALF_LOWER
    x_out = PoweredUpHubHousing.WALL_X_OUTER_LOWER
    y_mid = PoweredUpHubBatteryTray.TAB_Y_CENTER

    def occupied_anywhere(z):
        x = x_in
        while x <= x_out:
            probe = rounded_box(
                width=0.05, depth=1.0, height=0.1, corner_r=0.0,
                center=(x, y_mid, z),
            )
            if any(part.intersect(probe).solids().vals()
                   for part in (housing, cover, tray)):
                return round(x, 3)
            x += 0.05
        return None

    for z in (0.1, 0.4, 0.8, 1.1, 1.6, 3.0, 6.0):
        at = occupied_anywhere(z)
        assert at is not None, (
            f"the side window is open to daylight at z={z}: NOTHING (housing, "
            f"cover sill, or tray tab) occupies any X across the wall's full "
            f"{x_in:.3f}..{x_out:.3f} thickness, so the slot goes straight "
            f"through"
        )


def test_window_sill_clears_the_window_and_its_neighbours():
    """The sill has to fill the opening without binding in it.

    Y: the sill matches the TAB's half-width while the window is that
    outline offset outward by the running clearance, so there must be a
    positive gap on both sides -- checked by finding the sill's edge and
    the housing's edge and asserting daylight between them.

    Zero interference against every part it sits next to, with the
    single-solid check on the Cover itself as the positive control that
    the sill actually fused to the plate rather than floating beside it.
    """
    from vibe_cading.lego_adapters.poweredup_hub.battery_tray import (
        PoweredUpHubBatteryTray,
    )
    from vibe_cading.lego_adapters.poweredup_hub.battery_tray_cap import (
        PoweredUpHubBatteryTrayCap,
    )
    from vibe_cading.lego_adapters.poweredup_hub.housing import PoweredUpHubHousing

    cover = PoweredUpHubCover(profile="fdm_standard").solid
    assert len(cover.solids().vals()) == 1, (
        "the sill did not fuse to the plate -- it is a separate body"
    )

    seat = PoweredUpHubCover.PLATE_THICKNESS
    neighbours = {
        "Housing": PoweredUpHubHousing(profile="fdm_standard").solid,
        "Tray": PoweredUpHubBatteryTray(profile="fdm_standard").solid.translate(
            (0.0, 0.0, seat)
        ),
        "Cap": PoweredUpHubBatteryTrayCap(profile="fdm_standard").solid.translate(
            (0.0, 0.0, seat + PoweredUpHubBatteryTrayCap.SEAT_Z)
        ),
    }
    for name, other in neighbours.items():
        vol = sum(s.Volume() for s in cover.intersect(other).solids().vals())
        assert vol < 1e-6, f"Cover interferes with {name} by {vol:.4f} mm^3"

    # Daylight in Y between the sill's edge and the window's edge.
    x_mid = 28.000 - PoweredUpHubHousing.WALL_THICKNESS / 2.0
    z_mid = PoweredUpHubCover.PLATE_THICKNESS / 2.0
    gap = rounded_box(
        width=0.4, depth=0.05, height=0.4, corner_r=0.0,
        center=(
            x_mid,
            PoweredUpHubCover.WINDOW_SILL_Y_CENTER
            + PoweredUpHubCover.WINDOW_SILL_WIDTH / 2.0
            + 0.05,
            z_mid,
        ),
    )
    assert not cover.intersect(gap).solids().vals()
    assert not neighbours["Housing"].intersect(gap).solids().vals(), (
        "no clearance between the sill's edge and the window's -- it binds"
    )


def test_window_sill_tracks_the_tab_width():
    """The sill used to be a hardcoded copy of the Tray's ``TAB_PAD_Y_HALF``
    (the two classes cannot import each other -- see the constant's comment),
    measured off the built Tray rather than trusted from the comment.

    **Round 64 separated them deliberately.** The owner measured the sill
    against the REAL housing's window -- 23.500 wide, offset 2.000 toward the
    tongue end -- where the tab is 24.000 centred. So the sill is no longer
    "the tab's outline"; it is its own measured feature, and this equality is
    now false by direction rather than by drift.

    Kept, and xfailed rather than deleted, because the thing it protects is
    still real and still unresolved: our Housing cuts its window FROM the tab,
    so this sill overhangs that window's +Y edge by 1.750. Against a real
    housing it should fit; against ours it cannot. When the Housing is
    re-datumed this becomes a genuine check again -- rewritten against the
    window rather than the tab -- and the strict xfail will demand that
    rewrite by failing loudly the moment the two happen to agree.
    """
    from vibe_cading.lego_adapters.poweredup_hub.battery_tray import (
        PoweredUpHubBatteryTray,
    )

    assert (
        abs(
            PoweredUpHubCover.WINDOW_SILL_WIDTH / 2.0
            - PoweredUpHubBatteryTray.TAB_PAD_Y_HALF
        )
        < 1e-9
    ), "the Cover's sill and the Tray's tab have drifted apart in Y"
