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

    **Round 22**: the overall X envelope is now set by the side handles
    (re-homed from the deleted BatteryTray), which stand proud of the
    plate by design so they can be reached through the housing's own side
    windows. The plate's own 54.4 mm width is still asserted -- measured
    at a Z above the handles rather than off the overall bounding box, so
    this stays a real check on the plate rather than being relaxed away.
    """
    c = PoweredUpHubCover()
    bbox = c.solid.val().BoundingBox()
    assert abs(bbox.xlen - 2 * PoweredUpHubCover.HANDLE_LEDGE_X) < 1e-6
    assert abs(bbox.zmin - 0.0) < 1e-9
    prof = get_profile()
    lg = get_latch_geometry(prof)
    assert abs(bbox.zmax - lg.hook_depth) < 1e-6

    # The plate proper. Sampled at a Y band the handles do not span
    # (they reach only |Y| <= HANDLE_PAD_Y_HALF) rather than at a Z above
    # them -- the plate is just PLATE_THICKNESS tall, so no Z clears the
    # handles, but plenty of Y does.
    y_lo = PoweredUpHubCover.HANDLE_PAD_Y_HALF + 5.0
    slab = (
        cq.Workplane("XY")
        .box(200.0, 4.0, 200.0, centered=(True, False, False))
        .translate((0.0, y_lo, -50.0))
    )
    plate_bb = c.solid.intersect(slab).val().BoundingBox()
    assert abs(plate_bb.xlen - PoweredUpHubCover.PLATE_WIDTH) < 1e-6


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


def _proud_spans(shape: cq.Workplane, x_face: float, z: float,
                 step: float = 0.02) -> list[tuple[float, float]]:
    """Y intervals where ``shape`` reaches out to ``x_face`` at height ``z``.

    Probes just inboard of the plane, so the result is "is the part proud
    to here", which is what distinguishes a border from a solid pad.
    """
    probe = cq.Workplane("XY").box(step, step, step)
    hits, out, start = [], [], None
    ys = [round(-12.6 + i * step, 3) for i in range(int(25.2 / step) + 1)]
    for y in ys:
        b = probe.translate((x_face - step / 2.0, y, z))
        try:
            hits.append(bool(shape.intersect(b).solids().vals()))
        except Exception:
            hits.append(False)
    for i, h in enumerate(hits):
        if h and start is None:
            start = ys[i]
        elif not h and start is not None:
            out.append((start, ys[i - 1]))
            start = None
    if start is not None:
        out.append((start, ys[-1]))
    return out


def test_side_tab_carries_a_border_round_three_edges():
    """Round 47. Philo's tab (24849) is proud to X = 28.400 not as a
    straight top ledge but as a uniform 1.200 mm border tracing the tab
    outline round three edges, enclosing a recessed interior.

    The falsifier is the LOW stations: rounds 22-46 built only the top band
    (z 7.200..8.400), so at z = 2.000 they were proud to 28.400 *nowhere*
    and this test reads an empty list. A pad built solid out to 28.400
    instead of bordered fails the opposite way -- one span, not two.
    """
    c = PoweredUpHubCover
    cover = PoweredUpHubCover().solid
    w = c.HANDLE_FRAME_WIDTH

    # Down the straight sides: two separate legs, one per edge, each the
    # border's own width, seated on the tab's outer profile.
    for z in (0.5, 2.0, 4.0):
        legs = _proud_spans(cover, c.HANDLE_LEDGE_X, z)
        assert len(legs) == 2, (
            f"expected two border legs at z={z}, got {legs} -- a straight "
            "top ledge alone reads as [] here"
        )
        (lo_a, hi_a), (lo_b, hi_b) = legs
        assert abs(hi_b - c.HANDLE_PAD_Y_HALF) < 0.05
        assert abs(lo_a + c.HANDLE_PAD_Y_HALF) < 0.05
        assert abs(lo_b - (c.HANDLE_PAD_Y_HALF - w)) < 0.05
        assert abs((hi_a + c.HANDLE_PAD_Y_HALF - w)) < 0.05

    # Over the top the two legs have merged into one continuous run: the
    # border closes across the third edge.
    for z in (7.6, 8.2):
        top = _proud_spans(cover, c.HANDLE_LEDGE_X, z)
        assert len(top) == 1, f"expected a closed top segment at z={z}, got {top}"

    # And the interior it encloses is recessed -- not proud to the border.
    assert _proud_spans(cover, c.HANDLE_LEDGE_X, 6.0) != [], "border vanished at z=6"
    interior = _proud_spans(cover, c.HANDLE_LEDGE_X, 3.0)
    assert all(abs(abs(lo) - (c.HANDLE_PAD_Y_HALF - w)) < 0.05
               or abs(abs(hi) - (c.HANDLE_PAD_Y_HALF - w)) < 0.05
               for lo, hi in interior), (
        f"interior is not recessed behind the border: {interior}"
    )
