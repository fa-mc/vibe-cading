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

"""PoweredUpHubHousing -- regression net per
docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md,
*Multi-part structure -> Housing* and *Success Criteria*.
"""

import math

import cadquery as cq

from vibe_cading.cq_utils import rounded_box
from vibe_cading.lego.cutters.technic_pin_hole import TechnicPinHole
from vibe_cading.lego_adapters.poweredup_hub.battery_tray import (
    PoweredUpHubBatteryTray,
)
from vibe_cading.lego_adapters.poweredup_hub.cover import PoweredUpHubCover
from vibe_cading.lego_adapters.poweredup_hub.housing import PoweredUpHubHousing
from vibe_cading.print_settings import get_profile


def test_single_solid():
    h = PoweredUpHubHousing()
    assert len(h.solid.solids().vals()) == 1
    assert h.solid.val().isValid()


def test_envelope_matches_25560():
    """72.0 x 71.2 mm in plan; Z is DECK_Z.

    **Round 22**: Z is now 24.000 mm (3 studs -- the user's bottom-layer
    cap), a deliberate departure from the reference shell's own 29.600 mm.
    Asserted against the constant so the stud count stays the single
    source of truth. X grows to 72.0/72.6ish with the arm bosses; Y and Z
    are exact -- see class docstring's cross-section note."""
    h = PoweredUpHubHousing()
    bbox = h.solid.val().BoundingBox()
    assert abs(bbox.ylen - 2 * PoweredUpHubHousing.HALF_Y) < 1e-6
    assert abs(bbox.zmin - 0.0) < 1e-9
    assert abs(bbox.zmax - PoweredUpHubHousing.DECK_Z) < 1e-6
    # X grows slightly past the real 72.0 mm because the arm cross-section
    # deliberately keeps the class's own BEAM_WIDTH (7.8 mm nominal, 7.5 mm
    # as-built after round 16's outboard-only trim), not LDraw's idealised
    # 7.2 mm -- see class docstring.  Assert it's in the right ballpark,
    # not byte-exact to the LDraw figure.
    assert 71.9 < bbox.xlen < 73.5


def test_bottom_face_is_z_zero_and_open():
    """The lid is the floor -- Z = 0 is the housing's own bottom datum,
    and no material closes the bottom off (the housing's solid starts
    only above Z = 0, i.e. Z = 0 is a boundary, not a filled floor)."""
    h = PoweredUpHubHousing()
    bbox = h.solid.val().BoundingBox()
    # Compared to a tolerance, not for exact equality: since round 55f
    # the bottom edge is cut by a cylinder, and an OCCT boolean leaves
    # float noise at machine epsilon for the part's own magnitude
    # (~4e-14 mm here). An exact compare tests the kernel's rounding,
    # not the datum -- the same reasoning as the Cover's own
    # test_outer_face_is_z_zero.
    assert abs(bbox.zmin) < 1e-9
    # A slice right at the bottom face should show only the thin wall /
    # arm perimeter, not a filled disc -- probe the housing's own centre,
    # which must be empty (open cavity, no floor).
    section = h.solid.section(height=0.5)
    for w in section.wires().vals():
        bb = w.BoundingBox()
        assert not (bb.xmin < 0 < bb.xmax and bb.ymin < 0 < bb.ymax), (
            "unexpected material spanning the housing's own centre near Z=0 "
            "-- the bottom must stay open (the lid is the floor)"
        )


def _probe_material(solid, x, y, z, size=2.0):
    """Volume of `solid` inside a small box centred at (x, y, z) -- a cheap
    "is there material here" probe, more robust for this geometry than
    Workplane.section().wires() (which does not reliably surface small
    interior bore wires against this compound multi-feature body)."""
    import cadquery as cq

    box = cq.Workplane("XY").transformed(offset=cq.Vector(x, y, z - size / 2)).box(
        size, size, size, centered=(True, True, False)
    )
    inter = solid.intersect(box)
    vals = inter.solids().vals()
    return sum(s.Volume() for s in vals) if vals else 0.0


def test_twelve_pin_holes_present():
    """Each of the 4 arms carries 3 hole positions (2 vertical 'main' +
    1 horizontal 'none'/custom-bored 'middle') = 12 total, per the design
    brief's hole census. A material probe at each hole centre (hole-axis
    height, hole X/Y per the census) must be empty (bore present), while a
    probe just off-axis on the same arm must show material (not an
    over-cut wafer)."""
    h = PoweredUpHubHousing().solid
    for x_sign in (+1, -1):
        for y in PoweredUpHubHousing.HOLE_Y:
            for y_sign in (+1, -1):
                x = x_sign * PoweredUpHubHousing.HOLE_X
                yy = y_sign * y
                bore_vol = _probe_material(h, x, yy, PoweredUpHubHousing.HOLE_AXIS_Z)
                assert bore_vol < 1e-6, f"expected an open bore at (X={x}, Y={yy}), found material"
        # off-hole probe on this arm (between the inner and middle hole
        # positions) must show real material.
        material_vol = _probe_material(
            h, x_sign * PoweredUpHubHousing.HOLE_X, 20.0, PoweredUpHubHousing.HOLE_AXIS_Z
        )
        assert material_vol > 1.0, "expected solid material between adjacent hole positions"


def test_arm_meets_the_body_on_a_flat_face():
    """The arm's inboard half must be square, not a tangent cusp.

    Round 44. A full stadium cap touches the end plane at a single point and
    curves away immediately, so where the arm approached the housing it left a
    sharp re-entrant notch -- the body edge ran in at Y = 35.600 to X = 28.400,
    dropped to Y = 32.000, and only there did the arc start. A notch at a
    cantilever's root is the worst place to put one.

    Falsifier: drop the round-44 fill and the sampled points inboard of the
    hole line move back onto the arc, well short of the end plane.
    """
    h = PoweredUpHubHousing()
    solid = h.solid
    z = h.HOLE_AXIS_Z
    for y_end, inward in ((h.HALF_Y, -1.0), (h.ARM_Y_LO, +1.0)):
        for x in (h.HOLE_X - h.ARM_CAP_R + 0.3, h.HOLE_X - 1.0, h.HOLE_X - 0.2):
            y = y_end + inward * 0.2          # just inside the end face
            p = cq.Workplane("XY").box(0.04, 0.04, 0.04).translate((x, y, z))
            assert solid.intersect(p).solids().vals(), (
                f"no material at (X={x:.2f}, Y={y:.2f}) -- the arm still meets "
                f"the body on a curve, leaving a notch at its root"
            )
        # ...and the outboard corner must still be relieved (the round).
        y = y_end + inward * 0.2
        p = cq.Workplane("XY").box(0.04, 0.04, 0.04).translate((h.HOLE_X + 3.4, y, z))
        assert not solid.intersect(p).solids().vals(), (
            "positive control failed: material found where the outboard round "
            "should have relieved the corner, so the readings above prove nothing"
        )


def test_arm_end_cap_is_a_true_round_on_the_hole_centre():
    """The arm's outboard end must be a full R3.6 round centred on the outer
    hole -- not a round chopped by envelope trims.

    Round 43. Rounds 16-42 built the shared liftarm's 3.9 cap (centred 0.1 off
    the hole line) and squared it off at |X| = 35.6 and Y = 35.6, which left a
    3.440 mm FLAT CHORD across the tip and a flat down the outboard face. That
    is the "cut unnaturally" the user reported, and the re-entrant step it left
    against the end wall was the notch.

    Falsifier: reinstate either trim and one of the sampled points moves inside
    the nominal radius, because a chord lies inside the arc it subtends.
    Sampling sweeps the whole arc rather than checking the tangent points --
    the tangent points are exactly where a truncated cap still agrees.
    """
    h = PoweredUpHubHousing()
    solid = h.solid
    r = h.ARM_CAP_R
    cx, cy = h.HOLE_X, 32.0   # outer hole centre of the +X/+Y arm
    z = h.HOLE_AXIS_Z

    # Sweep the OUTBOARD half of the cap only: 0 deg (+Y, the tip) round to
    # +90 deg (+X, the tangent). Everything else is legitimately further from
    # the hole centre than the radius and would measure the wrong surface --
    # past +90 it is the arm's straight flank, and on the inboard side (angles
    # < 0) round 44 deliberately squares the cap off flat against the body.
    worst = None
    for i in range(0, 19):                     # 0..+90 deg about the hole centre
        ang = math.radians(i * 5.0)
        # Step outward along the ray until material ends: that is the cap edge.
        edge = None
        for j in range(120):
            d = r - 0.6 + j * 1.2 / 120.0
            x, y = cx + d * math.sin(ang), cy + d * math.cos(ang)
            p = cq.Workplane("XY").box(0.04, 0.04, 0.04).translate((x, y, z))
            if solid.intersect(p).solids().vals():
                edge = d
        if edge is None:
            continue
        err = abs(edge - r)
        if worst is None or err > worst[1]:
            worst = (i * 5.0, err, edge)

    assert worst is not None, "positive control failed: no material found on the cap at all"
    ang, err, edge = worst
    assert err < 0.06, (
        f"arm cap edge is {edge:.3f} mm from the hole centre at {ang:+.0f} deg, "
        f"expected the nominal cap radius {r:.3f} mm -- the cap is not a true "
        f"round (a trim has flattened it)"
    )


def test_horizontal_arm_hole_matches_ldraw_connhol3():
    """One counterbore, at the entry rim -- LDraw's blind-hole primitive.

    Round 43. Round 42 used the through-hole shape, which put a second Ø6.2
    flange immediately behind the bore floor: precisely where a blind hole has
    least material to give. Philo uses `connhol3` here (`connhole` at the two
    vertical positions), and its counterbored rim is the outboard one.

    Falsifier: switch back to counterbore_ends="both" and the floor-side
    reading widens from the bore diameter to the counterbore diameter.
    """
    h = PoweredUpHubHousing()
    solid = h.solid
    z = h.HOLE_AXIS_Z
    cb_d = TechnicPinHole.DEFAULT_CB_DIAMETER
    bore_d = 4.8 + 2 * h._profile.slip.radial

    def void_width(x):
        hits = [20.0 + j * 8.0 / 200.0 for j in range(201)]
        open_ys = [
            y for y in hits
            if not solid.intersect(
                cq.Workplane("XY").box(0.05, 0.05, 0.05).translate((x, y, z))
            ).solids().vals()
        ]
        return (open_ys[-1] - open_ys[0]) if open_ys else 0.0

    entry = void_width(35.4)          # 0.6 mm in -- inside the entry counterbore
    mid = void_width(32.0)            # mid-bore
    floor_side = void_width(29.0)     # 0.2 mm before the floor at 28.8

    assert entry > (cb_d + bore_d) / 2.0, (
        f"entry rim measures {entry:.3f} mm, expected a counterbore near {cb_d}"
    )
    assert abs(mid - bore_d) < 0.15, (
        f"mid-bore measures {mid:.3f} mm, expected the pin bore {bore_d:.3f}"
    )
    assert floor_side < (cb_d + bore_d) / 2.0, (
        f"the floor end measures {floor_side:.3f} mm -- a second counterbore is "
        f"still being cut there; the reference's connhol3 has only one"
    )


def test_middle_bore_is_blind():
    """The middle pin hole must NOT open into the battery cavity.

    Round 42 inverts this test. It used to assert the bore *did* break
    through -- and asserted it by probing |X| = 22.0, a point well inside
    the cavity, which is empty whether the bore reaches it or not. Cutting
    cannot add material, so no geometry could have failed it.

    The claim now has a falsifier and a positive control: the side wall on
    the hole's own axis must be SOLID (deepen the bore past the wall's outer
    face and it goes empty), and the same probe on the boss side must be
    EMPTY (so an "occupied" reading is a real measurement, not a probe that
    reports material everywhere).
    """
    h = PoweredUpHubHousing()
    solid = h.solid
    wall_mid_x = h.WALL_X_OUTER_LOWER - h.WALL_THICKNESS / 2.0   # 27.600
    for x_sign in (+1, -1):
        for y_sign in (+1, -1):
            y = y_sign * 24.0
            wall = _probe_material(solid, x_sign * wall_mid_x, y, h.HOLE_AXIS_Z)
            assert wall > 1e-6, (
                f"the middle bore has breached the side wall at "
                f"(|X| = {wall_mid_x}, Y = {y}) -- it must stop at the wall's "
                f"outer face and leave the cavity closed"
            )
            bore = _probe_material(solid, x_sign * 31.0, y, h.HOLE_AXIS_Z)
            assert bore < 1e-6, (
                "positive control failed: the probe reports material inside "
                "the bore itself, so the wall reading above proves nothing"
            )


def test_general_body_seated_interference_is_zero():
    """The seated Cover/Housing overlay must be zero EVERYWHERE.

    Round 40 removed this test's carve-out. Rounds 18-39 excluded the latch
    catch's own footprint because the catch made "a geometrically
    UNAVOIDABLE seated engagement" -- which was never true of a working
    mechanism (two rigid printed parts that overlap when seated cannot be
    assembled) and is now moot: the catch is gone and retention comes from
    the release-leg bead against the land, which engages with zero seated
    interference by construction.

    Note what this test canNOT see, which is why the two clearance tests
    below exist: a gap of exactly zero encloses no volume, so a part butted
    face-to-face against another scores 0.000 mm^3 here and passes.
    """
    h = PoweredUpHubHousing()
    c = PoweredUpHubCover()
    inter = h.solid.intersect(c.solid)
    vol = sum(s.Volume() for s in inter.solids().vals())
    assert vol < 1e-6, (
        f"Housing/Cover seated interference {vol:.4f} mm^3 -- expected 0"
    )


def test_tongue_rebate_matches_cover_tongue():
    """The rebate's step height/depth exactly match the Cover's own tongue
    tip datum (single source of truth: both read from the same measured
    LDraw figures, not independently re-typed)."""
    assert PoweredUpHubHousing.TONGUE_STEP_Z == PoweredUpHubCover.TIP_Z_LO
    assert PoweredUpHubHousing.TONGUE_INNER_Y_LOWER == PoweredUpHubCover.TONGUE_STEP_Y


def test_finger_windows_expose_thumb_pads():
    """The two 13.6 x 3.6 mm finger-access windows must actually be open
    (no housing material) over their own footprint."""
    h = PoweredUpHubHousing()
    section = h.solid.section(height=1.8)  # mid-height of the window band
    for w in section.wires().vals():
        bb = w.BoundingBox()
        for side in (+1, -1):
            x_lo = side * PoweredUpHubHousing.LATCH_WINDOW_X_LO
            x_hi = side * PoweredUpHubHousing.LATCH_WINDOW_X_HI
            lo, hi = min(x_lo, x_hi), max(x_lo, x_hi)
            center_x = (bb.xmin + bb.xmax) / 2.0
            center_y = (bb.ymin + bb.ymax) / 2.0
            assert not (
                lo < center_x < hi and center_y < -34.0
            ), f"unexpected material inside a finger window: {bb}"


def test_side_window_is_the_tab_outline_across_the_whole_round_over():
    """The side window must be the Tray's tab outline, offset by the
    clearance -- checked at every Z through the round-over.

    Round 41 (window built against Cover's tab, before round 51 moved the
    tab to :class:`PoweredUpHubBatteryTray`). The window used to be three
    straight chords sampled off the reference's arc, and a chord lies
    inside the arc it subtends, so it was narrower than the tab at every
    INTERMEDIATE Z while matching it exactly at the sampled ones. The
    tab-bearing part paid for that by shrinking its whole tab 0.320 mm.
    Probing only the shoulder and the top would still report a clean fit
    -- which is why this sweeps and ranks on the worst station instead of
    picking one.

    The tab is built in the Tray's own LOCAL frame (round 51), so it is
    translated up by ``PoweredUpHubCover.PLATE_THICKNESS`` here to match
    the window's world frame before comparing -- the same seating
    ``assemble()`` applies.

    Falsifier: restore the chord window and the worst gap goes to -0.452 mm
    against a nominal tab.
    """
    h = PoweredUpHubHousing()
    t = PoweredUpHubBatteryTray()
    clearance = h._profile.free.radial
    seat = PoweredUpHubCover.PLATE_THICKNESS
    tab = t._build_extraction_tab(+1).translate((0.0, 0.0, seat))
    window = h._build_side_window(+1)

    cz_world = PoweredUpHubBatteryTray.TAB_ROUND_CZ + seat
    zhi_world = PoweredUpHubBatteryTray.TAB_PAD_Z_HI + seat

    worst = None
    for i in range(41):
        z = cz_world + i * (zhi_world + 0.2 - cz_world) / 40.0
        sl = cq.Workplane("XY").box(4.0, 40.0, 0.04).translate((27.6, 0.0, z))
        w, tt = window.intersect(sl), tab.intersect(sl)
        if not w.solids().vals() or not tt.solids().vals():
            continue
        gap = w.val().BoundingBox().ymax - tt.val().BoundingBox().ymax
        if worst is None or gap < worst[1]:
            worst = (z, gap)

    assert worst is not None, "positive control failed: tab and window never overlap in Z"
    z, gap = worst
    assert gap >= clearance - 1e-6, (
        f"side window is {gap:.3f} mm clear of the tab at z = {z:.3f}, "
        f"expected at least the running clearance {clearance:.3f} mm"
    )


def test_side_tab_is_built_at_reference_size():
    """The tab carries no clearance of its own -- it lives on the window.

    Round 41 moved it there (hole, not shaft) and this pins the tab to the
    reference's measured figures, so a future clearance change cannot
    quietly start shrinking the part again. Round 51 moved the tab from
    Cover to :class:`PoweredUpHubBatteryTray`; the pinned figures
    (``TAB_PAD_Y_HALF``, and ``TAB_PAD_Z_HI`` re-based by the Tray's own
    seat offset) are unchanged from the reference's own dimensions.
    """
    bb = PoweredUpHubBatteryTray()._build_extraction_tab(+1).val().BoundingBox()
    assert abs(bb.ymax - PoweredUpHubBatteryTray.TAB_PAD_Y_HALF) < 1e-6
    assert abs(bb.ymin + PoweredUpHubBatteryTray.TAB_PAD_Y_HALF) < 1e-6
    assert abs(bb.zmax - PoweredUpHubBatteryTray.TAB_PAD_Z_HI) < 1e-6


def test_thumb_pad_has_running_clearance_in_its_window():
    """The pad must be able to enter, and then move in, its window.

    Round 40. Before the fix this gap was 0.000 mm on BOTH X edges -- a
    13.600 mm pad cut into a 13.600 mm slot -- because the window was cut to
    the LATCH_WINDOW_X_LO/HI literals rather than to the hook footprint plus
    a running clearance.

    Falsifier, stated up front: shrink the window by any amount and the
    measured gap goes negative; remove the clearance term and it goes to
    exactly zero. The seated-interference test cannot stand in for this one
    -- at zero clearance the two faces are tangent, enclose no volume, and
    that test scores them 0.000 mm^3 and passes.
    """
    h = PoweredUpHubHousing()
    c = PoweredUpHubCover()
    clearance = h._profile.free.radial

    pad = c._build_thumb_pad(+1).union(c._build_pad_end_walls(+1))
    pb = pad.val().BoundingBox()
    win = h._build_finger_windows().intersect(
        cq.Workplane("XY").box(60.0, 40.0, 40.0).translate((30.0, -33.0, 5.0))
    )
    wb = win.val().BoundingBox()

    for name, gap in (("-X", pb.xmin - wb.xmin), ("+X", wb.xmax - pb.xmax)):
        assert gap >= clearance - 1e-9, (
            f"thumb pad {name} edge has {gap:.3f} mm of window clearance, "
            f"expected at least the running clearance {clearance:.3f} mm"
        )


def test_latch_u_crown_has_headroom_under_the_wall():
    """The spring's crown must not be butted against the wall above it.

    Round 40. _build_latch_clearance cut its channel to engagement_band_hi,
    which for this latch geometry is the same number as hook_depth, so the
    wall resumed at exactly the crown's top face. Measured headroom at the
    apex was 0.024 mm (the arc falls away either side, which is the only
    reason it was not exactly zero) against a 0.150 mm running clearance
    everywhere else on this interface. A crown held against the ceiling
    preloads the spring and holds the lid off its seat.

    Falsifier: restore the old `height=lg.engagement_band_hi` and the
    measured headroom drops below the running clearance.
    """
    h = PoweredUpHubHousing()
    c = PoweredUpHubCover()
    clearance = h._profile.free.radial
    lg = c._latch

    u_top = c._build_latch_u(+1).val().BoundingBox().zmax
    x_center = lg.hook_pitch / 2.0 + lg.hook_width / 2.0
    solid = h.solid

    # Only material ABOVE the crown can be the ceiling. Without this bound
    # the column also catches the retention land (z 3.700..4.500), which
    # sits below the crown and reports a spurious -9.300 mm "headroom".
    above = cq.Workplane("XY").box(0.10, 0.10, 40.0).translate(
        (x_center, 0.0, u_top + 20.0))

    worst = None
    for i in range(21):  # sweep the crown in Y; do not hand-pick a station
        y = -34.0 + i * (34.0 - 30.6) / 20.0
        col = above.translate((0.0, y, 0.0))
        hit = solid.intersect(col)
        if not hit.solids().vals():
            continue
        head = hit.val().BoundingBox().zmin - u_top
        if worst is None or head < worst[1]:
            worst = (y, head)

    assert worst is not None, "positive control failed: no housing material above the crown"
    y, head = worst
    assert head >= clearance - 1e-9, (
        f"latch U crown has {head:.3f} mm of headroom at y = {y:.3f}, "
        f"expected at least the running clearance {clearance:.3f} mm"
    )


def test_envelope_is_exactly_72mm_in_x():
    """Post-fix hardening (round 16, Escalation 7): the arm's outboard face
    used to overshoot the exact-copy target by 0.3 mm (72.6 mm measured);
    the housing-local width trim in _build_arm_and_bore_local must pin the
    overall X envelope to exactly 72.0 mm, per Success Criterion #1. A
    regression here (e.g. the trim being dropped or misplaced) would
    silently reopen the overshoot."""
    h = PoweredUpHubHousing()
    bbox = h.solid.val().BoundingBox()
    assert abs(bbox.xlen - 72.0) < 1e-6
    assert abs(bbox.xmax - 36.0) < 1e-6
    assert abs(bbox.xmin + 36.0) < 1e-6


def test_arm_flat_face_matches_real_ldraw_half_width():
    """The arm's own flat outboard face (not just the boss tip) must land
    at the real LDraw half-width (X = 35.6 mm), confirming the width trim
    targets ARM_WIDTH_TRIM_Y (3.6 mm) and not some other boundary."""
    h = PoweredUpHubHousing().solid
    # Probe between the inner and middle hole positions (Y=20, clear of both
    # the pin holes' chamfer rings and the middle-hole boss at Y=24) on the
    # arm's own flat face -- must be solid just inside X=35.6 (the real
    # face) and open just past it (the old, overshot 35.9 mm face this fix
    # removed sat further out again).
    probe_y = 20.0
    assert _probe_material(h, 35.3, probe_y, PoweredUpHubHousing.HOLE_AXIS_Z, size=0.6) > 0.1
    # A small (0.6 mm) probe box well clear of the flat face's own boundary
    # (X=35.6) -- the default 2.0 mm probe would straddle that boundary and
    # register a spurious sliver.
    assert _probe_material(h, 36.5, probe_y, PoweredUpHubHousing.HOLE_AXIS_Z, size=0.6) < 1e-6


def test_root_bridge_band_a_retains_structural_fuse_margin():
    """Post-fix hardening for round 17, Escalation 8: Band A (the arm
    root-bridge's upper Z-slice, global Z in [WALL_STEP_Z, ARM_Z_LO +
    ARM_THICKNESS] = [22.0, 24.0]) is the primary structural fuse (round
    20, H4 gives Band B its own small SEAM_MARGIN reach, but Band A stays
    the deeper, load-bearing one). Independently probe a small material box
    straddling the bridge's own reach depth at a representative Band-A Z
    (WALL_STEP_Z + 1.0, mid-band) on one arm's root -- if this ever comes
    back empty, the two-band split has silently eaten the fuse the
    original root-bridge fix existed to guarantee (design brief's
    ~85.8 mm^3 margin), which is exactly the floating-arm defect this
    project's own regression suite must never let back in silently.
    """
    h = PoweredUpHubHousing().solid

    # One arm's root-bridge region: near global X = 27.0 (inside the
    # bridge's [26.35, 28.1]-ish reach), Y around one hole line (32.0),
    # Z at WALL_STEP_Z + 1.0 -- squarely inside Band A.
    probe_z = PoweredUpHubHousing.WALL_STEP_Z + 1.0
    assert _probe_material(h, 27.0, 32.0, probe_z, size=0.6) > 0.9 * 0.6**3, (
        "Root bridge Band A no longer fills its own structural-fuse region "
        "-- the arm may be floating detached from the wall again "
        "(round 17, Escalation 8's post-fix hardening guard)."
    )


def test_default_preserving_profile_kwarg():
    """Passing an explicit profile object vs. the same profile by name
    produces byte-identical geometry (volume as a cheap proxy)."""
    prof = get_profile("fdm_standard")
    a = PoweredUpHubHousing(profile=prof)
    b = PoweredUpHubHousing(profile="fdm_standard")
    assert abs(a.solid.val().Volume() - b.solid.val().Volume()) < 1e-9


def _x_bands(shape: cq.Workplane, y_lo: float, y_hi: float,
             z_lo: float, z_hi: float) -> list[tuple[float, float]]:
    """The X extent of every separate lump of ``shape`` inside a Y/Z window.

    Reads the tongue interface as a list of bands, which is the shape the
    reference (SS12.2 T1/T2/T3) describes it in: alternating slots and
    ribs across X.
    """
    slab = cq.Workplane("XY").box(
        200.0, y_hi - y_lo, z_hi - z_lo, centered=(True, False, False),
    ).translate((0.0, y_lo, z_lo))
    try:
        lumps = shape.intersect(slab).solids().vals()
    except Exception:
        return []
    return sorted(
        (round(s.BoundingBox().xmin, 3), round(s.BoundingBox().xmax, 3))
        for s in lumps
    )


def test_tongue_ribs_interleave_with_the_cover_tongue_slots():
    """Round 46. The Cover's tongue is four blades with three slots
    between them (SS12.2 T1/T2); this part's ribs are what enters those
    slots. Assert the interleave directly -- one housing rib per Cover
    slot, seated inside it, with the designed running clearance on every
    flank that faces a blade.

    The positive control matters here: a probe that found *no* housing
    material in this window would be indistinguishable from a probe built
    on the wrong plane, so the same helper is first shown to report the
    full-width plate at a station where both parts are known solid.
    """
    clr = get_profile("fdm_standard").free.radial
    hcls = PoweredUpHubHousing
    cover = PoweredUpHubCover(profile="fdm_standard").solid
    housing = PoweredUpHubHousing(profile="fdm_standard").solid

    # -- positive control: the helper reports material where it exists.
    # Sampled at Y 14..16, clear of the side tabs (|Y| <= 12.000), so this
    # reads the plate itself -- half-width PLATE_WIDTH/2 = 27.200. An
    # earlier version sampled Y 10..12 and expected 28.000, which was not
    # the plate at all but the tab pad standing proud of it.
    # Round 59: the printed plate is one running clearance per side narrower
    # than the reference's PLATE_WIDTH, so the control derives from what the
    # Cover actually builds rather than from the reference constant. Hard-
    # coding PLATE_WIDTH/2 here made this control fail the moment the cover
    # gained its clearance -- correctly, since it was asserting a width the
    # part no longer has.
    half = PoweredUpHubCover.PLATE_WIDTH / 2.0 - clr
    control = _x_bands(cover, 14.0, 16.0, 0.2, 1.0)
    assert control == [(-half, half)], (
        f"probe is mis-built -- the Cover's own full-width plate read as {control}"
    )

    # -- the interface itself, in the riser band where both parts meet.
    y_lo, y_hi = PoweredUpHubCover.LEDGE_Y_LO + 0.2, PoweredUpHubCover.TONGUE_STEP_Y - 0.2
    blades = _x_bands(cover, y_lo, y_hi, 0.2, 1.0)
    ribs = _x_bands(housing, y_lo, y_hi, 0.2, 1.0)

    assert len(blades) == 4, f"expected the Cover's four tongue blades, got {blades}"
    assert len(ribs) == 5, (
        f"expected 3 tongue ribs + the 2 shell side walls, got {ribs}"
    )

    # Each of the three slots between consecutive blades holds exactly one
    # rib, clear of both blade flanks by the running clearance.
    slots = [(blades[i][1], blades[i + 1][0]) for i in range(len(blades) - 1)]
    inner_ribs = [r for r in ribs if abs(r[0]) < 27.0 and abs(r[1]) < 27.0]
    assert len(inner_ribs) == len(slots) == 3

    # The outer rib pair merges with the shell side wall into one lump per
    # side, running from the rib's own clearanced inboard edge out to the
    # shell face. Width is asserted, not just presence: round 48's first
    # plate-edge relief cut a slot straight through this band and left a
    # 0.050 mm sliver of it, which a presence-only check would have passed.
    # Round 59: the lid's outer blade retreated by its own fit clearance, so
    # the rib correctly starts one running clearance outboard of where the
    # blade now ends -- not of the nominal 26.000. Derived from the lid's
    # actual edge so this keeps asserting the DESIGNED interleave rather than
    # a stale literal; it still fails if the band is cut into.
    cover_fit = PoweredUpHubCover.fit_clearance(get_profile("fdm_standard"))
    blade_edge = PoweredUpHubCover.RISER_X_HALF - cover_fit
    expected_w = hcls.WALL_X_OUTER_LOWER - blade_edge - clr
    outer = [r for r in ribs if max(abs(r[0]), abs(r[1])) > 27.0]
    assert len(outer) == 2, f"expected the two shell-side lumps, got {outer}"
    for lo, hi in outer:
        assert abs((hi - lo) - expected_w) < 0.05, (
            f"shell-side lump {(lo, hi)} is {hi - lo:.3f} mm wide -- expected "
            f"{expected_w:.3f}, the outer rib fused to the wall, so something "
            "has cut into it"
        )

    for (slot_lo, slot_hi), (rib_lo, rib_hi) in zip(slots, sorted(inner_ribs)):
        assert rib_lo == round(slot_lo + clr, 3), (
            f"rib {rib_lo} does not clear slot wall {slot_lo} by {clr}"
        )
        assert rib_hi == round(slot_hi - clr, 3), (
            f"rib {rib_hi} does not clear slot wall {slot_hi} by {clr}"
        )


# The battery this box exists to hold: Spektrum SPMX812SH2. Every vendor
# lists it as 58 x 32 x 20 mm and rounds 22-46 designed against that; the
# real part measures 20.900 mm tall on a caliper, which is 0.900 mm more.
# The height is the load-bearing figure -- X and Y have >10 mm to spare --
# so it is the one pinned here.
PACK_L, PACK_W, PACK_H = 58.0, 32.0, 20.900


def test_interior_clears_the_target_battery():
    """Round 47 post-fix guard. At ``DECK_THICKNESS = 2.000`` the interior
    was 20.800 mm and the measured pack interfered by 0.100 mm, holding the
    Cover proud of its own latch -- a functional miss that no existing test
    could see, because every one of them checked the two printed parts
    against each other and nothing checked them against their payload.

    Asserted from the built solids rather than from the constants, so a
    future obstruction hung under the deck (a rib, a boss, a port surround)
    fails this too and not just a change to ``DECK_THICKNESS``.
    """
    housing = PoweredUpHubHousing(profile="fdm_standard").solid
    cover = PoweredUpHubCover(profile="fdm_standard").solid
    floor = PoweredUpHubCover.PLATE_THICKNESS

    def clashes(height: float, width: float = PACK_W, length: float = PACK_L) -> float:
        pack = cq.Workplane("XY").box(
            width, length, height, centered=(True, True, False),
        ).translate((0.0, 0.6, floor))
        total = 0.0
        for part in (housing, cover):
            try:
                total += sum(s.Volume() for s in part.intersect(pack).solids().vals())
            except Exception:
                pass
        return total

    # Positive control -- a pack taller than any plausible interior MUST
    # collide, or a mis-placed probe would report "fits" for every input.
    assert clashes(PACK_H + 6.0) > 0.0, (
        "probe is mis-built: an oversized pack reported no collision"
    )

    assert clashes(PACK_H) == 0.0, (
        f"the {PACK_H} mm target pack does not fit -- interior is "
        f"{PoweredUpHubHousing.DECK_Z - PoweredUpHubHousing.DECK_THICKNESS - floor:.3f} mm"
    )

    # And it clears with room, not by a hair -- so a small future encroachment
    # shows up as a failing margin here rather than as a part that binds.
    interior = (PoweredUpHubHousing.DECK_Z
                - PoweredUpHubHousing.DECK_THICKNESS
                - floor)
    assert interior - PACK_H >= 0.25, (
        f"only {interior - PACK_H:.3f} mm of clearance over the target pack"
    )


class _NoPlateEdgeRelief(PoweredUpHubHousing):
    """The housing as it was before round 48 -- relief neutralised.

    Not a shipped variant; it exists so the test below can show its own
    falsifier rather than assert one. The override returns a 0.1 mm cube
    buried inside the deck, so the cut still runs against a real shape and
    the baseline differs in exactly one respect.
    """

    def _build_plate_edge_relief(self) -> cq.Workplane:
        return rounded_box(
            width=0.1, depth=0.1, height=0.1, corner_r=0.0,
            center=(0.0, 0.0, self.DECK_Z - 0.5),
        )


class _ZeroClearanceCover(PoweredUpHubCover):
    """The lid as it was before round 59 -- mating faces on the nominal.

    Its sibling above neutralises the HOUSING's relief; this neutralises the
    LID's own running clearance. Since round 59 both would have to be absent
    for the plate edge to bind, so the falsifier needs both -- with only one
    removed the pair is still clear, and the test would pass while proving
    nothing.
    """

    @classmethod
    def fit_clearance(cls, profile) -> float:
        return 0.0


def test_plate_edge_has_running_clearance_against_the_side_walls():
    """Round 48. ``PLATE_WIDTH/2`` and
    ``WALL_X_OUTER_LOWER - WALL_THICKNESS`` are both 27.200 mm, so before
    the relief the lid had to pass through a slot exactly its own width --
    zero clearance over the full 62.8 mm length.

    Seated interference cannot catch that: two faces that touch without
    overlapping measure 0.000 mm³ exactly as a properly-cleared pair does.
    The falsifier is sideways travel, and it is *demonstrated* here against
    a relief-free baseline rather than merely described.
    """
    clr = get_profile("fdm_standard").free.radial
    cover = PoweredUpHubCover(profile="fdm_standard").solid
    fixed = PoweredUpHubHousing(profile="fdm_standard").solid
    before = _NoPlateEdgeRelief(profile="fdm_standard").solid

    def bind(housing, dx, lid=None):
        moved = (lid if lid is not None else cover).translate((dx, 0.0, 0.0))
        try:
            return sum(s.Volume() for s in housing.intersect(moved).solids().vals())
        except Exception:
            return 0.0

    # Both seat cleanly -- which is exactly why this needed a motion test.
    assert bind(before, 0.0) == 0.0 and bind(fixed, 0.0) == 0.0

    # The falsifier needs BOTH clearances removed as of round 59. The lid now
    # carries its own running clearance, so a relief-free housing alone no
    # longer binds -- the pair is clear because the COVER got narrower, not
    # because the housing was relieved. Stripping the housing's relief and the
    # lid's clearance together restores the original zero-clearance pair and
    # shows the probe can still detect a bind at all.
    #
    # This is also the standing evidence that the housing's round-48 relief is
    # now REDUNDANT: it is no longer what keeps the plate edge free.
    old_lid = _ZeroClearanceCover(profile="fdm_standard").solid
    assert bind(before, clr / 2.0, lid=old_lid) > 0.0, (
        "the zero-clearance pair shows no interference at half the "
        "clearance -- this test can no longer detect the bug it guards"
    )

    # With it, the lid is free right out to the designed allowance, both ways.
    for dx in (clr / 3.0, clr * 2.0 / 3.0, clr):
        for sign in (-1.0, 1.0):
            assert bind(fixed, sign * dx) == 0.0, (
                f"plate edge binds at dX={sign * dx:+.3f}, inside its own "
                f"{clr} mm clearance"
            )

    # And beyond it, it still locates -- the relief is a clearance, not a
    # licence for the lid to wander.
    assert bind(fixed, clr + 0.05) > 0.0, "the lid is no longer located in X"

    # The wall keeps a printable section where it was thinned.
    assert PoweredUpHubHousing.WALL_THICKNESS - clr >= 0.6


def test_cord_port_is_a_clear_opening_into_the_battery_bay():
    """Round 49. The deck opening for the battery lead, sized 20.0 x 10.0
    clear so an EC3-class connector passes and not just an IC2.

    "There is a hole" is not the claim -- **a hole is not a route.** The
    first placement put the slot's -Y edge flush with the latch end wall
    and cut a perfectly good opening that a connector could not descend
    through, because the Cover's latch U reaches Y = -30.700 and Z = 12.160
    into that same channel. So this pushes a solid block down the path a
    connector really takes, against housing AND cover AND a seated pack.

    The expected rectangle is recomputed here from the same constants the
    builder uses, which risks the two drifting apart -- so the position is
    ALSO cross-checked against the built solid (open inside, solid just
    outside). If the builder moves and this arithmetic does not, the
    cross-check fails rather than the sweep silently testing empty air.
    That is not hypothetical: it happened twice while developing this.
    """
    H = PoweredUpHubHousing
    C = PoweredUpHubCover
    housing = PoweredUpHubHousing(profile="fdm_standard").solid
    cover = PoweredUpHubCover(profile="fdm_standard").solid
    pack = rounded_box(width=32.0, depth=58.0, height=PACK_H, corner_r=0.0,
                       center=(0.0, 0.6, C.PLATE_THICKNESS))

    # Round 55e: the port's outboard edge is flush with the UPPER section's
    # inner face, and CORD_PORT_MARGIN is taken entirely INBOARD (outboard
    # it would eat the wall -- see _build_cord_port). So the connector's own
    # nominal footprint sits inset by that margin from the outboard edge,
    # not hard against it: pressed flush against the edge its corners foul
    # CORD_PORT_CORNER_R, which is what the margin exists to avoid.
    x_hi = H.UPPER_X_INNER - H.CORD_PORT_MARGIN
    x_lo = x_hi - H.CORD_PORT_WIDTH
    y_lo = C.LATCH_BAND_Y_HI
    y_hi = y_lo + H.CORD_PORT_LENGTH
    x_c, y_c = (x_lo + x_hi) / 2.0, (y_lo + y_hi) / 2.0
    z_mid = H.DECK_Z - H.DECK_THICKNESS / 2.0

    def deck_solid(x, y):
        b = rounded_box(width=0.3, depth=0.3, height=0.3, corner_r=0.0,
                        center=(x, y, z_mid - 0.15))
        try:
            return bool(housing.intersect(b).solids().vals())
        except Exception:
            return False

    # -- the opening really is where the constants say it is.
    for x, y in ((x_c, y_c), (x_lo + 1.0, y_c), (x_hi - 1.0, y_c),
                 (x_c, y_lo + 1.0), (x_c, y_hi - 1.0)):
        assert not deck_solid(x, y), f"deck is solid inside the port at ({x}, {y})"
    for x, y in ((x_lo - 1.0, y_c), (x_c, y_lo - 1.0), (x_c, y_hi + 1.0)):
        assert deck_solid(x, y), (
            f"deck is open OUTSIDE the port at ({x}, {y}) -- the port is not "
            "where this test thinks it is, so the sweep below proves nothing"
        )

    def sweep(w, l, z_lo, parts=None):
        blk = rounded_box(width=w, depth=l, height=H.DECK_Z - z_lo,
                          corner_r=0.0, center=(x_c, y_c, z_lo))
        total = 0.0
        for part in (parts if parts is not None else (housing, cover, pack)):
            try:
                total += sum(s.Volume() for s in part.intersect(blk).solids().vals())
            except Exception:
                pass
        return total

    # -- positive control: oversized blocks must NOT pass.
    for w, l in ((H.CORD_PORT_WIDTH + 4.0, H.CORD_PORT_LENGTH),
                 (H.CORD_PORT_WIDTH, H.CORD_PORT_LENGTH + 6.0)):
        assert sweep(w, l, H.DECK_Z - H.DECK_THICKNESS) > 0.0, (
            f"a {w} x {l} block passed a {H.CORD_PORT_WIDTH} x "
            f"{H.CORD_PORT_LENGTH} opening -- this probe cannot fail"
        )

    # -- the requested connector clears the slab, and the whole descent.
    assert sweep(H.CORD_PORT_WIDTH, H.CORD_PORT_LENGTH,
                 H.DECK_Z - H.DECK_THICKNESS) == 0.0
    assert sweep(H.CORD_PORT_WIDTH, H.CORD_PORT_LENGTH,
                 C.LATCH_BAND_THICKNESS, parts=(housing, cover)) == 0.0, (
        "the connector clears the deck but fouls on the way down -- a hole "
        "is not a route"
    )

    # -- the channel's own width, which is what the descent above is really
    # about. The PACK is deliberately not an obstacle here (round 55e): it
    # has no X locating feature at all -- the tray's walls are 52.8 mm apart
    # for a 32 mm pack, so it floats +-10.4 mm -- and asserting a
    # sub-millimetre plan clearance against an arbitrary nominal centre is
    # precision this model does not have. What IS located is the wall, so
    # that is what the clearance is measured against.
    #
    # Round 55e narrowed this channel from 10.400 to 10.050 by moving the
    # wall inboard for the cover's 1.000 mm wall. A 10.000 mm connector now
    # has 0.050 mm of slack beside a centred pack, which is worth knowing
    # and is why this assertion is written as a number rather than left
    # implicit in the sweep above.
    channel = H.UPPER_X_INNER - 32.0 / 2.0
    assert channel >= H.CORD_PORT_WIDTH, (
        f"the channel beside the pack is {channel:.3f} mm, narrower than the "
        f"{H.CORD_PORT_WIDTH} mm port it has to carry"
    )

    assert len(housing.solids().vals()) == 1


def test_side_wall_carries_the_trapezoid_mating_socket():
    """Round 50. Philo's side wall has a trapezoidal recess in its OUTER
    face over ``[SOCKET_Z_LO, SOCKET_Z_HI]`` -- the intended register for a
    future cap.

    Rounds 16-49 recessed the wall to the socket floor along its
    whole length, which is the socket's own depth applied everywhere: all
    socket, therefore no socket. So the falsifier is not "is there a
    recess" but "is the recess LOCAL" -- the outer face must sit at
    28.000 outside the trapezoid and 27.200 inside it, at the same height.
    The old geometry reads 27.200 at both stations and fails.

    Positive control first: below the socket both stations must read
    28.000, or the probe is not finding the outer face at all.
    """
    H = PoweredUpHubHousing
    housing = PoweredUpHubHousing(profile="fdm_standard").solid

    def outer_face(y, z):
        """Outermost X carrying material at (y, z), searching the wall band."""
        x = H.WALL_X_OUTER_LOWER + 0.2
        while x > H.UPPER_X_INNER - 0.2:
            b = rounded_box(width=0.08, depth=0.2, height=0.4, corner_r=0.0,
                            center=(x - 0.04, y, z - 0.2))
            try:
                if housing.intersect(b).solids().vals():
                    return round(x, 2)
            except Exception:
                pass
            x -= 0.04
        return None

    z_mid = (H.SOCKET_Z_LO + H.SOCKET_Z_HI) / 2.0     # 23.0, inside the socket band
    y_in = 0.0                                   # inside the trapezoid
    # Outside the trapezoid but INSIDE the arm root at ARM_Y_LO = 12.400 --
    # the clear window is only 1.2 mm wide, and a station past it reads the
    # arm (which reaches X = 36) rather than the wall.
    y_out = (H.SOCKET_Y_HALF_HI + H.ARM_Y_LO) / 2.0    # 11.8

    # -- positive control: below the socket, both stations are plain wall.
    for y in (y_in, y_out):
        below = outer_face(y, H.SOCKET_Z_LO - 2.0)
        assert below is not None and abs(below - H.WALL_X_OUTER_LOWER) < 0.1, (
            f"probe did not find the outer face below the socket at Y={y}: {below}"
        )

    # -- the socket itself: recessed inside, full section outside.
    inside = outer_face(y_in, z_mid)
    outside = outer_face(y_out, z_mid)
    assert inside is not None and outside is not None
    assert abs(inside - H.UPPER_X_OUTER) < 0.1, (
        f"no socket at Y={y_in}, z={z_mid}: outer face reads {inside}, "
        f"expected {H.UPPER_X_OUTER}"
    )
    assert abs(outside - H.WALL_X_OUTER_LOWER) < 0.1, (
        f"the wall is recessed at Y={y_out} too, so the socket is not a "
        f"local feature: outer face reads {outside}, expected "
        f"{H.WALL_X_OUTER_LOWER} -- this is the pre-round-50 geometry"
    )

    # -- it really is a trapezoid: the mouth is wider than the base.
    assert H.SOCKET_Y_HALF_HI > H.SOCKET_Y_HALF_LO
    near_base = outer_face(H.SOCKET_Y_HALF_LO + 0.5, H.SOCKET_Z_LO + 0.2)
    near_mouth = outer_face(H.SOCKET_Y_HALF_LO + 0.5, H.SOCKET_Z_HI - 0.2)
    assert abs(near_base - H.WALL_X_OUTER_LOWER) < 0.1, (
        "the socket has not narrowed at its base -- flanks are not sloped"
    )
    assert abs(near_mouth - H.UPPER_X_OUTER) < 0.1, (
        "the socket has not widened at its mouth -- flanks are not sloped"
    )

    assert len(housing.solids().vals()) == 1


def test_end_walls_carry_the_trapezoid_mating_socket():
    """Round 51. The same molded recess as the side walls, on the two END
    walls -- the other half of the cap register the user asked for.

    Only the Z band and the flank angle transfer from the side walls; the
    half-widths and the depth are separately measured (see
    ``END_SOCKET_X_HALF_LO``). So this test pins the END numbers, not the
    side ones, and it must fail on a part that has the side sockets only.

    The falsifiers, in order:

    * probe cannot see the end wall at all       -> positive control below
    * recess absent                              -> ``inside`` reads 35.600
    * recess not LOCAL (whole face stepped back) -> ``outside`` reads 34.400
    * flanks not sloped                          -> base/mouth read alike
    * recess is a HOLE, not a pocket             -> nothing behind the floor
    """
    H = PoweredUpHubHousing
    housing = PoweredUpHubHousing(profile="fdm_standard").solid
    floor = H.HALF_Y - H.END_SOCKET_DEPTH        # 34.400

    def outer_face(y_sign, x, z):
        """Outermost |Y| carrying material at (x, z), searching the wall."""
        y = H.HALF_Y + 0.2
        while y > floor - 0.6:
            b = rounded_box(width=0.2, depth=0.08, height=0.4, corner_r=0.0,
                            center=(x, y_sign * (y - 0.04), z - 0.2))
            try:
                if housing.intersect(b).solids().vals():
                    return round(y, 2)
            except Exception:
                pass
            y -= 0.04
        return None

    z_mid = (H.END_SOCKET_Z_LO + H.SOCKET_Z_HI) / 2.0        # 23.0
    x_in = 0.0                                          # inside the trapezoid
    x_out = H.END_SOCKET_X_HALF_HI + 2.0                # 18.0, clear of the flank
    assert x_out < H.HOLE_X - H.ARM_THICKNESS / 2.0, (
        "the outside station has drifted into the arm root and would read "
        "the arm rather than the end wall"
    )

    for y_sign in (+1, -1):
        end = "+Y tongue" if y_sign > 0 else "-Y latch"

        # -- positive control: below the socket, both stations are plain wall.
        for x in (x_in, x_out):
            below = outer_face(y_sign, x, H.END_SOCKET_Z_LO - 2.0)
            assert below is not None and abs(below - H.HALF_Y) < 0.1, (
                f"{end}: probe did not find the outer face below the socket "
                f"at X={x}: {below}"
            )

        # -- the socket itself: recessed inside, full section outside.
        inside = outer_face(y_sign, x_in, z_mid)
        outside = outer_face(y_sign, x_out, z_mid)
        assert inside is not None and abs(inside - floor) < 0.1, (
            f"{end}: no socket at X={x_in}, Z={z_mid}: outer face reads "
            f"{inside}, expected {floor}"
        )
        assert outside is not None and abs(outside - H.HALF_Y) < 0.1, (
            f"{end}: the end wall is recessed at X={x_out} too, so the "
            f"socket is not a local feature: outer face reads {outside}"
        )

        # -- it really is a trapezoid: the mouth is wider than the base.
        # Station chosen just outboard of the base half-width, where the
        # 45-degree flank crosses between the two heights.
        x_flank = H.END_SOCKET_X_HALF_LO + 0.5          # 14.5
        assert H.END_SOCKET_X_HALF_LO < x_flank < H.END_SOCKET_X_HALF_HI
        near_base = outer_face(y_sign, x_flank, H.END_SOCKET_Z_LO + 0.2)
        near_mouth = outer_face(y_sign, x_flank, H.SOCKET_Z_HI - 0.2)
        assert near_base is not None and abs(near_base - H.HALF_Y) < 0.1, (
            f"{end}: the socket has not narrowed at its base -- flanks "
            f"are not sloped (reads {near_base})"
        )
        assert near_mouth is not None and abs(near_mouth - floor) < 0.1, (
            f"{end}: the socket has not widened at its mouth -- flanks "
            f"are not sloped (reads {near_mouth})"
        )

        # -- a pocket, not a hole: material must survive behind the floor.
        # Sampled across the footprint rather than at one flattering point;
        # the thinnest place is the top, where only the deck is behind it.
        for x in (0.0, 8.0, 13.0):
            for z in (H.END_SOCKET_Z_LO + 0.3, z_mid, H.SOCKET_Z_HI - 0.3):
                probe = rounded_box(
                    width=0.4, depth=0.3, height=0.2, corner_r=0.0,
                    center=(x, y_sign * (floor - 0.3), z - 0.1),
                )
                assert housing.intersect(probe).solids().vals(), (
                    f"{end}: the socket is a HOLE at X={x}, Z={z} -- nothing "
                    f"behind its floor at |Y| = {floor - 0.3}"
                )

    assert len(housing.solids().vals()) == 1


def test_wall_sockets_stop_at_the_reference_step_not_at_the_deck():
    """Round 55. Both trapezoid sockets take their top from
    ``SOCKET_Z_HI`` (24.000, the reference's own step), NOT from
    ``DECK_Z``, which rose to 29.600 in the same round.

    Why this needs a test rather than a comment: the two constants were the
    SAME number for rounds 50-54, so every existing socket test passes
    under either wiring.

    The discriminating measurement is the socket's MOUTH WIDTH at the step,
    not whether material exists above it -- round 55b's step-in removes the
    wall's outer band above 24.000 anyway, so an "is there wall at X = 27.6
    above the step" probe (this test's first form) cannot tell the two
    wirings apart and passed for the wrong reason.

    The trapezoid runs from ``SOCKET_Y_HALF_LO`` at ``SOCKET_Z_LO`` to
    ``SOCKET_Y_HALF_HI`` at its top. Pinned at 24.000 it reaches the full
    11.200 just under the step. Wired to ``DECK_Z`` the same flanks would
    stretch over 7.600 mm instead of 2.000, so just under the step it would
    have opened to only 9.2 + 2.0 x 1.9 / 7.6 = 9.700 -- a 1.450 mm
    difference this assertion sees and nothing else does.
    """
    H = PoweredUpHubHousing
    housing = PoweredUpHubHousing(profile="fdm_standard").solid
    assert H.SOCKET_Z_HI < H.DECK_Z, (
        "this test is vacuous unless the step and the deck differ"
    )

    z = H.SOCKET_Z_HI - 0.1
    # Slice the wall's OUTER band (the only X range the socket cuts) at a
    # Z just below the socket's top edge. What survives is the wall either
    # side of the socket mouth, so the gap between the two pieces is the
    # mouth itself.
    band = housing.intersect(
        rounded_box(
            width=H.UPPER_INSET,
            depth=4 * H.SOCKET_Y_HALF_HI, height=0.05, corner_r=0.0,
            center=((H.UPPER_X_OUTER + H.WALL_X_OUTER_LOWER) / 2.0, 0.0, z),
        )
    )
    pieces = sorted(
        (sol.BoundingBox() for sol in band.solids().vals()),
        key=lambda bb: bb.ymin,
    )
    assert len(pieces) == 2, (
        f"expected wall either side of the socket mouth, got {len(pieces)} "
        "piece(s) -- positive control failed, the slice is not cutting the "
        "socket band at all"
    )
    mouth_half = (pieces[1].ymin - pieces[0].ymax) / 2.0

    expected = H.SOCKET_Y_HALF_LO + (H.SOCKET_Y_HALF_HI - H.SOCKET_Y_HALF_LO) * (
        (z - H.SOCKET_Z_LO) / (H.SOCKET_Z_HI - H.SOCKET_Z_LO)
    )
    assert abs(mouth_half - expected) < 0.02, (
        f"socket mouth half-width {mouth_half:.3f} at z={z}, expected "
        f"{expected:.3f} -- the trapezoid has been stretched to a different "
        "top edge (DECK_Z would give "
        f"{H.SOCKET_Y_HALF_LO + (H.SOCKET_Y_HALF_HI - H.SOCKET_Y_HALF_LO) * ((z - H.SOCKET_Z_LO) / (H.DECK_Z - H.SOCKET_Z_LO)):.3f})"
    )


def test_interior_clears_the_battery_above_the_tray_floor():
    """Round 55. Rounds 51-54 deliberately did NOT assert this: the tray
    did not fit under a 3-stud deck and asserting a known-false fit would
    just have restated "the height hasn't been revisited yet".

    It has been revisited, so the real question is now answerable and is
    asserted on the BUILT solids: the clear height from the Cover's inner
    face to the Housing's deck underside must exceed the tray floor plus
    the caliper-measured pack.

    Target pack: Spektrum SPMX812SH2, 58 x 32 x 20.9 mm -- 20.900 measured
    on the real part, NOT the 20 mm every vendor lists, which is the error
    that cost round 47 a whole design cycle.
    """
    from vibe_cading.lego_adapters.poweredup_hub.battery_tray import (
        PoweredUpHubBatteryTray,
    )

    PACK_H = 20.900
    housing = PoweredUpHubHousing(profile="fdm_standard").solid
    cover = PoweredUpHubCover(profile="fdm_standard")

    # Deck underside, measured rather than derived: the highest Z at which
    # a probe on the axis still finds no housing material.
    deck_underside = PoweredUpHubHousing.DECK_Z - PoweredUpHubHousing.DECK_THICKNESS
    on_axis = rounded_box(
        width=4.0, depth=4.0, height=0.2, corner_r=0.0,
        center=(0.0, 0.0, deck_underside - 0.3),
    )
    assert not housing.intersect(on_axis).solids().vals(), (
        "positive control failed: the interior is already blocked below "
        "the deck underside, so the clear height below is not what it says"
    )

    interior = deck_underside - cover.PLATE_THICKNESS
    needed = PoweredUpHubBatteryTray.FLOOR_THICKNESS + PACK_H
    assert interior > needed, (
        f"interior {interior:.3f} mm does not clear the tray floor plus "
        f"pack ({needed:.3f} mm) -- short by {needed - interior:.3f}"
    )


def test_shell_steps_in_above_the_reference_step():
    """Round 55b. Above ``REF_STEP_Z`` the reference is a NARROWER box, not
    a continuation of the lower shell, and the trapezoid socket only reads
    as a recess because its top edge meets that step.

    Asserted as a pair at every face -- material just inboard of the upper
    footprint, none just outboard -- because either half alone is
    satisfiable by a broken part: "nothing outboard" passes for a shell
    that stops at the step entirely, and "material inboard" passes for the
    un-stepped extrusion this replaces.
    """
    H = PoweredUpHubHousing
    housing = PoweredUpHubHousing(profile="fdm_standard").solid
    z = (H.REF_STEP_Z + H.DECK_Z - H.DECK_THICKNESS) / 2.0   # mid upper wall

    def material(x, y):
        return housing.val().isInside(cq.Vector(x, y, z), tolerance=1e-9)

    faces = (
        ("+X", (H.UPPER_X_OUTER - 0.2, 0.0), (H.UPPER_X_OUTER + 0.2, 0.0)),
        ("-X", (-H.UPPER_X_OUTER + 0.2, 0.0), (-H.UPPER_X_OUTER - 0.2, 0.0)),
        ("+Y", (0.0, H.UPPER_Y_HI - 0.2), (0.0, H.UPPER_Y_HI + 0.2)),
        ("-Y", (0.0, H.UPPER_Y_LO + 0.2), (0.0, H.UPPER_Y_LO - 0.2)),
    )
    for name, inboard, outboard in faces:
        assert material(*inboard), (
            f"{name}: no wall just inboard of the upper footprint at z={z} "
            "-- positive control failed, so the outboard reading proves nothing"
        )
        assert not material(*outboard), (
            f"{name}: material still outboard of the upper footprint at "
            f"z={z} -- the shell did not step in"
        )

    # ...and BELOW the step the full lower footprint must survive: this cut
    # has no downward overcut precisely so it cannot shave the sockets, the
    # arms (which end at exactly REF_STEP_Z) or the wall step itself.
    #
    # Sampled at X = 22.000, clear of the end socket. Since round 55d
    # UPPER_Y_HI IS the end socket's own floor, so a probe on the part's
    # centreline just outboard of it lands INSIDE that recess and reads
    # empty for a completely legitimate reason -- which is what this
    # assertion did when the roof was extended, failing for the wrong cause.
    below = H.REF_STEP_Z - 0.2
    x_clear = 22.0
    assert x_clear > H.END_SOCKET_X_HALF_HI, (
        "this probe must sit outboard of the end socket's own mouth or it "
        "measures the socket, not the shell"
    )
    assert housing.val().isInside(
        cq.Vector(x_clear, H.UPPER_Y_HI + 1.0, below), tolerance=1e-9
    ), "the step-in cut reached below REF_STEP_Z and ate the lower shell"


def test_upper_section_x_faces_are_the_cover_budget_not_the_reference():
    """Round 55e RENAMED this test, and the rename is the point.

    As ``test_upper_section_x_faces_match_the_reference`` (round 55b) it
    asserted the upper wall sat at the reference's own +-27.200 / +-26.400.
    Round 55e moved it 0.350 mm inboard, to +-26.850 / +-26.050, so a future
    cover gets a 1.000 mm wall instead of 0.650. The assertions were written
    against ``UPPER_X_OUTER`` rather than against literals, so they kept
    passing under the old name -- a test that still went green while its name
    and docstring asserted a reference agreement that had stopped being true.

    What it checks now is what is actually claimed: the wall keeps a normal
    ``WALL_THICKNESS`` section, and its outer face is exactly the cover
    budget's derived inset. The reference comparison it used to make lives in
    ``reference_contracts.toml``'s upper-side-wall row, which measures the
    departure instead of hiding it.
    """
    H = PoweredUpHubHousing
    housing = PoweredUpHubHousing(profile="fdm_standard").solid
    z = (H.REF_STEP_Z + H.DECK_Z - H.DECK_THICKNESS) / 2.0

    section = housing.intersect(
        rounded_box(width=4.0, depth=1.0, height=0.2, corner_r=0.0,
                    center=(H.UPPER_X_OUTER - 0.4, 0.0, z))
    )
    solids = section.solids().vals()
    assert solids, "no upper side wall to measure"
    bb = solids[0].BoundingBox()

    assert abs(bb.xmax - H.UPPER_X_OUTER) < 1e-6, (
        f"upper wall outer face at {bb.xmax:.3f}, cover budget wants "
        f"{H.UPPER_X_OUTER}"
    )
    assert abs(bb.xmin - H.UPPER_X_INNER) < 1e-6, (
        f"upper wall inner face at {bb.xmin:.3f}, expected {H.UPPER_X_INNER}"
    )
    assert abs((bb.xmax - bb.xmin) - H.WALL_THICKNESS) < 1e-6, (
        f"upper wall is {(bb.xmax - bb.xmin):.3f} thick, not the shell's own "
        f"{H.WALL_THICKNESS} -- moving one face without the other"
    )
    # And the departure is real, not accidental: state it, so that reverting
    # UPPER_INSET to the reference's 0.800 fails here rather than silently
    # shrinking the cover's wall back to 0.650.
    assert abs(H.UPPER_X_OUTER - 27.200) > 0.1, (
        "UPPER_X_OUTER is back on the reference's own figure -- the cover's "
        "wall is 0.650 again"
    )


def test_cover_budget_and_socket_floor_stay_inline():
    """Round 55e. The trapezoids exist to register a future cover whose legs
    mate into them and whose outer wall sits FLUSH with this part's side
    walls, so the cover's wall thickness is set entirely by this class:
    ``outer face - (upper section + fit clearance)``.

    The user's requirement is 1.000 mm minimum -- 0.650 (rounds 55b-55d, the
    reference's own inset) is about 1.6 extrusion widths. Asserted on the
    BUILT solid at both faces, not re-derived from the constants that set it,
    since a builder can ignore a constant.

    Also asserts the two things deepening the socket is apt to break, both of
    which it did break in this round before being caught:

    * the wall left BEHIND the socket must stay a normal section -- a 1.150
      recess in a 1.600 wall leaves 0.450;
    * the socket floor must stay INLINE with the upper section, which is what
      makes the recess read as a socket rather than a slot in a flat face.
    """
    H = PoweredUpHubHousing
    housing = PoweredUpHubHousing(profile="fdm_standard").solid

    def outer_face_at(y, z, start, step=-0.01):
        """Scan inward from outside the part for the first material."""
        x = start
        while x > start - 3.0:
            if housing.val().isInside(cq.Vector(x, y, z), tolerance=1e-9):
                return x
            x += step
        return None

    # Long edge: measured at a Z above the step, where the cover's wall sits.
    z_upper = (H.REF_STEP_Z + H.DECK_Z - H.DECK_THICKNESS) / 2.0
    upper_face = outer_face_at(0.0, z_upper, H.WALL_X_OUTER_LOWER + 0.5)
    assert upper_face is not None, "no upper side wall found to measure"
    wall = H.WALL_X_OUTER_LOWER - (upper_face + H.COVER_FIT_CLEARANCE)
    assert wall >= H.COVER_WALL - 1e-6, (
        f"a cover wall of only {wall:.3f} mm fits on the long edge "
        f"(need {H.COVER_WALL})"
    )

    # Short end: the reference's own 1.200 socket depth already exceeds the
    # 1.000 target, so it is left reference-exact rather than moved 0.050.
    end_wall = H.HALF_Y - (H.UPPER_Y_HI + H.COVER_FIT_CLEARANCE)
    assert end_wall >= H.COVER_WALL - 1e-6, (
        f"a cover wall of only {end_wall:.3f} mm fits on the short end"
    )

    # Inline: the socket floor and the upper section are one plane.
    z_socket = (H.SOCKET_Z_LO + H.SOCKET_Z_HI) / 2.0
    socket_floor = outer_face_at(0.0, z_socket, H.WALL_X_OUTER_LOWER + 0.5)
    assert socket_floor is not None, "no socket recess found to measure"
    assert abs(socket_floor - upper_face) < 0.02, (
        f"socket floor at {socket_floor:.3f} is not inline with the upper "
        f"section at {upper_face:.3f} -- the recess reads as a slot"
    )

    # ...and a normal section behind the recess: walk inward from the floor
    # until material stops.
    inner = socket_floor
    while housing.val().isInside(cq.Vector(inner - 0.01, 0.0, z_socket), tolerance=1e-9):
        inner -= 0.01
    assert socket_floor - inner >= H.WALL_THICKNESS - 0.03, (
        f"only {socket_floor - inner:.3f} mm of wall behind the socket "
        f"(expected {H.WALL_THICKNESS}) -- deepening the recess ate its floor"
    )


def test_cord_port_leaves_a_full_wall_section_outboard():
    """Round 55e. The port's outboard edge is flush with the upper wall's
    inner face, so what stands between it and the outside of the part is
    that wall at its full ``WALL_THICKNESS``.

    Written because the fit margin nearly ate it: ``CORD_PORT_MARGIN``
    applied symmetrically pushed the cut 0.300 mm past flush, leaving
    0.500 mm -- about 1.25 extrusion widths -- and no existing test looked
    at the outboard side at all. The margin is now taken inboard only.

    Falsifier: restore the symmetric margin and this drops to 0.500.
    """
    H = PoweredUpHubHousing
    housing = PoweredUpHubHousing(profile="fdm_standard").solid.val()
    z = H.DECK_Z - H.DECK_THICKNESS / 2.0
    y = -20.0     # inside the port's own Y span

    def first_boundary(x_from, x_to, step):
        prev, x = None, x_from
        while (x < x_to) if step > 0 else (x > x_to):
            cur = housing.isInside(cq.Vector(x, y, z), tolerance=1e-9)
            if prev is not None and cur != prev:
                return x
            prev, x = cur, x + step
        return None

    # Walk outward from inside the port: void -> material is the port's
    # outboard edge; material -> void is the roof's outer edge.
    port_edge = first_boundary(H.UPPER_X_INNER - 2.0, H.WALL_X_OUTER_LOWER, 0.005)
    assert port_edge is not None, (
        "positive control failed: no port/roof boundary found -- the probe is "
        "not in the port"
    )
    roof_edge = first_boundary(port_edge + 0.05, H.WALL_X_OUTER_LOWER + 0.5, 0.005)
    assert roof_edge is not None, "no outer roof edge found"

    left = roof_edge - port_edge
    assert left >= H.WALL_THICKNESS - 0.02, (
        f"only {left:.3f} mm of roof outboard of the cord port (expected the "
        f"wall's own {H.WALL_THICKNESS}) -- the fit margin has eaten into it"
    )


def _end_reach(housing, x, z, y_sign):
    """Furthest |Y| carrying material at (x, z), or None."""
    H = PoweredUpHubHousing
    y = y_sign * (H.HALF_Y + 0.5)
    step = -y_sign * 0.002
    # Must span past the round's full pullback (BOTTOM_ROUND_R = 3.600 at
    # Z = 0) or the probe returns None for a correctly-rounded segment and
    # the caller reads that as "no material".
    for _ in range(3000):
        if housing.isInside(cq.Vector(x, y, z), tolerance=1e-9):
            return y
        y += step
    return None


def test_bottom_end_round_follows_the_reference_arc():
    """Round 55f. The shell's bottom edge is rounded into each end plane on
    an arc of ``BOTTOM_ROUND_R``, measured off the reference's own vertices.

    Checked against the reference's measured stations rather than against
    the constants that built it -- re-deriving from ``BOTTOM_ROUND_R`` here
    would only confirm the code agrees with itself.

    Positive control: well above the arc the wall must reach the full
    ``HALF_Y``, so a probe that finds a pullback everywhere (a cutter gone
    wild) fails rather than looking like a very large radius.
    """
    H = PoweredUpHubHousing
    housing = PoweredUpHubHousing(profile="fdm_standard").solid.val()

    # (z, |Y| reached) from tmp/ldraw/curve_fit.py.
    #
    # LATCH END ONLY. Round 56 made the whole tongue end a full-depth arc by
    # user direction, so the tongue end no longer follows the reference's
    # truncated profile ANYWHERE -- not on the side wall (round 55g) and no
    # longer on the ribs either. Asserting reference agreement there would be
    # asserting something the part deliberately is not; the tongue end's own
    # shape is pinned by test_the_tongue_end_is_rounded_all_the_way_across
    # and declared as an accepted deviation in reference_contracts.toml.
    stations = {
        -1: ((0.274, -33.378), (1.054, -34.546), (2.222, -35.326)),
    }
    x_probe = {-1: 24.0}
    for sign in (-1,):
        above = _end_reach(housing, x_probe[sign], 6.0, sign)
        assert above is not None and abs(abs(above) - H.HALF_Y) < 1e-3, (
            f"positive control failed: at Z=6 the wall reads {above}, not the "
            f"full {H.HALF_Y} -- the round is not confined to the bottom"
        )
        for z, y_ref in stations[sign]:
            y = _end_reach(housing, x_probe[sign], z + 0.02, sign)
            assert y is not None, f"no material at X={x_probe[sign]}, Z={z}"
            assert abs(y - y_ref) < 0.06, (
                f"bottom round is off the reference at Z={z}: {y:.3f} vs "
                f"{y_ref:.3f}"
            )


def test_bottom_round_leaves_the_latch_end_middle_square():
    """The user's own qualifier: "on the end with the thumb tabs, only the
    outer segments have the curve."

    Measured on the reference (tmp/ldraw/curve_span.py): at the latch end
    only ``|X|`` 19.200..28.000 is rounded, and square vertices survive at
    ``Y = -35.600`` out at ``X = +-5.600``. So the cut's X bands take no
    overcut -- the one direction in that builder that does not.

    Falsifier: widen ``BOTTOM_ROUND_X_LATCH`` inboard, or give the cutter
    an X overcut, and the centreline stops reaching -35.600.
    """
    H = PoweredUpHubHousing
    housing = PoweredUpHubHousing(profile="fdm_standard").solid.val()

    square = _end_reach(housing, 0.0, 0.05, -1)
    assert square is not None and square < -H.HALF_Y + 0.01, (
        f"the latch end's middle reaches only {square} at Z=0.05 -- it has "
        "been rounded along with the outer segments"
    )

    rounded = _end_reach(housing, 24.0, 0.05, -1)
    assert rounded is not None and rounded > -H.HALF_Y + 0.5, (
        f"the latch end's outer segment reaches {rounded} at Z=0.05 -- it is "
        "still square, so the check above proves nothing by contrast"
    )


def test_the_tongue_end_is_rounded_all_the_way_across():
    """Round 56. User direction, twice: "the tongue side wall should have the
    curve all the way", then "I'm still seeing squares."

    Round 55g read "all the way" as arc DEPTH and gave the two outer rib
    bands the full-depth arc while keeping the reference's band structure.
    That left 47.200 mm of square bottom edge in the four gaps between
    bands. "All the way" is about EXTENT along X: the whole tongue end
    carries one arc now.

    Swept, not sampled at hand-picked stations -- the failure this replaces
    was invisible to a three-station probe precisely because all three
    stations sat on bands that HAD been rounded. The gaps between them were
    what the user could see.

    Positive control: the same sweep is run against the latch end, whose
    middle is square by user direction and by the reference. It must report
    squares -- otherwise a probe that cannot detect a square edge at all
    would "prove" the tongue end rounded.
    """
    H = PoweredUpHubHousing
    housing = PoweredUpHubHousing(profile="fdm_standard").solid.val()
    z = 0.02

    def square_stations(y_sign):
        """X stations where the wall still runs square down to the bed.

        One point per station: material present at the bed AND hard
        against the outer face means the arc never touched this X. That
        is the whole property, and it costs one ``isInside`` rather than
        the ~1800-step march ``_end_reach`` needs to find a reach.
        """
        out = []
        for i in range(141):                      # -28.0 .. +28.0, 0.4 mm
            x = -28.0 + i * 0.4
            y = y_sign * (H.HALF_Y - 0.01)
            if housing.isInside(cq.Vector(x, y, z), tolerance=1e-9):
                out.append(round(x, 3))
        return out

    latch_square = square_stations(-1)
    assert latch_square, (
        "positive control failed: the sweep found NO square station at the "
        "latch end, whose middle is square by user direction -- the probe "
        "cannot tell a square edge from a rounded one, so its verdict on "
        "the tongue end means nothing"
    )
    assert max(abs(x) for x in latch_square) < 6.0, (
        f"the latch end is square out to X={max(abs(x) for x in latch_square)}"
        " -- its outer segments have lost their curve"
    )

    tongue_square = square_stations(+1)
    assert not tongue_square, (
        f"the tongue end still runs square to the bed at X={tongue_square} "
        "-- the arc does not span the full wall"
    )
