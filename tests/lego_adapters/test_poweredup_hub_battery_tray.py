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

"""PoweredUpHubBatteryTray -- regression net per
docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md and the
round-51 resurrection recorded in
docs/design_plans/2026-08-19-poweredup-hub-battery-box_reference-comparison.md.

**Round 55**: round 54's split of the whole floor into a separately-printed
plate is reverted per user direction -- the floor is integral again and
``.solid`` is one contiguous body (see :func:`test_single_solid`). What IS
still a separate part is the small strap-channel cap
(``PoweredUpHubBatteryTrayCap``, tested in
``test_poweredup_hub_battery_tray_cap.py``); the tray-side half of that
joint -- the through-corridor and the underside rebate -- is tested here.

**Deliberately not tested here**: whether the pack fits above the Tray
inside the current 3-stud Housing. The user asked to
design the tray first and revisit the housing's height afterward
(round 51) -- asserting a fit that is known not to hold yet would just be
a second, redundant way of saying "the height hasn't been revisited", and
would need deleting the moment it has. ``test_interior_clears_the_target_battery``
in ``test_poweredup_hub_housing.py`` remains the one source of truth for
that question, unmodified.
"""

import cadquery as cq

from vibe_cading.cq_utils import rounded_box
from vibe_cading.print_settings import get_profile
from vibe_cading.lego_adapters.poweredup_hub.battery_tray import (
    PoweredUpHubBatteryTray,
)
from vibe_cading.lego_adapters.poweredup_hub.cover import PoweredUpHubCover
from vibe_cading.lego_adapters.poweredup_hub.housing import PoweredUpHubHousing
from tests.lego_adapters._poweredup_hub_datum import xfail_cross_datum


def test_single_solid():
    """Round 55 merges the floor back in, so this is one piece again. The
    floor is the ONLY thing joining the two side walls (there are no end
    walls -- see *U shape*), so a regression in its seam overlaps shows up
    here as a body count of 2 or 3, not as a silent sliver.
    """
    t = PoweredUpHubBatteryTray()
    solids = t.solid.solids().vals()
    assert len(solids) == 1, f"expected one contiguous tray, got {len(solids)}"
    assert solids[0].isValid()


def test_strap_corridor_is_cut_clear_through_the_floor():
    """The sketch's centre band: one opening through the floor joining the
    two strap slots, ``STRAP_WIDTH`` wide in Y.

    Positive control FIRST: the floor must be solid at the same Z outboard
    of the corridor in Y, so an empty result inside it is a real cutout
    rather than a probe aimed at open air -- this exact probe class has
    already produced one confident, specific, fictional measurement in
    this part's history.
    """
    T = PoweredUpHubBatteryTray
    tray = PoweredUpHubBatteryTray(profile="fdm_standard").solid
    z_mid = (T.STRAP_CAP_THICKNESS + T.FLOOR_THICKNESS) / 2.0

    control = rounded_box(
        width=2.0, depth=2.0, height=0.4, corner_r=0.0,
        center=(0.0, T.STRAP_CAP_Y_HALF + 3.0, z_mid),
    )
    assert tray.intersect(control).solids().vals(), (
        "positive control failed: no floor material outboard of the corridor"
    )

    # Empty everywhere along the corridor's own length, at both the
    # channel height and the full floor height (it is cut CLEAR through).
    for x in (0.0, T.STRAP_HOLDER_X - 2.0, -(T.STRAP_HOLDER_X - 2.0)):
        for z in (z_mid, T.FLOOR_THICKNESS - 0.2):
            probe = rounded_box(
                width=1.0, depth=T.STRAP_WIDTH - 1.0, height=0.1, corner_r=0.0,
                center=(x, 0.0, z),
            )
            assert not tray.intersect(probe).solids().vals(), (
                f"corridor is blocked at x={x}, z={z}"
            )


def test_strap_corridor_ends_outboard_of_the_pack():
    """The corridor's two ends are where the strap leaves the channel and
    goes over the pack. They must sit OUTBOARD of the pack's own half-width
    or the strap surfaces underneath the battery and retains nothing.

    Falsifier: an end inboard of 16.000 mm would pass every other corridor
    test (the opening exists, the floor is solid elsewhere) while the strap
    silently does nothing.
    """
    T = PoweredUpHubBatteryTray
    tray = PoweredUpHubBatteryTray(profile="fdm_standard").solid
    pack_x_half = 32.0 / 2.0

    bb = tray.intersect(
        rounded_box(
            width=2 * T.WALL_INNER_X, depth=T.STRAP_WIDTH - 1.0,
            height=0.2, corner_r=0.0,
            center=(0.0, 0.0, T.FLOOR_THICKNESS - 0.2),
        )
    )
    # Slicing the floor along the corridor's own Y band leaves only the
    # material OUTBOARD of the corridor's two ends, so its inner edges are
    # the corridor ends themselves.
    xs = sorted(s.BoundingBox().xmin for s in bb.solids().vals())
    assert len(xs) == 2, f"expected floor on both sides of the corridor, got {len(xs)}"
    corridor_end = min(abs(x) for x in xs)
    assert corridor_end > pack_x_half, (
        f"corridor end at |X| = {corridor_end:.3f} is inboard of the pack's "
        f"own half-width ({pack_x_half}) -- the strap would not cross it"
    )


def test_floor_is_flush_with_the_bottom_rim():
    """No standoff (the round-52/53 raised shelf is gone): the floor's
    underside sits ON this class's own ``Z = 0`` datum, which is what makes
    the part printable flat on the bed.

    Probed away from the cap rebate, which legitimately opens the underside
    over its own footprint.
    """
    T = PoweredUpHubBatteryTray
    tray = PoweredUpHubBatteryTray(profile="fdm_standard").solid
    y_outboard = T.STRAP_CAP_Y_HALF + 3.0

    at_the_rim = rounded_box(
        width=2.0, depth=2.0, height=0.1, corner_r=0.0,
        center=(0.0, y_outboard, 0.0),
    )
    assert tray.intersect(at_the_rim).solids().vals(), (
        "the floor does not reach the Z = 0 bottom rim -- a standoff is back"
    )
    assert abs(tray.val().BoundingBox().zmin) < 1e-6


def test_cap_rebate_thins_the_floor_flanks_without_holing_them():
    """The sketch's hatched flanks: thinner, not absent. The rebate takes
    exactly ``STRAP_CAP_THICKNESS`` off the floor's TOP face, so material
    must be gone above :attr:`STRAP_CAP_Z` and present below it -- both
    halves asserted, because either alone is satisfiable by a broken part
    (a rebate that cut clean through would pass the "gone above" half on
    its own, and leave nothing for the cap to glue to).
    """
    T = PoweredUpHubBatteryTray
    tray = PoweredUpHubBatteryTray(profile="fdm_standard").solid
    y_flank = (T.STRAP_WIDTH / 2.0 + T.STRAP_CAP_Y_HALF) / 2.0

    above = rounded_box(
        width=2.0, depth=2.0, height=0.1, corner_r=0.0,
        center=(0.0, y_flank, (T.STRAP_CAP_Z + T.FLOOR_THICKNESS) / 2.0),
    )
    assert not tray.intersect(above).solids().vals(), (
        "the cap rebate is missing -- the cap would stand proud of the floor"
    )
    below = rounded_box(
        width=2.0, depth=2.0, height=0.1, corner_r=0.0,
        center=(0.0, y_flank, T.STRAP_CAP_Z / 2.0),
    )
    assert tray.intersect(below).solids().vals(), (
        "the rebate cut clear through the flank -- it is a blind pocket, and "
        "what is left below it is the ledge the cap glues onto"
    )


def test_the_rebate_opens_upward_so_nothing_bridges():
    """The orientation the user corrected, asserted rather than trusted to
    a comment.

    Everything the rebate removes must have solid tray material directly
    beneath it, all the way down to the bed at ``Z = 0``. If the rebate
    were cut into the UNDERSIDE instead, that column would be empty and
    the flank above it would print as a bridge.

    Falsifier: flip ``_build_cap_rebate``'s Z back to the underside and
    this fails immediately -- which is the point, since the geometry is
    otherwise identical and every other test in this file passes either
    way up.
    """
    T = PoweredUpHubBatteryTray
    tray = PoweredUpHubBatteryTray(profile="fdm_standard").solid
    y_flank = (T.STRAP_WIDTH / 2.0 + T.STRAP_CAP_Y_HALF) / 2.0

    column = rounded_box(
        width=1.0, depth=1.0, height=T.STRAP_CAP_Z, corner_r=0.0,
        center=(0.0, y_flank, 0.0),
    )
    solids = tray.intersect(column).solids().vals()
    assert solids, "positive control failed: nothing under the rebate at all"
    filled = sum(s.Volume() for s in solids)
    assert abs(filled - 1.0 * 1.0 * T.STRAP_CAP_Z) < 1e-6, (
        f"the column under the rebate is only {filled:.3f} mm^3 of a "
        f"possible {T.STRAP_CAP_Z:.3f} -- the rebate is not resting on "
        "solid material and its flank would print as a bridge"
    )


def test_cap_rebate_stays_clear_of_the_side_walls():
    """The rebate's X and Y bounds must stop well inside the side walls.

    This is the guard for the failure mode this part has already shipped
    once: an overcut aimed at a direction nobody checked, which reduced a
    1.850 mm locating rib to a 0.050 mm sliver while every other check
    stayed green. Assert the WIDTH of the wall the rebate passes near, not
    merely its presence.
    """
    T = PoweredUpHubBatteryTray
    prof = get_profile("fdm_standard")
    x_half, y_half = T.cap_rebate_half_extents(prof)
    assert y_half < T.WALL_INNER_X
    assert x_half < T.WALL_INNER_X

    tray = PoweredUpHubBatteryTray(profile="fdm_standard").solid
    section = tray.intersect(
        rounded_box(
            width=2 * T.WALL_OUTER_X, depth=2.0, height=0.1, corner_r=0.0,
            center=(0.0, y_half - 1.0, T.STRAP_CAP_Z + T.STRAP_CAP_THICKNESS / 2.0),
        )
    )
    widths = [
        s.BoundingBox().xmax - s.BoundingBox().xmin for s in section.solids().vals()
    ]
    assert widths, "positive control failed: no material at the wall's own Z"
    assert max(widths) >= T.WALL_THICKNESS - 1e-6, (
        f"the side wall is thinner than {T.WALL_THICKNESS} at the rebate's Z: "
        f"{max(widths):.3f} -- the rebate has eaten into it"
    )


def test_open_at_both_ends():
    """The U shape's whole point: no material at either Y extreme past the
    walls' own footprint -- i.e. nothing caps the channel.

    Falsifier: reintroduce either retired end wall and this probe, run
    just outside the tray's own ``WALL_Y_LO``/``WALL_Y_HI``, finds material.
    """
    T = PoweredUpHubBatteryTray
    tray = PoweredUpHubBatteryTray().solid
    probe = rounded_box(
        width=2 * T.WALL_OUTER_X + 4.0, depth=0.5, height=30.0,
        corner_r=0.0, center=(-T.WALL_OUTER_X - 2.0, 0.0, -1.0),
    )
    for y_sign, label in ((-1, "latch (-Y)"), (1, "tongue (+Y)")):
        beyond = probe.translate((0.0, y_sign * (abs(T.WALL_Y_HI) + 1.0), 0.0))
        hit = tray.intersect(beyond).solids().vals()
        assert not hit, f"found material beyond the {label} end -- U is not open there"


def test_side_walls_span_the_open_length_and_carry_the_tab():
    """Each side wall reaches the tray's full (open-ended) Y span, per
    :attr:`PoweredUpHubBatteryTray.WALL_Y_LO`/``WALL_Y_HI`` -- checked at a
    Z below the extraction tab, away from either.
    """
    T = PoweredUpHubBatteryTray
    tray = PoweredUpHubBatteryTray().solid
    z = T.WALL_Z_HI / 2.0
    for x_sign in (1, -1):
        slab = cq.Workplane("XY").box(0.4, 0.4, 0.4).translate(
            (x_sign * (T.WALL_OUTER_X - 0.4), T.WALL_Y_LO + 0.5, z)
        )
        assert tray.intersect(slab).solids().vals(), (
            f"no wall material near Y = WALL_Y_LO on the {'X+' if x_sign > 0 else 'X-'} side"
        )
        slab2 = slab.translate((0.0, T.WALL_Y_HI - T.WALL_Y_LO - 1.0, 0.0))
        assert tray.intersect(slab2).solids().vals(), (
            f"no wall material near Y = WALL_Y_HI on the {'X+' if x_sign > 0 else 'X-'} side"
        )


def test_side_tab_is_built_at_reference_size():
    """The tab carries no clearance of its own -- it lives on the window
    (round 41, moved with the tab to this class in round 51). Pins the tab
    to the reference's measured figures so a future clearance change cannot
    quietly start shrinking the part again.
    """
    bb = PoweredUpHubBatteryTray()._build_extraction_tab(+1).val().BoundingBox()
    # Round 71: the tab is no longer centred on Y = 0. Its length and its
    # centre both derive from the Cover's window sill (the Cover is ground
    # truth), so these are stated about TAB_Y_CENTER rather than about zero.
    _yc = PoweredUpHubBatteryTray.TAB_Y_CENTER
    assert abs(bb.ymax - (_yc + PoweredUpHubBatteryTray.TAB_PAD_Y_HALF)) < 1e-6
    assert abs(bb.ymin - (_yc - PoweredUpHubBatteryTray.TAB_PAD_Y_HALF)) < 1e-6
    assert abs(bb.zmax - PoweredUpHubBatteryTray.TAB_PAD_Z_HI) < 1e-6


def _proud_spans(shape: cq.Workplane, x_face: float, z: float,
                 step: float = 0.02) -> list[tuple[float, float]]:
    """Y intervals where ``shape`` reaches out to ``x_face`` at height ``z``.

    Probes just inboard of the plane, so the result is "is the part proud
    to here", which is what distinguishes a border from a solid pad.
    """
    probe = cq.Workplane("XY").box(step, step, step)
    hits, out, start = [], [], None
    # Round 71: the window follows TAB_Y_CENTER. It was a Y=0-centred literal
    # (-12.6..+12.6) while the tab was symmetric about Y=0; once the tab moved
    # to centre +2.000 that window CLIPPED its far edge, and a clipped span
    # reads as a real edge -- the probe reported hi = 12.600 (the window's own
    # limit) for an edge actually at 13.750. Derive it so it cannot happen again.
    y_c = PoweredUpHubBatteryTray.TAB_Y_CENTER
    y_lo, y_hi = y_c - 12.6, y_c + 12.6
    ys = [round(y_lo + i * step, 3)
          for i in range(int((y_hi - y_lo) / step) + 1)]
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
    """Round 47 (on Cover), moved here round 51. Philo's tab (24849) is
    proud to X = TAB_LEDGE_X not as a straight top ledge but as a uniform
    ``TAB_FRAME_WIDTH`` border tracing the tab outline round three edges,
    enclosing a recessed interior.

    Z stations are local to this class's own frame (its bottom rim, not
    world Z=0) -- re-picked from the retired Cover-based test's world-Z
    stations to land in the same STRUCTURAL bands (side legs vs. merged
    top segment) now that the tab's own local height is
    :attr:`PoweredUpHubBatteryTray.TAB_PAD_Z_HI` (7.200 mm) rather than the
    old world-frame 8.400 mm -- the bottom 1.2 mm of the old tab is genuinely
    gone (it can't have negative local Z; see the class's own TAB_* comment),
    not mis-converted.

    The falsifier is the LOW stations: a tab built with only the top band
    (no side legs) reads an empty list at any side-band Z.
    """
    T = PoweredUpHubBatteryTray
    tray = PoweredUpHubBatteryTray().solid
    w = T.TAB_FRAME_WIDTH
    top_lo = T.TAB_PAD_Z_HI - w   # local top-band floor, == old 7.200 - 1.200

    # Down the straight sides: two separate legs, one per edge, each the
    # border's own width, seated on the tab's outer profile.
    #
    # Round 71: the stations were the literals (0.5, 2.0, 4.0), chosen when
    # TAB_ROUND_CZ was 3.600. It is now 2.700, so z = 4.0 sits 1.300 mm INSIDE
    # the corner round-over and the probe reads the arc (13.507) rather than
    # the straight side (13.750) -- a genuine reading of the wrong feature, not
    # a geometry fault. z = 4.0 was already 0.400 inside the old round-over and
    # passed only because the arc had not yet pulled in by more than the 0.05
    # tolerance. Derive the stations from the round-over's own start so a
    # future move of TAB_ROUND_CZ cannot silently re-aim them.
    for z in (0.5, T.TAB_ROUND_CZ * 0.5, T.TAB_ROUND_CZ - 0.2):
        legs = _proud_spans(tray, T.TAB_LEDGE_X, z)
        assert len(legs) == 2, (
            f"expected two border legs at z={z}, got {legs} -- a straight "
            "top ledge alone reads as [] here"
        )
        (lo_a, hi_a), (lo_b, hi_b) = legs
        # Round 71: offset by TAB_Y_CENTER -- see test_side_tab_is_built_at
        # _reference_size. The two legs are still mirrored about the tab's
        # own centre, just not about Y = 0.
        yc = T.TAB_Y_CENTER
        assert abs(hi_b - (yc + T.TAB_PAD_Y_HALF)) < 0.05
        assert abs(lo_a - (yc - T.TAB_PAD_Y_HALF)) < 0.05
        assert abs(lo_b - (yc + T.TAB_PAD_Y_HALF - w)) < 0.05
        assert abs(hi_a - (yc - T.TAB_PAD_Y_HALF + w)) < 0.05

    # Over the top the two legs have merged into one continuous run: the
    # border closes across the third edge.
    for z in (top_lo + 0.4, T.TAB_PAD_Z_HI - 0.2):
        top = _proud_spans(tray, T.TAB_LEDGE_X, z)
        assert len(top) == 1, f"expected a closed top segment at z={z}, got {top}"

    # And the interior it encloses is recessed -- not proud to the border.
    near_top = top_lo - 1.0
    assert _proud_spans(tray, T.TAB_LEDGE_X, near_top) != [], (
        f"border vanished at z={near_top}"
    )
    interior = _proud_spans(tray, T.TAB_LEDGE_X, 3.0)
    assert all(abs(abs(lo - T.TAB_Y_CENTER) - (T.TAB_PAD_Y_HALF - w)) < 0.05
               or abs(abs(hi - T.TAB_Y_CENTER) - (T.TAB_PAD_Y_HALF - w)) < 0.05
               for lo, hi in interior), (
        f"interior is not recessed behind the border: {interior}"
    )


@xfail_cross_datum
def test_seats_against_housing_and_cover_with_zero_interference():
    """Seated per assembly.py's own placement (translated up by
    ``PoweredUpHubCover.PLATE_THICKNESS``): the Tray must not interfere
    with either neighbour it actually touches.

    This does NOT check whether the pack fits above the Tray -- see this
    module's own docstring for why that is deliberately out of scope this
    round.
    """
    housing = PoweredUpHubHousing(profile="fdm_standard").solid
    cover = PoweredUpHubCover(profile="fdm_standard").solid
    tray = PoweredUpHubBatteryTray(profile="fdm_standard").solid.translate(
        (0.0, 0.0, PoweredUpHubCover.PLATE_THICKNESS)
    )

    for name, other in (("Housing", housing), ("Cover", cover)):
        vol = sum(s.Volume() for s in tray.intersect(other).solids().vals())
        assert vol < 1e-6, f"Tray interferes with {name} by {vol:.4f} mm^3"


def test_default_preserving_profile_kwarg():
    """Passing an explicit profile object vs. the same profile by name
    produces byte-identical geometry (volume as a cheap proxy)."""
    from vibe_cading.print_settings import get_profile

    prof = get_profile("fdm_standard")
    a = PoweredUpHubBatteryTray(profile=prof)
    b = PoweredUpHubBatteryTray(profile="fdm_standard")
    assert abs(a.solid.val().Volume() - b.solid.val().Volume()) < 1e-9


def _z_runs(shape, x, y, z_hi, step=0.1):
    """Vertically separated runs of material on the line (x, y), as a list
    of ``(z_first_hit, z_last_hit)``.

    Returns positions, not just a count, because "how many runs" alone
    does not distinguish a supported column from one that starts in
    mid-air: a band floating over nothing is a single run, same as a wall
    standing on the bed. The caller needs the first run's START to tell
    them apart.
    """
    runs = []
    z = step / 2.0
    while z < z_hi:
        if shape.isInside(cq.Vector(x, y, z), tolerance=1e-9):
            if runs and abs(runs[-1][1] - (z - step)) < step / 2.0:
                runs[-1][1] = z
            else:
                runs.append([z, z])
        z += step
    return [tuple(r) for r in runs]


def test_no_wall_material_floats_above_a_void():
    """Round 57. The wall must be vertically contiguous at every X -- no
    band of material sitting above empty space with nothing under it.

    This is the defect the user reported ("this creates a floating
    region"). Until round 57 the wall followed Housing's cavity inboard
    with a second, narrower band whose X span (25.250..25.900) was
    DISJOINT from the lower band's (26.400..27.200); the two touched only
    at a hairline ledge. The part was still ONE SOLID, so
    ``test_single_solid`` passed throughout -- connectivity and
    printability are different properties, and only the first was checked.

    Sampled on a Y line clear of the strap channel (|Y| <= 10.250), the
    cap rebate (|Y| <= 15.250) and the extraction tabs (|Y| <= 12.000), so
    a second run means an unsupported wall band and not one of those
    features.
    """
    T = PoweredUpHubBatteryTray
    tray = PoweredUpHubBatteryTray().solid.val()
    y = T.WALL_Y_LO + 2.0
    z_hi = T.WALL_Z_HI + 8.0          # well past the removed band's top

    floating, midair = [], []
    for i in range(35):
        x = 24.0 + i * 0.1
        for x_sign in (1, -1):
            runs = _z_runs(tray, x_sign * x, y, z_hi)
            if not runs:
                continue
            if len(runs) > 1:
                floating.append((round(x_sign * x, 3), runs))
            if runs[0][0] > 0.2:
                midair.append((round(x_sign * x, 3), runs[0][0]))

    assert not floating, (
        f"material sits above a void at (X, runs)={floating} -- a wall band "
        "is unsupported from below"
    )
    assert not midair, (
        f"a column starts in mid-air at (X, Z)={midair} -- nothing reaches "
        "the bed under it"
    )


def test_the_floating_region_check_can_actually_see_one():
    """Positive control for :func:`test_no_wall_material_floats_above_a_void`.

    That test passes when it finds nothing, so on its own it is also
    passed by a broken probe. Here the round-55 defect is rebuilt
    deliberately -- floor, wall slab, and the narrower band floating above
    the floor with the wall's inner face outboard of it -- and the helper
    must see the break. If this fails, the other test proves nothing.
    """
    T = PoweredUpHubBatteryTray
    floor = rounded_box(
        width=2 * T.WALL_INNER_X, depth=10.0, height=T.FLOOR_THICKNESS,
        corner_r=0.0, center=(0.0, 0.0, 0.0),
    )
    wall = rounded_box(
        width=T.WALL_THICKNESS, depth=10.0, height=T.WALL_Z_HI, corner_r=0.0,
        center=(T.WALL_OUTER_X - T.WALL_THICKNESS / 2.0, 0.0, 0.0),
    )
    # ROUND 72 -- both probe X's were literals (25.575 and 26.8) keyed to the
    # wall as it stood when this was written (inner face 26.400, outer 27.200).
    # Thickening the wall inboard to 24.250 put 25.575 INSIDE the wall, so the
    # "floating" band was no longer floating -- it fused to the wall and read
    # as one continuous run, failing a test about the PROBE while the model was
    # fine. 26.8 meanwhile fell outside the wall entirely. Derived now, so the
    # synthetic defect stays a genuine defect wherever the wall goes:
    #   band_x  -- just inboard of the inner face: over the floor, clear of the
    #              wall, hence actually unsupported.
    #   wall_x  -- the wall's own mid-thickness: actually supported.
    band_w = 0.650
    band_x = T.WALL_INNER_X - band_w / 2.0
    wall_x = T.WALL_OUTER_X - T.WALL_THICKNESS / 2.0
    assert band_x < T.WALL_INNER_X, (
        "the floating-band probe must sit inboard of the wall's inner face"
    )
    assert T.WALL_INNER_X < wall_x < T.WALL_OUTER_X, (
        "the supported-wall probe must sit inside the wall's own section"
    )

    band = rounded_box(                           # round 55's upper band
        width=band_w, depth=10.0, height=6.0, corner_r=0.0,
        center=(band_x, 0.0, T.WALL_Z_HI),
    )
    defect = floor.union(wall).union(band).val()
    z_hi = T.WALL_Z_HI + 8.0

    broken = _z_runs(defect, band_x, 0.0, z_hi)
    assert len(broken) == 2, (
        f"the helper sees {len(broken)} run(s) where the defect has two -- "
        "it cannot see a floating band built on purpose, so it is not a check"
    )
    whole = _z_runs(defect, wall_x, 0.0, z_hi)
    assert len(whole) == 1 and whole[0][0] < 0.1 and (
        abs(whole[0][1] - T.WALL_Z_HI) < 0.1
    ), (
        f"the helper reports {whole} for the supported wall, not one run "
        "from the bed to its top -- it cannot distinguish supported from "
        "floating"
    )


def test_tray_is_reversible_in_y():
    """The tray drops in either way round (round 85e).

    Replaces a class-body assert that compared WALL_Y_HI's own derivation
    against the datum it was derived from -- an identity that could not fail.
    Symmetry is a property of the built GEOMETRY, so it is measured here.

    Falsifier: any material present in the part that the flipped copy does
    not also cover. The motion checked is the one actually performed --
    180 degrees about a vertical axis through the centre -- not a mirror,
    because a mirror is not a rigid motion and a part can pass it while being
    impossible to physically turn round.

    Positive control: the same comparison against a 1 mm-displaced copy must
    report a large mismatch. Without it, a boolean that silently returns
    nothing is indistinguishable from perfect symmetry -- and "returns
    nothing" is the more likely of the two.
    """
    T = PoweredUpHubBatteryTray
    t = PoweredUpHubBatteryTray().solid
    cy = (T.WALL_Y_LO + T.WALL_Y_HI) / 2.0

    def mismatch(a, b):
        return (sum(s.Volume() for s in a.cut(b).solids().vals())
                + sum(s.Volume() for s in b.cut(a).solids().vals()))

    displaced = mismatch(t, t.translate((0.0, 1.0, 0.0)))
    assert displaced > 100.0, (
        f"positive control failed: a 1 mm-displaced copy differs by only "
        f"{displaced:.3f} mm^3, so the comparison cannot detect asymmetry "
        f"and the verdict below would be meaningless"
    )

    flipped = t.rotate((0, cy, 0), (0, cy, 1), 180)
    got = mismatch(t, flipped)
    assert got < 1e-6, (
        f"flipping the tray end-for-end leaves {got:.4f} mm^3 of mismatch -- "
        f"it is not reversible. Both the envelope (WALL_Y_LO/HI) and every "
        f"feature must be centred on PoweredUpHubCover.WINDOW_SILL_Y_CENTER; "
        f"the classic cause is a feature datumed to the Cover's PLATE edges "
        f"instead, which sit on a midplane 0.200 mm away."
    )


def test_tray_trapezoid_relief_is_a_through_cut():
    """The trapezoid relief removes the WHOLE wall section, leaving an
    opening rather than a recess (round 82b).

    Replaces a class-body assert that compared a depth against its own
    definition. Measured on the built solid instead: scan across the wall at
    a station inside the relief and require NO material at any X.

    Positive control: the same scan just BELOW the relief's own start must
    find the full wall. A scan that finds nothing everywhere is a broken
    probe, not a through cut.
    """
    T = PoweredUpHubBatteryTray
    v = PoweredUpHubBatteryTray().solid.val()
    yc = T.TAB_Y_CENTER
    z_in = (T.TRAPEZOID_RELIEF_Z_LO + T.WALL_Z_HI) / 2.0
    z_below = T.TRAPEZOID_RELIEF_Z_LO - 1.0

    def material_across_wall(z):
        x = T.WALL_INNER_X
        while x <= T.WALL_OUTER_X:
            if v.isInside(cq.Vector(x, yc, z), tolerance=1e-9):
                return True
            x += 0.005
        return False

    assert material_across_wall(z_below), (
        f"positive control failed: no wall found at Z {z_below:.3f}, below "
        f"the relief -- the scan is not on the wall, so its 'no material' "
        f"result inside the relief would prove nothing"
    )
    assert not material_across_wall(z_in), (
        f"material survives across the wall at Z {z_in:.3f}, inside the "
        f"trapezoid relief -- this is a recess, not the through cut the "
        f"Housing's inner patch has to pass into"
    )
