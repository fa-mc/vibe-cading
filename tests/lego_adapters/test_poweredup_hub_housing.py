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

import cadquery as cq

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
    assert bbox.zmin == 0.0
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


def test_middle_bore_breaks_through():
    """The three-step middle bore must actually open into the cavity
    (Ø7.2 mm relief) -- not stop blind at the wall's inner face. A probe
    well inside the nominal cavity, on the middle-hole axis line, must be
    empty (open bore continuing through, not blind)."""
    h = PoweredUpHubHousing().solid
    for x_sign in (+1, -1):
        for y_sign in (+1, -1):
            vol = _probe_material(h, x_sign * 22.0, y_sign * 24.0, PoweredUpHubHousing.HOLE_AXIS_Z)
            assert vol < 1e-6, "expected the middle-hole relief to break through into the cavity"


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


def test_side_window_is_the_handle_outline_across_the_whole_round_over():
    """The side window must be the cover's tab outline, offset by the
    clearance -- checked at every Z through the round-over.

    Round 41. The window used to be three straight chords sampled off the
    reference's arc, and a chord lies inside the arc it subtends, so it was
    narrower than the tab at every INTERMEDIATE Z while matching it exactly
    at the sampled ones. The cover paid for that by shrinking its whole tab
    0.320 mm. Probing only the shoulder and the top would still report a
    clean fit -- which is why this sweeps and ranks on the worst station
    instead of picking one.

    Falsifier: restore the chord window and the worst gap goes to -0.452 mm
    against a nominal tab.
    """
    h = PoweredUpHubHousing()
    c = PoweredUpHubCover()
    clearance = h._profile.free.radial
    handle = c._build_side_handle(+1)
    window = h._build_side_window(+1)

    worst = None
    for i in range(41):
        z = PoweredUpHubCover.HANDLE_ROUND_CZ + i * (
            PoweredUpHubCover.HANDLE_PAD_Z_HI + 0.2 - PoweredUpHubCover.HANDLE_ROUND_CZ) / 40.0
        sl = cq.Workplane("XY").box(4.0, 40.0, 0.04).translate((27.6, 0.0, z))
        w, t = window.intersect(sl), handle.intersect(sl)
        if not w.solids().vals() or not t.solids().vals():
            continue
        gap = w.val().BoundingBox().ymax - t.val().BoundingBox().ymax
        if worst is None or gap < worst[1]:
            worst = (z, gap)

    assert worst is not None, "positive control failed: tab and window never overlap in Z"
    z, gap = worst
    assert gap >= clearance - 1e-6, (
        f"side window is {gap:.3f} mm clear of the tab at z = {z:.3f}, "
        f"expected at least the running clearance {clearance:.3f} mm"
    )


def test_side_handle_is_built_at_reference_size():
    """The tab carries no clearance of its own -- it lives on the window.

    Round 41 moved it there (hole, not shaft) and this pins the tab to the
    reference's measured figures, so a future clearance change cannot quietly
    start shrinking the part again.
    """
    bb = PoweredUpHubCover()._build_side_handle(+1).val().BoundingBox()
    assert abs(bb.ymax - PoweredUpHubCover.HANDLE_PAD_Y_HALF) < 1e-6
    assert abs(bb.ymin + PoweredUpHubCover.HANDLE_PAD_Y_HALF) < 1e-6
    assert abs(bb.zmax - PoweredUpHubCover.HANDLE_PAD_Z_HI) < 1e-6


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
