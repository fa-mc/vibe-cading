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
    """72.0 x 71.2 x 33.8 mm (X grows to 72.0/72.6ish with the arm bosses;
    Y and Z are exact -- see class docstring's cross-section note)."""
    h = PoweredUpHubHousing()
    bbox = h.solid.val().BoundingBox()
    assert abs(bbox.ylen - 2 * PoweredUpHubHousing.HALF_Y) < 1e-6
    assert abs(bbox.zmin - 0.0) < 1e-9
    assert abs(bbox.zmax - PoweredUpHubHousing.TOP_Z) < 1e-6
    # X grows slightly past the real 72.0 mm because the arm cross-section
    # deliberately keeps the class's own BEAM_WIDTH (7.8 mm), not LDraw's
    # idealised 7.2 mm -- see class docstring.  Assert it's in the right
    # ballpark, not byte-exact to the LDraw figure.
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


def test_latch_catch_zero_interference_with_cover():
    """The mandatory cross-part acceptance check: PoweredUpHubCover, built
    with no transform (already in its seated position -- both classes
    share one Z=0 / Y datum, see class docstring), must not intersect the
    housing at all."""
    h = PoweredUpHubHousing()
    c = PoweredUpHubCover()
    inter = h.solid.intersect(c.solid)
    vol = sum(s.Volume() for s in inter.solids().vals()) if inter.solids().vals() else 0.0
    assert vol < 1e-6, f"Housing/Cover interference volume {vol:.4f} mm^3 -- expected 0"


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


def test_default_preserving_profile_kwarg():
    """Passing an explicit profile object vs. the same profile by name
    produces byte-identical geometry (volume as a cheap proxy)."""
    prof = get_profile("fdm_standard")
    a = PoweredUpHubHousing(profile=prof)
    b = PoweredUpHubHousing(profile="fdm_standard")
    assert abs(a.solid.val().Volume() - b.solid.val().Volume()) < 1e-9
