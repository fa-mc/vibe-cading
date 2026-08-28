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

    # --- Plate (design brief K3, SS1.1) ---
    PLATE_WIDTH = 54.400
    PLATE_Y_LO = -30.800  # latch-end plate edge
    PLATE_Y_HI = 32.000   # tongue-end plate edge
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
    TONGUE_X_HALF = 15.600   # tip half-width (Tongue A only, retention-critical, unchanged)
    RISER_X_HALF = 26.000    # riser half-width (round 20, C4 -- restores Tongue B's plan outline)
    TONGUE_STEP_Y = 33.378
    TONGUE_Y_HI = 34.400
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
    TONGUE_GAP_X_INNER = 0.800   # centre gap is |X| <= this (half-width)
    TONGUE_RIB_X_HI = 17.200     # rib gap spans TONGUE_X_HALF .. this

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
    TOOTH_X_BANDS = ((0.800, 2.000), (7.600, 8.800), (14.400, 15.600))
    NOTCH_FLOOR_Z = 1.600
    LEDGE_Z_HI = 2.800         # == RISER_Z_HI; the teeth rise to the ledge top
    LEDGE_X_HALF = 15.600      # == TONGUE_X_HALF
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
    U_WALL = 0.800                # 2 x 0.4 mm extrusion width
    U_CENTRELINE_SEP = 2.400      # -> bend radius 1.200, inner radius 0.800
    U_FINGER_CL_Y = -31.150       # finger spans -31.550..-30.750
    # Round 39: the BEND is thicker than the legs. It is the most highly and
    # most cyclically loaded section of the spring, so it carries more
    # material -- but NOT by shrinking the inner radius, which would raise the
    # stress concentration it exists to avoid. The inner radius stays at
    # 0.800 (= 1.00 x leg wall) and the OUTER surface flares instead, from
    # U_FLARE_Z up to the bend. Because the outer arc radius grows to
    # U_BEND_WALL + 0.800, the bend centre drops so the crown still lands
    # exactly on hook_depth.
    # 1.050, not 1.200: the reference's own bend wall measures 1.047, and at
    # 1.200 the flare put the leg's outer face at -34.350 -- 0.050 mm off the
    # housing wall, and cost 14 points of agreement for material the reference
    # does not have. Still 1.31x the leg wall, which is the point.
    U_BEND_WALL = 1.050
    U_FLARE_Z = 8.000

    BEAD_Z_LO = 4.750
    BEAD_Z_HI = 5.750
    BEAD_PEAK_Y = -34.220
    BEAD_BASELINE_Y = -34.000
    # Round 38: -34.000 -> -33.900. The U ribbon's leg outer face is at
    # -33.950, so the old value left a 0.050 mm gap and the pad (and the
    # end walls, which share this bound) came off as separate solids.
    # Now overlaps the leg by 0.050 -- volume overlap, not a touching face.
    # Thumb-pad plan outline: scalloped in Y across the hook width.
    PAD_SCALLOP = (
        (5.600, -35.600), (8.320, -35.600), (11.040, -35.200),
        (13.760, -35.200), (16.480, -35.600), (19.200, -35.600),
    )
    PAD_INNER_Y = -33.900
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
    PAD_END_WALL_Y = -35.400
    PAD_END_WALL_Z_HI = 2.791

    def __init__(self, profile: ToleranceProfile | str | None = None) -> None:
        if profile is None or isinstance(profile, str):
            prof = get_profile(profile) if isinstance(profile, str) else get_profile()
        else:
            prof = profile
        self._profile = prof
        self._latch = get_latch_geometry(prof)
        self._solid = self._build()

    def _build(self) -> cq.Workplane:
        part = self._build_plate()
        part = part.union(self._build_latch_u(+1))
        part = part.union(self._build_latch_u(-1))
        part = part.union(self._build_leg_bead(+1))
        part = part.union(self._build_leg_bead(-1))
        part = part.union(self._build_pad_end_walls(+1))
        part = part.union(self._build_pad_end_walls(-1))
        part = part.union(self._build_thumb_pad(+1))
        part = part.union(self._build_thumb_pad(-1))
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

        x_inner = self.PLATE_WIDTH / 2.0 - seam_overlap
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
        y_span = self.PLATE_Y_HI - self.PLATE_Y_LO
        plate = rounded_box(
            width=self.PLATE_WIDTH,
            depth=y_span,
            height=self.PLATE_THICKNESS,
            corner_r=0.0,  # sharp corners, measured (SS1.1)
            center=(0.0, (self.PLATE_Y_LO + self.PLATE_Y_HI) / 2.0, 0.0),
        )
        band_span = self.LATCH_BAND_Y_HI - self.LATCH_BAND_Y_LO
        band = rounded_box(
            width=self.PLATE_WIDTH,
            depth=band_span,
            height=self.LATCH_BAND_THICKNESS - self.PLATE_THICKNESS,
            corner_r=0.0,
            center=(
                0.0,
                (self.LATCH_BAND_Y_LO + self.LATCH_BAND_Y_HI) / 2.0,
                self.PLATE_THICKNESS,
            ),
        )
        return plate.union(band)

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
        pts = [(side * x, y) for x, y in self.PAD_SCALLOP]
        pts += [(side * self.PAD_SCALLOP[-1][0], self.PAD_INNER_Y),
                (side * self.PAD_SCALLOP[0][0], self.PAD_INNER_Y)]
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
        lg: LatchGeometry = self._latch
        half_w = lg.hook_width / 2.0
        x_center = side * (lg.hook_pitch / 2.0 + half_w)
        depth = self.PAD_INNER_Y - self.PAD_END_WALL_Y
        y_mid = (self.PAD_END_WALL_Y + self.PAD_INNER_Y) / 2.0

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

    def _build_latch_u(self, side: int) -> cq.Workplane:
        """The latch U -- one constant-thickness ribbon (round 38).

        A hairpin spring: down the release leg, around the bend, up the
        finger. Built by offsetting an OPEN centreline, which
        :meth:`cadquery.Workplane.offset2D` closes into a constant-thickness
        ribbon with rounded end caps in a single call.

        The centreline starts at ``z = U_WALL/2`` so those end caps land
        exactly on ``z = 0`` rather than below it.

        **Validation is not optional here.** Per the research, offset failures
        are SILENT: a self-intersecting ribbon still returns one closed wire
        with ``solids() == 1`` and an area within 0.01% of nominal, and
        ``isValid()`` returns True for tight-radius collapses. The design keeps
        the centreline bend radius at 3.0x the offset distance (measured
        threshold: 1.05x), well clear of that regime.
        """
        lg: LatchGeometry = self._latch
        half_w = lg.hook_width / 2.0
        x_center = side * (lg.hook_pitch / 2.0 + half_w)

        d = self.U_WALL / 2.0
        finger_cl = self.U_FINGER_CL_Y
        leg_cl = finger_cl - self.U_CENTRELINE_SEP

        # Aperture faces -- these set the INNER arc and never move.
        leg_in = leg_cl + d
        finger_out = finger_cl - d
        y_c = (leg_in + finger_out) / 2.0
        r_in = (finger_out - leg_in) / 2.0          # 0.800 = 1.00 x U_WALL

        # Outer faces: nominal down the legs, flared at the bend.
        leg_out = leg_cl - d
        finger_in = finger_cl + d
        r_out = r_in + self.U_BEND_WALL
        z_bend = lg.hook_depth - r_out              # crown lands on hook_depth
        leg_out_bend = y_c - r_out
        finger_in_bend = y_c + r_out

        # One closed U profile: up the leg's outer face, over the crown, down
        # the finger's inner face, across the foot, up the finger's aperture
        # face, around the inner arc, down the leg's aperture face, close.
        wp = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0.0, 0.0, x_center - half_w))
            .moveTo(leg_out, 0.0)
            .lineTo(leg_out, self.U_FLARE_Z)
            .lineTo(leg_out_bend, z_bend)
            .threePointArc((y_c, lg.hook_depth), (finger_in_bend, z_bend))
            .lineTo(finger_in, self.U_FLARE_Z)
            .lineTo(finger_in, 0.0)
            .lineTo(finger_out, 0.0)
            .lineTo(finger_out, z_bend)
            .threePointArc((y_c, z_bend + r_in), (leg_in, z_bend))
            .lineTo(leg_in, 0.0)
        )
        return wp.close().extrude(lg.hook_width)


    def _build_leg_bead(self, side: int) -> cq.Workplane:
        """The retention bead: a local thickening of the leg's outer face.

        In the reference this is not a bolted-on feature but a bulge in the
        leg's own wall (thickness 0.70 -> 1.028 at z = 5.0), which is why
        modelling it as a separate body kept looking wrong.
        """
        lg: LatchGeometry = self._latch
        half_w = lg.hook_width / 2.0
        x_center = side * (lg.hook_pitch / 2.0 + half_w)
        leg_outer = self.U_FINGER_CL_Y - self.U_CENTRELINE_SEP - self.U_WALL / 2.0
        z_c = (self.BEAD_Z_LO + self.BEAD_Z_HI) / 2.0
        r_b = (self.BEAD_Z_HI - self.BEAD_Z_LO) / 2.0
        protrusion = self.BEAD_BASELINE_Y - self.BEAD_PEAK_Y   # 0.220
        axis_y = leg_outer + (r_b - protrusion)
        seam = 0.05

        disc = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0.0, 0.0, x_center - half_w))
            .center(axis_y, z_c)
            .circle(r_b)
            .extrude(lg.hook_width)
        )
        keep = cq.Workplane("XY").box(120.0, 40.0, 40.0).translate(
            (0.0, leg_outer + seam - 20.0, z_c))
        return disc.intersect(keep)

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
        riser_depth = self.TONGUE_STEP_Y - self.PLATE_Y_HI
        riser_y_center = (self.PLATE_Y_HI + self.TONGUE_STEP_Y) / 2.0
        # Round 22: the full-height riser starts at LEDGE_Y_LO, not at the
        # plate edge -- see that constant. The 0.400 mm strip in between is
        # plain plate, and the teeth built by _build_ledge_teeth carry the
        # ledge height forward from there.
        ledge_depth = self.TONGUE_STEP_Y - self.LEDGE_Y_LO
        riser_inner = rounded_box(
            width=2 * self.TONGUE_X_HALF,
            depth=ledge_depth,
            height=self.RISER_Z_HI,
            corner_r=0.0,
            center=(0.0, (self.LEDGE_Y_LO + self.TONGUE_STEP_Y) / 2.0, 0.0),
        )
        riser_outer = rounded_box(
            width=2 * self.RISER_X_HALF,
            depth=riser_depth,
            height=self.PLATE_THICKNESS,
            corner_r=0.0,
            center=(0.0, riser_y_center, 0.0),
        )
        tip = rounded_box(
            width=2 * self.TONGUE_X_HALF,
            depth=self.TONGUE_Y_HI - self.TONGUE_STEP_Y,
            height=self.RISER_Z_HI - self.TIP_Z_LO,
            corner_r=0.0,
            center=(
                0.0,
                (self.TONGUE_STEP_Y + self.TONGUE_Y_HI) / 2.0,
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
        gap_y_hi = self.TONGUE_Y_HI + oc
        gap_bands = [(-self.TONGUE_GAP_X_INNER, self.TONGUE_GAP_X_INNER)]
        for sign in (-1.0, 1.0):
            lo, hi = sorted((sign * self.TONGUE_X_HALF, sign * self.TONGUE_RIB_X_HI))
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
            width=self.PLATE_WIDTH,
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
            width=2 * self.LEDGE_X_HALF,
            depth=y_span,
            height=self.NOTCH_FLOOR_Z - self.PLATE_THICKNESS,
            corner_r=0.0,
            center=(0.0, (self.TEETH_Y_LO + self.TEETH_Y_HI) / 2.0, self.PLATE_THICKNESS),
        )
        for x_lo, x_hi in self.TOOTH_X_BANDS:
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
