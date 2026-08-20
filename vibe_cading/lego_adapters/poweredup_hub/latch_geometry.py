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

"""Shared latch-geometry parameters for the Powered Up hub battery box.

This module is the single source of truth for the one mechanism that is
split across two parts of ``docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md``:
:class:`~vibe_cading.lego_adapters.poweredup_hub.cover.PoweredUpHubCover`'s male
cantilever latch fingers (built here, this PR) and the future
``HousingBox``'s female catch pocket (a later PR — the design's *Housing*
task). Per that design's TL round (*Reusable classes -> Q2*), the two halves
do **not** share a generated-geometry class — the male finger is copied
verbatim from the real LEGO lid (``24853``), not parameterised, so a class
that "generates both halves from one contract" cannot earn its keep when one
half is fixed, foreign geometry. What both halves *do* need is to never
drift apart on the numbers that couple them — hence this frozen parameter
object, imported by both.

All dimensions below are read from ``tmp/ldraw-parts-geometry.md`` SS1.4
(LDraw library, CC BY 4.0, author Philippe Hurbain) unless flagged as
*derived*. The derived undercut depth / catch width / ramp angle are the
Housing side's future numbers, computed here (not re-derived per call site)
against the currently active tolerance profile so the two parts can never
silently diverge.
"""

from __future__ import annotations

from dataclasses import dataclass

from vibe_cading.print_settings import ToleranceProfile, get_profile


@dataclass(frozen=True)
class LatchGeometry:
    """One frozen bundle of latch dimensions, shared by Cover and HousingBox.

    Attributes
    ----------
    barb_diameter:
        Cylindrical bead diameter (mm) at the tip of each cantilever hook.
    barb_arc_deg:
        Barb sweep angle (degrees) — LDraw measures 157.5 degrees (7/16 of a
        full circle).
    barb_protrusion:
        How far the barb bead stands proud of the hook arm's own drafted
        face (mm), measured inboard (+Y). **Corrected round 18 (audit
        finding S4, folded into B1)**: derived from the barb's own axis
        (``Y = -32.200``, radius ``1.000`` -> crest ``Y = -31.200``,
        self-consistent with :class:`~vibe_cading.lego_adapters.poweredup_hub.cover.PoweredUpHubCover`'s
        own flat-faceted drafted face at ``HOOK_FACE_Y1 = -32.240``), not
        the earlier ``0.83`` eyeballed estimate -- see the design brief's
        *Round 18 -> B1* for the full derivation.
    hook_width:
        Width of each latch finger across X (mm).
    hook_pitch:
        The clear gap (mm) between the two mirrored hooks' facing edges —
        **not** their centre-to-centre spacing (round-18 audit finding S3;
        both consumers already compute the hooks' true centres correctly as
        ``X = +-(hook_pitch/2 + hook_width/2)``, i.e. +-12.400 mm, not the
        +-hook_pitch/2 = +-5.600 mm this docstring previously implied).
    engagement_band_lo, engagement_band_hi:
        Z span (mm, measured from the plate's outer/mating face) that the
        barb's crest-to-root height covers. A catch must span at least this
        band to make full contact with the bead.
    hook_depth:
        Overall Z depth (mm) of each hook, measured from the outer face —
        how far down the finger extends.
    barb_axis_z:
        Z height (mm) of the barb's cylindrical axis.
    arm_draft_deg:
        Draft angle (degrees) of the hook arm's inboard face.
    undercut_depth:
        Derived — how deep the female catch's undercut pocket must cut
        behind the housing wall's nominal inner face to receive the barb
        with a repeatable, non-press-tight running clearance.
    catch_width:
        Derived — width (mm) of the female catch pocket, sized to clear
        each hook's own side walls during insertion/release without
        rubbing them.
    ramp_angle_deg:
        Derived — lead-in ramp angle (degrees) for the female catch,
        Designer-recommended (not print-test-confirmed) shallow angle for
        an uncertain-deflection compliant beam. See the design brief's
        *Latch catch -- derived design* section for the full reasoning.
    """

    barb_diameter: float
    barb_arc_deg: float
    barb_protrusion: float
    hook_width: float
    hook_pitch: float
    engagement_band_lo: float
    engagement_band_hi: float
    hook_depth: float
    barb_axis_z: float
    arm_draft_deg: float
    undercut_depth: float
    catch_width: float
    ramp_angle_deg: float


def get_latch_geometry(profile: ToleranceProfile | str | None = None) -> LatchGeometry:
    """Build the frozen :class:`LatchGeometry` against a tolerance profile.

    The as-measured male-side numbers (barb, hook width/pitch, engagement
    band, hook depth, draft) are profile-independent constants straight off
    the real LEGO lid. The three *derived* female-side numbers depend on the
    active :class:`~vibe_cading.print_settings.ToleranceProfile` fit grades,
    per the design brief's *Latch catch -- derived design* section:

    - ``undercut_depth = barb_protrusion - profile.slip.radial`` — a
      captured, repeatedly-engaged retention feature is closest to
      ``slip`` semantics (not ``free``, which would remove too much of an
      already-small ~1.0 mm feature; not ``press``, a one-time
      non-releasing fit).
    - ``catch_width = hook_width - 2 * profile.free.radial`` — a lateral
      running clearance during insertion/release, not a retention surface,
      so the more generous ``free`` grade applies.
    """
    prof = get_profile(profile) if isinstance(profile, str) or profile is None else profile

    # Corrected round 18 (audit finding S4, folded into B1): derived from
    # the barb's own axis (Y = -32.200, radius 1.000 -> crest Y = -31.200)
    # against PoweredUpHubCover.HOOK_FACE_Y1 = -32.240 (the model's own flat
    # drafted face at the barb's Z = 12.000, not an extrapolation of the
    # real part's continued taper -- see the design brief's Round 18 -> B1).
    # barb_protrusion = crest_Y - HOOK_FACE_Y1 = -31.200 - (-32.240) = 1.040.
    barb_protrusion = 1.040
    hook_width = 13.600

    return LatchGeometry(
        barb_diameter=2.000,
        barb_arc_deg=157.5,
        barb_protrusion=barb_protrusion,
        hook_width=hook_width,
        hook_pitch=11.200,
        engagement_band_lo=11.0,
        engagement_band_hi=13.0,
        hook_depth=13.000,
        barb_axis_z=12.000,
        arm_draft_deg=2.0,
        undercut_depth=barb_protrusion - prof.slip.radial,
        catch_width=hook_width - 2 * prof.free.radial,
        ramp_angle_deg=30.0,
    )
