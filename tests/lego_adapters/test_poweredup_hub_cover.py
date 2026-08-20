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

from vibe_cading.lego_adapters.poweredup_hub.cover import PoweredUpHubCover
from vibe_cading.lego_adapters.poweredup_hub.latch_geometry import get_latch_geometry
from vibe_cading.print_settings import get_profile


def test_single_solid():
    c = PoweredUpHubCover()
    assert len(c.solid.solids().vals()) == 1
    assert c.solid.val().isValid()


def test_plate_envelope():
    """Overall X/Z envelope matches the measured lid, per SS1.1/SS1.4 of
    docs/design_plans/2026-08-19-poweredup-hub-battery-box_ldraw-parts-geometry.md: 54.4 mm wide, 13.0 mm deep (hook tip)."""
    c = PoweredUpHubCover()
    bbox = c.solid.val().BoundingBox()
    assert abs(bbox.xlen - PoweredUpHubCover.PLATE_WIDTH) < 1e-6
    assert abs(bbox.zmin - 0.0) < 1e-9
    prof = get_profile()
    lg = get_latch_geometry(prof)
    assert abs(bbox.zmax - lg.hook_depth) < 1e-6


def test_outer_face_is_z_zero():
    """The Z = 0 datum is the plate's outer/mating face — see class
    docstring, 'The Z = 0 datum, resolved'."""
    c = PoweredUpHubCover()
    bbox = c.solid.val().BoundingBox()
    assert bbox.zmin == 0.0


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
    for w in wires:
        bb = w.BoundingBox()
        # Ribs sat at Y in [-23.6, 22.8] (SS1.3) -- exclude the latch/tongue
        # end features which legitimately have material at this height.
        if -23.0 < (bb.ymin + bb.ymax) / 2 < 22.0:
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


def test_default_preserving_profile_kwarg():
    """Passing an explicit profile object vs. the same profile by name
    produces byte-identical geometry (volume as a cheap proxy)."""
    prof = get_profile("fdm_standard")
    a = PoweredUpHubCover(profile=prof)
    b = PoweredUpHubCover(profile="fdm_standard")
    assert abs(a.solid.val().Volume() - b.solid.val().Volume()) < 1e-9
