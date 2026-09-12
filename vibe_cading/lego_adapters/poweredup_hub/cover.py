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
    # ROUND 67: body 59.800 -> 60.000, measured side by side against the real
    # part ("from outer side of the two straight lines across the body").
    #
    # The 0.200 is taken at the TONGUE end by the owner's decision, so the
    # LATCH end is now the fixed datum -- the opposite of rounds 61-66. The
    # reason is the hook: it was certified working on the round-63 print, and
    # growing the body at that end would have pushed the whole latch 0.200 mm
    # deeper into the housing pocket. Nothing about the latch moves.
    #
    # Two consequences that follow from the same choice:
    #   * the tongue lengths below are measured from the NEW edge (32.200)
    #   * the window sill stays where it is, because it is dimensioned from
    #     the thumb-tab (latch) side -- see WINDOW_SILL_Y_CENTER
    PLATE_Y_LO = -27.800  # latch-end plate edge, now the held datum
    PLATE_Y_HI = 32.200   # = PLATE_Y_LO + 60.000 (measured, round 67)
    # The plate edge every latch constant below was MEASURED against. The
    # latch sub-assembly is built in that frame and translated to wherever
    # PLATE_Y_LO now sits, so re-datuming the lid's length never again means
    # editing a column of reference measurements (and losing what they record).
    LATCH_DATUM_Y = -30.800
    PLATE_THICKNESS = 1.200

    # --- Side-window sill (round 55) -- see _build_window_sill. ---
    #
    # ROUND 64: these are now MEASURED against the real housing's window, and
    # no longer derived from the Tray's extraction tab.
    #
    # Rounds 55-63 set the sill from PoweredUpHubBatteryTray.TAB_PAD_Y_HALF
    # (hardcoded rather than imported, because the Tray imports this class and
    # the reverse would cycle). That was right while the window was defined as
    # "the tab's outline plus clearance". The owner has now measured the sill
    # against the real part, and 23.500 wide offset 2.000 toward the tongue
    # end is not the tab's 24.000 centred -- so the two features have been
    # separated deliberately, not by drift.
    #
    # CONSEQUENCE, flagged rather than discovered: our Housing still cuts its
    # window from the tab, so this sill now overhangs that window's +Y edge by
    # 1.750. Against a REAL housing it should fit; against ours it will not.
    # test_window_sill_tracks_the_tab_width is xfailed for exactly this.
    WINDOW_SILL_WIDTH = 23.500     # measured (was 2 x 12.000 from the tab)
    # Measured, shifted toward the tongue end. ROUND 67: confirmed good on the
    # print and deliberately NOT moved when the body grew, per "hold the
    # position constant (relative to the thumb tab side)". Because the 0.200
    # was taken at the tongue end, PLATE_Y_LO did not move and this absolute
    # figure already IS anchored to the thumb-tab side -- so holding it means
    # changing nothing here. Stated explicitly because that is a coincidence
    # of this round's datum choice, not a property of the constant: had the
    # growth gone to the latch end, this would have needed +0.200.
    WINDOW_SILL_Y_CENTER = 2.000
    #: ``True`` puts the sill's outer face flush with the housing's outer
    #: wall. Rounds 55-63 held it one running clearance short, so that the
    #: worst case under the lid's own +-X play was flush rather than proud.
    #: The owner asked for flush ("inline with the housing outer wall") after
    #: measuring the printed part; the play argument is recorded here because
    #: it is the reason to revisit this first if the lid scuffs going in.
    WINDOW_SILL_FLUSH = True
    #: The housing's outer wall face the sill is made flush with.
    #:
    #: ROUND 65: 28.000 -> 27.800, and the change of SOURCE is the point.
    #: 28.000 was our own Housing's stud-grid envelope; 27.800 is the owner's
    #: measurement of the real part (outer width 55.600). The sill was
    #: therefore standing 0.200 mm proud of the wall it is meant to sit flush
    #: with -- the one thing "inline with the housing outer wall" rules out.
    #:
    #: This is the first constant on the Cover to be sourced from the real
    #: housing rather than from ours, which is the direction of travel: the
    #: Cover is being frozen against the real part and the Housing brought
    #: backward to it, not the reverse.
    HOUSING_WALL_X_OUTER = 27.800

    # --- Latch-end local thickening band (SS1.4) ---
    # ROUND 68: the OTHER of the two "straight lines across the body". Its
    # outer face was already on the plate edge; it was 0.800 wide against the
    # owner's measured 1.200, so it grows INBOARD to match. Both lines are now
    # 1.200 wide with their outer faces on their respective edges.
    #
    # Written in the LATCH frame (LATCH_DATUM_Y), so growing it inboard cannot
    # disturb the hook -- which is what "keep the pegs and hook unchanged, the
    # position should be relative to the hook side edge" requires.
    LATCH_BAND_Y_LO = -30.800   # == LATCH_DATUM_Y: on the plate edge
    LATCH_BAND_Y_HI = -29.600   # = LO + 1.200 (was -30.000, i.e. 0.800 wide)
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
    # ROUND 67: the four blades are TWO different lengths, both measured from
    # the body's end line -- the outer pair ("short pegs, on each side")
    # 2.000, the inner pair ("long pegs, toward the middle") 3.800.
    #
    # The model already had two lengths in the right sense (the outer pair
    # ends at the riser step, the inner pair carries on as the thin tip), so
    # this is a correction of 0.290 and 0.200, not a rework. The split itself
    # is no longer inferred from an LDraw proportion -- both numbers are now
    # measured, which retires the round-61 note that flagged them as guesses.
    #
    # Note TONGUE_Y_HI does not move: the body's edge grew out to meet the
    # tip (32.000 + 4.000 and 32.200 + 3.800 are the same place). The tongue
    # tip is, in effect, the one part of this end that was already right.
    TONGUE_STEP_Y = 34.200   # PLATE_Y_HI + 2.000 -- outer pair ends here
    TONGUE_Y_HI = 36.000     # PLATE_Y_HI + 3.800 -- inner pair ends here
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
    # Round 66: how far the gaps start OUTBOARD of the plate edge, shortening
    # them along Y from 4.000 to 3.200 so the blades stay joined at their root.
    #
    # Round 64 misread the same instruction ("the gaps are too tall, reduce
    # them by 0.800") as the gaps' HEIGHT and raised their floor to Z = 0.800.
    # Over the riser -- where the tongue is only PLATE_THICKNESS deep -- that
    # left 0.400 mm of slot in 1.200 mm of material, so the gaps read as
    # REMOVED rather than shortened. The Z extent is back to the full depth;
    # this is the dimension that was meant.
    #
    # Taken off the ROOT end, not the tip: the housing's locating rib enters
    # from the tip, so closing that end would stop the rib entering at all.
    # The X figures are unchanged -- "the width is OK".
    TONGUE_GAP_Y_INSET = 0.800

    # --- Locating groove / land (SS1.5) -- RESTORED round 22 ---
    # The inner face steps 1.200 -> 1.600 mm deep over Y in [30.0, 31.2],
    # full width. Rounds 18-21 built this and attributed it to the
    # BatteryTray's bottom rim; last round deleted it with the tray on that
    # attribution. The attribution was wrong: SS1.5 states plainly that
    # "the lid seats laterally on the 1.600 mm groove at Y in [30.0, 31.2]"
    # -- a lid-to-HOUSING seating feature that has nothing to do with the
    # tray. Restored here on the reference's own wording.
    # ROUND 68: this is one of the two "straight lines across the body" the
    # owner measures the cover's length between -- 1.200 wide, and its OUTER
    # face sits ON the plate edge.
    #
    # It was at [30.000, 31.200], 1.000 short of the edge, and the ledge-teeth
    # floor at [31.200, 32.400] stood at the same height right beside it. The
    # two therefore read as ONE raised band 2.400 wide that overshot the plate
    # edge by 0.200 -- neither the width nor the position the owner measures.
    # Merged into a single 1.200 band ending exactly on the edge.
    GROOVE_Y_LO = 31.000       # = GROOVE_Y_HI - 1.200
    GROOVE_Y_HI = 32.200       # == PLATE_Y_HI: the line locates on the edge
    GROOVE_THICKNESS = 1.600   # local plate thickness over the band

    # --- Ledge (SS1.5) ---
    # ROUND 68: the six locating TEETH are gone, at the owner's direction --
    # "get rid of the three dots behind each tongue, they are interfering with
    # the battery tray". Round 22 had restored them from the LDraw reference;
    # they are a real feature of the real lid, but they foul this project's
    # own tray, and the tray is the part that has to work.
    #
    # LEDGE_X_HALF and LEDGE_Y_LO survive the teeth because
    # PoweredUpHubHousing consumes both to shape its tongue rebate. They are
    # NOT vestigial -- deleting them would break that import -- but they are
    # now the ledge's own bounds only, with no castellation on them.
    LEDGE_X_HALF = 14.950      # == TONGUE_X_HALF (round 60, measured)
    # ROUND 68: 32.400 -> 32.200. The ledge now starts exactly at the plate
    # edge, because the band that used to occupy [32.200, 32.400] is gone
    # with the teeth. Leaving it at 32.400 would have opened a 0.200 mm step
    # of plain plate between the line and the ledge that nothing fills.
    LEDGE_Y_LO = 32.200

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
    #   * The plate-side member is a STRAIGHT vertical wall.
    #
    # Round 61 read "the leg is further out at the bottom than the top" as
    # "the leg is in the wrong place" and translated the whole assembly
    # outboard by 1.580 to get the peg's reach. The owner's correction --
    # "make the peg larger, not increasing the size of the hook" -- is exactly
    # that error. The leg goes back; the PEG grows instead.
    #
    # Look at the geometry before believing a table about it.
    #
    # === ROUND 63 -- the slope was on the wrong face ===
    #
    # Round 62 got the convergence right and then put ALL of it on the leg's
    # OUTER face, which made the hook a wedge -- thick at the plate, thin at
    # the tip. The owner's sketch shows the opposite: the outer wall runs
    # VERTICAL off the cover plate and only slopes near the top.
    #
    # Re-reading round 62's own reference plot confirms the sketch, and shows
    # the miss was there to be caught: between z = 3 and z = 11 the
    # reference's leg outer face moves 0.633 mm (4.5 deg -- essentially
    # vertical) while its INNER face moves 0.987. The leg THICKENS as it
    # rises; the aperture closes because its outboard wall climbs inboard,
    # not because the outside leans in. Round 62 read "the members converge"
    # off the plot and then chose, unprompted, which face carried it.
    #
    # Lesson, one level up from round 62's own: seeing the shape is not the
    # same as decomposing it. The plot showed convergence; only differencing
    # the two faces SEPARATELY says which one moves.
    U_WALL = 0.800                # LEG wall: 2 x 0.4 mm extrusion width
    FINGER_WALL = 1.600           # the straight, plate-rooted member
    U_FINGER_CL_Y = -31.550       # finger spans -32.350..-30.750 (1.600 wall)

    # --- The leg: vertical outer wall, sloped inner wall ---
    # The outer face is VERTICAL over the whole straight run -- the owner's
    # "the outer wall runs a straight portion that is vertical to the cover
    # plate". It carries the peg and the arms, so keeping it a single plane
    # is also what lets both be simple rectangles.
    LEG_OUT_Y = -34.604
    # Where the outer wall stops being vertical and slopes to the tip. From
    # the owner's sketch, ~79% of the hook's height.
    LEG_SLOPE_Z_FRAC = 0.786
    # Where the leg's INNER face reaches the finger and the aperture closes.
    # The reference closes at z = 11.2 of 13.000, i.e. 0.862.
    APEX_Z_FRAC = 0.862
    # The flat tip's width, measured inboard from the finger's inner face --
    # the finger stays vertical right to the top, so only the OUTER face
    # slopes in. That is what the sketch shows: one vertical edge full height,
    # one edge that kinks.
    CROWN_TIP_WIDTH = 2.400

    # --- The peg (the "tongue that joins the housing") ---
    # Measured: tip 5.000 mm outboard of the plate edge, ~1 mm tall, and
    # ROUND 63 -- rectangular in section. Round 62 built it as a right
    # triangle (ramped underside as a lead-in, flat top for retention), which
    # was engineering reasoning, not measurement, and the owner's sketch
    # overrules it: "the whole peg body needs to be rectangle".
    #
    # Consequence worth stating rather than discovering on the bed: the
    # underside is now a flat 1.196 mm horizontal overhang. It should bridge,
    # but if it droops this is the feature to look at first -- and the fix is
    # a chamfer on the UNDERSIDE only, never on the top face, which is what
    # takes the pull-out load.
    BEAD_Z_LO = 4.750
    BEAD_Z_HI = 5.750             # 1.000 tall, measured
    BARB_TIP_OUT = 5.000          # peg tip, outboard from LATCH_DATUM_Y

    # --- Stiffening arms above the peg (round 63) ---
    # Two small ribs at the hook's X extremes, sitting directly on top of the
    # peg -- the same trick as PAD_END_WALL_X does for the thumb tab, and
    # visible in Philo's own model. They brace the peg's root against the
    # bending moment that pull-out applies to it.
    ARM_X = 0.800                 # each arm's width, as the pad's end walls
    ARM_Z = 2.000                 # how far they rise above the peg
    ARM_OUT = 1.100               # how far they stand proud of the leg face
    # Round 67: the arms' top OUTBOARD corner is rounded, not square.
    #
    # Round 63 built them as plain blocks, which put a square shoulder at the
    # leading edge -- the hook travels +Z on insertion, so that corner is the
    # first thing to meet the housing wall and it catches rather than rides.
    # The radius turns it into a lead-in.
    #
    # Only that ONE corner. The arms' inboard-top corner is buried against the
    # leg, and their BOTTOM face sits on the peg, where a radius would cut
    # into the peg's own flat retention face -- the surface taking pull-out,
    # which the owner specifically asked to keep rectangular.
    ARM_TIP_R = 0.800             # inferred: 0.73 x ARM_OUT, leaves 1.200
    #                             # of full-protrusion arm below the curve
    # --- The thumb tab ---
    TAB_TIP_OUT = 6.000           # tab tip, outboard from LATCH_DATUM_Y
    # Thumb-pad plan outline: scalloped in Y across the hook width.
    # Round 62: the tab tip is TAB_TIP_OUT (6.000) outboard of the plate edge,
    # i.e. -36.800, superseding round 61's -36.990 (which came from the
    # earlier 6.240 depth reading). The 0.400 scallop step is kept as measured.
    #
    # X used to be six literal steps across the nominal hook footprint,
    # hardcoded at whatever hook_width was current. That went stale in round
    # 61 (hook_width 13.600 -> 12.200 left the pad 1.400 mm wider than both
    # the hook and the window -- silent, because the pad is union-only) and
    # went stale AGAIN at round 69 (12.200 -> 12.800), the same failure twice.
    # See self._pad_scallop() in __init__: the X values are now DERIVED from
    # LatchGeometry every time this class is built, so a third hook_width
    # change cannot repeat this -- there is no literal left to go stale.
    PAD_SCALLOP_Y_OUTER = -36.800
    PAD_SCALLOP_Y_INNER = -36.400
    # Derived, not a constant -- see self._pad_inner_y in __init__.
    #
    # Round 63 makes the leg's outer face vertical, so this is once again the
    # same value at every height and the derivation looks redundant. It is
    # KEPT because of what round 62 cost: with a sloped outer face, a fixed
    # bound here lost contact with the leg above z = 0.44. The pad stayed
    # fused to the PLATE, so `solids == 1` and every dimensional check passed,
    # while a thumb pad that no longer drives the leg is a dead release
    # mechanism that measures perfectly. Reading the leg's own face keeps that
    # failure impossible rather than merely absent at today's geometry.
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

    def __init__(
        self,
        profile: ToleranceProfile | str | None = None,
        window_sill: bool = True,
    ) -> None:
        """Build the lid.

        Parameters
        ----------
        profile:
            Tolerance profile, by name or instance; ``None`` takes the
            environment's default.
        window_sill:
            Build the two side-window sills (round 64). ``True`` is the
            default and the shipped part -- the sills close the 1.200 mm slot
            that would otherwise run right through the housing's side wall
            below the tray's extraction tab (see :meth:`_build_window_sill`).
            Pass ``False`` for a sill-less lid.

            This exists because the sills are the one feature on this part
            whose fit cannot be checked against our own Housing -- it is still
            on the LDraw datum while the sills are now measured against the
            real one. A knob makes "does the lid seat without them?" a
            separable question from "does the latch work?", so a single failed
            print does not confound the two.
        """
        if profile is None or isinstance(profile, str):
            prof = get_profile(profile) if isinstance(profile, str) else get_profile()
        else:
            prof = profile
        self._profile = prof
        self._window_sill = window_sill
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
        # Falsifier: move LEG_OUT_Y outboard to chase the reach and the
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
        #
        # PAD_SCALLOP_Y_OUTER rather than self._pad_scallop() here: this runs
        # before that derivation (below), and the tab's outermost Y does not
        # depend on hook_width, so the constant is exact -- not a shortcut.
        tab_tip = self.PAD_SCALLOP_Y_OUTER
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

        # Round 69: the thumb pad's plan-outline X positions, derived from
        # LatchGeometry rather than the hardcoded PAD_SCALLOP this replaces.
        # Six points, five equal steps across the NOMINAL hook footprint
        # [hook_pitch/2, hook_pitch/2 + hook_width] -- verified to reproduce
        # the old literal exactly at hook_width = 12.200 before this was
        # trusted to replace it (tmp/r69_pad_scallop.py).
        lo = self._latch.hook_pitch / 2.0
        step = self._latch.hook_width / 5.0
        ys = (
            self.PAD_SCALLOP_Y_OUTER, self.PAD_SCALLOP_Y_OUTER,
            self.PAD_SCALLOP_Y_INNER, self.PAD_SCALLOP_Y_INNER,
            self.PAD_SCALLOP_Y_OUTER, self.PAD_SCALLOP_Y_OUTER,
        )
        self._pad_scallop = tuple((lo + i * step, y) for i, y in enumerate(ys))

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
        part = part.union(self._latch_frame(self._build_peg_arms(+1)))
        part = part.union(self._latch_frame(self._build_peg_arms(-1)))
        part = part.union(self._latch_frame(self._build_pad_end_walls(+1)))
        part = part.union(self._latch_frame(self._build_pad_end_walls(-1)))
        part = part.union(self._latch_frame(self._build_thumb_pad(+1)))
        part = part.union(self._latch_frame(self._build_thumb_pad(-1)))
        part = part.union(self._build_tongue())
        part = part.union(self._build_locating_groove())
        if self._window_sill:
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
        * **+X** -- flush with the housing wall's outer face as of round 64
          (:attr:`WINDOW_SILL_FLUSH`). It used to stop one running clearance
          short, so that under the lid's own +-X play the worst case was
          flush rather than proud; see that constant for when to go back.
        * **-X** -- overlaps back into the plate for a real fused volume,
          not a coincident face.

        :attr:`HOUSING_WALL_X_OUTER` is a constant here rather than imported
        from :class:`~vibe_cading.lego_adapters.poweredup_hub.housing.PoweredUpHubHousing`,
        which imports this class -- the reverse would cycle. Round 65 changed
        where its VALUE comes from: it is now the owner's measurement of the
        real housing (27.800), not our own Housing's stud-grid envelope
        (28.000). Against the real part the old figure stood the sill 0.200 mm
        proud of the wall it is supposed to sit flush with.
        """
        housing_wall_x_outer = self.HOUSING_WALL_X_OUTER
        c = self._profile.free.radial
        seam_overlap = 0.050

        x_inner = self._plate_width / 2.0 - seam_overlap
        # Round 64: flush with the wall, per the owner's measurement, rather
        # than one running clearance short. See WINDOW_SILL_FLUSH.
        x_outer = housing_wall_x_outer - (0.0 if self.WINDOW_SILL_FLUSH else c)
        x_lo = min(x_sign * x_inner, x_sign * x_outer)
        x_hi = max(x_sign * x_inner, x_sign * x_outer)

        return rounded_box(
            width=x_hi - x_lo,
            depth=self.WINDOW_SILL_WIDTH,
            height=self.PLATE_THICKNESS,
            corner_r=0.0,
            center=((x_lo + x_hi) / 2.0, self.WINDOW_SILL_Y_CENTER, 0.0),
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
        # The scallop's X values span the NOMINAL hook footprint (see
        # self._pad_scallop in __init__). Scale them about the footprint's own
        # centre by the printed/nominal ratio so the pad takes the same
        # lateral clearance as the ribbon it sits on -- scaled rather than
        # shifted, so the scallop keeps its shape instead of having its two
        # end segments distorted.
        lg: LatchGeometry = self._latch
        nominal_c = lg.hook_pitch / 2.0 + lg.hook_width / 2.0
        k = self._hook_width_printed / lg.hook_width

        def sx(x: float) -> float:
            return side * (nominal_c + (x - nominal_c) * k)

        pts = [(sx(x), y) for x, y in self._pad_scallop]
        pts += [(sx(self._pad_scallop[-1][0]), self._pad_inner_y),
                (sx(self._pad_scallop[0][0]), self._pad_inner_y)]
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
        """``(outer, inner)`` Y of the outer member at height ``z``.

        Round 63: the OUTER face is vertical (:attr:`LEG_OUT_Y`) and only the
        INNER face climbs inboard, so the leg *thickens* as it rises and the
        aperture closes from its outboard side. Round 62 had this the other
        way round -- constant thickness with the outer face leaning in, making
        a wedge that was thick at the plate and thin at the tip.

        The reference settles it: over ``z = 3..11`` its leg's outer face
        moves 0.633 mm and its inner face 0.987. The outside is near-vertical;
        the inside does the work.

        Only valid below :meth:`_slope_z` -- above that the outer face is
        sloping to the tip and the profile in :meth:`_build_latch_u` is the
        authority. The peg and arms both live well below it.
        """
        finger_out, _ = self._finger_faces()
        base_in = self.LEG_OUT_Y + self.U_WALL
        t = min(max(z / self._apex_z(), 0.0), 1.0)
        return self.LEG_OUT_Y, base_in + t * (finger_out - base_in)

    def _apex_z(self) -> float:
        """Z at which the aperture closes and the two members merge."""
        return self._latch.hook_depth * self.APEX_Z_FRAC

    def _slope_z(self) -> float:
        """Z at which the leg's vertical outer wall starts sloping to the tip."""
        return self._latch.hook_depth * self.LEG_SLOPE_Z_FRAC

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
        _, base_in = self._leg_faces(0.0)
        z_apex = self._apex_z()
        z_slope = self._slope_z()
        crown_out = finger_in - self.CROWN_TIP_WIDTH

        # The aperture must open at the plate and close going up, and the leg
        # must not over-run the finger. A crossed profile still extrudes into
        # one valid-looking solid in OCCT -- the silent failure this file has
        # been caught by before, so it is checked rather than assumed.
        assert base_in < finger_out - 1e-9, (
            f"the leg's inner face at the plate ({base_in:.3f}) is not "
            f"outboard of the finger's outer face ({finger_out:.3f}) -- "
            "there is no aperture to open"
        )
        assert z_slope < lg.hook_depth - 1e-9, (
            f"the outer wall's vertical run ({z_slope:.3f}) reaches the hook "
            f"tip ({lg.hook_depth:.3f}) -- there is no slope to join it"
        )
        # The tip must be NARROWER than the section below it, or the "slope"
        # leans outward and the hook is an undercut that cannot be withdrawn.
        assert crown_out > self.LEG_OUT_Y + 1e-9, (
            f"the tip's outer edge ({crown_out:.3f}) is not inboard of the "
            f"vertical wall ({self.LEG_OUT_Y:.3f}) -- CROWN_TIP_WIDTH "
            f"({self.CROWN_TIP_WIDTH}) makes the top flare outward"
        )

        # One closed profile from the leg's outer foot: straight up the
        # VERTICAL outer wall, slope in to the flat tip, across it, then down
        # the finger's inner face -- which stays vertical the whole height --
        # across the foot, up the finger's aperture face to the apex, and back
        # down the leg's sloped inner face.
        wp = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0.0, 0.0, x_center - half_w))
            .moveTo(self.LEG_OUT_Y, 0.0)
            .lineTo(self.LEG_OUT_Y, z_slope)
            .lineTo(crown_out, lg.hook_depth)
            .lineTo(finger_in, lg.hook_depth)
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
        root, _ = self._leg_faces(self.BEAD_Z_HI)
        seam = 0.050   # bite back into the leg so this fuses by volume

        assert tip_y < root - 1e-9, (
            f"the peg's tip ({tip_y:.3f}) is not outboard of the leg face it "
            f"grows from ({root:.3f}) -- it would be a notch, not a peg"
        )

        return rounded_box(
            width=self._hook_width_printed,
            depth=(root + seam) - tip_y,
            height=self.BEAD_Z_HI - self.BEAD_Z_LO,
            corner_r=0.0,
            center=(
                x_center,
                (tip_y + root + seam) / 2.0,
                self.BEAD_Z_LO,
            ),
        )

    def _build_peg_arms(self, side: int) -> cq.Workplane:
        """The two stiffening arms sitting on top of the peg (round 63).

        One at each X extreme of the hook, exactly the trick
        :meth:`_build_pad_end_walls` already plays for the thumb tab, and
        present in Philo's own model. They brace the peg's root against the
        bending moment pull-out applies to it: the peg is a cantilever off a
        0.800 mm wall, and the load acts at its tip.

        Deliberately at the ENDS, not the middle. The peg's root wants support
        where the section is stiffest in torsion; a single central rib would
        also sit exactly where the leg needs to flex to release.
        """
        x_center, half_w = self._hook_span(side)
        root, _ = self._leg_faces(self.BEAD_Z_HI)
        y_outer = root - self.ARM_OUT
        seam = 0.050

        assert y_outer > self.LATCH_DATUM_Y - self.BARB_TIP_OUT, (
            f"the arms ({y_outer:.3f}) stand further outboard than the peg "
            f"({self.LATCH_DATUM_Y - self.BARB_TIP_OUT:.3f}) -- they would "
            "foul the housing before the peg ever engaged it"
        )

        z_lo = self.BEAD_Z_HI
        z_hi = z_lo + self.ARM_Z
        r = self.ARM_TIP_R
        y_root = root + seam

        assert r < self.ARM_OUT + seam and r < self.ARM_Z, (
            f"ARM_TIP_R ({r}) does not fit the arm it rounds "
            f"({self.ARM_OUT} out x {self.ARM_Z} tall)"
        )

        # Profile in YZ, extruded across ARM_X. Built as an explicit arc rather
        # than a fillet() on a box: OCCT fillets on a small feature that also
        # gets unioned into a larger solid are a known source of silent
        # failures here, and an arc through three known points cannot collapse.
        #
        # Up the outboard face, round the top-outboard corner, across the top
        # to the leg, and down the leg face. Arc centre is (y_outer + r,
        # z_hi - r), so the midpoint is that centre offset by r at 135 deg.
        arc_mid = (
            y_outer + r - r * 0.7071067811865476,
            z_hi - r + r * 0.7071067811865476,
        )
        arms = None
        for edge in (-1, +1):
            x_edge = x_center + edge * half_w
            x_start = min(x_edge, x_edge - edge * self.ARM_X)
            wp = (
                cq.Workplane("YZ")
                .transformed(offset=cq.Vector(0.0, 0.0, x_start))
                .moveTo(y_root, z_lo)
                .lineTo(y_outer, z_lo)
                .lineTo(y_outer, z_hi - r)
                .threePointArc(arc_mid, (y_outer + r, z_hi))
                .lineTo(y_root, z_hi)
            )
            block = wp.close().extrude(self.ARM_X)
            arms = block if arms is None else arms.union(block)
        return arms

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
        # Round 68: LEDGE_Y_LO is now the plate edge itself, so the riser and
        # the plate start together. Rounds 22-67 held the ledge 0.400 back and
        # let the ledge teeth carry its height forward over that strip; with
        # the teeth removed, keeping the setback would leave a step of plain
        # plate with nothing on it.
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
        # Round 66: the gaps start TONGUE_GAP_Y_INSET outboard of the plate
        # edge instead of overcutting past it, shortening them by that much
        # and leaving the blades joined at their root. No overcut on this
        # face -- it is a real internal face now, not a seam to clear.
        gap_y_lo = self.PLATE_Y_HI + self.TONGUE_GAP_Y_INSET
        gap_y_hi = self._tongue_y_hi + oc
        gap_z_lo = -oc          # full depth again; see TONGUE_GAP_Y_INSET
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
                    height=(self.RISER_Z_HI + oc) - gap_z_lo,
                    corner_r=0.0,
                    center=(
                        (x_lo + x_hi) / 2.0,
                        (gap_y_lo + gap_y_hi) / 2.0,
                        gap_z_lo,
                    ),
                )
            )

        # ROUND 77 -- give the two SIDE sockets the same root web the three
        # interior ones have, so all five open at the same Y.
        #
        # Owner: *"On the plate, the length of the sockets on the sides
        # should be the same as the 3 sockets in the middle, adjust it."*
        # Measured before this: the interior sockets open at Y 33.025
        # (= PLATE_Y_HI + TONGUE_GAP_Y_INSET, the round-66 web that keeps the
        # blades joined at their root), but the side sockets -- the strips
        # between the riser's outer edge and the plate edge -- open at
        # 32.225, i.e. straight off the plate edge, 0.800 longer.  They were
        # never gap-CUT at all; they are simply where the tongue stops in X,
        # so the web that shortens the others never applied to them.
        #
        # Adding it here rather than widening the tongue: the tongue's own
        # outer extent (RISER_X_HALF) is measured ground truth and must not
        # move.  This is only the missing root web, spanning the same Y band
        # and the same height as the interior webs.
        for sign in (-1.0, 1.0):
            lo, hi = sorted((sign * self.RISER_X_HALF,
                             sign * self.PLATE_WIDTH / 2.0))
            tongue = tongue.union(
                rounded_box(
                    width=hi - lo,
                    depth=self.TONGUE_GAP_Y_INSET,
                    height=self.RISER_Z_HI,
                    corner_r=0.0,
                    center=((lo + hi) / 2.0,
                            self.PLATE_Y_HI + self.TONGUE_GAP_Y_INSET / 2.0,
                            0.0),
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

    @property
    def solid(self) -> cq.Workplane:
        return self._solid
