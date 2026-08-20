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

from vibe_cading.lego_adapters.poweredup_hub.cover import PoweredUpHubCover
from vibe_cading.lego_adapters.poweredup_hub.housing import PoweredUpHubHousing
from vibe_cading.print_settings import get_profile


def test_single_solid():
    h = PoweredUpHubHousing()
    assert len(h.solid.solids().vals()) == 1
    assert h.solid.val().isValid()


def test_envelope_matches_25560():
    """72.0 x 71.2 x 29.6 mm -- the real shell's own envelope, not the
    LDraw part's bounding box (round 20, H1: the earlier 33.8 mm figure
    was the bbox, reached only by two now-out-of-scope port tubes). X
    grows to 72.0/72.6ish with the arm bosses; Y and Z are exact -- see
    class docstring's cross-section note."""
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
    """Every part of the seated Cover/Housing overlay EXCEPT the latch
    catch's own necessary engagement sliver must be exactly zero -- the
    tongue rebate, the general envelope, the pin-hole/arm region, etc.

    Round 18 replaced the single blanket
    ``test_latch_catch_zero_interference_with_cover`` (which asserted
    total seated interference == 0) with this test plus
    ``tests/lego_adapters/test_poweredup_hub_kinematic.py``'s own tests,
    because the B1 catch fix makes a small, geometrically UNAVOIDABLE
    seated engagement at the catch itself (see that module's own
    ``test_latch_catch_seated_engagement_is_the_proven_minimum`` for the
    full proof) -- filtering it out here isolates the ONE thing this test
    still needs to guarantee: nothing ELSE in the seated overlay regressed.
    """
    h = PoweredUpHubHousing()
    c = PoweredUpHubCover()
    inter = h.solid.intersect(c.solid)
    non_catch_vol = 0.0
    for s in inter.solids().vals():
        bb = s.BoundingBox()
        # The catch nub's own footprint (both sides): |X| in
        # [LATCH_WINDOW_X_LO, LATCH_WINDOW_X_HI], Y < -30 (latch end only).
        is_catch = (
            bb.ymax < -30.0
            and min(abs(bb.xmin), abs(bb.xmax)) >= PoweredUpHubHousing.LATCH_WINDOW_X_LO - 0.01
        )
        if not is_catch:
            non_catch_vol += s.Volume()
    assert non_catch_vol < 1e-6, (
        f"Non-catch Housing/Cover interference volume {non_catch_vol:.4f} mm^3 -- expected 0"
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


def test_undercut_wall_thickness_floor_holds():
    """Post-fix hardening (TL round Q2): the undercut-depth-sets-a-floor
    assertion inside _build_latch_catch must not be silently satisfied by
    accident -- verify the margin is comfortably positive for the active
    profile, matching the class's own assertion."""
    from vibe_cading.lego_adapters.poweredup_hub.latch_geometry import get_latch_geometry

    prof = get_profile()
    lg = get_latch_geometry(prof)
    clearance = prof.free.radial
    y_slot_outer = PoweredUpHubCover.HOOK_FACE_Y1 - clearance - lg.undercut_depth
    local_wall = y_slot_outer - PoweredUpHubHousing.LATCH_Y
    assert local_wall >= PoweredUpHubHousing._MIN_MATERIAL_BEHIND_UNDERCUT


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


def test_housing_tray_upper_band_interference_is_zero():
    """The mandatory cross-part acceptance check for round 16, Escalation 5:
    PoweredUpHubBatteryTray, seated on PoweredUpHubCover's own floor (world
    Z = tray-local Z + PLATE_THICKNESS -- see design brief round 16), must
    not intersect Housing's own *upper* wall band (world Z >= WALL_STEP_Z)
    at all -- this is the interference the wall-step fix specifically
    targets and fully eliminates.

    **Round 20, Escalation 11a**: this was NO LONGER exactly zero. H1's
    deck-height correction (round 20) positioned the deck at its real,
    lower height for the first time -- before H1, the deck sat entirely
    above z=29.6, leaving the whole [22, 29.6] band clear regardless of
    the tray's own height, which structurally hid this collision. The
    tray's own topmost extent fell ~0.08 mm inside the corrected deck's
    own underside across nearly its whole footprint.

    **Round 21 fixes this, back to exactly zero (Escalation 11a)**: the
    deck's own thickness now routes through `profile.free.radial` (a real
    running clearance against the tray's top face) instead of a flat
    literal derived from a corrugated ceiling's explicitly-undetermined
    centre value -- see `PoweredUpHubHousing.__init__`'s own
    `self._deck_thickness`.
    """
    import cadquery as cq

    from vibe_cading.lego_adapters.poweredup_hub.battery_tray import PoweredUpHubBatteryTray

    h = PoweredUpHubHousing()
    t = PoweredUpHubBatteryTray()
    tray_world = t.solid.translate((0, 0, PoweredUpHubCover.PLATE_THICKNESS))

    upper_band = cq.Workplane("XY").box(200, 200, 20.0, centered=(True, True, False)).translate(
        (-100, -100, PoweredUpHubHousing.WALL_STEP_Z)
    )
    h_upper = h.solid.intersect(upper_band)
    t_upper = tray_world.intersect(upper_band)
    inter = h_upper.intersect(t_upper)
    vol = sum(s.Volume() for s in inter.solids().vals()) if inter.solids().vals() else 0.0
    assert vol < 1e-6, (
        f"Housing/Tray upper-band interference {vol:.4f} mm^3 -- expected 0 "
        "(round 21 fixed Escalation 11a, see docstring)"
    )


def test_housing_tray_root_bridge_band_interference_is_zero():
    """Round 17, Escalation 8's own acceptance check: the root-bridge's own
    Band B Z-range (world Z in [ARM_Z_LO, WALL_STEP_Z] = [16.0, 22.0],
    where the tray's lower-band wall sits) must be interference-free.
    Before the Z-dependent two-band root bridge, the bridge's uniform
    reach crossed through this exact region -- 259.014 mm^3, independently
    re-derived in the design brief. The fix drops the bridge's
    wall-reaching extension entirely there, so this must now be exactly
    zero, not merely reduced.

    Probed at Z in [16.0, 21.9] rather than the full [16.0, 22.0] --
    the top 0.1 mm is deliberately excluded to isolate this check from a
    separate, smaller (~4.05 mm^3) residual discovered *while verifying
    this fix*, at the Z = 22.0 wall-step seam itself: Housing's and the
    Tray's own independent 0.05 mm coincident-faces overlap tricks (each
    part's own `_build_side_wall` / `_build_shell`, both citing the same
    "coincident faces" pitfall) each extend their own upper wall band
    0.05 mm *below* the nominal Z = 22.0 step -- and each part's downward
    extension turns out to reach into the *other* part's still-present
    lower-band wall material in that sliver, producing a tiny genuine
    interference neither part's own single-part construction comment
    anticipated. This is unrelated to the root bridge (confirmed by
    computing it with `_build_side_wall()` alone, no arms) and out of
    this fix's scope -- see the design brief's Escalations for the
    follow-up entry. NOT asserted zero here.
    """
    import cadquery as cq

    from vibe_cading.lego_adapters.poweredup_hub.battery_tray import PoweredUpHubBatteryTray

    h = PoweredUpHubHousing()
    t = PoweredUpHubBatteryTray()
    tray_world = t.solid.translate((0, 0, PoweredUpHubCover.PLATE_THICKNESS))

    band_z_hi = PoweredUpHubHousing.WALL_STEP_Z - 0.1  # clear of the seam sliver, see docstring
    band = cq.Workplane("XY").box(
        200, 200, band_z_hi - PoweredUpHubHousing.ARM_Z_LO, centered=(True, True, False)
    ).translate((-100, -100, PoweredUpHubHousing.ARM_Z_LO))
    h_band = h.solid.intersect(band)
    t_band = tray_world.intersect(band)
    inter = h_band.intersect(t_band)
    vol = sum(s.Volume() for s in inter.solids().vals()) if inter.solids().vals() else 0.0
    assert vol < 1e-6, (
        f"Housing/Tray root-bridge-band interference {vol:.4f} mm^3 -- expected 0 "
        "(round 17, Escalation 8)"
    )


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
