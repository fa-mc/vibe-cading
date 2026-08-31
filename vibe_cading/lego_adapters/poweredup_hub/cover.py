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

"""PoweredUpHubCover -- battery-bay lid for the Powered Up hub battery box.

Dimensions are read from the LDraw parts library (CC BY 4.0, author
Philippe Hurbain) part ``24853`` ("Electric Technic Battery Holder Cover"),
as extracted in
``docs/design_plans/2026-08-19-poweredup-hub-battery-box_ldraw-parts-geometry.md``
SS1 (no LDraw ``.dat`` file, converted geometry, or render is committed to
this repo -- only independently-written measurements and from-scratch
CadQuery code).
Full design rationale:
``docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md``,
*Multi-part structure -> Cover*.

Per that design, this is an exact copy of the real lid with exactly **one**
deletion (the three inner AA-cell divider ribs) and no added geometry -- the
15 outer through-slots are additionally closed (left un-cut, i.e. simply not
modelled), per the design's round-13 user decision.
"""

from __future__ import annotations

import cadquery as cq

from vibe_cading.cq_utils import rounded_box
from vibe_cading.lego_adapters.poweredup_hub.latch_geometry import (
    LatchGeometry,
    get_latch_geometry,
)
from vibe_cading.print_settings import ToleranceProfile, get_profile


class PoweredUpHubCover:
    """Exact copy of LEGO lid ``24853``, minus the three AA-cell divider ribs.

    Origin / datum
    ---------------
    ``(0, 0, 0)`` is the plate's **outer (bottom) face** -- simultaneously
    the LEGO-mating reference, the print-bed face, and the assembly datum
    (design brief, *Cover -- The Z = 0 datum, resolved*). Every feature
    extrudes ``+Z`` from there. X is centred on the plate's mid-width
    (symmetric, ``+-PLATE_WIDTH/2``). Y follows the real lid's own asymmetric
    frame: the **latch end** (cantilever hooks) sits at the plate's negative-Y
    edge and the hooks extend further into ``-Y``; the **tongue / insertion
    end** sits at the plate's positive-Y edge and the tongue extends further
    into ``+Y``. This matches ``docs/design_plans/2026-08-19-poweredup-hub-battery-box_ldraw-parts-geometry.md``'s own
    recommended CadQuery mapping (SS0), which this class's constants are
    read directly from.

    Kept, as measured (design brief K1-K4, minus the ribs):
        - The flat 1.2 mm plate and its sharp-cornered rectangular outline,
          with the local 1.2->2.0 mm thickening band at the latch end.
        - Both cantilever latch fingers with their Ø2.000 mm barbs (K1).
        - The slide-in tongue / ledge at the insertion end (K2), simplified
          to a single uniform-thickness blade -- see *Known simplifications*
          below.
        - **(Removed round 22)** A locating groove near the tongue end
          registered the old BatteryTray's 1.600 mm bottom rim. It was a
          tray-to-lid interface, not a lid-to-housing one, so deleting the
          tray deleted its only mate; the land went with it.

    Deleted (the one named deviation, design brief O1/O2):
        - The three inner-face AA-cell divider ribs and their flank gussets.

    Closed (round 13 user decision, design brief K4):
        - The 15 outer through-slots -- simply never cut, leaving a plain
          flat plate apart from the latch/tongue features.

    Known simplifications (documented deviations from the LDraw source,
    all cosmetic / non-load-bearing unless noted -- flagged per this
    project's Experimental Integrity convention rather than silently
    applied):
        - **Latch finger -- the full cantilever U is now built (round 18,
          B2)**, correcting an earlier version that modelled only the hook
          leg. The real part's second leg (the pressable "thumb pad" outer
          skin, joined to the hook leg only at the crown -- its own tip --
          never at the root) is the compliant member's *other half*, not a
          cosmetic ergonomics detail: see :meth:`_build_release_leg` for
          the geometry and the class-level *Release leg / U-spring*
          constants below for the Developer-derived dimensions (the real
          part's own leg cross-section is not directly measurable from
          LDraw -- see that method's own docstring for the numbers this
          implementation chose and why). **Cross-section corrected round
          20 (findings C1/C2/C3)**: the round-18 version was a straight,
          constant-thickness (0.500 mm) wall flush with Housing's own
          outer wall (Y = -35.600 mm) -- a Developer guess made without
          reference data for this feature. The whole-part comparison found
          the real leg is a slanted, variable-thickness blade
          (0.7-1.05 mm) whose outer face never reaches past Y = -34.063 mm;
          the corrected profile (:attr:`_LEG_OUTER_Y` / :attr:`_LEG_THICKNESS`)
          reproduces the reference's own exact ray-crossing coordinates.
          **Round 21 (finding RC1)** prepends the reference's own
          flared-foot points below Z = 2.0 (see :attr:`_LEG_OUTER_Y`'s own
          note) -- this departure had never been declared at all until
          this round; it is larger than the crown's own declared
          deviation and sits at the leg's structurally more important
          root, not its tip. See those constants' own note for the one
          place (near the crown, Z > 11.0 mm) this implementation
          deliberately does NOT follow the reference's own trend.
          **Round 21 (finding RC3) re-justifies that crown hold**: the
          originally-stated reason ("avoids a hook-leg collision") does
          not survive -- the rebuilt leg collides with the *housing*
          instead (Escalation 11c ⑴), not the hook leg the original
          justification named. The flat hold is kept anyway, on
          corrected grounds: it is a bounded shape simplification
          (max 0.982 mm deviation, concentrated at the very tip), it
          moves the leg's compliance in the *stiffening* direction (safe
          for retention, unquantified for insertion force), and -- once
          Escalation 11c ⑴ is fixed at its own root cause (the catch's
          Y-reach, in :class:`~vibe_cading.lego_adapters.poweredup_hub.housing.PoweredUpHubHousing`) --
          introduces no interference of its own. No geometry change here;
          this is a correction to the *stated reason*, not the shape.
        - The barb's true R1.000 mm cylindrical bead (157.5 deg arc) is
          approximated as a faceted (straight-edged) crest at the same
          position and protrusion, not a true arc -- a cosmetic rounding
          simplification, consistent with this project's chamfer/fillet
          simplification convention (see CLAUDE.md, *Reverse-engineering
          from STEP files*). **Re-opened per round 18's own note (finding
          C1)**: cosmetic only as long as nothing touches the barb crest;
          now that :class:`~vibe_cading.lego_adapters.poweredup_hub.housing.PoweredUpHubHousing`'s
          corrected catch (B1) does engage it, the facet-vs-arc difference
          is a genuine (if small) shape simplification at the mating
          surface, still judged non-blocking (max radial error < 0.03 mm).
        - The tongue's distal *tip* (the actual 0.926 mm-thick, |X| <=
          TONGUE_X_HALF = 15.600 mm retention blade) is modelled as one
          uniform *thickness* spanning the full measured tongue-to-ledge Y
          range. (The 6 locating teeth and the notches between them are no
          longer a simplification -- round 22 restored them in full; see
          :attr:`TOOTH_X_BANDS`.)
        - **Tongue segmentation -- no longer a simplification either
          (round 45).** Rounds 18-44 built the tongue as one continuous
          slab across the width; the reference is four separate blades
          (|X| in [0.800, 15.600] and [17.200, 26.000]) with 1.600 mm gaps
          that receive the housing's own locating ribs. The gaps are now
          cut -- see :attr:`TONGUE_GAP_X_INNER`. Measured over the tongue
          region against the reference, worst-direction surface agreement
          went 91.2% -> 98.8%; the residual that the slab carried sat
          exactly on the four blade boundaries, which is what the earlier
          rounds read as "reinforcements at both edges".
          **Mirrored on the Housing in round 46**, which was the other
          half of this: ``PoweredUpHubHousing._build_tongue_ribs`` now
          builds the three mirrored rib pairs that enter these slots, so
          the reference's +-X location at this end (SS12.2's "Sideways ->
          located") is present rather than merely implied by a slot with
          nothing in it. Each flank carries ``profile.free.radial``
          clearance, measured: the ribs contribute no interference to a
          sideways displacement within that clearance and a growing one
          beyond it, and none at all to withdrawal along -Y. The lap
          retention, which is what the tongue is for, is unaffected
          either way -- it bears on the ledge in Z.
        - **Tongue B's own plan-outline footprint restored (round 20,
          finding C4, supersedes round 18's "just document it" triage).**
          Round 18 (finding S6) omitted Tongue B (the outer pair,
          |X| 17.2..26.0 mm) outright, reasoning retention was preserved
          via Tongue A alone -- correct for retention, but the omission
          left a 1.378 mm gap in the plate's own plan outline over 17.6 mm
          of width, large enough that the whole-part comparison's own
          end-to-end verdict singled it out. The **riser** (full-thickness,
          fused to the plate) now extends to :attr:`RISER_X_HALF`
          (26.000 mm) over its own Y span (:attr:`PLATE_Y_HI` to
          :attr:`TONGUE_STEP_Y`), matching Tongue A's already-correct edge
          -- this is purely a plan-outline restoration; the thin distal
          *tip* stays at the narrower :attr:`TONGUE_X_HALF` (15.600 mm),
          since Tongue B's own retention-critical tip footprint was never
          the gap (only its riser-level plan outline was). **Round 21
          (finding RC4) corrects the Z-extent of that restoration**: round
          20 built the whole restored width at the full riser height
          (2.800 mm), over-correcting Tongue B's own outer band (|X| in
          [:attr:`TONGUE_X_HALF`, :attr:`RISER_X_HALF`]) -- the reference
          has plain :attr:`PLATE_THICKNESS` (1.200 mm) plate there, not a
          riser; only Tongue A's own |X| <= :attr:`TONGUE_X_HALF` band is
          a genuine full-height riser. :meth:`_build_tongue` now builds
          the outer band at plate thickness only, on the tongue's own
          mating face.
        - **Locating land -- gone (round 22).** Rounds 18-21 built a
          raised registration land (plate locally 1.600 mm thick over Y in
          [30.0, 31.2]) matching the old BatteryTray's own bottom-rim
          thickness. With the tray deleted the land registers nothing, so
          it was removed rather than left as a bump with no mate.
        - **Side handle -- gone (round 51).** Round 22 re-homed the tray's
          own extraction tab onto this class as a stand-in, once the tray
          was deleted. Round 51 resurrects
          :class:`~vibe_cading.lego_adapters.poweredup_hub.battery_tray.PoweredUpHubBatteryTray`
          and moves the tab back onto it -- a return to the real reference's
          own division of labour (24849 carries the tab, 24853 never did).
          This class no longer builds one.

    Parameters
    ----------
    profile:
        Manufacturing tolerance profile, used only by the locating groove's
        registration clearance and the shared
        :class:`~vibe_cading.lego_adapters.poweredup_hub.latch_geometry.LatchGeometry`
        (whose *male*-side numbers this class consumes as fixed constants --
        only the shared parameter object's *derived* female-side numbers are
        profile-dependent, and this class does not build those). Accepts a
        :class:`~vibe_cading.print_settings.ToleranceProfile` instance, a
        profile name string, or ``None`` for the process-global default.
    """

    # --- Plate -- RE-DATUMED round 60 to the REAL part ---------------------
    # Source is no longer LDraw 24853. Calipers on the physical cover
    # (docs/design_plans/2026-08-28-poweredup-hub_physical-measurements.md)
    # give a plate 52.33 wide where LDraw draws exactly 54.400 -- a 2.07 mm
    # error, far outside anything tolerance explains. The LDraw figures were
    # verified three independent ways (raw .dat in LDU, converted mesh, STEP)
    # and agree with each other while disagreeing with the hardware, so the
    # pipeline was never the problem; the reference is simply wrong here.
    #
    # These values carry NO added clearance and must not have any applied on
    # top. They were measured on a real mating pair, so the working fit is
    # already inside them: 52.33 in a 52.96 cavity is 0.315 mm per side.
    PLATE_WIDTH = 52.330
    # Length 61.900 measured excluding tongues. Taken off the LATCH end,
    # holding PLATE_Y_HI, because the tongue end's own protrusion is pinned
    # by the 63.600 "including tongues" reading (63.600 - 61.900 = 1.700).
    #
    # CAUTION, recorded rather than smoothed over: 61.900 is 0.240 mm LONGER
    # than the measured housing cavity (61.660) it sits in, which cannot be
    # right for a part that assembles. The width pair reconciles cleanly, so
    # this is specific to the length -- most likely a different datum (draft,
    # rim, or a ledge the plate rests on). Using the measured figure for this
    # print test; re-measure before treating it as settled.
    # ROUND 61 -- re-datumed from the printed part. The owner printed round 60
    # and measured the body (tongues excluded) at 59.800, against the 62.800
    # built here. The earlier 61.900 reading is superseded: it never
    # reconciled with the 61.660 cavity it has to sit inside, and 59.800 does
    # (0.930 mm per end). That the unconfirmed figure was the one that would
    # not close is the corroboration.
    #
    # Taken off the LATCH end, holding PLATE_Y_HI, because the tongue end is
    # pinned twice over: it is the class's stated Y datum, and the tongue's
    # own protrusion is measured FROM this edge (see TONGUE_Y_HI).
    #
    # Rounds 59-60 refused to move this edge because it translates the ENTIRE
    # latch assembly -- U, bead, thumb pad, end walls, all written against the
    # old edge -- and moving the edge alone left the finger short of the plate.
    # That coupling is now handled properly by LATCH_DATUM_Y below instead of
    # being a reason not to move: the latch constants keep their reference
    # provenance and the assembly rides along.
    PLATE_Y_LO = -27.800  # = PLATE_Y_HI - 59.800 (measured, round 61)
    PLATE_Y_HI = 32.000   # tongue-end plate edge, held as the datum
    # The plate edge every latch constant below was MEASURED against. The
    # latch sub-assembly is built in that frame and translated to wherever
    # PLATE_Y_LO now sits, so re-datuming the lid's length never again means
    # editing a column of reference measurements (and losing what they record).
    LATCH_DATUM_Y = -30.800
    PLATE_THICKNESS = 1.200

    # --- Side-window sill (round 55) -- see _build_window_sill. ---
    # The extraction tab's own half-width, in the frame this class and the
    # window share. Hardcoded, not imported from
    # PoweredUpHubBatteryTray.TAB_PAD_Y_HALF, because that class imports
    # THIS one and the reverse import would cycle -- the same reason
    # PoweredUpHubHousing carries its own reference-measured WINDOW_Y_HALF.
    # Housing asserts that its window and the tray's tab still describe one
    # feature (_build_side_window); this constant must track the same
    # number, and test_window_sill_matches_the_tab_width holds it to that
    # by measuring the built Tray rather than trusting this comment.
    WINDOW_SILL_Y_HALF = 12.000

    # --- Latch-end local thickening band (SS1.4) ---
    LATCH_BAND_Y_LO = -30.800
    LATCH_BAND_Y_HI = -30.000
    LATCH_BAND_THICKNESS = 2.000

    # --- Tongue / ledge (SS1.5, simplified -- see class docstring) ---
    # The riser fills the full plate thickness up to the ledge height over
    # [PLATE_Y_HI, TONGUE_STEP_Y] -- this is what fuses to the plate with a
    # real volume overlap (Z [0, PLATE_THICKNESS] in common), not just a
    # touching edge. The thin distal tip then continues from TONGUE_STEP_Y
    # to TONGUE_Y_HI at the recessed TIP_Z_LO..RISER_Z_HI band only -- this
    # is the 0.926 mm-thick blade the design's Housing rebate must receive.
    # Round 60, from the measured part: tongue 13.800 wide with three
    # 2.300 gaps ("between tongues and the edge"). Two tongues and three
    # gaps is the only arrangement those words fit, giving
    # 2*13.800 + 3*2.300 = 34.500 total, centred -- so gap | tongue | gap |
    # tongue | gap, and the tongue's outer edge lands at 14.950.
    # Corroboration: that total is 34.500 against the 34.400 we had modelled
    # from LDraw, i.e. the same overall feature, redistributed internally.
    TONGUE_X_HALF = 14.950   # tongue outer edge (was 15.600)
    # NOT measured -- scaled with the plate (26.000 * 52.330 / 54.400) so the
    # riser keeps its proportion of the width. Flagged as inferred: if the
    # riser matters for the fit, measure it.
    RISER_X_HALF = 25.010
    # ROUND 61: the tongue protrudes 4.000 beyond the body edge, measured on
    # the real part ("the tongue length to be 4mm from the end of the body").
    # Round 60 built 1.700, derived as 63.600 - 61.900 from two whole-part
    # readings -- an arithmetic difference of two large numbers, so both
    # errors landed in it. This is the feature measured directly, and it also
    # closes the length books: 59.800 + 4.000 = 63.800 against the 63.600
    # "including tongues" reading.
    #
    # The riser/tip split is still NOT measured; the LDraw proportion (1.378
    # riser to 1.022 tip, 2.400 total) is scaled by 4.000/2.400 so the tip
    # stays a blade rather than guessing a new split. Inferred -- if the
    # rebate fit is wrong at this end, this is the number to measure next.
    TONGUE_STEP_Y = 34.297   # PLATE_Y_HI + 1.378 * (4.000 / 2.400)
    TONGUE_Y_HI = 36.000     # PLATE_Y_HI + 4.000
    RISER_Z_HI = 2.800
    TIP_Z_LO = 1.874

    # --- Tongue segmentation (round 45) ---
    # The reference tongue is NOT one continuous slab: rays along X give
    # four separate blades, |X| in [0.800, 15.600] (Tongue A, the pair
    # either side of the centreline) and [17.200, 26.000] (Tongue B), with
    # 1.600 mm gaps between them. The gaps are where the HOUSING's own ribs
    # sit -- ldraw-housing-geometry.md SS12.2 T1/T2/T3 measures the slot
    # side walls at |X| = 0.800 / 15.600 / 17.200 / 26.000 and the ribs
    # between the slots at |X| 15.600..17.200 and 26.000..28.000. Those
    # walls are what locate the lid in +-X; a continuous slab could not
    # enter the slots at all on the real part.
    # Rounds 18-22 built the tongue as one slab and the residual deviation
    # sat exactly on these four boundaries (the reference reading as
    # "reinforcements at both edges" -- an artefact of the segmentation,
    # not ribs added to a blade). Cut here as gaps rather than built as
    # four bodies, so TONGUE_X_HALF / RISER_X_HALF keep their meaning as
    # the tongue's outer bounds.
    # Round 60, from the same measured layout as TONGUE_X_HALF above.
    TONGUE_GAP_X_INNER = 1.150   # centre gap half-width (was 0.800)
    TONGUE_RIB_X_HI = 17.250     # outer gap ends here (was 17.200)

    # --- Locating groove / land (SS1.5) -- RESTORED round 22 ---
    # The inner face steps 1.200 -> 1.600 mm deep over Y in [30.0, 31.2],
    # full width. Rounds 18-21 built this and attributed it to the
    # BatteryTray's bottom rim; last round deleted it with the tray on that
    # attribution. The attribution was wrong: SS1.5 states plainly that
    # "the lid seats laterally on the 1.600 mm groove at Y in [30.0, 31.2]"
    # -- a lid-to-HOUSING seating feature that has nothing to do with the
    # tray. Restored here on the reference's own wording.
    GROOVE_Y_LO = 30.000
    GROOVE_Y_HI = 31.200
    GROOVE_THICKNESS = 1.600   # local plate thickness over the groove band

    # --- Ledge locating teeth + notches (SS1.5) -- round 22 full copy ---
    # The reference's castellation at the insertion end, reproduced exactly
    # rather than simplified away: 6 teeth (3 per half) at the |X| bands
    # below extend the ledge forward from LEDGE_Y_LO to TEETH_Y_LO, and the
    # floor between them drops back to NOTCH_FLOOR_Z. Rounds 18-21 dropped
    # both ("rather than reproducing the 6 locating teeth or the ledge
    # notches between them"); round 22 restores them at the user's
    # direction. The teeth are the male side and the notches simply the
    # material between them -- both live on this part, exactly as in the
    # reference, so the housing carries a plain mating lip and no ridges.
    TEETH_Y_LO = 31.200
    TEETH_Y_HI = 32.400
    # Scaled with the ledge in _build_ledge_teeth (round 59) -- these stay
    # the LDraw pattern because the teeth themselves were not measured; only
    # their outer extent is pinned, by riding on LEDGE_X_HALF.
    TOOTH_X_BANDS = ((0.800, 2.000), (7.600, 8.800), (14.400, 15.600))
    NOTCH_FLOOR_Z = 1.600
    LEDGE_Z_HI = 2.800         # == RISER_Z_HI; the teeth rise to the ledge top
    LEDGE_X_HALF = 14.950      # == TONGUE_X_HALF (round 60, measured)
    # The ledge proper starts where the teeth end. Rounds 18-21 ran the
    # riser from the plate edge (32.000), which is 0.400 mm too far
    # forward: SS1.5 puts the raised ledge over Y in [32.400, 34.400] and
    # leaves [32.000, 32.400] as plain plate.
    LEDGE_Y_LO = 32.400

    # --- Release leg / U-spring (SS1.4) ---
    # OUTER face of the leg. Rounds 18-21's profile is kept -- it was
    # reference-verified, including round 21's flared foot -- with ONE
    # correction at the top, which is where the U-hook defect lived.
    #
    # Round 21 held the profile flat past z = 11.0 at y = -33.367 and paired
    # it with a 1.047 mm thickness, putting the leg's INNER face at -32.320.
    # The reference's own aperture-bounding face there is -33.302 (measured
    # at z = 11.2 / 11.4 / 11.6, `parts/24853.dat` sectioned at the finger
    # centre), so the aperture should be 1.062 mm and was instead 0.043 mm.
    # Full table and a method caveat in
    # `docs/design_plans/2026-08-19-poweredup-hub-battery-box_reference-comparison.md`
    # section R22. That closed gap -- not the crown -- is why the barb bead
    # had nowhere to protrude and was swallowed.
    #
    # Correction: at z = 11.0 the outer face steps out to -34.000 and the
    # thickness returns to the reference's base 0.698, putting the inner
    # face at -33.302 exactly. The aperture opens to 1.062 mm, the bead
    # (outboard extreme -33.124) clears the leg by 0.178 mm, and the leg's
    # own outer face still clears the housing's 1.2 mm latch skin
    # (inner face -34.400) by 0.400 mm.
    # Round 30: the reference's retention bead is resolved here at 0.25 mm
    # sampling rather than left as one interpolated peak. Profiling
    # 24853.dat's leg face shows a flat -34.000 baseline over z = 3.00..4.75,
    # a bulge peaking at -34.220 at z = 5.00 (0.220 mm proud), a gentle decay
    # to -34.170 by 5.50, then a drop away by 5.75. THAT bulge is Philo's
    # barb. Rounds 27-29 carried only the (5.0, -34.220) sample, so linear
    # interpolation smeared it across z = 3.6..8.0 -- present but unusable.
    # The bead's working numbers, read by the Housing's retention land so the
    # two cannot drift apart.
    # --- Latch U as a SPRING (round 38) ---------------------------------
    # The U is a hairpin cantilever spring, so it is modelled as ONE
    # constant-thickness ribbon: an open centreline offset both ways by
    # U_WALL/2 in a single `offset2D` call. Thickness is then structural
    # rather than arithmetic -- measured 0.800000 +- 3.8e-15 in
    # tmp/research/cadquery-spring-modelling.md.
    #
    # Rounds 18-36 built the U as separate unioned solids (finger wedge,
    # spine, crown/head, bead, pad). That is why wall thickness and
    # continuity kept drifting and why each fix broke a neighbour -- and why
    # the aperture ended up terminating in a FLAT-BOTTOMED SLOT (0.618 mm at
    # z = 10.00, closed by 10.25): a sharp internal corner at the most
    # cyclically loaded point in the spring, carrying Kt 2-5 and consuming
    # the whole PLA strain margin. See the reference-comparison R37.
    #
    # Geometry is set by three constraints, not by copying the reference:
    #   * leg outer face must clear PoweredUpHubHousing.LATCH_LAND_Y (-34.050)
    #   * finger inner face must OVERLAP PLATE_Y_LO (-30.800), not touch it
    #   * inner bend radius >= 1.0 x wall (Ticona 0.5 x t is the sourced
    #     floor; 1.0 x t is preferred for a load-bearing feature)
    #
    # --- ROUND 61: the latch is deepened, the finger thickened, the crown
    # --- sloped. Three separate findings off the printed part.
    #
    # (a) REACH. The owner measured the engaging tongue's tip at 5.000 mm
    #     outboard of the body's end face; the bead peaked at 3.420, i.e.
    #     1.580 short. That is the "too short" report, and it is the whole of
    #     it -- the bead's Z position and profile both stay.
    #     Independent corroboration: the round-60 measurement session put the
    #     latch's full depth (thumb-tab face to the hook's root) at 6.240
    #     against our 4.850. Two readings taken on different features, a round
    #     apart, asking for the same ~1.5 mm of deepening.
    # (b) FINGER THICKNESS 1.600, up from 0.800. The finger is the member
    #     rooted in the body -- the owner's "straight line shot out vertically
    #     from the body". The reference has it at 1.100, so the printed part,
    #     the reference and this class all disagreed; the printed part wins.
    #     The LEG deliberately stays at U_WALL: it is the thin, pressable,
    #     compliant member, and the owner confirmed last round that "the
    #     spring was OK". Thickening both -- which a single-ribbon model would
    #     force -- would raise stiffness with the CUBE of thickness and throw
    #     away a spring that already works. This is why the two walls are now
    #     separate constants.
    # (c) CROWN. "Joined by a slope", not our semicircular hairpin bend.
    #     Confirmed on the reference independently (tmp/ldraw/latch_shape_r61.py):
    #     its outer profile converges from 2.153 mm wide at z = 11.25 to
    #     1.286 at z = 12.75 before ending at 13.000 -- a taper, not an arc.
    #
    # === ROUND 62 -- the latch is a V, and round 61 built the wrong fix ===
    #
    # The owner printed round 61 and reported the hook still wrong. The cause
    # is worth recording, because it was a METHOD failure, not an arithmetic
    # one: rounds 60 and 61 both read span TABLES off the reference and
    # inferred a shape from the numbers. Plotting the section
    # (tmp/ldraw/latch_picture_r62.py) shows what the tables could not:
    #
    #   * The two members CONVERGE. The aperture between them is 1.454 mm
    #     wide at z = 2 and 0.087 at z = 11 -- a V with its vertex UP, not the
    #     parallel-legged U every previous round built.
    #   * The plate-side member is a STRAIGHT vertical wall. The slope is
    #     entirely on the outer member.
    #
    # Round 61 read "the leg is further out at the bottom than the top" as
    # "the leg is in the wrong place" and translated the whole assembly
    # outboard by 1.580 to get the peg's reach. The owner's correction --
    # "make the peg larger, not increasing the size of the hook" -- is exactly
    # that error. The leg goes back; the PEG grows instead.
    #
    # Look at the geometry before believing a table about it.
    U_WALL = 0.800                # LEG wall: 2 x 0.4 mm extrusion width
    FINGER_WALL = 1.600           # the straight, plate-rooted member
    U_FINGER_CL_Y = -31.550       # finger spans -32.350..-30.750 (1.600 wall)

    # --- The V ---
    # The leg's OUTER face at the plate (z = 0), its widest point. Chosen so
    # the aperture's base is 1.454 -- the reference's own base width -- given
    # the finger's outer face at -32.350. INFERRED from the reference's
    # proportion, not measured: if the spring's feel is wrong, this is the
    # constant that sets its free length and lever arm.
    LEG_BASE_OUT_Y = -34.604
    # Where the two members meet, as a fraction of hook height. The reference
    # closes its aperture at z = 11.2 of 13.000, i.e. 0.862.
    APEX_Z_FRAC = 0.862
    # Crown: above the apex the hook is solid, tapering to a flat tip.
    CROWN_TOP_HALF = 0.500

    # --- The peg (the "tongue that joins the housing") ---
    # Measured: tip 5.000 mm outboard of the plate edge, and ~1 mm tall.
    # 1 mm tall with a ~1.6 mm protrusion makes it a SHELF, not the reference's
    # smooth 0.220 bulge -- so it is built as a right triangle in section:
    #   * ramped underside, which is the lead-in as the hook enters (+Z), and
    #     also the printable face (a 32 deg overhang rather than a 90 deg one);
    #   * FLAT horizontal top, which is the retention face -- it takes the
    #     pull-out load in -Z square-on, and prints as a short bridge.
    # A symmetric bump would put a 17 deg overhang under the peg and bear the
    # retention load on a slope that wants to cam itself open.
    BEAD_Z_LO = 4.750
    BEAD_Z_HI = 5.750             # 1.000 tall, measured
    BARB_TIP_OUT = 5.000          # peg tip, outboard from LATCH_DATUM_Y
    # --- The thumb tab ---
    TAB_TIP_OUT = 6.000           # tab tip, outboard from LATCH_DATUM_Y
    # Thumb-pad plan outline: scalloped in Y across the hook width.
    # Round 62: the tab tip is TAB_TIP_OUT (6.000) outboard of the plate edge,
    # i.e. -36.800, superseding round 61's -36.990 (which came from the
    # earlier 6.240 depth reading). The 0.400 scallop step is kept as measured.
    #
    # X: the NOMINAL hook footprint, 5.600..17.800, in six evenly-spaced steps
    # (round 61 fix -- these had been left on the pre-round-60 13.600 hook
    # width, making the pad 1.400 mm wider than both the hook it sits on and
    # the window it passes through; silent, because the pad is union-only).
    PAD_SCALLOP = (
        (5.600, -36.800), (8.040, -36.800), (10.480, -36.400),
        (12.920, -36.400), (15.360, -36.800), (17.800, -36.800),
    )
    # NOT a constant any more -- see self._pad_inner_y, derived in __init__.
    # The leg SLOPES, so its outer face retreats inboard as Z rises and a
    # fixed inner bound here loses contact with it partway up the pad. A first
    # round-62 version used LEG_BASE_OUT_Y + 0.050 (the leg's face at the
    # PLATE) and the pad parted company with the leg above z = 0.44 -- visible
    # immediately in the section plot, and invisible to every check we own:
    # the pad is still fused to the PLATE, so `solids == 1` passes, and a
    # thumb pad that no longer drives the leg is a dead release mechanism that
    # measures perfectly.
    # Round 33: the reference's pad is a LIP, not a tall block. Ray-probing
    # 24853.dat's own outer face gives -35.120 at z = 1.0 and -35.104 at
    # z = 1.2, then -34.112 at z = 1.4 -- so it ends between 1.2 and 1.4. The
    # old 2.791 value held our pad proud to -35.200 all the way to z = 2.8,
    # which surface_diff scored as 1.394..1.595 mm of INVENTED material at
    # z = 2.50..3.00 (R32). Those stations were invisible until the sweep was
    # fixed to rank on both directions.
    PAD_TOP_Z = 1.300             # the pad's own top, per the reference

    # --- Pad end-walls (round 36) -- the R34 open gap, now closed ---
    # The pad is NOT uniform in X. At its two extremes the reference carries a
    # tall wall: measured at z = 2.5 the outer face is -35.400 at x = 5.8 and
    # 6.2 (mirrored 18.6, 19.0) and absent from 6.6 through 18.2. So two walls
    # ~0.8 mm wide at the ends of the hook width, running to z ~ 2.791, either
    # side of the low central lip.
    #
    # This is what a single PAD_TOP_Z could not express, and why probing
    # x = 12.400 alone (the pad's centre, where it genuinely IS a lip) led to
    # cutting the walls off entirely: 1.361 mm missing at x = 6.400 / 18.400,
    # y = -35.377, z = 2.791.
    PAD_END_WALL_X = 0.800
    PAD_END_WALL_Y = -36.600   # round 62: rides with the pad's new tip
    PAD_END_WALL_Z_HI = 2.791

    def __init__(self, profile: ToleranceProfile | str | None = None) -> None:
        if profile is None or isinstance(profile, str):
            prof = get_profile(profile) if isinstance(profile, str) else get_profile()
        else:
            prof = profile
        self._profile = prof
        self._latch = get_latch_geometry(prof)

        # --- Lateral (X) running clearance on the male latch features
        # (round 58, user report: "the U hook ... currently it gets stuck").
        #
        # The REFERENCE gives none. Measured off both reference meshes
        # (tmp/ldraw/ref_latch_fit.py), 24853's hook and 25560's slot both
        # span X 5.600..19.200 -- 13.600 against 13.600, zero clearance per
        # side. That is not an oversight in the reference: LDraw models
        # NOMINAL geometry, and a moulded LEGO part takes its working fit
        # from mould tolerance and material. Printed on an FDM machine the
        # same pair is a press fit.
        #
        # PoweredUpHubHousing already opens its channel by free.radial per
        # side (round 40, which fixed a literal 0.000 mm case). Measured on
        # the built parts, that gives a uniform 0.150 mm on all four gaps
        # over the full leg height -- no taper, no local pinch
        # (tmp/ldraw/latch_x_gap.py). So the bind is not a defect to repair;
        # 0.150 mm per side is simply too tight for this feature in print.
        # The housing is held reference-faithful by user direction, so the
        # second half of the clearance comes off THIS part, taking the pair
        # to 2 x free.radial per side.
        self._hook_lateral_clearance = prof.free.radial
        self._hook_width_printed = (
            self._latch.hook_width - 2 * self._hook_lateral_clearance
        )

        # --- Whole-lid running clearance (round 59, user direction: "the
        # cover width, length and the gaps on the tongue side all need
        # clearance").
        #
        # Same root cause as the hook: the reference is a zero-clearance
        # model throughout, so every face this lid slides past was built to
        # the housing's own nominal figure. Measured on the built pair
        # (tmp/ldraw/cover_fit_gaps.py) before changing anything:
        #
        #     width, X plate edge      0.150 per side  (housing's round-48 relief)
        #     tongue blade, outboard   0.150
        #     LENGTH, latch end        0.000
        #     LENGTH, tongue step      0.000
        #
        # The two length figures are the interesting ones: the lid is exactly
        # as long as the cavity, face to face, at BOTH ends. No amount of
        # width clearance helps that.
        #
        # Applied here as derived build dimensions rather than by editing the
        # constants, deliberately. PLATE_WIDTH, TONGUE_STEP_Y and the rest are
        # REFERENCE MEASUREMENTS and are cited as such throughout this file and
        # in reference_contracts.toml; rewriting them would destroy that
        # provenance and leave no record of what the real part measures. The
        # constants stay the reference; these are what we print.
        #
        # Male faces shrink, female gaps grow -- the sign differs per feature,
        # which is why this cannot be a single scale factor.
        self._fit = self.fit_clearance(prof)
        self._plate_width = self.PLATE_WIDTH - 2 * self._fit
        # NOT clearance-adjusted, and the exception is load-bearing. Moving
        # this edge inboard is coupled to the latch: the U's finger inner face
        # sits at -30.750 and must reach INBOARD PAST the plate edge to fuse
        # with it (0.050 mm of overlap at the reference -30.800). A round-59
        # version applied the clearance here and opened a 0.100 mm GAP
        # instead -- the lid survived only because the latch band happens to
        # bridge it, and the assertion below was written with its inequality
        # reversed, so it certified the broken state instead of catching it.
        #
        # The latch end's own length clearance therefore comes from
        # translating the whole latch assembly (self._latch_dy below), never
        # from retreating the plate edge out from under it.
        self._plate_y_lo = self.PLATE_Y_LO

        # Round 61: how far the latch sub-assembly rides from the frame its
        # constants were measured in to wherever the plate edge now is. Every
        # latch feature -- U ribbon, bead, thumb pad, pad end walls, and the
        # plate's own latch thickening band -- is built at LATCH_DATUM_Y and
        # translated by this. The alternative, editing ~10 measured Y
        # constants by hand, would silently destroy the provenance this file
        # spends most of its comments recording.
        self._latch_dy = self._plate_y_lo - self.LATCH_DATUM_Y
        self._tongue_step_y = self.TONGUE_STEP_Y - self._fit
        self._tongue_y_hi = self.TONGUE_Y_HI - self._fit
        self._tongue_x_half = self.TONGUE_X_HALF - self._fit
        self._riser_x_half = self.RISER_X_HALF - self._fit
        self._ledge_x_half = self.LEDGE_X_HALF - self._fit
        # The centre gap and the rib gaps are VOIDS the housing's ribs stand
        # in, so they open outward by the clearance instead of closing.
        self._tongue_gap_x_inner = self.TONGUE_GAP_X_INNER + self._fit
        # Both walls of the rib gap must move, not just the inner one. A
        # first version widened only the TONGUE_X_HALF side and left this at
        # nominal, so the gap grew asymmetrically -- and the housing rib that
        # enters it, sized from the lid's own walls, then butted this face at
        # zero clearance. Caught by the kinematic sideways-travel test, not by
        # any seated check: touching faces measure 0.000 mm^3.
        self._tongue_rib_x_hi = self.TONGUE_RIB_X_HI + self._fit

        # The U's finger must OVERLAP the plate edge rather than touch it (see
        # the U geometry constraints above), so it is checked rather than
        # assumed. OVERLAP means the finger reaches inboard PAST the edge,
        # i.e. finger_inner is at a GREATER Y. An earlier version compared the
        # other way round, which is satisfied precisely by the gap it was
        # meant to forbid.
        #
        # What can still falsify this after round 61: the latch rides with the
        # plate edge, so a length re-datum alone can no longer break the fuse
        # -- but editing U_FINGER_CL_Y, U_WALL or LATCH_DATUM_Y independently
        # can, and that is exactly the drift this now guards. Both sides are
        # therefore stated in the latch's OWN frame, not the built one, where
        # the comparison would reduce to an identity and assert nothing.
        finger_inner = self.U_FINGER_CL_Y + self.FINGER_WALL / 2.0
        assert finger_inner > self.LATCH_DATUM_Y + 1e-9, (
            f"the latch finger's inner face ({finger_inner:.3f}) does not "
            f"reach inboard past the plate edge it is measured against "
            f"({self.LATCH_DATUM_Y:.3f}) -- they meet on a coincident face or "
            f"leave a {self.LATCH_DATUM_Y - finger_inner:.3f} mm gap, so the "
            "U is not fused to the plate"
        )

        # Round 62: the peg must GROW to its reach, not be carried there.
        #
        # This is the guard the owner's correction earns. Rounds 58-61 each
        # met BARB_TIP_OUT by translating the leg outboard, and nothing
        # objected -- the reach was correct every time, and the hook got
        # bigger every time. So the check is not "does the peg reach 5.000"
        # (it always did) but "does the peg reach 5.000 by PROTRUDING from a
        # leg that is still where the spring's own geometry puts it".
        #
        # Falsifier: move LEG_BASE_OUT_Y outboard to chase the reach and the
        # protrusion collapses toward zero, failing the lower bound. Leave the
        # leg alone and shrink the peg, and it fails too.
        peg_root, _ = self._leg_faces(self.BEAD_Z_HI)
        peg_tip = self.LATCH_DATUM_Y - self.BARB_TIP_OUT
        protrusion = peg_root - peg_tip
        assert protrusion > 0.500, (
            f"the peg protrudes only {protrusion:.3f} mm from the leg face "
            f"({peg_root:.3f}) -- its {self.BARB_TIP_OUT:.3f} mm reach is "
            "coming from the leg's position rather than from the peg itself, "
            "which is the round 58-61 mistake"
        )
        # And the thumb tab is the outermost thing on the part, by measurement
        # (6.000 vs the peg's 5.000). If that order ever inverts, the peg is
        # what the thumb presses on.
        tab_tip = min(y for _, y in self.PAD_SCALLOP)
        assert tab_tip < peg_tip - 1e-9, (
            f"the thumb tab ({tab_tip:.3f}) does not reach further outboard "
            f"than the peg ({peg_tip:.3f})"
        )

        # The pad's inner bound, taken at the pad's OWN TOP -- the worst case,
        # because the sloped leg is furthest inboard there. Sampling anywhere
        # lower certifies an overlap that has already run out higher up.
        pad_leg_out, _ = self._leg_faces(self.PAD_TOP_Z)
        self._pad_inner_y = pad_leg_out + 0.050
        assert self._pad_inner_y > pad_leg_out, "pad does not bite into the leg"

        self._solid = self._build()

    @classmethod
    def fit_clearance(cls, profile: ToleranceProfile) -> float:
        """Per-face running clearance taken off the lid's mating surfaces.

        A seam, not decoration: a subclass returning ``0.0`` reproduces the
        pre-round-59 zero-clearance lid, which is what the plate-edge relief
        test needs in order to *demonstrate* binding rather than assert it.
        Without something to falsify against, that test can only claim the
        pair is clear -- and a check that cannot fail is not a check.

        **Returns 0.000 as of round 60, and that is not a disabling.** Rounds
        58-59 derived this clearance empirically because the LDraw datum gave
        a zero-clearance pair. Round 60 replaced that datum with calipers on
        the real parts, and those readings were taken on a real MATING pair --
        52.33 in a 52.96 cavity -- so the working fit is already inside the
        numbers. Subtracting more here would double it. The empirical value is
        not wasted: 0.295 mm/side landed within 0.02 mm of the real
        assembly's own 0.315, which is the corroboration that the clearance
        work was right and only its datum was wrong.
        """
        return 0.0

    def _hook_span(self, side: int) -> tuple[float, float]:
        """``(x_center, half_width)`` for the male latch features.

        ``x_center`` stays on the **nominal** footprint centre while only
        the half-width shrinks, so the clearance splits evenly between the
        two channel walls. Deriving the centre from the narrowed width
        instead would slide the whole hook inboard by the clearance and
        park it hard against one wall -- same total width, none of the
        clearance, and an asymmetry no seated interference check would
        report (touching faces measure 0.000 mm^3).
        """
        lg: LatchGeometry = self._latch
        x_center = side * (lg.hook_pitch / 2.0 + lg.hook_width / 2.0)
        return x_center, self._hook_width_printed / 2.0

    def _latch_frame(self, wp: cq.Workplane) -> cq.Workplane:
        """Move a latch-frame solid onto the plate edge as currently datumed.

        Every latch builder works in the frame its reference measurements were
        taken in (:attr:`LATCH_DATUM_Y`); this is the single place that frame
        is reconciled with :attr:`PLATE_Y_LO`. Routing them all through one
        method is what stops a future length change from moving four of the
        five latch features and leaving the fifth behind -- a failure a seated
        interference check cannot see, because a detached pad still measures
        0.000 mm^3 against the housing.
        """
        return wp.translate((0.0, self._latch_dy, 0.0))

    def _build(self) -> cq.Workplane:
        part = self._build_plate()
        part = part.union(self._latch_frame(self._build_latch_u(+1)))
        part = part.union(self._latch_frame(self._build_latch_u(-1)))
        part = part.union(self._latch_frame(self._build_leg_bead(+1)))
        part = part.union(self._latch_frame(self._build_leg_bead(-1)))
        part = part.union(self._latch_frame(self._build_pad_end_walls(+1)))
        part = part.union(self._latch_frame(self._build_pad_end_walls(-1)))
        part = part.union(self._latch_frame(self._build_thumb_pad(+1)))
        part = part.union(self._latch_frame(self._build_thumb_pad(-1)))
        part = part.union(self._build_tongue())
        part = part.union(self._build_locating_groove())
        part = part.union(self._build_ledge_teeth())
        part = part.union(self._build_window_sill(+1))
        part = part.union(self._build_window_sill(-1))

        assert len(part.solids().vals()) == 1, "Expected single solid, got multiple pieces"
        return part

    def _build_window_sill(self, x_sign: int) -> cq.Workplane:
        """Fill the bottom ``PLATE_THICKNESS`` of the housing's side window
        (round 55) -- the user's "stripe".

        **Why the gap exists.** Until round 51 the extraction tab lived on
        THIS class and was rooted at the plate, so it started at world
        ``Z = 0`` and filled the window from the very bottom. Round 51 moved
        the tab to
        :class:`~vibe_cading.lego_adapters.poweredup_hub.battery_tray.PoweredUpHubBatteryTray`,
        which seats :attr:`PLATE_THICKNESS` above world zero -- so the tab
        now starts at ``Z = 1.200`` while the window it passes through still
        starts at ``Z = 0``. That left a 1.200 mm slot right through the
        side wall, open to daylight, spanning the window's full width.
        Nothing detected it: the window is cut to the TAB's outline and the
        tab still fits it perfectly; the fault is only visible where the two
        parts meet.

        This strip is the plate's own edge carried outward through that
        slot, ``PLATE_THICKNESS`` tall, so the wall reads as continuous
        below the tab.

        Bounds, and why each is where it is:

        * **Y** -- the TAB's own half-width, not the window's. The window is
          the tab's outline offset outward by the running clearance, so
          matching the tab leaves exactly that clearance on both sides and
          the strip cannot bind in the opening.
        * **+X** -- stops one running clearance SHORT of the housing wall's
          outer face rather than flush with it. The Cover has +-0.150 mm of
          deliberate sideways play (the round-48 plate-edge relief), so a
          flush strip would stand proud of the wall whenever the lid sits
          off-centre; recessed, the worst case is flush.
        * **-X** -- overlaps back into the plate for a real fused volume,
          not a coincident face.

        ``WALL_X_OUTER_LOWER`` (28.000) is hardcoded rather than imported:
        :class:`~vibe_cading.lego_adapters.poweredup_hub.housing.PoweredUpHubHousing`
        imports this class, so importing it back would cycle. It has been
        the reference's own outer face since the envelope was first
        measured; re-derive by hand if it ever moves.
        """
        housing_wall_x_outer = 28.000
        c = self._profile.free.radial
        seam_overlap = 0.050

        x_inner = self._plate_width / 2.0 - seam_overlap
        x_outer = housing_wall_x_outer - c
        x_lo = min(x_sign * x_inner, x_sign * x_outer)
        x_hi = max(x_sign * x_inner, x_sign * x_outer)

        return rounded_box(
            width=x_hi - x_lo,
            depth=2 * self.WINDOW_SILL_Y_HALF,
            height=self.PLATE_THICKNESS,
            corner_r=0.0,
            center=((x_lo + x_hi) / 2.0, 0.0, 0.0),
        )

    def _build_plate(self) -> cq.Workplane:
        y_span = self.PLATE_Y_HI - self._plate_y_lo
        plate = rounded_box(
            width=self._plate_width,
            depth=y_span,
            height=self.PLATE_THICKNESS,
            corner_r=0.0,  # sharp corners, measured (SS1.1)
            center=(0.0, (self._plate_y_lo + self.PLATE_Y_HI) / 2.0, 0.0),
        )
        # The band is a LATCH-frame feature (it thickens the plate exactly
        # where the fingers root), so it rides with the latch rather than
        # staying at its measured Y. Left behind, it would sit 3 mm inboard of
        # the fingers it exists to support and the lid would still build,
        # still be one solid, and still seat at zero interference.
        band_span = self.LATCH_BAND_Y_HI - self.LATCH_BAND_Y_LO
        band = rounded_box(
            width=self._plate_width,
            depth=band_span,
            height=self.LATCH_BAND_THICKNESS - self.PLATE_THICKNESS,
            corner_r=0.0,
            center=(
                0.0,
                (self.LATCH_BAND_Y_LO + self.LATCH_BAND_Y_HI) / 2.0,
                self.PLATE_THICKNESS,
            ),
        )
        return plate.union(self._latch_frame(band))

    @staticmethod
    def _interp(profile: tuple[tuple[float, float], ...], z: float) -> float:
        """Piecewise-linear interpolation of a ``(z, value)`` profile,
        clamped flat beyond either end -- shared by the release leg's
        outer-face and thickness profiles (see :attr:`_LEG_OUTER_Y` /
        :attr:`_LEG_THICKNESS`).
        """
        if z <= profile[0][0]:
            return profile[0][1]
        if z >= profile[-1][0]:
            return profile[-1][1]
        for (z0, v0), (z1, v1) in zip(profile, profile[1:]):
            if z0 <= z <= z1:
                t = (z - z0) / (z1 - z0)
                return v0 + t * (v1 - v0)
        return profile[-1][1]  # pragma: no cover -- unreachable, profile covers [0, last]

    def _build_thumb_pad(self, side: int) -> cq.Workplane:
        """The scalloped thumb pad (SS1.4) -- see :attr:`PAD_SCALLOP`.

        A plan-view polygon (scalloped outer edge, straight inner edge at
        :attr:`PAD_INNER_Y`) extruded to :attr:`PAD_TOP_Z`. Union-only by
        design: everywhere the swept leg profile already reaches, this
        changes nothing; where the reference stands proud of it, this
        supplies the missing material.
        """
        # The scallop's X values are the NOMINAL hook footprint
        # (5.600..19.200). Scale them about the footprint's own centre by
        # the printed/nominal ratio so the pad takes the same lateral
        # clearance as the ribbon it sits on -- scaled rather than shifted,
        # so the scallop keeps its shape instead of having its two end
        # segments distorted.
        lg: LatchGeometry = self._latch
        nominal_c = lg.hook_pitch / 2.0 + lg.hook_width / 2.0
        k = self._hook_width_printed / lg.hook_width

        def sx(x: float) -> float:
            return side * (nominal_c + (x - nominal_c) * k)

        pts = [(sx(x), y) for x, y in self.PAD_SCALLOP]
        pts += [(sx(self.PAD_SCALLOP[-1][0]), self._pad_inner_y),
                (sx(self.PAD_SCALLOP[0][0]), self._pad_inner_y)]
        wp = cq.Workplane("XY").moveTo(*pts[0])
        for q in pts[1:]:
            wp = wp.lineTo(*q)
        return wp.close().extrude(self.PAD_TOP_Z)

    def _build_pad_end_walls(self, side: int) -> cq.Workplane:
        """The two tall walls flanking the thumb pad (round 36).

        See :attr:`PAD_END_WALL_X`. Inboard bound is :attr:`PAD_INNER_Y`,
        which sits marginally outboard of the leg's own face over this Z band,
        so the union is a volume overlap rather than the coincident-faces case.
        """
        x_center, half_w = self._hook_span(side)
        depth = self._pad_inner_y - self.PAD_END_WALL_Y
        y_mid = (self.PAD_END_WALL_Y + self._pad_inner_y) / 2.0

        walls = None
        for edge in (-1, +1):
            x_edge = x_center + edge * half_w
            x_mid = x_edge - edge * self.PAD_END_WALL_X / 2.0
            block = rounded_box(
                width=self.PAD_END_WALL_X,
                depth=depth,
                height=self.PAD_END_WALL_Z_HI,
                corner_r=0.0,
                center=(x_mid, y_mid, 0.0),
            )
            walls = block if walls is None else walls.union(block)
        return walls

    def _finger_faces(self) -> tuple[float, float]:
        """``(outer, inner)`` Y of the straight, plate-rooted member.

        Vertical -- it does not vary with Z. That is the owner's "the side
        connecting to the cover plate in a straight shape", and it is what the
        reference section shows: a constant-width band from the plate to the
        crown, with all of the slope on the other member.
        """
        d = self.FINGER_WALL / 2.0
        return self.U_FINGER_CL_Y - d, self.U_FINGER_CL_Y + d

    def _leg_faces(self, z: float) -> tuple[float, float]:
        """``(outer, inner)`` Y of the SLOPED member at height ``z``.

        The leg is widest at the plate and converges on the finger as it
        rises, closing the aperture to a point at ``_apex_z()``. Constant
        thickness :attr:`U_WALL` throughout -- it is a leaning wall, not a
        tapering one, so its stiffness does not vary along its length.
        """
        finger_out, _ = self._finger_faces()
        base_in = self.LEG_BASE_OUT_Y + self.U_WALL
        t = min(max(z / self._apex_z(), 0.0), 1.0)
        inner = base_in + t * (finger_out - base_in)
        return inner - self.U_WALL, inner

    def _apex_z(self) -> float:
        """Z at which the aperture closes and the two members merge."""
        return self._latch.hook_depth * self.APEX_Z_FRAC

    def _build_latch_u(self, side: int) -> cq.Workplane:
        """The latch: a converging **V**, not the hairpin U of rounds 38-61.

        Round 62, from plotting the reference's own section rather than
        reading a table of it (``tmp/ldraw/latch_picture_r62.py``). Two
        members: a straight vertical finger rooted in the plate, and a leg
        that leans inboard as it rises until the two meet at
        :meth:`_apex_z`, above which the hook is solid and tapers to a flat
        tip at ``hook_depth``.

        The aperture is therefore a wedge, open at the plate and closed at the
        top -- the reference measures it 1.454 mm wide at ``z = 2`` and
        0.087 at ``z = 11``. Every earlier round built these two members
        PARALLEL and then argued about where to put them; that is why the
        shape kept being wrong while each individual dimension looked right.
        """
        lg: LatchGeometry = self._latch
        x_center, half_w = self._hook_span(side)

        finger_out, finger_in = self._finger_faces()
        base_out, base_in = self._leg_faces(0.0)
        z_apex = self._apex_z()

        # Above the apex the hook is one solid section spanning the leg's
        # outer face to the finger's inner face, tapering to a flat tip.
        apex_out, _ = self._leg_faces(z_apex)
        mid = (apex_out + finger_in) / 2.0
        crown_out = mid - self.CROWN_TOP_HALF
        crown_in = mid + self.CROWN_TOP_HALF

        # The V must actually converge, and must not cross over. A leg that
        # over-runs the finger would produce a self-intersecting profile,
        # which OCCT will happily extrude into a single valid-looking solid
        # -- the silent-failure mode this file has been bitten by before.
        assert base_in < finger_out - 1e-9, (
            f"the leg's inner face at the plate ({base_in:.3f}) is not "
            f"outboard of the finger's outer face ({finger_out:.3f}) -- "
            "there is no aperture to open, so this is not a V"
        )
        assert z_apex < lg.hook_depth - 1e-9, (
            f"the aperture closes at {z_apex:.3f}, at or above the hook tip "
            f"({lg.hook_depth:.3f}) -- APEX_Z_FRAC leaves no crown"
        )
        assert crown_out < crown_in and crown_out > apex_out - 1e-9, (
            f"the crown flat ({crown_out:.3f}..{crown_in:.3f}) does not sit "
            f"inside the hook's own section at the apex "
            f"({apex_out:.3f}..{finger_in:.3f})"
        )

        # One closed profile, anticlockwise from the leg's outer foot: up the
        # sloped leg, up the crown taper, across the flat, down the finger's
        # inner face to the plate, across the foot, up the finger's vertical
        # aperture face to the apex, then back down the leg's inner face.
        wp = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0.0, 0.0, x_center - half_w))
            .moveTo(base_out, 0.0)
            .lineTo(apex_out, z_apex)
            .lineTo(crown_out, lg.hook_depth)
            .lineTo(crown_in, lg.hook_depth)
            .lineTo(finger_in, z_apex)
            .lineTo(finger_in, 0.0)
            .lineTo(finger_out, 0.0)
            .lineTo(finger_out, z_apex)
            .lineTo(base_in, 0.0)
        )
        return wp.close().extrude(self._hook_width_printed)


    def _build_leg_bead(self, side: int) -> cq.Workplane:
        """The **peg** -- the tongue that engages the housing.

        Round 62. Measured on the real cover: tip 5.000 mm outboard of the
        plate edge, ~1 mm tall. Rounds 58-61 kept the reference's smooth
        0.220 mm bulge and chased the reach by MOVING THE WHOLE LEG outboard;
        the owner's correction -- *"make the peg larger, not increasing the
        size of the hook"* -- is that error named. The leg is back on its own
        geometry and the peg grows out of it instead.

        1 mm tall against a ~1.6 mm protrusion makes this a shelf, so it is a
        right triangle in section, and which way round matters:

        * **Ramped underside**, from the leg face at :attr:`BEAD_Z_LO` out to
          the tip at :attr:`BEAD_Z_HI`. This is the lead-in as the hook
          enters (+Z), and it is also the printable face -- roughly 32 deg
          from horizontal instead of an unsupported 90 deg.
        * **Flat horizontal top** at :attr:`BEAD_Z_HI`, back to the leg. This
          is the retention face: pull-out acts in -Z and bears on it
          square-on. A symmetric bump would instead present a slope that cams
          itself open under load, and hang a 17 deg overhang underneath.

        The peg sits on the leg's own SLOPED face, so its root Y is read from
        :meth:`_leg_faces` at each end rather than from a constant -- a fixed
        baseline would float off the leg at one end and bury itself at the
        other.
        """
        x_center, half_w = self._hook_span(side)
        tip_y = self.LATCH_DATUM_Y - self.BARB_TIP_OUT
        root_lo, _ = self._leg_faces(self.BEAD_Z_LO)
        root_hi, _ = self._leg_faces(self.BEAD_Z_HI)
        seam = 0.050   # bite back into the leg so this fuses by volume

        assert tip_y < root_hi - 1e-9, (
            f"the peg's tip ({tip_y:.3f}) is not outboard of the leg face it "
            f"grows from ({root_hi:.3f}) -- it would be a notch, not a peg"
        )

        wp = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0.0, 0.0, x_center - half_w))
            .moveTo(root_lo + seam, self.BEAD_Z_LO)
            .lineTo(tip_y, self.BEAD_Z_HI)
            .lineTo(root_hi + seam, self.BEAD_Z_HI)
        )
        return wp.close().extrude(self._hook_width_printed)

    def _build_tongue(self) -> cq.Workplane:
        """Slide-in tongue + ledge -- a riser (fused to the plate, full
        thickness) plus a thin distal tip (the actual 0.926 mm rebate
        blade), per the class docstring's *Known simplifications*.

        The riser's own plan outline uses :attr:`RISER_X_HALF`
        (26.000 mm), wider than the tip's own :attr:`TONGUE_X_HALF`
        (15.600 mm) -- round 20, finding C4: this restores Tongue B's own
        plan-outline footprint (|X| 17.2..26.0 mm) at the riser level,
        matching Tongue A's already-correct edge. **Round 21 (finding
        RC4) corrects the riser's own Z-extent over that outer (Tongue B,
        |X| in [TONGUE_X_HALF, RISER_X_HALF]) band** -- round 20 restored
        the *plan outline* correctly but built the whole width at the
        full :attr:`RISER_Z_HI` (2.800 mm) riser height, when only Tongue
        A's own |X| <= TONGUE_X_HALF band is actually a full-height riser
        there; the outer Tongue-B band is plain :attr:`PLATE_THICKNESS`
        (1.200 mm) plate, matching the rest of the plate and Tongue A's
        own tip. This is a thickness-only correction on an
        already-correctly-positioned outline (C4's own restoration is not
        in question) -- it lands on the tongue's *mating* face, so it is
        functional, not cosmetic.
        """
        riser_depth = self._tongue_step_y - self.PLATE_Y_HI
        riser_y_center = (self.PLATE_Y_HI + self._tongue_step_y) / 2.0
        # Round 22: the full-height riser starts at LEDGE_Y_LO, not at the
        # plate edge -- see that constant. The 0.400 mm strip in between is
        # plain plate, and the teeth built by _build_ledge_teeth carry the
        # ledge height forward from there.
        ledge_depth = self._tongue_step_y - self.LEDGE_Y_LO
        riser_inner = rounded_box(
            width=2 * self._tongue_x_half,
            depth=ledge_depth,
            height=self.RISER_Z_HI,
            corner_r=0.0,
            center=(0.0, (self.LEDGE_Y_LO + self._tongue_step_y) / 2.0, 0.0),
        )
        riser_outer = rounded_box(
            width=2 * self._riser_x_half,
            depth=riser_depth,
            height=self.PLATE_THICKNESS,
            corner_r=0.0,
            center=(0.0, riser_y_center, 0.0),
        )
        tip = rounded_box(
            width=2 * self._tongue_x_half,
            depth=self._tongue_y_hi - self._tongue_step_y,
            height=self.RISER_Z_HI - self.TIP_Z_LO,
            corner_r=0.0,
            center=(
                0.0,
                (self._tongue_step_y + self._tongue_y_hi) / 2.0,
                self.TIP_Z_LO,
            ),
        )
        tongue = riser_inner.union(riser_outer).union(tip)

        # Round 45 -- segment the tongue into the reference's four blades.
        # One cutter per gap, spanning the tongue's whole Y and Z extent so
        # the slot is open on every face the housing rib has to pass; the
        # overcut keeps the cutter off the tongue's own bounding faces
        # (coincident faces are unreliable in the OCCT boolean kernel --
        # see CLAUDE.md, *Chord-vs-arc ring*). The centre gap runs the full
        # depth (the reference rebate's own side walls stand at |X| =
        # 0.800 over the tip band, SS12.2 T4); the rib gaps only ever meet
        # material out to TONGUE_STEP_Y, since the tip is |X| <=
        # TONGUE_X_HALF, but are cut to the same depth for one shape.
        # The -Y overcut is safe *here* and only here: this cut is applied
        # to the tongue alone, before it is unioned with the plate, and the
        # tongue carries no material below PLATE_Y_HI -- so the overcut
        # buys a clean non-coincident cutter face at the plate seam without
        # touching the full-width plate or the ledge teeth that straddle it.
        oc = 1.0
        gap_y_lo = self.PLATE_Y_HI - oc
        gap_y_hi = self._tongue_y_hi + oc
        gap_bands = [(-self._tongue_gap_x_inner, self._tongue_gap_x_inner)]
        for sign in (-1.0, 1.0):
            lo, hi = sorted((sign * self._tongue_x_half,
                             sign * self._tongue_rib_x_hi))
            gap_bands.append((lo, hi))
        for x_lo, x_hi in gap_bands:
            tongue = tongue.cut(
                rounded_box(
                    width=x_hi - x_lo,
                    depth=gap_y_hi - gap_y_lo,
                    height=self.RISER_Z_HI + 2 * oc,
                    corner_r=0.0,
                    center=(
                        (x_lo + x_hi) / 2.0,
                        (gap_y_lo + gap_y_hi) / 2.0,
                        -oc,
                    ),
                )
            )
        return tongue

    def _build_locating_groove(self) -> cq.Workplane:
        """The full-width locating land over ``[GROOVE_Y_LO, GROOVE_Y_HI]``
        (SS1.5) -- see :attr:`GROOVE_THICKNESS` for why this is a
        lid-to-housing feature and not the tray interface it was previously
        recorded as.

        Built as a raised land (a union bringing the plate locally to
        ``GROOVE_THICKNESS``), not a recess -- round 18's own S1 correction,
        which still holds.
        """
        return rounded_box(
            width=self._plate_width,
            depth=self.GROOVE_Y_HI - self.GROOVE_Y_LO,
            height=self.GROOVE_THICKNESS - self.PLATE_THICKNESS,
            corner_r=0.0,
            center=(0.0, (self.GROOVE_Y_LO + self.GROOVE_Y_HI) / 2.0, self.PLATE_THICKNESS),
        )

    def _build_ledge_teeth(self) -> cq.Workplane:
        """The 6 ledge locating teeth and the 4 notches between them
        (SS1.5) -- the reference's castellation at the insertion end.

        Two stacked bands over ``[TEETH_Y_LO, TEETH_Y_HI]``:

        * a continuous floor across the ledge width, raised to
          :attr:`NOTCH_FLOOR_Z` -- this IS the notch floor, so the notches
          are not cut, they are simply where the teeth are absent;
        * the 6 teeth themselves, rising from that floor to
          :attr:`LEDGE_Z_HI` at the three ``TOOTH_X_BANDS`` per half.

        Modelling the notches as "floor without a tooth on top" rather than
        as a subtractive cut keeps this additive-only, so it cannot
        interact with the tongue geometry built alongside it.
        """
        y_span = self.TEETH_Y_HI - self.TEETH_Y_LO
        part = rounded_box(
            width=2 * self._ledge_x_half,
            depth=y_span,
            height=self.NOTCH_FLOOR_Z - self.PLATE_THICKNESS,
            corner_r=0.0,
            center=(0.0, (self.TEETH_Y_LO + self.TEETH_Y_HI) / 2.0, self.PLATE_THICKNESS),
        )
        # Round 59: the teeth ride on the ledge, so they scale with it. The
        # outermost band ends at the nominal LEDGE_X_HALF (15.600); left
        # unscaled it stood proud of the clearance-adjusted ledge under it
        # and butted the housing's locating rib, which had been sized from
        # the lid's retreated walls. Interference was 0.0225 mm^3 at half the
        # flank clearance -- invisible seated, and found only by the
        # sideways-travel test.
        k = self._ledge_x_half / self.LEDGE_X_HALF
        for nom_lo, nom_hi in self.TOOTH_X_BANDS:
            x_lo, x_hi = nom_lo * k, nom_hi * k
            for side in (+1, -1):
                tooth = rounded_box(
                    width=x_hi - x_lo,
                    depth=y_span,
                    height=self.LEDGE_Z_HI - self.NOTCH_FLOOR_Z,
                    corner_r=0.0,
                    center=(
                        side * (x_lo + x_hi) / 2.0,
                        (self.TEETH_Y_LO + self.TEETH_Y_HI) / 2.0,
                        self.NOTCH_FLOOR_Z,
                    ),
                )
                part = part.union(tooth)
        return part

    @property
    def solid(self) -> cq.Workplane:
        return self._solid
