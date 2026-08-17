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

"""TechnicPinHoleBushing — regression net per
docs/design_plans/2026-08-10-technic-pin-hole-bushing_design.md Tests table.

All numeric expectations are derived from ``get_profile("fdm_standard")`` in
the test body, never as bare literals — a hardcoded ``4.72`` would silently
pass if the OD formula's sign flipped *and* someone edited the constant.
"""

import cadquery as cq
import pytest

from vibe_cading.lego.constants import BEAM_THICKNESS, PIN_HOLE_DIAMETER
from vibe_cading.lego.cutters.technic_pin_hole import (
    TECHNIC_PIN_CB_DEPTH,
    TECHNIC_PIN_CB_DIAMETER,
)
from vibe_cading.lego_adapters.technic_pin_hole_bushing import TechnicPinHoleBushing
from vibe_cading.mechanical.screws.metric import METRIC_SIZES, MetricMachineScrew
from vibe_cading.print_settings import FitGrade, ToleranceProfile, get_profile


# ── Row 1: barrel OD + X/Y bbox-centring ─────────────────────────────────────


@pytest.mark.parametrize("flange", [True, False])
def test_barrel_od_and_xy_centring(flange):
    prof = get_profile("fdm_standard")
    b = TechnicPinHoleBushing(flange=flange, profile=prof)

    expected_od = PIN_HOLE_DIAMETER - 2 * prof.press.radial
    assert abs(b.od - expected_od) < 1e-9

    bbox = b.solid.val().BoundingBox()
    if not flange:
        # Unflanged: the barrel is the only feature, so the overall bbox
        # width equals the barrel OD directly.
        assert abs(max(bbox.xlen, bbox.ylen) - expected_od) < 1e-6
    else:
        # Flanged: the widest cross-section is the flange (Ø7.0), not the
        # barrel — verify the barrel's own cross-section directly instead.
        section = b.solid.section(height=b.length / 2)
        barrel_width = max(w.BoundingBox().xlen for w in section.wires().vals())
        assert abs(barrel_width - expected_od) < 1e-6

    # X/Y-centring (R8) — the bore axis sits on (0, 0) regardless of flange.
    assert abs(bbox.xmin + bbox.xmax) < 1e-6
    assert abs(bbox.ymin + bbox.ymax) < 1e-6


# ── Row 2: sign guard — grade monotonicity ───────────────────────────────────


def test_od_grade_monotonicity_press_gt_slip_gt_free():
    prof = get_profile("fdm_standard")
    od_press = TechnicPinHoleBushing(fit="press", profile=prof).od
    od_slip = TechnicPinHoleBushing(fit="slip", profile=prof).od
    od_free = TechnicPinHoleBushing(fit="free", profile=prof).od
    assert od_press > od_slip > od_free


# ── Row 3: profile plumbing (instance / string / None) + negative radial ────


def test_profile_resolution_instance_string_none():
    prof_instance = get_profile("fdm_standard")
    b_instance = TechnicPinHoleBushing(profile=prof_instance)
    b_string = TechnicPinHoleBushing(profile="fdm_standard")
    b_none = TechnicPinHoleBushing(profile=None)

    assert abs(b_instance.od - b_string.od) < 1e-9
    assert isinstance(b_none.solid, cq.Workplane)


def test_negative_press_radial_yields_true_interference():
    synthetic = ToleranceProfile(
        name="synthetic_negative_press",
        free=FitGrade(radial=0.15),
        slip=FitGrade(radial=0.05),
        press=FitGrade(radial=-0.10),
    )
    b = TechnicPinHoleBushing(fit="press", profile=synthetic)
    assert b.od > PIN_HOLE_DIAMETER


# ── Row 4: bore diameter (M3 clearance convention) ───────────────────────────


def test_bore_diameter_matches_m3_clearance_convention():
    # Default bore_fit is "slip" (snug, no-rattle clearance) — NOT "free".
    prof = get_profile("fdm_standard")
    length = BEAM_THICKNESS
    b = TechnicPinHoleBushing(length=length, profile=prof)
    assert b.bore_fit == "slip"

    m3_clearance = MetricMachineScrew.from_size("M3", length=length).clearance_diameter
    expected_as_cut_bore = m3_clearance + 2 * prof.slip.radial

    # Verified from the through-hole cross-section.
    section = b.solid.section(height=b.barrel_length / 2)
    bore_wire = min(section.wires().vals(), key=lambda w: w.BoundingBox().xlen)
    measured_bore = bore_wire.BoundingBox().xlen
    assert abs(measured_bore - expected_as_cut_bore) < 1e-6
    assert measured_bore < b.od


def test_bore_grade_monotonicity_press_gt_slip_gt_free():
    # Ordinary female/void ordering (NOT inverted like the OD's `fit`):
    # a tighter bore grade means MORE material removed, i.e. a LARGER bore.
    prof = get_profile("fdm_standard")
    bore_press = TechnicPinHoleBushing(bore_fit="press", profile=prof).bore_nominal
    # bore_nominal itself doesn't vary with bore_fit — verify via the as-cut
    # diameter (nominal + 2*grade.radial) instead.

    def as_cut(bore_fit):
        b = TechnicPinHoleBushing(bore_fit=bore_fit, profile=prof)
        return b.bore_nominal + 2 * getattr(prof, bore_fit).radial

    assert as_cut("free") > as_cut("slip") > as_cut("press")
    assert bore_press == MetricMachineScrew.from_size("M3", length=1.0).clearance_diameter


def test_fit_and_bore_fit_are_independent():
    prof = get_profile("fdm_standard")
    # Changing bore_fit must not move the OD, and vice versa.
    od_default = TechnicPinHoleBushing(profile=prof).od
    od_with_free_bore = TechnicPinHoleBushing(bore_fit="free", profile=prof).od
    assert abs(od_default - od_with_free_bore) < 1e-9

    def as_cut_bore(fit, bore_fit):
        b = TechnicPinHoleBushing(fit=fit, bore_fit=bore_fit, profile=prof)
        return b.bore_nominal + 2 * getattr(prof, bore_fit).radial

    assert abs(as_cut_bore("press", "slip") - as_cut_bore("free", "slip")) < 1e-9


# ── Row 4b: bore-vs-barrel guard ─────────────────────────────────────────────


def test_oversized_bore_nominal_diameter_raises():
    with pytest.raises(ValueError):
        TechnicPinHoleBushing(bore_nominal_diameter=6.0, profile="fdm_standard")


def test_m4_on_free_fit_boundary_raises():
    # bore_fit explicitly "free" (the loosest/largest-bore grade) to make
    # this boundary deterministic regardless of the default bore_fit grade.
    m4_clearance = METRIC_SIZES["M4"]["clearance"]
    with pytest.raises(ValueError):
        TechnicPinHoleBushing(
            fit="free",
            bore_fit="free",
            bore_nominal_diameter=m4_clearance,
            profile="fdm_standard",
        )


def test_valid_bore_override_does_not_raise():
    # A non-default nominal that still clears the barrel wall must not raise.
    TechnicPinHoleBushing(bore_nominal_diameter=3.2, profile="fdm_standard")


# ── Row 5: length default + override ─────────────────────────────────────────


def test_default_length_equals_beam_thickness():
    b = TechnicPinHoleBushing(profile="fdm_standard")
    assert b.length == BEAM_THICKNESS


def test_length_override_produces_exact_total_span():
    # `length` is the TOTAL span (flange nested within it) — see the class
    # docstring's Origin/datum section — so the overall bbox height, not
    # bbox.zmax alone, must equal `length`.
    b = TechnicPinHoleBushing(length=15.6, profile="fdm_standard")
    bbox = b.solid.val().BoundingBox()
    assert abs((bbox.zmax - bbox.zmin) - 15.6) < 1e-6
    # Flanged by default: the flange consumes the first flange_thickness mm.
    assert abs(bbox.zmin - (-b.flange_thickness)) < 1e-6
    assert abs(bbox.zmax - (15.6 - b.flange_thickness)) < 1e-6


def test_length_override_unflanged_zmax_equals_length():
    b = TechnicPinHoleBushing(length=15.6, flange=False, profile="fdm_standard")
    bbox = b.solid.val().BoundingBox()
    assert abs(bbox.zmax - 15.6) < 1e-6
    assert abs(bbox.zmin - 0.0) < 1e-6


def test_non_positive_length_raises():
    with pytest.raises(ValueError):
        TechnicPinHoleBushing(length=0.0, profile="fdm_standard")
    with pytest.raises(ValueError):
        TechnicPinHoleBushing(length=-5.0, profile="fdm_standard")


def test_non_positive_flange_thickness_raises_only_when_flanged():
    with pytest.raises(ValueError):
        TechnicPinHoleBushing(flange=True, flange_thickness=0.0, profile="fdm_standard")
    with pytest.raises(ValueError):
        TechnicPinHoleBushing(flange=True, flange_thickness=-1.0, profile="fdm_standard")
    # A non-positive flange_thickness is irrelevant (and harmless) when
    # flange=False — the flange disc is never built.
    TechnicPinHoleBushing(flange=False, flange_thickness=0.0, profile="fdm_standard")


# ── Row 6: .solid contract ────────────────────────────────────────────────────


def test_solid_is_workplane_idempotent_single_solid():
    b = TechnicPinHoleBushing(profile="fdm_standard")
    s1 = b.solid
    s2 = b.solid
    assert isinstance(s1, cq.Workplane)
    assert isinstance(s2, cq.Workplane)
    assert len(s1.solids().vals()) == 1


# ── Row 7: profile default resolves with no explicit argument ───────────────


def test_default_construction_resolves_profile_without_raising():
    b = TechnicPinHoleBushing()
    assert isinstance(b.solid, cq.Workplane)


# ── Row 9: total-span invariance under the flange flag ──────────────────────
# NOTE: earlier revisions of this class kept the *barrel's* Z-extent
# invariant under `flange` (toggling the flag only added/removed material
# below Z=0). Human feedback after printing/fitting the part changed this:
# `length` is now the TOTAL insertion depth (matching e.g. one beam
# thickness), with the flange nested inside that span rather than added on
# top of it — so it's the TOTAL span, not the barrel length, that must stay
# invariant under the flag. See the class docstring's Origin/datum section.


def test_total_span_invariant_under_flange_flag():
    prof = get_profile("fdm_standard")
    length = BEAM_THICKNESS
    flange_thickness = 0.8

    b_flanged = TechnicPinHoleBushing(
        length=length, flange=True, flange_thickness=flange_thickness, profile=prof
    )
    b_unflanged = TechnicPinHoleBushing(length=length, flange=False, profile=prof)

    for b in (b_flanged, b_unflanged):
        bbox = b.solid.val().BoundingBox()
        # Total Z-span is `length` in both configurations...
        assert abs((bbox.zmax - bbox.zmin) - length) < 1e-6
        # ...but the barrel's own extent (zmax, since flange only ever
        # occupies Z <= 0) is NOT invariant — it shrinks by flange_thickness
        # when the flange is nested inside the same total span.
    assert abs(b_flanged.solid.val().BoundingBox().zmax - (length - flange_thickness)) < 1e-6
    assert abs(b_unflanged.solid.val().BoundingBox().zmax - length) < 1e-6

    assert abs(b_flanged.solid.val().BoundingBox().zmin - (-flange_thickness)) < 1e-6
    assert abs(b_unflanged.solid.val().BoundingBox().zmin - 0.0) < 1e-6

    # Cross-section near each barrel's own mid-span has the same outer
    # radius in both — the OD formula itself is unaffected by the flange.
    section_flanged = b_flanged.solid.section(height=(length - flange_thickness) / 2)
    section_unflanged = b_unflanged.solid.section(height=length / 2)
    outer_flanged = max(w.BoundingBox().xlen for w in section_flanged.wires().vals())
    outer_unflanged = max(w.BoundingBox().xlen for w in section_unflanged.wires().vals())
    assert abs(outer_flanged - outer_unflanged) < 1e-6


def test_length_leq_flange_thickness_raises():
    with pytest.raises(ValueError):
        TechnicPinHoleBushing(length=0.8, flange=True, flange_thickness=0.8, profile="fdm_standard")
    with pytest.raises(ValueError):
        TechnicPinHoleBushing(length=0.5, flange=True, flange_thickness=0.8, profile="fdm_standard")


# ── Row 10: flange bounds vs. live constants + guard ─────────────────────────


def test_flange_od_bounds_against_live_constants():
    # The default flange sinks into the standard Technic pin-hole
    # counterbore: wider than the through-hole (so it catches on the step)
    # but narrower than the counterbore itself (so it sinks below the
    # beam's flat outer face rather than standing proud on top of it).
    prof = get_profile("fdm_standard")
    b = TechnicPinHoleBushing(profile=prof)
    assert b.flange_od > PIN_HOLE_DIAMETER
    assert b.flange_od < TECHNIC_PIN_CB_DIAMETER
    assert b.flange_od > b.od


def test_default_flange_thickness_fits_under_counterbore_depth():
    b = TechnicPinHoleBushing(profile="fdm_standard")
    assert b.flange_thickness < TECHNIC_PIN_CB_DEPTH


def test_oversized_flange_od_warns_but_does_not_raise():
    with pytest.warns(UserWarning, match="counterbore diameter"):
        b = TechnicPinHoleBushing(flange_od=TECHNIC_PIN_CB_DIAMETER, profile="fdm_standard")
    assert isinstance(b.solid, cq.Workplane)


def test_overthick_flange_warns_but_does_not_raise():
    with pytest.warns(UserWarning, match="counterbore depth"):
        b = TechnicPinHoleBushing(
            flange_thickness=TECHNIC_PIN_CB_DEPTH + 0.5, profile="fdm_standard"
        )
    assert isinstance(b.solid, cq.Workplane)


def test_flange_od_leq_od_raises():
    prof = get_profile("fdm_standard")
    od = TechnicPinHoleBushing(profile=prof).od
    with pytest.raises(ValueError):
        TechnicPinHoleBushing(flange=True, flange_od=od, profile=prof)
