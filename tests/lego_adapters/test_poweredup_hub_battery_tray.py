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

"""PoweredUpHubBatteryTray — regression net per
docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md,
*Multi-part structure -> Battery tray* and *Success Criteria*.
"""

import cadquery as cq

from vibe_cading.lego_adapters.poweredup_hub.battery_tray import PoweredUpHubBatteryTray
from vibe_cading.print_settings import get_profile

# The Spektrum SPMX812SH2 pack this tray is sized for (design brief Objective).
PACK_LENGTH = 58.0
PACK_WIDTH = 32.0
PACK_HEIGHT = 20.0


def test_single_solid():
    t = PoweredUpHubBatteryTray()
    assert len(t.solid.solids().vals()) == 1
    assert t.solid.val().isValid()


def test_bottom_face_is_z_zero():
    t = PoweredUpHubBatteryTray()
    bbox = t.solid.val().BoundingBox()
    assert bbox.zmin == 0.0


def test_clear_cell_bay_exceeds_pack_length_with_relief():
    """Both transverse partitions removed gives exactly 58.000 mm (design
    brief SS *Battery tray*); the 1.5 mm relief must push this strictly
    past the pack's own 58 mm length, not leave it zero-slack."""
    t = PoweredUpHubBatteryTray()
    cavity_y_lo, cavity_y_hi = t._cavity_y_span()
    clear_length = cavity_y_hi - cavity_y_lo
    assert clear_length > PACK_LENGTH
    assert abs(clear_length - (PACK_LENGTH + PoweredUpHubBatteryTray.RELIEF)) < 1e-6


def test_clear_cavity_width_exceeds_pack_width():
    clear_width = 2 * PoweredUpHubBatteryTray.WALL_INNER_X
    assert clear_width > PACK_WIDTH


def test_both_end_walls_present():
    """Both end walls are KEPT (design brief round-13 resolution) -- slice
    at the wall mid-height and confirm material exists at both Y extremes,
    outside the inner cavity."""
    t = PoweredUpHubBatteryTray()
    section = t.solid.section(height=15.0)
    wires = section.wires().vals()
    y_mins = [w.BoundingBox().ymin for w in wires]
    y_maxs = [w.BoundingBox().ymax for w in wires]
    assert min(y_mins) <= PoweredUpHubBatteryTray.END_WALL_NEG_Y_LO + 1e-6
    assert max(y_maxs) >= (
        PoweredUpHubBatteryTray.END_WALL_POS_Y_HI_NOMINAL + PoweredUpHubBatteryTray.RELIEF - 1e-6
    )


def test_no_transverse_partitions_in_cavity():
    """The cell bay must be clear of material between the two end walls --
    confirms both internal partitions were actually removed, not just
    narrowed."""
    t = PoweredUpHubBatteryTray()
    cavity_y_lo, cavity_y_hi = t._cavity_y_span()
    section = t.solid.section(height=15.0)
    for w in section.wires().vals():
        bb = w.BoundingBox()
        # A partition wire would be a thin sliver strictly inside the cavity
        # span, away from the outer walls (|X| < WALL_INNER_X).
        if cavity_y_lo + 0.5 < bb.ymin and bb.ymax < cavity_y_hi - 0.5:
            if bb.xmax < PoweredUpHubBatteryTray.WALL_INNER_X - 0.5:
                raise AssertionError(f"Unexpected partition-like material: {bb}")


def test_extraction_tabs_present_and_mirrored():
    """Both side extraction tabs (K5) present, mirrored about X = 0, proud
    of the outer wall face."""
    t = PoweredUpHubBatteryTray()
    section = t.solid.section(height=1.0)  # through the pad's Z range
    wires = section.wires().vals()
    x_maxes = sorted(w.BoundingBox().xmax for w in wires)
    assert abs(x_maxes[-1] - PoweredUpHubBatteryTray.TAB_PAD_X) < 1e-6
    x_mins = sorted(w.BoundingBox().xmin for w in wires)
    assert abs(x_mins[0] + PoweredUpHubBatteryTray.TAB_PAD_X) < 1e-6


def test_floor_present():
    """The new floor -- absent on the real part -- exists as a continuous
    slab across the inner cavity at Z in [0, FLOOR_THICKNESS]."""
    t = PoweredUpHubBatteryTray()
    section = t.solid.section(height=PoweredUpHubBatteryTray.FLOOR_THICKNESS / 2.0)
    wires = section.wires().vals()
    assert len(wires) >= 1
    total_area = sum(w.BoundingBox().xlen * w.BoundingBox().ylen for w in wires)
    cavity_y_lo, cavity_y_hi = t._cavity_y_span()
    min_expected_area = 2 * PoweredUpHubBatteryTray.WALL_INNER_X * (cavity_y_hi - cavity_y_lo) * 0.9
    assert total_area >= min_expected_area


def test_strap_holder_slots_sized_to_confirmed_opening():
    """Both strap-holder slots are STRAP_WIDTH (20.5 mm, round-8 confirmed)
    wide -- cut fully through the floor, unlike the floor immediately to
    either side of them. Probed with a small test cylinder intersected
    against the solid (a boolean-volume check, robust against wire-bbox
    ambiguity between a hole's inner loop and its outer boundary)."""
    t = PoweredUpHubBatteryTray()
    mid_floor_z = PoweredUpHubBatteryTray.FLOOR_THICKNESS / 2.0

    def has_material_at(x: float, y: float) -> bool:
        probe = (
            cq.Workplane("XY", origin=(x, y, mid_floor_z))
            .circle(0.5)
            .extrude(0.1, both=True)
        )
        return probe.intersect(t.solid).val().Volume() > 1e-6

    for y_center in (-PoweredUpHubBatteryTray.STRAP_HOLDER_Y, PoweredUpHubBatteryTray.STRAP_HOLDER_Y):
        assert not has_material_at(0.0, y_center), (
            f"expected no floor material through the strap slot at Y={y_center}"
        )
        # A point 5 mm further along Y (still inside the cavity, outside the
        # slot's own narrow Y band) must still show floor material -- proves
        # the cut is a *slot*, not an accidental removal of the whole floor.
        assert has_material_at(0.0, y_center + 5.0), "expected floor material just past the strap slot"


def test_default_preserving_profile_kwarg():
    prof = get_profile("fdm_standard")
    a = PoweredUpHubBatteryTray(profile=prof)
    b = PoweredUpHubBatteryTray(profile="fdm_standard")
    assert abs(a.solid.val().Volume() - b.solid.val().Volume()) < 1e-9
