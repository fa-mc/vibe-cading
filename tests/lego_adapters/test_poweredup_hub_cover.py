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

    # The sill reaches one running clearance short of the housing wall's
    # own outer face (28.000) -- see _build_window_sill.
    assert abs(bbox.xlen - 2 * (28.000 - prof.free.radial)) < 1e-6

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
    assert abs(bb_p.xlen - PoweredUpHubCover.PLATE_WIDTH) < 1e-6


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
    assert plate[0][0] < -27.0 and plate[0][1] > 27.0, (
        f"positive control failed: plate band {plate[0]} is not full width"
    )

    inner, x_half = PoweredUpHubCover.TONGUE_GAP_X_INNER, PoweredUpHubCover.TONGUE_X_HALF
    rib, riser_half = PoweredUpHubCover.TONGUE_RIB_X_HI, PoweredUpHubCover.RISER_X_HALF

    # Riser: all four blades (Tongue A inner pair + Tongue B outer pair).
    for y, z in ((32.200, 0.600), (33.000, 0.600)):
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
    for y, z in ((33.000, 2.400), (33.900, 2.300)):
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

    # A column inside the wall's own X band, on the window's centreline.
    x_mid = 28.000 - PoweredUpHubHousing.WALL_THICKNESS / 2.0
    for z in (0.1, 0.4, 0.8, 1.1, 1.6, 3.0, 6.0):
        probe = rounded_box(
            width=0.4, depth=1.0, height=0.1, corner_r=0.0,
            center=(x_mid, 0.0, z),
        )
        filled = any(
            part.intersect(probe).solids().vals()
            for part in (housing, cover, tray)
        )
        assert filled, (
            f"the side window is open to daylight at z={z} -- nothing "
            "(housing, cover sill, or tray tab) occupies the wall there"
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
        center=(x_mid, PoweredUpHubCover.WINDOW_SILL_Y_HALF + 0.05, z_mid),
    )
    assert not cover.intersect(gap).solids().vals()
    assert not neighbours["Housing"].intersect(gap).solids().vals(), (
        "no clearance between the sill's edge and the window's -- it binds"
    )


def test_window_sill_tracks_the_tab_width():
    """``WINDOW_SILL_Y_HALF`` is a hardcoded copy of the Tray's own
    ``TAB_PAD_Y_HALF`` (the two classes cannot import each other -- see the
    constant's comment). Measure the built Tray rather than trusting that
    comment: a sill narrower than the tab leaves a visible notch at the
    step, a wider one binds in the window.
    """
    from vibe_cading.lego_adapters.poweredup_hub.battery_tray import (
        PoweredUpHubBatteryTray,
    )

    assert (
        abs(
            PoweredUpHubCover.WINDOW_SILL_Y_HALF
            - PoweredUpHubBatteryTray.TAB_PAD_Y_HALF
        )
        < 1e-9
    ), "the Cover's sill and the Tray's tab have drifted apart in Y"
