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

"""PoweredUpHubHousing -- battery-box shell for the Powered Up hub battery box.

Dimensions are read from the LDraw parts library (CC BY 4.0, author
Philippe Hurbain) part ``25560`` ("Electric Control+ Hub Bottom"), as
extracted in
``docs/design_plans/2026-08-19-poweredup-hub-battery-box_ldraw-housing-geometry.md``
(no LDraw ``.dat`` file, converted geometry, or render is committed to this
repo -- only independently-written measurements and from-scratch CadQuery
code).
Full design rationale:
``docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md``,
*Multi-part structure -> Housing*.

Per that design, this was an exact copy of the real ``25560`` shell's own
**shell envelope** -- ``72.0 x 71.2 x 29.6 mm``.  **Round 22 caps the
height at 3 studs (24.0 mm)** by explicit user direction -- this part is
the BOTTOM LAYER of a two-layer box, not a whole hub -- so the built
envelope is now ``72.0 x 71.2 x 24.0 mm``: an exact copy in plan, a
declared departure in Z.  See :attr:`PoweredUpHubHousing.DECK_Z`.  There
is also a scoped, deliberate departure at the two lid-retention regions: the latch end
(``-Y``) and the tongue end (``+Y``) each carry a single wall instead of
LEGO's real two-skin sandwich construction, per the design's *Single wall
at BOTH ends* section.  Everything else -- overall envelope, the four
liftarm arms, the twelve pin holes, the wall step at height 22.0 mm, the
side windows, the port ribs -- is an exact copy.

**Round 20 correction (finding H1, blocking)**: earlier rounds quoted
``25560``'s LDraw **bounding box** (``72.0 x 71.2 x 33.8 mm``) as "the
envelope" without separately noting that the real *shell* tops out
``4.2 mm`` short of that box -- only two narrow connector-port tubes
(``26.9 mm^2`` of face, now ruled out of scope -- see *Known
simplifications*) reach ``Z = 33.8``.  The shell's own top face --
``3,469.6 mm^2`` of up-facing area -- is at ``Z = 29.6``.  The retired
``TOP_Z`` (``33.8 mm``) figure quoted by rounds 1-19 is the bounding box,
not the shell.  (Round 22 then cut the class's own height below both
figures, to ``DECK_Z = 24.0 mm``, for the design reason above.)
"""

from __future__ import annotations

import math

import cadquery as cq

from vibe_cading.cq_utils import cylinder, rounded_box
from vibe_cading.lego.constants import STUD_PITCH
from vibe_cading.lego.cutters.technic_pin_hole import TechnicPinHole
from vibe_cading.lego_adapters.poweredup_hub.battery_tray import (
    PoweredUpHubBatteryTray,
)
from vibe_cading.lego_adapters.poweredup_hub.cover import PoweredUpHubCover
from vibe_cading.lego_adapters.poweredup_hub.latch_geometry import (
    LatchGeometry,
    get_latch_geometry,
)
from vibe_cading.print_settings import ToleranceProfile, get_profile


class PoweredUpHubHousing:
    """Exact copy of LEGO housing shell ``25560``, minus LEGO's two-skin
    retention sandwiches at the latch and tongue ends (single wall there
    instead -- see class docstring above).

    Origin / datum
    ---------------
    ``(0, 0, 0)`` is the housing's **bottom face** -- the same datum as
    :class:`~vibe_cading.lego_adapters.poweredup_hub.cover.PoweredUpHubCover`'s
    outer face (the lid *is* the floor, per the design brief's *Housing*
    section: "the bottom is otherwise wide open"), so a
    :class:`PoweredUpHubCover` instance built with no transform at all is
    already in its seated position relative to this class -- both parts
    share one LDraw parent frame (``docs/design_plans/2026-08-19-poweredup-hub-battery-box_ldraw-housing-geometry.md`` SS11.1:
    the lid-to-housing LDraw transform is a pure translation with no
    rotation and no sign flip, and that translation is already baked into
    each class's own ``Z = 0`` datum). Every feature extrudes ``+Z`` from
    there, up to :attr:`DECK_Z` (24.000 mm -- 3 studs, the round-22
    bottom-layer cap; see that constant's own comment). X is
    centred on the housing's mid-width (hole plane at ``X = +-32.000``);
    Y follows the same frame as the Cover (latch end at ``-Y``, tongue end
    at ``+Y``).

    Kept, as an exact copy (design brief *Housing*):
        - Overall envelope 72.0 x 71.2 mm **in plan** (with the arm
          bosses included in the 72.0 mm X figure) -- the shell's own
          envelope, not the LDraw part's bounding box (round 20, H1).
          Height is the round-22 3-stud cap, not the reference's own.
        - Stepped side walls (0.8 mm, outward step at height 22.0 mm).
        - Four arms -- literally LDraw 3-hole liftarms, reusing
          :class:`~vibe_cading.lego.technic_beam_perp.PerpendicularHolesLiftarm`
          per the TL round's decision (composed, not a class-contract
          change) -- with the real 12-hole pin map, the middle-hole boss,
          and the one-sided three-step middle bore.
        - Two side windows (handle access -- these cleared the deleted
          tray's extraction tabs, and now clear
          :class:`PoweredUpHubCover`'s own re-homed side handles),
          simplified to a single
          rectangular cutout each -- see *Known simplifications*.
        - The tongue-end rebate (a lap, not a snap -- fully specified from
          LDraw) and the latch-end catch (derived, absent from LDraw, from
          the shared :class:`~vibe_cading.lego_adapters.poweredup_hub.latch_geometry.LatchGeometry`
          parameter object and :class:`PoweredUpHubCover`'s own barb
          geometry -- see *Latch catch derivation* below).

    Deliberately departed from an exact copy (design brief *Single wall at
    BOTH ends*, scoped to the latch-end pocket and the tongue-end slot
    region only):
        - **Single wall** at both retention ends, instead of LEGO's real
          two-skin sandwich.  The latch-end wall is locally thickened at
          each catch (undercut + material-behind floor, asserted in code
          -- see :meth:`_build_latch_wall`).  The tongue-end wall
          reproduces only the rebate step (no thickness floor -- a step,
          not an undercut).
        - The 6 locating teeth and the 1.6 mm locating groove are dropped
          from this interface entirely (confirmed non-load-bearing here;
          the groove survived on :class:`PoweredUpHubCover` for the tray
          interface, and round 22 deleted the tray with it).

    Known simplifications (documented deviations, all cosmetic /
    non-load-bearing unless noted, per this project's Experimental
    Integrity convention):
        - **Top deck** modelled as a solid slab, ``DECK_THICKNESS``
          (2.082 mm) thick, spanning ``Z`` in
          ``[DECK_Z - DECK_THICKNESS, DECK_Z]`` (``[22.400, 24.000]``)
          rather than a hollow shell -- the real deck's own *internal*
          structure (corrugated AA-cell cradle ceiling, four connector-port
          keying ribs, one asymmetric screw boss) is genuinely unreadable
          from LDraw as a hollow-shell wall thickness, so a solid slab at
          the shell's own measured top-face position is the conservative
          choice (round 20, H1 -- corrected from an earlier version that
          built this slab entirely *above* ``DECK_Z``, 4.2 mm outside the
          real shell's own envelope). The corrugated cradle ceiling, the
          keying ribs, and the screw boss remain omitted -- purely
          cosmetic/non-interface features, per the design brief's own
          "Explicitly NOT decided by this TL round" note leaving the
          middle-hole neck relief as a Designer/Developer fidelity call
          (also omitted here for the same reason). **Connector-port tubes
          explicitly out of scope** (round 20, H1): the reference's two
          narrow tubes reaching ``Z = 33.8`` (``26.9 mm^2`` of face) are
          hub-electronics connector conduits with no function in a battery
          box -- omitted, not silently dropped.
        - **Side windows** simplified from LDraw's ramped-end trapezoid
          profile to a piecewise-linear taper (round 20, H3; re-corrected
          round 21, H3/RH3 -- see :attr:`WINDOW_TAPER_PROFILE`'s own note):
          flat at half-width :attr:`WINDOW_Y_HALF` (12.000 mm) for
          ``Z <= WINDOW_SHOULDER_Z`` (4.8 mm), then tapering through the
          reference's own measured shoulder points to a genuine FLAT top
          face (half-width 8.400 mm at ``Z = 8.400``, matching a real
          planar face in the LDraw source) rather than a point apex --
          round 20's 8.500 mm figure replaced that flat top with a point,
          corrected here. (An earlier round-18 note here recorded that
          this simplification had been *masking* the deleted BatteryTray's
          own Z-datum error; both the masking and the tray are gone as of
          round 22. The windows now clear
          :class:`PoweredUpHubCover`'s re-homed side handles instead --
          see the cross-part tests.)
        - **End-wall X extent** (latch and tongue walls) simplified to a
          constant :attr:`WALL_X_OUTER_LOWER` (28.0 mm) across their full
          height, rather than stepping to match the side walls' own
          22.0 mm step -- the two walls are a structurally distinct
          feature family from the side walls' stepped profile, and using
          the wider (lower-band) figure throughout is again a
          material-only-added simplification. **Re-verified round 18
          (finding C8)**: this ``28.0 mm`` figure matches the real part's
          own end-wall extent exactly -- the earlier ``|x| <= 32.0 mm``
          reference-doc figure was itself a transcription error in
          ``docs/design_plans/2026-08-19-poweredup-hub-battery-box_ldraw-housing-geometry.md``, not a modelling gap here.
        - **End-wall thickness** -- **round 22**: both end walls are
          thickened inward to meet :class:`PoweredUpHubCover`'s own plate
          edges (latch end to ``PLATE_Y_LO``, tongue end to
          ``PLATE_Y_HI`` above the riser), closing the open perimeter slot
          the round-18 single-skin walls left. The latch-U band is cut
          straight back to the original 1.200 mm skin
          (:meth:`_build_latch_clearance`), so no verified latch interface
          moved -- see :attr:`LATCH_WALL_THICKNESS`.
        - **End-wall Z extent** (latch and tongue walls), ``Z`` in
          ``[0, END_WALL_Z_HI]`` (``0..24.0 mm``) -- round 18 (finding C3)
          originally built these full-height to ``DECK_Z`` (``29.6 mm``,
          a documented additive-only simplification); round 21 (finding
          RH1) corrects this to the real end wall's own measured height
          (``24.0 mm``, matching the reference exactly) -- this was the
          single largest remaining visual difference after round 20's H1
          fix. This class's own single-wall departure still scopes the
          latch/tongue ends away from an exact copy of LEGO's two-skin
          sandwich (``3.6..22.0 mm`` per ``docs/design_plans/2026-08-19-poweredup-hub-battery-box_ldraw-housing-geometry.md``)
          -- see *Single wall at BOTH ends* above -- but the Z extent
          itself is no longer over-height.
        - **Arm cross-section** stays at the class's own
          Cailliau-calibrated ``BEAM_WIDTH`` (7.8 mm *nominal*, vs.
          LDraw's idealised 7.2 mm) -- the design brief's explicit "not
          changed, deliberately" ruling (real moulded liftarms measure
          7.4-7.8 mm; LDraw's 7.2 mm is a grid-snapped idealisation) still
          governs the shared :class:`PerpendicularHolesLiftarm` class
          itself, and the arm's *root* region (root-bridge/wall-overlap
          logic, hidden internal structure) still reads the class's own
          untrimmed ``BEAM_WIDTH / 2`` edge. **The outboard edge is a
          documented exception** (design brief round 16, Escalation 7):
          because Success Criterion #1 already pins the housing's overall
          X envelope to exactly ``72.0 mm``, a housing-local, one-sided
          ``.cut()`` trims the arm's outboard face to LDraw's literal
          ``3.600 mm`` half-width before the boss/middle-bore code reads
          it -- so the boss and middle bore land at the real
          ``35.6/36.0 mm`` figures, not the class's own ``3.9 mm``
          Cailliau half-width, on this one (outboard) edge only. **As-built
          width is therefore 7.500 mm, not 7.8 mm** (round 20 correction --
          the design record's earlier "7.8 mm as built" language was
          wrong; the geometry itself is unchanged and correct: inboard
          edge untouched at the nominal ``X = 28.100``, outboard edge
          trimmed to the real ``X = 35.600``, giving ``35.600 - 28.100 =
          7.500 mm`` as the deliberate, direct consequence of round 16's
          asymmetric outboard-only trim).
        - **Arm faces NOT dished** (round 42, user direction -- a
          deliberate departure, reversing round 20's H2). The reference
          cuts a shallow relief pocket into both faces of each arm,
          leaving a ``2.756 mm`` web; rounds 20-41 reproduced it exactly.
          It is the wrong shape to *print*: it thins the section of a
          cantilevered arm precisely where bending stress peaks, and asks
          an FDM machine to bridge a thin web. This class keeps the plain
          full-thickness beam instead. Fidelity to the reference's
          appearance is knowingly traded for strength here; the arm's
          function -- hole positions, pitch, envelope -- is unchanged.
        - **Middle hole is a blind standard pin hole** (round 42): a real
          :class:`~vibe_cading.lego.cutters.technic_pin_hole.TechnicPinHole`
          entered at the boss tip and floored at the side wall's outer
          face, replacing a hand-rolled three-step bore whose relief
          punched through into the battery cavity.

    Latch interface (round 40)
    --------------------------
    This class mates the cover's **hairpin-spring** latch, and carries no
    catch boss, undercut slot, or keeper nub -- those belonged to a
    barb-on-the-finger the cover has not had since round 38, and they were
    measured dead before removal (the slot cutter overlapped 0.0000 mm^3 of
    the built wall; the nub was already not unioned; the boss's only
    remaining effect was a 0.150 mm overhang the wall itself provides). The
    interface is now three surfaces, each derived from the cover rather than
    re-typed:

    * :meth:`_build_latch_clearance` -- the channel the U ribbon lives in,
      ``hook_width`` wide and reaching ``hook_depth`` **plus a running
      clearance**, so the crown is not butted against the wall above it;
    * :meth:`_build_finger_windows` -- the through-slot the thumb pad
      passes into, likewise clearance-widened against the pad's own span;
    * :meth:`_build_latch_land` -- the rail the release-leg bead snaps
      over, which is where retention actually comes from.

    Because clearances that go to exactly zero enclose no volume, a boolean
    intersection reports 0.000 mm^3 for them and reads as a *pass*. Both
    clearance-bearing surfaces above are therefore pinned by explicit
    minimum-gap tests, not by the seated-interference test alone.

    Parameters
    ----------
    profile:
        Manufacturing tolerance profile, forwarded to the shared
        :class:`~vibe_cading.lego_adapters.poweredup_hub.latch_geometry.LatchGeometry`
        and to the arms' :class:`~vibe_cading.lego.technic_beam_perp.PerpendicularHolesLiftarm`
        pin-hole cutters. Accepts a
        :class:`~vibe_cading.print_settings.ToleranceProfile` instance, a
        profile name string, or ``None`` for the process-global default.
    """

    # --- Envelope (SS0, SS1) ---
    # ROUND 73 -- owner-measured with calipers on the real part, superseding
    # the LDraw-derived 35.600. "Length between the outer end walls =
    # 71.350" -> HALF_Y = 35.675. This is a ground-truth input, not derived
    # from anything else in this class -- but it CASCADES into every
    # constant below that is itself derived from HALF_Y (DECK_Y_LO/HI,
    # BOTTOM_ROUND_CY, the end-socket floor, UPPER_Y_HI/LO, LATCH_Y,
    # TONGUE_Y): those moves are unavoidable consequences of this one
    # ground-truth change, not separate decisions, and none of them touch
    # the parked trapezoid-socket / cover-budget group's OWN literals
    # (SOCKET_*, END_SOCKET_*, UPPER_INSET, COVER_WALL, COVER_FIT_CLEARANCE,
    # DECK_THICKNESS all stay exactly as they were).
    #
    # ROUND 73b -- REVISED, superseding the above 71.350/35.675. Owner,
    # verbatim, with the actual inner-wall measurement this time: "The
    # length between the inner walls (flat part, not counting the holes
    # left for the tongues and pegs) is 61.75mm. Outer wall length put
    # 71.25mm." -> HALF_Y = 71.250 / 2 = 35.625. See CAVITY_LENGTH below for
    # the owner's own cross-check on this figure, made impossible to break
    # silently by a runtime assert.
    #
    # NOT re-coupled to the arm's X envelope. Round 73b's item 4 found that
    # ARM_CAP_R (and everything built from the arm's own width) must NOT
    # key off HALF_Y at all -- the X arm envelope (ARM_X_OUTER, see below)
    # and this Y length are now two independently owner-measured figures
    # that no longer coincide (they did, by coincidence, at 35.675 in round
    # 73a). See ARM_X_OUTER's own comment for the coincidence-coupling bug
    # this discovery repeats (the same class of bug ARM_Y_LO already caught
    # once this round against a hardcoded literal).
    HALF_Y = 35.625

    # ROUND 74 -- the shell's own LENGTH (2 * HALF_Y = 71.250) is locked
    # ground truth (unchanged above), but its POSITION in the assembly was
    # wrong. The owner gave two independent registration constraints, both
    # read off the real, ground-truth Cover: (1) the hook's inner (+Y) face
    # must sit flush with the latch wall's own INNER face (not the hook
    # cavity), and (2) the thumb tab's outer (-Y) face must sit flush with,
    # or slightly proud of, the latch wall's OUTER face. Measured against
    # the frozen Cover (`tmp/r74_latch_wall_datum.py`), those two
    # constraints require the whole shell to move +1.825 mm in +Y (and the
    # latch wall to thicken -- see :attr:`LATCH_WALL_THICKNESS`).
    #
    # This is applied as ONE final rigid-body translate of the fully
    # assembled shell in :meth:`_build`, rather than by editing HALF_Y (or
    # any of the ~15 constants derived from it) -- every constant authored
    # in the shell's OWN internal frame (DECK_Y_LO/HI, BOTTOM_ROUND_CY, the
    # end-socket floor, UPPER_Y_HI/LO, LATCH_Y, TONGUE_Y, ...) stays exactly
    # as self-consistent as it always was; only the shell's placement in the
    # WORLD/assembly frame changes.
    #
    # The one thing a single rigid translate does NOT fix for free: any
    # feature that was built using another part's OWN ground-truth Y
    # constant directly (`PoweredUpHubBatteryTray.TAB_Y_CENTER`,
    # `PoweredUpHubCover.PLATE_Y_LO/HI`, `PoweredUpHubCover.LEDGE_Y_LO`,
    # `PoweredUpHubCover.LATCH_BAND_Y_HI`) as if it were already a WORLD
    # position. Those features are built in the shell's LOCAL (pre-translate)
    # frame like everything else, so once this offset is applied they would
    # drift +SHELL_Y_OFFSET off their intended target. Each such site is
    # back-compensated by `- SHELL_Y_OFFSET` at its own point of use (grep
    # for `SHELL_Y_OFFSET` below) so it still lands on the OTHER part's own,
    # unmoved ground truth after the shell-wide translate. Z-valued
    # cross-part references (`PLATE_THICKNESS`, `RISER_Z_HI`, ...) are
    # untouched -- this offset is Y-only.
    SHELL_Y_OFFSET = 1.825

    # DECK_Z is the housing's own overall height.
    #
    # **Round 22 -- this is now a DESIGN DECISION, not a copy of the
    # reference.** Rounds 20/21 set this to 29.600 mm, the real 25560
    # shell's own measured top face, under the round-12 "match the real
    # part" direction. The user's round-22 direction supersedes that: this
    # part is the BOTTOM LAYER of a two-layer box and is capped at **3
    # studs**, i.e. 3 x STUD_PITCH = 3 x 8.000 = 24.000 mm (the design
    # brief's own *Height convention* section, corrected round 10: the real
    # hub is 40.0 mm for 5 studs, so the module is STUD_PITCH, NOT the
    # 9.6 mm brick height). The shell is therefore 5.600 mm SHORTER than
    # the reference by intent -- a declared departure, not a fidelity
    # regression, and the reason the separate BatteryTray part had to go
    # (it no longer fits; see the assembly module's round-22 note).
    #
    # TOP_Z (33.800 mm) remains RETIRED: it was the LDraw part's bounding
    # box, reached only by two 26.9 mm^2 connector-port tubes ruled out of
    # scope, not by the shell itself.
    STUD_PITCH = 8.000
    #
    # **Round 55 -- back to the reference's own shell height, by user
    # direction ("just use 29.6 for now. I don't need the top cover
    # (yet)").** Two things forced it: the tray's floor plus the
    # caliper-measured 20.900 mm pack need 24.800 mm of interior, and a
    # 3-stud shell gives 21.200. Raising DECK_Z is what buys the room.
    #
    # **This is a DECLARED DEPARTURE ABOVE Z = 24.000, and a bigger one
    # than the number suggests -- read before "improving" it.** The
    # reference is NOT a constant section up to 29.600. Ray-cast of
    # 25560.dat (tmp/ldraw/step_z.py, tmp/ldraw/upper_cavity.py) bisects
    # the step at EXACTLY Z = 24.000 -- |X|max is 35.600 at 24.000 and
    # 27.200 at 24.010 -- above which the real shell narrows to a separate
    # upper section: X +-27.200 (cavity +-26.400), Y -32.000..+33.200
    # (cavity -30.800..+32.000), ceiling at 27.498, top skin to 29.600.
    #
    # This class extrudes its FULL 72 x 71.2 footprint to 29.600 instead,
    # so between 24.000 and 29.600 it carries roughly 13,000 mm^3 the
    # reference does not have. That is a deliberate simplification while
    # the top cover is deferred, NOT a fidelity improvement: measured
    # against the reference this height is *less* faithful above the step
    # than round 22's truncation was, and reference_contracts.toml records
    # it as an accepted deviation with that reason. Modelling the real
    # upper section is the follow-up, and it is what makes this part able
    # to carry a cap at all.
    #
    # The round-22 3-stud cap (DECK_STUDS = 3, retired here) was not an
    # approximation of the reference -- it landed on the reference's own
    # step exactly. Restore it, plus the upper section, when the cap lands.
    #
    # TOP_Z (33.800 mm) remains RETIRED: it was the LDraw part's bounding
    # box, reached only by two 26.9 mm^2 connector-port tubes ruled out of
    # scope, not by the shell itself.
    REF_SHELL_Z = 29.600      # measured top face of the real 25560 shell
    REF_STEP_Z = 24.000       # where the reference narrows -- bisected
    DECK_Z = REF_SHELL_Z

    # --- Upper section footprint (round 55b) ---
    # Above REF_STEP_Z the reference is a NARROWER box, not a continuation
    # of the lower shell. Ray-cast of 25560.dat (tmp/ldraw/upper_section.py),
    # positive-controlled at Z = 15.000 against the walls this class already
    # models (|X| 27.200/28.000):
    #
    #   X   outer +-27.200, inner +-26.400          (0.800 wall, constant)
    #   Y   outer -32.000 .. +33.3, inner -30.800 .. +32.000
    #   ceiling 28.000, top face 29.600             (1.600 skin)
    #
    # The 28.000 ceiling and 1.600 skin are ALREADY this class's own
    # DECK_Z - DECK_THICKNESS and DECK_THICKNESS -- round 47 arrived at
    # 1.600 by thinning the deck to clear the pack and landed on the
    # reference's own figure. Nothing there needs changing; only the plan
    # footprint above the step does.
    # Round 22: DECK_THICKNESS is a plain constant again. Round 21's
    # E11-a wired an instance-level running clearance into it so the deck's
    # underside would clear PoweredUpHubBatteryTray's own top face. That
    # tray no longer exists (round 22), so there is nothing under the deck
    # to clear and the derived value would be a clearance against nothing.
    #
    # Round 47: 2.000 -> 1.600, on a caliper measurement of the real pack.
    # The 2.000 figure was chosen because it put the underside at
    # DECK_Z - 2.000 = 22.000 = WALL_STEP_Z, so the deck seated on the side
    # walls' own upper band rather than floating at an arbitrary offset.
    # That was tidy, and it was also 0.100 mm too thick to hold the battery
    # this box exists for. Interior height is
    # DECK_Z - DECK_THICKNESS - PoweredUpHubCover.PLATE_THICKNESS; at 2.000
    # that is 20.800 mm, and the target pack (Spektrum SPMX812SH2)
    # measures 20.900 mm tall on the real part -- every vendor lists it as
    # 20 mm, which is what rounds 22-46 designed against. A pack 0.100 mm
    # proud holds the Cover off its own latch, so this is a functional
    # miss, not a cosmetic one.
    #
    # 1.600 puts the underside at 22.400 and the interior at 21.200 --
    # 0.300 mm of clearance on the measured pack. The deck no longer lands
    # on WALL_STEP_Z; it now sits 0.400 mm above it, which costs the
    # seats-on-the-step relationship and nothing structural (the wall's
    # upper band continues past the step either way). The user chose this
    # over raising DECK_STUDS, so the external 3-stud / 24.000 mm height --
    # the round-22 decision -- is deliberately preserved. 1.600 mm is still
    # four perimeters at a 0.4 mm nozzle.
    DECK_THICKNESS = 1.600

    # Round 22 -- the deck spans the FULL Y envelope again.
    # Round 21 (RH1) narrowed it to [-32.000, 33.200] because the real
    # shell narrows to its inner-skin line ABOVE the end walls' own
    # 24.000 mm height. At round 22's DECK_Z the end walls and the deck top
    # are the same 24.000 mm plane, so that narrowing band no longer exists
    # in this part at all -- the deck now caps the end walls instead of
    # sitting inboard of them, which is also what closes the top of the
    # box. X is unchanged (WALL_X_OUTER_UPPER, the side walls' upper band).
    DECK_Y_LO = -HALF_Y
    DECK_Y_HI = HALF_Y

    # --- Side walls (X-direction, stepped -- SS4) ---
    WALL_THICKNESS = 0.800
    # ROUND 73b -- LEGACY, retired as a description of any current wall
    # geometry. This used to mark where the wall's own X-profile stepped
    # in Z (hence the name); it has not described that since round 55's
    # redatum split it from SOCKET_Z_LO (see that constant's own note),
    # and now that WALL_INNER_STEP_Z has moved to 26.000 (the Tray's own
    # wall top, item 2), the REAL current wall step is at a completely
    # different Z than this constant. Kept ONLY because
    # `_build_arm_and_bore_local`'s Band A/B Z-split still reads it as an
    # internal bookkeeping boundary (see that method's own assert) -- not
    # because it still means "the wall steps here". Do not read this as a
    # wall-geometry constant; see WALL_INNER_STEP_Z for the real one.
    WALL_STEP_Z = 22.000
    # --- Plate-edge running clearance (round 48) ---
    # The Cover's plate is PLATE_WIDTH/2 = 27.200 mm half-width and this
    # wall's inner face is WALL_X_OUTER_LOWER - WALL_THICKNESS = 27.200 mm.
    # Both are reference-measured, and they are the SAME number, so the two
    # parts butted at zero clearance along the whole 62.8 mm length -- the
    # lid had to be pushed through a slot exactly its own width. Measured
    # before the fix: a 0.050 mm sideways displacement already produced
    # 2.366 mm^3 of interference against these two faces, which is what
    # made the round-46 tongue ribs' own 0.150 mm clearance moot.
    #
    # The clearance goes on the HOUSING, and locally. Shrinking the plate
    # was the obvious alternative and is wrong here: PoweredUpHubCover's
    # side tabs root at HANDLE_ROOT_X = 27.200, an independent literal, so
    # a narrower plate would leave them floating clear of it and the Cover
    # would stop being one solid.
    #
    # Local, because the plate edge is short: measured against the built
    # Cover it stands 1.200 mm tall over almost the whole length, rising to
    # GROOVE_THICKNESS (1.600) at the tongue end and LATCH_BAND_THICKNESS
    # (2.000) at the latch end. Only that band needs relief, so the wall
    # keeps its full 0.800 mm section everywhere above it and thins to
    # 0.650 mm only in a 2 mm strip at the bottom rim, where it carries no
    # load (the Cover IS the floor -- this rim meets nothing).
    # Inboard/downward overcut for the relief cutter. Kept small and named
    # because the first version's 1.0 mm ate the tongue ribs -- see
    # _build_plate_edge_relief. 0.300 mm clears the wall's own inner face
    # without reaching anything that stands in the interior.
    _RELIEF_X_OVERCUT = 0.300
    # ROUND 76 -- owner, from an annotated top view: the hook-side contact
    # bands "should have 1mm gaps".  Measured at the time, all three read
    # -0.050 (interference).  Applied by _build_latch_plate_relief over the
    # plate's Z band ONLY, so the Cover hook's flush seat higher up (round
    # 74's ground-truth constraint) is preserved -- see that method.
    LATCH_PLATE_RELIEF_GAP = 1.000

    PLATE_EDGE_RELIEF_Z_HI = max(
        PoweredUpHubCover.PLATE_THICKNESS,
        PoweredUpHubCover.GROOVE_THICKNESS,
        PoweredUpHubCover.LATCH_BAND_THICKNESS,
    )
    # ROUND 73 -- owner-measured with calipers, superseding the LDraw-derived
    # 28.000: "outer shell width over Z [10.000, 21.500] = 55.700" -> half
    # 27.850. That Z band sits entirely inside band 1/2's own outer face
    # (both read this same constant; only band 3, past REF_STEP_Z, reads
    # the separate, parked UPPER_X_OUTER), so this one change satisfies the
    # measurement exactly with no other constant needing to move. The owner
    # reasons it as clearing 7 Technic studs (7 * STUD_PITCH = 56.000) less
    # clearance -- consistent with, but not re-derived from, STUD_PITCH,
    # since the exact clearance split is a caliper reading, not a grid rule.
    # ROUND 78 -- 27.850 -> 27.500, owner-measured: *"the short side is
    # measured 55mm between outer walls"* => half 27.500.  Supersedes the
    # round-73 reading of 55.700 over Z[10.000, 21.500].
    #
    # This is the SHELL only.  The arms are explicitly NOT affected -- owner:
    # *"Do not change the arm to arm length though, it should be locked"* --
    # and they do not read this constant: :attr:`ARM_X_OUTER` (35.675, arm
    # flat-face half-width) is its own owner-measured value, and the
    # round-73b note there records that deriving one from the other is a
    # coincidence-coupling this file has already retired once.
    #
    # Consistency check against the other two measured numbers, since three
    # independent readings now constrain this axis: outer 55.000 with a Cover
    # plate of 52.330 leaves (55.000 - 52.330) / 2 = 1.335 per side for wall
    # PLUS running gap.  With the cavity at CAVITY_X_HALF_LOWER (26.500,
    # separately measured) the wall becomes 1.000 and the gap 0.335 -- which
    # matches the 0.315/side the owner measured on the real mating pair to
    # within 0.020.  The three numbers agree; none is being forced.
    # ROUND 81b -- 27.500 -> 27.800. The owner re-measured the real part
    # carefully ("I gave a good measure of the housing") and the BASE, near
    # the arms, is 55.600 across the outer faces, not the 55.000 measured in
    # round 79. That earlier figure was taken without knowing the wall is
    # not a constant section -- the shell narrows toward the top, so a
    # single "short side" reading depends entirely on the height it was
    # taken at. This constant is now explicitly the BASE width; the top is
    # UPPER_X_OUTER, narrower by UPPER_INSET.
    WALL_X_OUTER_LOWER = 27.800   # |X| outer face at the BASE, Z < UPPER_STEP_Z
    # NO LONGER the socket floor, nor the face above it -- round 55e moved
    # both to UPPER_X_OUTER (26.850) when it deepened the socket to widen
    # the cover's wall. What is left of this constant is the TOP DECK's
    # own nominal half-width, which _build_upper_step_in then trims to the
    # upper footprint anyway; it survives as the deck slab's starting
    # size, not as a face anything mates against.
    WALL_X_OUTER_UPPER = 27.200   # top deck slab half-width, pre-trim

    # ROUND 73 -- band 1's OWN wall thickness, owner-measured and split out
    # from the shared WALL_THICKNESS constant above. Cavity clear half-width
    # over Z [10.000, 20.000] is measured at 26.500 ("53.000 across"), and
    # this Z band sits entirely below WALL_INNER_STEP_Z (21.200), i.e.
    # entirely inside band 1. Deriving it as WALL_X_OUTER_LOWER - 26.500
    # rather than retyping keeps it tied to the same owner-measured outer
    # face rather than an independent literal.
    #
    # This is a NEW, separate constant rather than a change to
    # WALL_THICKNESS itself, because WALL_THICKNESS is not band 1's alone:
    # it is also band 3's own section thickness AND (via UPPER_X_INNER
    # below) an input to the parked trapezoid-socket / cover-budget group.
    # Changing WALL_THICKNESS's value would have silently thinned the
    # socket's own "normal 0.800 section" and shifted UPPER_X_INNER --
    # exactly the parked-group collision this round's task brief says to
    # avoid "beyond what is unavoidable". Band 1 has no such coupling (the
    # socket only ever lives in bands 2/3), so it gets its own constant
    # instead, used by band 1's own slab, the plate-edge relief, and the
    # side window -- the three places that read band 1's real inner face.
    # ROUND 81b -- 26.500 -> 26.400, derived from the owner's re-measure:
    # base outer 55.600 with 1.400 mm side walls (their words: "The side
    # walls (along Y) are 1.4mm thick" -- the +-X walls, i.e. the ones that
    # RUN along Y). Cross-check against the frozen Cover: 26.400 leaves
    # 26.400 - PLATE_WIDTH/2 (26.165) = 0.235 mm of clearance per side,
    # consistent with the ~0.315 the owner measured in round 79 under the
    # coarser 55.000 figure.
    CAVITY_X_HALF_LOWER = 26.400   # owner-measured, UNPATCHED cavity face
    WALL_THICKNESS_LOWER = WALL_X_OUTER_LOWER - CAVITY_X_HALF_LOWER  # 1.400

    # --- Trapezoid mating socket, outer face of each side wall (round 50) ---
    # Measured off 25560.dat. Rounds 16-49 read the design doc's SS4 line
    # "side-wall step at 22.0" as a step running the WHOLE length, and built
    # the wall recessed to 27.200 above Z = 22 everywhere -- which is the
    # socket smeared across the entire wall, so no socket at all. SS4 also
    # records that step's own extent, "z +-23" (= Y +-9.200), but the table
    # does not say that is a LOCAL feature and nothing downstream noticed.
    #
    # Ray-cast against the reference, the outer face steps back at:
    #     Y = 0, +-6  (inside)  -> Z = 22.000
    #     Y = +-12, +-15 (outside) -> Z = 24.000
    # i.e. a trapezoidal patch where the recess dips 2 mm lower than the
    # surrounding wall. Its own panel at X = 27.200 measures 40.800 mm^2,
    # exactly (18.400 + 22.400) / 2 * 2.000 -- an isosceles trapezoid with
    # 45-degree flanks, narrow edge down:
    #
    #   Z=24.000  (-11.200) ----------------- (+11.200)
    #                        \               /
    #   Z=22.000    (-9.200) ----------------- (+9.200)
    #
    # The wall is locally DOUBLE thickness so the recess is a real pocket and
    # not a hole: the inner face steps 27.200 -> 26.400 at Z = 21.200 (the
    # reference's own X = 26.400 panel starts there), giving 1.600 mm of wall
    # over Z 21.200..24.000, of which the socket removes the outboard 0.800.
    # Inside the socket the wall is back to a normal 0.800 section.
    #
    # Intended as the mating point for a future cap (user, round 50). In the
    # reference the socket is a closed recess in a wall that continues up to
    # 29.600. Rounds 50-54 stopped this part at 24.000, so the socket's top
    # edge WAS the top of the part and it read as a notch open upward --
    # which is what made it usable as a cap register. Round 55 raised
    # DECK_Z to 29.600, so the wall now continues past it and the socket is
    # a closed recess again, as in the reference. It is therefore no longer
    # a usable cap register in its own right; the user deferred the top
    # cover in the same breath, so nothing depends on that today. Restoring
    # the register means restoring the step (see DECK_Z), not re-cutting
    # this feature.
    # ROUND 73b: no longer "== WALL_STEP_Z" in any derived sense -- that
    # constant is now retired/legacy (see its own note) and this socket
    # band sits, numerically coincidentally, at the SAME Z the old
    # WALL_STEP_Z also names, but the two are independent literals now.
    # The socket's own Z-depth stays PARKED (owner direction, round 73b):
    # this value is unchanged.
    SOCKET_Z_LO = 22.000
    SOCKET_Y_HALF_LO = 9.200      # narrow (lower) edge half-width
    SOCKET_Y_HALF_HI = 11.200     # wide (upper) edge half-width, at SOCKET_Z_HI
    # ROUND 73 -- owner: "the center line of the trapezoid should be aligned
    # with the center line of the thumb tab on the tray". Read live from the
    # Tray (ground truth), the same pattern WINDOW_Y_CENTER below already
    # uses for the side window -- not retyped as 2.000, so the two cannot
    # silently drift apart if the Tray's own tab centre ever moves.  This is
    # a Y-AXIS CENTRING change only: SOCKET_Y_HALF_LO/HI (the trapezoid's own
    # half-widths) and its Z band are unchanged, per the owner's explicit
    # scope note that this does not reopen the parked Z-depth question.
    # ROUND 74 -- back-compensated by `- SHELL_Y_OFFSET`. This socket is cut
    # in the shell's LOCAL (pre-translate) frame like every other feature,
    # so without the compensation the shell-wide translate would carry it
    # SHELL_Y_OFFSET past the Tray's own tab centreline instead of landing
    # on it. See SHELL_Y_OFFSET's own comment.
    SOCKET_Y_CENTER = PoweredUpHubBatteryTray.TAB_Y_CENTER - SHELL_Y_OFFSET   # 0.175
    # Round 55: pinned to the reference's own step, NOT to DECK_Z. The
    # wide edge above was measured AT Z = 24.000; once DECK_Z rose to
    # 29.600 a z_hi of DECK_Z would have stretched the same trapezoid
    # over 7.600 mm instead of 2.000, changing a measured flank angle
    # into a derived one and widening the mouth by 5.600 mm of pure
    # extrapolation past the sampled band.
    SOCKET_Z_HI = REF_STEP_Z      # 24.000

    # ROUND 73b -- DECIDED by the owner, resolving the round-71/§1 blocker
    # this constant carried for many rounds (see the retired history below
    # this comment, kept for the record).
    #
    # DECISION: raise the wall's inner step to the Tray's own wall top, and
    # change nothing else about the upper section. Derived from two frozen
    # ground-truth constants, not typed, so it tracks them if either ever
    # moves: `PoweredUpHubCover.PLATE_THICKNESS + PoweredUpHubBatteryTray.WALL_Z_HI`
    # = 1.200 + 24.800 = 26.000 (world Z). The narrowing now begins exactly
    # where the Tray's wall ends, so the Tray sees the full lower cavity
    # (53.000 mm clear, WALL_THICKNESS_LOWER-thick wall) over its ENTIRE
    # standing height, and the narrower upper band (51.800 mm clear,
    # unchanged -- UPPER_INSET/COVER_WALL/COVER_FIT_CLEARANCE all untouched,
    # per the owner's explicit choice to spend no external width and no
    # top-cover budget) no longer intersects the Tray at all. The 1.200 mm
    # gap between the Tray's wall top (24.800 mm local / 26.000 mm world)
    # and the compartment ceiling (27.200 mm world) is
    # `PoweredUpHubBatteryTray.SNAP_FIT_ALLOWANCE` -- room a future top
    # cover's own snap-fits occupy, so the narrowed band living in that
    # zone is fine, not a fidelity gap.
    #
    # THE TRAP (round 71 shipped it once already; do not repeat it):
    # `_build_side_wall` used to build a separate "thickened band 2" over
    # `[WALL_INNER_STEP_Z, REF_STEP_Z]` to host the socket. With
    # WALL_INNER_STEP_Z now ABOVE REF_STEP_Z (26.000 > 24.000), that
    # interval is INVERTED and OCCT raises nothing -- it silently vanishes,
    # taking the socket's own host material with it. Round 73b restructures
    # the banding instead of retrying that shape: the socket's own Z-band
    # [SOCKET_Z_LO, SOCKET_Z_HI] = [22.000, 24.000] now sits entirely INSIDE
    # what was band 1 (now the single full-thickness band, [0,
    # WALL_INNER_STEP_Z]), and the socket is still a plain OUTER-face
    # recess -- it does not care which inner-face band it's pocketed into,
    # as long as that band is thick enough to host it as a blind pocket
    # (WALL_THICKNESS_LOWER = 1.350 > UPPER_INSET = 1.150, leaving 0.200 mm
    # of floor behind it -- topologically a pocket, not a hole, but NOT a
    # printable wall section: 0.200 mm is under a single typical FDM
    # extrusion width (~0.4 mm). This was a real, open trade flagged for the
    # owner in the round-73b report -- restoring a normal section here
    # costs either item 5's CAVITY_X_HALF_LOWER (thin the cavity) or the
    # parked UPPER_INSET (thicken the cover budget's own wall).
    #
    # ROUND 73d RESOLVED this: the owner chose neither of the above --
    # instead of moving CAVITY_X_HALF_LOWER or UPPER_INSET, the socket's own
    # depth was decoupled into its own constant (SOCKET_DEPTH = 0.500,
    # backing 0.850) so the recess itself got shallower rather than either
    # of the walls around it changing. `test_cover_budget_and_socket_floor_
    # stay_inline` (renamed -- see its own docstring) now passes on real,
    # not tautological, backing. See SOCKET_DEPTH's own comment for the
    # fix and `_build_wall_socket`'s docstring for the coplanarity this
    # traded away.) See
    # `_build_side_wall`'s own docstring for the resulting two-band
    # structure (full-thickness 0..26.000, narrowed 26.000..DECK_Z).
    # `_build_wall_socket` needed no change AT THE TIME -- round 73b it
    # still read `UPPER_X_OUTER` directly, never `WALL_INNER_STEP_Z` (round
    # 73d later gave it its own `SOCKET_FLOOR_X`, unrelated to this item's
    # own Z-banding change). `_build_upper_step_in` DID need a change --
    # its own ``z_lo`` used to read `REF_STEP_Z` (24.000); left
    # unchanged it would cut into the now-full-thickness band between
    # 24.000 and the new 26.000 step, a second instance of the exact same
    # inverted-interval trap this whole item exists to avoid. See that
    # method's own docstring for the fix.
    #
    # RETIRED HISTORY (round 71-73a, kept for the record; no longer the
    # blocking state): the constant used to sit at 21.200 ("where the wall
    # doubles to 1.600mm" under the old, now-removed thickened-band
    # scheme), which put the Tray's own wall (26.250 half-width, standing
    # to world Z 27.200) in direct 413.040 mm^3 collision with the
    # housing's narrowed cavity -- the Tray could not physically enter.
    # Round 73a's owner-measured cavity figures (26.500 half over Z[10,20])
    # only fixed the region BELOW this step; the step's own position was
    # explicitly left as an open question (§1 of the round-73 redatum plan)
    # until this round's owner decision above closed it.
    WALL_INNER_STEP_Z = (
        PoweredUpHubCover.PLATE_THICKNESS + PoweredUpHubBatteryTray.WALL_Z_HI
    )   # 26.000

    # --- Cover budget (round 55e) ---
    # The trapezoid sockets are kept as the register for a future cover
    # (user, rounds 50/55d): its legs mate into them and its outer wall sits
    # FLUSH with this part's own side walls. So the cover's wall thickness is
    # not the cover's choice -- it is whatever gap this class leaves between
    # its own outer face and the upper section, minus the fit clearance.
    #
    # Rounds 55b-55d left that gap at the reference's own figure, which made
    # the cover's long-edge wall 28.000 - (27.200 + 0.150) = 0.650 mm: about
    # 1.6 extrusion widths, which the user judged too thin ("Can we use 1mm
    # for all the cover walls? I feel 0.65 is too thin").
    #
    # So the budget is now the INPUT and the upper section is derived from
    # it, rather than the other way round.
    #
    # ROUND 73d -- the paragraph that used to stand here claimed deriving
    # UPPER_INSET this way ALSO made "inline with the trapezoid" structural,
    # because the socket's own depth was this same constant. That coupling
    # is RETIRED: the socket's depth is now its own constant, SOCKET_DEPTH,
    # decoupled on purpose so the owner's request to shrink the socket
    # recess did not also (silently) widen the upper shell externally. See
    # SOCKET_DEPTH's own comment for the trade and the fix it makes.
    # UPPER_INSET/UPPER_X_OUTER/COVER_WALL below are UNCHANGED by that
    # change -- they still govern the upper section's own step-in, which
    # nobody asked to move.
    COVER_WALL = 1.000
    # Nominal, not read from the live profile: this class must not change
    # shape with the print profile (its visual contracts are byte-compared),
    # and the cover -- which does not exist yet -- will apply its own
    # clearance when it is built. 0.150 is fdm_standard's free.radial.
    COVER_FIT_CLEARANCE = 0.150
    # ROUND 81 -- the owner sets the recess directly, and the trapezoid
    # socket's depth is DERIVED from it (see SOCKET_DEPTH below), re-fusing
    # the coupling round 73d deliberately broke.
    #
    # Owner: *"reduce the length and width of the top portion (above the
    # arms but include the trapezoids) ... 0.5mm to 1mm recess compared to
    # the bottom portion. The recess should be equal to the recess of the
    # trapezoids"*, then, choosing among the priced options: **1.000, with
    # SOCKET_DEPTH rising to match**, and the step at **Z = 24.000** so the
    # *"trapezoid socket bottom is flush with the recessed surface"*.
    #
    # So this constant is no longer `COVER_WALL + COVER_FIT_CLEARANCE`. That
    # derivation belonged to the abandoned slip-over-cover scheme and made
    # the number answer to a part that was never built; it now answers to a
    # measurement the owner states directly. COVER_WALL/COVER_FIT_CLEARANCE
    # are left in place (other comments still cite them) but no longer feed
    # anything geometric.
    # ROUND 81b -- 1.000 -> 0.800, from the owner's re-measure. The patched
    # section is 2.200 against an unpatched 1.400, i.e. 0.800 of inboard
    # patch, and the owner reads the SAME 0.800 as the top portion's recess
    # ("likely the 0.8mm for the recess on the top portion as well").
    UPPER_INSET = 0.800
    # ROUND 81 -- 26.500. Note this now lands exactly on
    # CAVITY_X_HALF_LOWER (26.500), i.e. the recessed upper face is
    # coplanar with the lower band's own INNER face. That is a coincidence
    # of the current numbers, not a designed identity -- do not derive one
    # from the other.
    UPPER_X_OUTER = WALL_X_OUTER_LOWER - UPPER_INSET        # 26.500
    UPPER_X_INNER = UPPER_X_OUTER - WALL_THICKNESS          # 25.700

    # ROUND 81 -- where the OUTER silhouette steps in. Split out from
    # WALL_INNER_STEP_Z, which round 73b had made do double duty as both
    # "where the wall changes its inner-face thickness" and "where the
    # external silhouette narrows". The owner moved the silhouette step
    # down to the trapezoids' own top (REF_STEP_Z = 24.000) so the sockets
    # fall inside the recessed portion; the cord port still keys off
    # WALL_INNER_STEP_Z (26.000) and is deliberately NOT moved with it.
    #
    # Do not collapse these two back into one constant: they now answer to
    # different requirements, and round 73b's own docstring records what
    # happens when a single Z is asked to mean two things (an inverted
    # [26.000, 24.000] band that OCCT accepts silently while deleting the
    # socket's host material).
    UPPER_STEP_Z = REF_STEP_Z                               # 24.000

    # --- ROUND 73d: the socket recess DECOUPLED from the upper inset ---
    #
    # Owner: "Can we reduce the recess's thickness, to something like 0.5mm?"
    #
    # Until now the socket's depth WAS `UPPER_INSET`, deliberately -- the
    # comment above calls that "structural": one constant made the socket
    # floor and the upper wall the same plane by construction. That was a
    # good property while both faces answered to the same requirement. They
    # no longer do, and keeping them fused would mean the owner's request
    # (a shallower RECESS) silently widened the housing's whole upper shell
    # from 53.400 to 54.700 -- an externally visible change nobody asked
    # for. So the two are now separate constants, and the property they used
    # to share is asserted rather than assumed (see below).
    #
    # WHY 0.500 IS THE RIGHT ORDER OF MAGNITUDE, not just "what was asked":
    # the wall hosting the socket is `WALL_THICKNESS_LOWER` = 1.350 thick
    # (set by the owner's own 53.000 cavity measurement), so the material
    # left behind the recess is 1.350 - depth. At the old 1.150 that was
    # 0.200 mm -- under one 0.4 mm extrusion width, i.e. not printable as a
    # wall at all, which is the defect this fixes. At 0.500 it is 0.850,
    # comfortably above the 0.770 "normal section" floor that
    # `test_cover_budget_and_socket_backing_are_sufficient` guards (renamed
    # in round 73d from `..._floor_stay_inline` -- "stay inline" described
    # exactly the coplanarity property this change retires; see that
    # test's own docstring).
    # ROUND 73e -- 0.500 -> 0.550, the owner's "more balanced" call, made
    # against the one fact that governs this choice:
    #
    #     cover lip + backing = WALL_THICKNESS_LOWER - COVER_FIT_CLEARANCE
    #                         = 1.350 - 0.150 = 1.200 mm, FIXED.
    #
    # The two are a 1:1 trade, so there is no depth that makes both
    # comfortable -- two solid 0.800 walls would need 1.600 and the budget is
    # 1.200. 0.550 splits it onto clean 0.4 mm-nozzle multiples: backing
    # 0.800 (exactly two perimeters, clear of the 0.770 floor with margin
    # rather than sitting on it) and cover lip 0.400 (exactly one).
    #
    # NOT split evenly at 0.600/0.600 (depth 0.750), which sounds more
    # balanced and is worse: the backing is the battery compartment's own
    # structural outer wall -- thin it and the compartment opens into the
    # recess -- while the socket is a REGISTER whose job is to locate a cover,
    # not carry load. An even split weakens a load-bearing wall to strengthen
    # an alignment feature. It also drops the backing below the 0.770 guard.
    #
    # If 0.400 proves too thin for the cover's lip, the honest fix is to WIDEN
    # the wall (i.e. revisit the owner-measured 53.000 cavity or 55.700 shell)
    # -- NOT to shave the backing or lower the guard. Lowering a bound to
    # accommodate a number is the ratchet this project has already been bitten
    # by; see the *Functional Claims* ratchet corollary in vibe/INSTRUCTIONS.md.
    # ROUND 78 -- 0.550 -> 0.230, forced by the owner's new 55.000 mm
    # short-side measurement and chosen by the owner over removing the
    # socket outright.
    #
    # That measurement puts the side wall at WALL_THICKNESS_LOWER = 1.000
    # (27.500 outer less the 26.500 cavity), and a 0.550 recess left only
    # 0.450 mm of backing -- the SOCKET_BACKING >= 0.770 guard below fired
    # and the model would not build.  The guard was NOT relaxed: it defends
    # a real failure (the battery compartment breaking through into the
    # recess), and this project treats widening such a bound to reach green
    # as a defect in itself.
    #
    # 0.230 is the deepest recess that keeps 0.770 backing at a 1.000 wall
    # (1.000 - 0.230 = 0.770 exactly).  The arithmetic has no slack left:
    # deepening this again requires either a thicker wall (a larger outer
    # dimension, which the 55.000 measurement rules out) or a narrower
    # cavity, and the cavity is already within 0.335 of the frozen Cover's
    # own plate edge.  Consequence accepted by the owner: the socket is now
    # a shallow register rather than a deep seat, so whatever mates into it
    # engages less.
    # ROUND 81 -- DERIVED from UPPER_INSET again, reversing round 73d's
    # decoupling on owner instruction: *"The recess should be equal to the
    # recess of the trapezoids"*, and *"make the trapezoid thickness =
    # recess so the trapezoid socket bottom is flush with the recessed
    # surface"*. The socket floor and the recessed upper face are once more
    # the same plane BY CONSTRUCTION (asserted below), which is the whole
    # point -- the trapezoid reads as the transition into the recess rather
    # than as a separate pocket inside it.
    #
    # The round-73d paragraph above records why they were split (the owner
    # then wanted a shallow register matching the real part without
    # widening the shell). That requirement is superseded, not forgotten:
    # the cost of re-fusing them is that the recess is now 1.000 mm deep
    # against a 1.000 mm wall, i.e. the socket eats the ENTIRE lower wall
    # section and the backing has to be rebuilt inboard as a local pad --
    # see SOCKET_PAD_X_INNER and _build_socket_backing.
    SOCKET_DEPTH = UPPER_INSET                               # 1.000
    #: |X| of the socket's floor -- derived, so it tracks the outer face.
    SOCKET_FLOOR_X = WALL_X_OUTER_LOWER - SOCKET_DEPTH       # 26.500

    #: Minimum wall that must survive behind the recess. Unchanged bound --
    #: round 73b reached 0.200 mm here by spending it silently, and this is
    #: the guard that has caught every attempt since.
    SOCKET_BACKING_MIN = 0.770
    # ROUND 81 -- with SOCKET_DEPTH == WALL_THICKNESS_LOWER (both 1.000),
    # `WALL_THICKNESS_LOWER - SOCKET_DEPTH` is 0.000: the recess cuts clean
    # through the side wall and the trapezoid would be a WINDOW into the
    # battery bay, not a socket. The backing is therefore no longer whatever
    # the plain wall happens to leave -- it is built back deliberately, as a
    # local pad inboard of the socket footprint (owner: *"just patch up the
    # trapezoids + z>=24 portion"*).
    #
    # SOCKET_BACKING is redefined to measure the pad rather than the plain
    # wall, so the assert in _build_wall_socket still checks the section
    # that ACTUALLY survives. It is not relaxed and not removed -- if the
    # pad is ever dropped or mis-sized, that guard must fire.
    #
    # The owner has accepted, for now, that this pad reaches inboard of
    # CAVITY_X_HALF_LOWER and so collides with PoweredUpHubBatteryTray
    # (tray outer |X| 26.250 vs this pad's 25.730): *"This may make the
    # inner wall collide with the battery tray, do not worry about it for
    # now, will address later."* That is a KNOWN, ACCEPTED conflict, not an
    # oversight -- do not "fix" it by thinning the pad below
    # SOCKET_BACKING_MIN.
    # --- ROUND 81b: the inner patches, as measured on the real part ---
    #
    # The owner measured the +-X wall as 1.400 mm unpatched and 2.200 mm
    # where it is patched -- so the patch is 0.800 mm of material added
    # INBOARD, and it starts at two different heights depending on where
    # along the wall you are:
    #
    #   * a TRAPEZOID-shaped patch, echoing the outer socket's own outline,
    #     from Z = 20.000 up;
    #   * a UNIVERSAL patch running the whole wall length, from Z = 22.500 up.
    #
    # These Z values apply to the INNER wall only. The outer wall's own Z
    # shape is NOT touched by them (owner, explicitly: *"Do not change the
    # z shape on the outer wall"*) -- the silhouette still steps once, at
    # UPPER_STEP_Z = 24.000.
    #
    # Scope is the +-X (long) side walls only, per the owner's answer at the
    # design gate: both the 1.400/2.200 readings and the corresponding tray
    # cut are long-wall measurements, and the +-Y end walls have their own,
    # different measured recess (END_SOCKET_DEPTH = 1.200). Do not
    # extrapolate this patch around the perimeter without a measurement.
    PATCH_THICKNESS = 0.800
    #: Inner face where either patch is present: 1.400 + 0.800 = 2.200 mm
    #: of total section, matching the owner's patched reading.
    PATCH_X_INNER = CAVITY_X_HALF_LOWER - PATCH_THICKNESS     # 25.600
    #: Trapezoid patch's own start height (world Z), owner-measured.
    TRAPEZOID_PATCH_Z_LO = 20.000
    #: Full-length patch's start height (world Z), owner-measured.
    UNIVERSAL_PATCH_Z_LO = 22.500
    #: Material surviving behind the recess. Named because it is the whole
    #: point of this change and because a future edit to either input
    #: silently spends it -- exactly how it reached 0.200 in round 73b.
    SOCKET_BACKING = SOCKET_FLOOR_X - PATCH_X_INNER          # 1.400

    # CONSEQUENCE THE OWNER MUST OWN, recorded here rather than buried:
    # the socket is the register for a FUTURE top cover, and its depth was
    # previously sized as COVER_WALL (1.000) + COVER_FIT_CLEARANCE (0.150).
    # At a 0.500 recess, a cover wall seating in it can be at most
    # 0.500 - 0.150 = 0.350 mm. `COVER_WALL` (1.000) is therefore NO LONGER
    # the wall that fits this socket -- it still describes the upper
    # section's step-in, which is untouched. Do not read COVER_WALL as "the
    # thickness the top cover's wall may be at the socket"; that number is
    # now SOCKET_DEPTH - COVER_FIT_CLEARANCE.
    SOCKET_COVER_WALL_BUDGET = SOCKET_DEPTH - COVER_FIT_CLEARANCE   # 0.350

    # --- End-wall trapezoid mating sockets (round 51) ---
    # The same molded feature as SOCKET_* above, on the two END walls
    # (-Y latch end, +Y tongue end). Requested by the user as the second
    # half of the cap register; round 50 built only the +-X pair.
    #
    # MEASURED, not assumed to transfer -- and it does not: only the Z band
    # and the 45-degree flank angle are shared. Ray-cast of 25560.dat along
    # +-Y (tmp/ldraw/end_wall_extent.py, bisecting for the X where the outer
    # skin at |Y| = 35.600 reappears) gives, identically on BOTH ends:
    #
    #     Z = 22.10 -> |X| <= 14.100      Z = 23.10 -> |X| <= 15.100
    #     Z = 22.50 -> |X| <= 14.500      Z = 23.90 -> |X| <= 15.900
    #
    # i.e. |X|max = Z - 8.000 exactly: an isosceles trapezoid rising from
    # half-width 14.000 at Z = 22.000 to 16.000 at Z = 24.000, narrow edge
    # down. Below Z = 22.000 the skin is continuous; above DECK_Z the whole
    # shell steps in, which is a different (already-modelled) feature.
    #
    # Depth is the reference's outer-skin thickness: in the reference the
    # recess removes the 35.600 -> 34.400 skin outright (both crossings
    # vanish together), so the floor sits at |Y| = 34.400. On THIS part that
    # stays a blind pocket rather than becoming a hole, because our end
    # walls are thicker than the reference's skin where the recess lands --
    # 4.800 mm at the latch end (LATCH_WALL_THICKNESS) and, above the bay,
    # the solid deck at both ends.
    END_SOCKET_Z_LO = 22.000        # narrow (lower) edge, == SOCKET_Z_LO
    END_SOCKET_X_HALF_LO = 14.000   # narrow (lower) edge half-width
    END_SOCKET_X_HALF_HI = 16.000   # wide (upper) edge half-width, at SOCKET_Z_HI
    #                                 (the same pinning as SOCKET_Z_HI --
    #                                 |X|max = Z - 8.000 was sampled only
    #                                 over Z 22.1..23.9; 29.600 is far
    #                                 outside that band.)
    END_SOCKET_DEPTH = 1.200        # floor at |Y| = HALF_Y - 1.200 = 34.400

    # --- Upper section, Y:  a DEPARTURE from the reference, by user direction (round 55d) ---
    # The reference's upper section stops at Y = -32.000 / +33.3, inboard of
    # the end-wall trapezoids' own floor. This class carries it out to that
    # floor at BOTH ends instead: "extend both shorter ends to sit inline
    # with the trapezoid (similar to what we currently have for the long
    # edges)".
    #
    # The long edges already worked that way AT THE TIME (round 55d): the
    # side trapezoid's floor was at |X| = 27.200 (WALL_X_OUTER_UPPER, where
    # _build_wall_socket started cutting) and the upper section's outer face
    # was the same 27.200, so the socket floor and the wall above it were
    # one continuous plane. ROUND 73d RETIRED that side-wall coplanarity on
    # purpose (see SOCKET_DEPTH's own comment) -- the side socket's floor is
    # now SOCKET_FLOOR_X (27.350), independent of UPPER_X_OUTER (26.700).
    # This paragraph is kept for why UPPER_Y_HI below is DERIVED rather than
    # typed; the END-wall coplanarity it describes is UNCHANGED by round
    # 73d (END_SOCKET_DEPTH was not touched) -- only the SIDE-wall analogy
    # that originally motivated it is now historical.  The end trapezoids'
    # floor is at |Y| = HALF_Y - END_SOCKET_DEPTH = 34.400 while the
    # reference's upper section stops 2.400 / 1.124 mm short of it, leaving
    # the end sockets with a lip over them that the side ones do not have.
    #
    # DERIVED, not typed: "inline with the trapezoid" IS the requirement, so
    # it is expressed as the same arithmetic the end socket's own floor uses
    # (see _build_end_wall_socket). Retyping 34.400 here would let the two
    # drift apart silently, which is the failure this whole feature is about.
    #
    # Cost, recorded in reference_contracts.toml: above the step this class's
    # Y faces no longer match the reference at either end, and the reference's
    # tongue-end draft (33.316 at Z 24.1 -> 33.234 at Z 28.0) is moot since
    # that face is not where the reference puts it at all. X is unaffected and
    # remains reference-exact on both faces.
    UPPER_Y_HI = HALF_Y - END_SOCKET_DEPTH      # 34.400
    UPPER_Y_LO = -UPPER_Y_HI

    # Round 22: the end walls run the shell's full height, which is now
    # the same 24.000 mm they were already capped at by round 21 (RH1) --
    # the number is unchanged, but its MEANING is: it used to be "the real
    # end wall stops here, below the deck", and is now "the end wall
    # reaches the deck". Derived from DECK_Z rather than re-typed so the
    # two cannot drift apart.
    END_WALL_Z_HI = DECK_Z

    # --- Bottom end rounds (round 55f) ---
    # The reference's bottom edge is rounded where the shell meets each end
    # plane. User request: "for the bottom of the housing the reference model
    # have curve on both end of the side wall... Note on the end with the
    # thumb tabs, only the outer segments have the curve."
    #
    # MEASURED off 25560.dat's own VERTICES, not off slices
    # (tmp/ldraw/curve_fit.py). Slicing samples wherever the cutting plane
    # crosses a facet, which made this look like two different radii that
    # drifted with whichever Z was fitted; the vertices are the curve's
    # control points, and they fit one arc almost exactly:
    #
    #   -Y  pullback 3.600 / 2.222 / 1.054 / 0.274 / 0.000
    #       at Z      0.000 / 0.274 / 1.054 / 2.222 / 3.600   -> R 3.600, rms 0.0005
    #   +Y  pullback 2.222 / 1.054 / 0.274 / 0.000
    #       at Z      0.000 / 0.780 / 1.948 / 3.326           -> the SAME arc,
    #                                                            truncated 0.274 up
    #
    # So one radius, one centre |Y|, and the ends differ only in how far up
    # the arc's centre sits -- the tongue end's bottom face cuts the same arc
    # 0.274 mm above its tangent point.
    BOTTOM_ROUND_R = 3.600

    # ROUND 75 -- floor for the TONGUE end's bottom round, in Z.
    #
    # Owner, round 75: "The end should sit flush with the cover bottom and
    # lives little gap (the tongues should be mostly covered)".  The Cover's
    # bottom face is Z = 0.000 (it is the print-bed datum), and the housing's
    # tongue-end wall was bottoming out at Z = 0.264 -- the height at which
    # the bottom-round arc crosses that wall's own inner face (Y 35.203).
    #
    # DISABLED (None) -- flooring the cutter was the WRONG MECHANISM and is
    # kept only as a documented dead end.
    #
    # Setting a floor stops the arc cutting below it, which does bring the
    # wall down to the Cover's bottom -- but it does so by leaving a FLAT
    # square lip (measured: a Z 0.000..1.874 slab at Y 35.5..36.0), i.e. it
    # destroys the very curve the owner asked to keep.  Owner, immediately
    # after seeing it: *"The tongue side should stay curved"*.
    #
    # The owner's actual request -- "the bottom curve EXTENDS and wraps like
    # a pocket... the end should sit flush with the cover bottom" -- is that
    # MORE of the same arc be realised, not that the arc be truncated flat.
    # On this arc (R 3.600, centre Y 33.850, tangent to Z = 0 there) the wall
    # bottoms out wherever its own inner face crosses it: at the present
    # inner face, Y 35.203, that crossing is Z 0.264.  Extending the wall
    # inboard is what walks the curve further down -- Y 34.693 would put it
    # at Z 0.100 -- with the radius, and the latch end, untouched.
    BOTTOM_ROUND_Z_FLOOR_TONGUE: float | None = None
    BOTTOM_ROUND_Z_FLOOR_TONGUE: float | None = None
    BOTTOM_ROUND_CY = HALF_Y - BOTTOM_ROUND_R      # 32.000, both ends
    BOTTOM_ROUND_CZ_FULL = 3.600                   # tangent to Z = 0
    BOTTOM_ROUND_CZ_TRUNCATED = 3.326              # 0.274 lower
    #
    # WHICH SEGMENTS carry it -- also measured, and the two ends genuinely
    # differ (tmp/ldraw/curve_span.py, reading vertices at Z = 0):
    #
    #   latch end   |X| 19.200 .. 28.000 only. The middle is square: there
    #               are square vertices at Y = -35.600 out at X = +-5.600.
    #               This is the user's "only the outer segments".
    #   tongue end  the RIB bands, and only those -- |X| <= 0.800 (the centre
    #               wall), 15.600..17.200 (inner ribs), 26.000..28.000 (outer
    #               ribs). Those are exactly SS12.2's T1/T2/T3, i.e. the same
    #               bands _build_tongue_ribs already builds.
    #
    # Bands are ``(x_lo, x_hi, centre_z)``, signed rather than mirrored from
    # absolute values because the tongue end's centre band straddles X = 0
    # and does not mirror.
    #
    # ROUND 56 -- the tongue end is ONE CONTINUOUS ARC, a deliberate whole-end
    # deviation from the reference. Round 55g read "the tongue side wall should
    # have the curve all the way" as "give the outer rib bands the full-depth
    # arc" and kept the reference's band structure; that left 47.200 mm of
    # square bottom edge in the four gaps between bands
    # (tmp/ldraw/tongue_bottom_scan.py), which is what the user was still
    # seeing. "All the way" is about EXTENT along X, not about arc depth: the
    # tongue end now carries a single band spanning the full wall, at the same
    # full-depth arc as the latch end.
    #
    # The truncated arc (BOTTOM_ROUND_CZ_TRUNCATED) is consequently unused by
    # the built part. It is kept as the recorded reference measurement, which
    # test_bottom_end_round_follows_the_reference_arc still checks against.
    #
    # The latch end is UNCHANGED and stays segmented -- the user asked for its
    # middle to remain square ("only the outer segments have the curve"), and
    # the reference agrees, with square vertices at X = +-5.600.
    # ROUND 73: the outer bound of each band IS the wall's own outer face
    # (a real identity, not a coincidence -- the round necessarily reaches
    # all the way to the shell's own edge), so it reads WALL_X_OUTER_LOWER
    # live instead of the pre-round-73 literal 28.000. The 19.200 inner
    # bound is an independent LDraw-measured curve-span boundary, unrelated
    # to the wall thickness, and is untouched.
    # ROUND 83 -- the inner bound is now LATCH_WINDOW_X_HI (18.400), not the
    # LDraw-measured 19.200.
    #
    # Owner: *"The curve on the hook end should extend all the way to the
    # hook socket. Currently there are probably around 1mm residual, remove
    # it."* The arithmetic matches exactly: the curve stopped at 19.200
    # while the hook socket's own edge is at LATCH_WINDOW_X_HI = 18.400,
    # leaving 0.800 mm of square bottom edge stranded between them on each
    # side -- visible as a small step where the arc should have run into the
    # socket.
    #
    # This is the same class of finding as round 56 at the TONGUE end, where
    # "all the way" also turned out to be about EXTENT along X rather than
    # arc depth, and 47.200 mm of square edge was hiding in the gaps between
    # bands. Same lesson, smaller number.
    #
    # The bound is CONCEPTUALLY `LATCH_WINDOW_X_HI` -- "where the hook socket
    # starts" -- but that constant is defined further down this class body,
    # so referencing it here would raise NameError at class-creation time.
    # Written as the literal, with _build_bottom_end_round asserting the two
    # stay equal: if the hook socket ever moves and this does not follow, the
    # assert fires instead of a fresh residual appearing silently. The
    # superseded LDraw reading was 19.200.
    _LATCH_ROUND_X_INNER = 18.400
    BOTTOM_ROUND_X_LATCH = (
        (-WALL_X_OUTER_LOWER, -_LATCH_ROUND_X_INNER, BOTTOM_ROUND_CZ_FULL),
        (_LATCH_ROUND_X_INNER, WALL_X_OUTER_LOWER, BOTTOM_ROUND_CZ_FULL),
    )
    BOTTOM_ROUND_X_TONGUE = (
        (-WALL_X_OUTER_LOWER, WALL_X_OUTER_LOWER, BOTTOM_ROUND_CZ_FULL),  # round 56, full span
    )

    # --- Side windows (SS7.2, round 20 H3, round 21 RH3, round 41) ---
    # The window is the SAME OUTLINE as the cover's side handle, offset
    # outward by the running clearance -- see _build_side_window. These two
    # constants are the reference's own measurements of it, kept as the
    # cross-check that this class and the cover still describe one feature
    # (asserted in _build_side_window, not merely documented here).
    # ROUND 71: these were the LDraw reference's own measurements (12.000 and
    # 4.800). The Cover is now ground truth and the Tray's tab derives from
    # its window sill, so these follow the TAB rather than the reference --
    # otherwise the assertion in _build_side_window fires, which is exactly
    # what it is for and exactly what happened when the tab moved.
    #
    # Kept as constants rather than inlined into the builder: they are still
    # the independent statement of "what this window is", and the assertion
    # comparing them against the tab is still a real cross-check on the
    # DERIVATION (a sign error or a missing seat offset in _build_side_window
    # would break it). What changed is which part is authoritative.
    WINDOW_Y_HALF = PoweredUpHubBatteryTray.TAB_PAD_Y_HALF        # 11.750
    # ROUND 74 -- back-compensated by `- SHELL_Y_OFFSET`, same reasoning as
    # SOCKET_Y_CENTER above: this window is cut in the shell's LOCAL frame
    # and must still land on the Tray's own tab centreline once the
    # shell-wide translate is applied. _build_side_window reads this
    # constant (`self.WINDOW_Y_CENTER`), not the bare Tray constant, so the
    # two stay coupled through one definition.
    WINDOW_Y_CENTER = PoweredUpHubBatteryTray.TAB_Y_CENTER - SHELL_Y_OFFSET   # 0.175
    WINDOW_SHOULDER_Z = (
        PoweredUpHubBatteryTray.TAB_ROUND_CZ + PoweredUpHubCover.PLATE_THICKNESS
    )  # 4.350 world
    #
    # Round 41 retires WINDOW_TAPER_PROFILE = ((6.000, 11.761),
    # (8.000, 9.966), (8.400, 8.400)) -- three points sampled off the
    # reference's own faceted arc and joined by straight lines. A chord
    # always lies INSIDE the arc it subtends, so that outline was narrower
    # than the tab passing through it at every intermediate Z, and the cover
    # compensated by shrinking the whole tab 0.320 mm (its retired
    # _HANDLE_CHORD_ALLOWANCE) -- removing material the reference has, from
    # the part, to fit a cut that was the thing modelled wrong. This is
    # exactly the chord-vs-arc pitfall in vibe/INSTRUCTIONS.md, and the fix
    # the pitfall prescribes is to cut the true arc, not to trim the part.

    # --- Cord pass-through in the deck (round 49) ---
    # User-requested opening for the battery lead. Sized 20.0 x 10.0 clear so
    # an EC3-class connector passes, not just the IC2 the pack ships with.
    #
    # ORIENTATION IS FORCED, not chosen. The pack fills the box: 20.9 mm of
    # 21.2 in Z (0.3 mm -- nothing routes over the top) and 58.0 of 62.8 in Y
    # (2.4 mm at each end). The only real room is beside it in X, and at DECK
    # level that channel is 10.4 mm wide, not the 11.2 it is lower down,
    # because the side wall steps inward at WALL_STEP_Z to an inner face of
    # WALL_X_OUTER_UPPER - WALL_THICKNESS = 26.400. So the 20 runs along Y and
    # the 10 across X, and the slot very nearly fills the channel's width.
    #
    # The OUTBOARD edge sits FLUSH with the stepped side wall's inner face
    # (26.400) rather than a little short of it. Stopping short would leave a
    # 20 mm long, sub-millimetre ligament of deck spanning between hole and
    # wall: fragile, and about one extrusion wide. Flush, the deck simply ends
    # where the wall begins.
    #
    # The -Y edge does NOT go flush with the latch end wall (-30.800), which
    # was the first attempt. Measured against the built Cover, two of ITS
    # features reach into this channel there: the latch U at X 16.4..19.2 up
    # to Y = -30.700 and Z = 12.160, and the latch band (the plate's own
    # 1.200 -> 2.000 thickening) out to LATCH_BAND_Y_HI. A slot flush with the
    # wall cleared the deck slab but the connector fouled the U on the way
    # down -- a hole is not a route. Taking the Cover's own LATCH_BAND_Y_HI as
    # the datum clears both, and leaves a 0.800 mm strip of deck between slot
    # and end wall: not a free ligament, since it is continuous with the deck
    # capping the wall, and 0.800 is this part's ordinary wall section anyway.
    #
    # This puts the slot 6.0 mm off the reference's own forward port centre
    # (SS7.3: Y = -24.000, 13.600 long). A 20 mm opening cannot be centred
    # there regardless -- it would reach Y = -34.000, into the end wall's top.
    # The slot still sits within that port's channel, just pushed inboard.
    CORD_PORT_WIDTH = 10.000     # X, across the side channel
    CORD_PORT_LENGTH = 20.000    # Y, along the box
    # Corner radius, plus the margin that keeps the CLEAR opening at the full
    # 20.0 x 10.0. A sharp-cornered box of half-extents (a, b) passes a
    # rounded slot of half-extents (a+m, b+m) with radius r only when
    # m >= r(1 - 1/sqrt(2)) ~= 0.293r; at r = 1.000 that is 0.293, taken as
    # 0.300. Without the margin the corners clip and the stated size is a lie.
    # ROUND 81b -- frozen at 26.000, the value this port has always had, but
    # stated directly instead of inherited from WALL_INNER_STEP_Z (which is
    # PoweredUpHubCover.PLATE_THICKNESS + PoweredUpHubBatteryTray.WALL_Z_HI).
    # That inheritance was harmless while the Tray's wall top and the port's
    # floor happened to coincide; the owner's round-81b re-measure dropped
    # the Tray's long wall to world 22.300, which would have moved this port
    # 3.700 mm as an invisible side effect. The port answers to where the
    # cord leaves the box, not to how tall the Tray is.
    CORD_PORT_Z_LO = 26.000
    CORD_PORT_CORNER_R = 1.000
    CORD_PORT_MARGIN = 0.300

    # --- Pin-hole / arm map (SS1, SS2) ---
    # ROUND 73 -- owner: "the two side arms' hole centres are 64.000 apart",
    # and explicit that the Technic pattern is STRICT and must not be
    # compromised to suit the shell. Derived from the stud pitch rather
    # than left a bare literal, per that direction; the assert below is the
    # verification the owner asked for (64.000 = 2 * HOLE_X).
    HOLE_X = 4 * STUD_PITCH   # 32.000
    assert abs(2 * HOLE_X - 64.000) < 1e-9, (
        "owner-measured round 73: the two side arms' hole centres must be "
        "64.000 mm apart -- the strict Technic pattern is not negotiable"
    )
    HOLE_Y = (16.000, 24.000, HOLE_X)   # inner / middle / outer, one quadrant
    # outer element derived, not retyped: the outer hole sits at the same
    # distance from centre in both X and Y (this is why a single ARM_CAP_R
    # makes the arm tangent to the envelope in both directions -- see it).
    HOLE_AXIS_Z = 20.000
    ARM_THICKNESS = 8.000                # -> PerpendicularHolesLiftarm(thickness=...)
    ARM_Z_LO = HOLE_AXIS_Z - ARM_THICKNESS / 2   # 16.000
    # ARM_Y_LO (inboard flat face), ARM_Y_HI (outboard face) and
    # ARM_LENGTH are defined further down, once ARM_CAP_R exists -- round
    # 73 made ARM_Y_LO a DERIVED value (see the note there for why the old
    # fixed literal silently broke), and round 73b made ARM_Y_HI derived
    # too (it must NOT read HALF_Y -- see its own note).

    # Root-bridge Band A (round 17, Escalation 8) -- the arm-local Z
    # window (thickness axis, pre-_place_arm) where the root bridge
    # reaches deepest into the wall. Local Z in [ROOT_BAND_A_Z_LO,
    # ARM_THICKNESS] maps to global Z in [WALL_STEP_Z, ARM_Z_LO +
    # ARM_THICKNESS] = [22.0, 24.0] (both ends via the +ARM_Z_LO offset
    # _place_arm applies), i.e. exactly the wall's upper band. Below
    # ROOT_BAND_A_Z_LO (Band B, global Z in [ARM_Z_LO, WALL_STEP_Z] =
    # [16.0, 22.0], the wall's lower band -- where the tray's own wall
    # sits), a SHALLOWER reach applies (round 20, H4 -- see
    # _build_arm_and_bore_local's own comment) rather than none at all;
    # see that method's comment for the full derivation and the ~85.8 mm^3
    # margin proving Band A alone still fuses the arm to the wall.
    ROOT_BAND_A_Z_HI = ARM_THICKNESS
    ROOT_BAND_A_Z_LO = ARM_THICKNESS - 2.000

    # --- Arm plan geometry (round 43) -- measured off Philo's own LDraw
    # subpart `s\24851s01.dat`, which builds each arm end from
    # `1-4cylo` at scale 9 LDU centred ON the outer hole:
    #
    #     1 16 80 -10 80   9 0 0 / 0 20 0 / 0 0 9   1-4cylo.dat
    #
    # 9 LDU = 3.600 mm, so the cap radius EQUALS the arm's half-width and
    # its centre IS the hole centre. Centred on the hole at 32.000 that
    # reaches exactly 35.600 in both plan directions -- the cap is
    # naturally tangent to the envelope, and nothing is trimmed.
    #
    # Rounds 16-42 instead took PerpendicularHolesLiftarm's own
    # Cailliau-calibrated 7.800 width / 3.900 cap radius (overshooting to
    # 36.000 and 35.900) and squared it off with two flat trims. That is
    # what cut the round cap into a 3.440 mm flat chord at the tip and a
    # flat down the outboard side, and what left the re-entrant notch where
    # the arm met the end wall.
    # ROUND 73a -- owner-measured: "overall width INCLUDING the arms =
    # 71.350" -> half 35.675, DERIVED at the time as `HALF_Y - HOLE_X`
    # because the X arm-envelope and the Y length HAPPENED to share the
    # same 35.675 figure that round.
    #
    # ROUND 73b -- that coupling is now WRONG and has been removed. HALF_Y
    # moved to 35.625 (see its own comment) on a completely independent
    # owner measurement (inner cavity length), while the arm's own X reach
    # is UNCHANGED at 71.350/half 35.675 (owner re-confirmed: "along X:
    # arm flat face to flat face = 71.350... unchanged"). Deriving
    # ARM_CAP_R from HALF_Y would have silently SHRUNK the arm by 0.050 mm
    # the moment HALF_Y moved -- exactly the class of coincidence-coupling
    # bug already caught once this round against ARM_Y_LO's old hardcoded
    # literal (see that constant's own note). `ARM_X_OUTER` is the correct,
    # independent input: it is its OWN owner ground truth (the arm's flat
    # face envelope), not derived from the housing's Y length.
    ARM_X_OUTER = 35.675   # owner-measured, arm flat-face half-width (71.350 / 2)
    # ROUND 73b -- owner: "I did not include the bosses. When including
    # them the measurement is 71.7mm" -> boss-tip half-width 35.850. This
    # is the SECOND independent X-axis ground truth this round (the first
    # being ARM_X_OUTER above); BOSS_PROUD below is derived from the two
    # rather than kept as its own free literal, so the two measurements
    # cannot silently drift apart.
    ARM_BOSS_X_OUTER = 35.850   # owner-measured, boss-tip half-width (71.700 / 2)
    # The arm's cap is centred ON the outer hole (HOLE_X) and tangent to
    # the X envelope (see the LDraw note above), so the cap radius is the
    # remaining reach from the hole centre to ARM_X_OUTER.
    ARM_CAP_R = ARM_X_OUTER - HOLE_X   # 3.675
    ARM_WIDTH = 2 * ARM_CAP_R     # 7.350
    ARM_LENGTH = 2 * STUD_PITCH + ARM_WIDTH   # 23.350; 2 x hole pitch + 2 x cap radius

    # ROUND 73 CORRECTION (found by the verification probe, not by paper
    # arithmetic -- see the round-73 implementation report). ARM_Y_LO used
    # to be a fixed literal (12.400, "inboard flat face, envelope trim").
    # That was fine only as long as it happened to satisfy
    # HOLE_X - ARM_Y_LO == 2 * STUD_PITCH (32.000 - 12.400 == 19.600 ==
    # 2 * 8.000) -- the coincidence that made the arm's two vertical hole
    # positions (built from `half_w + i * STUD_PITCH` in
    # _build_arm_and_bore_local) land on the correct global Y (HOLE_Y) AND
    # made the outboard cap land exactly on HALF_Y, simultaneously, with
    # the OLD ARM_CAP_R (3.600). Once ARM_CAP_R moved to 3.675 (this
    # round), a fixed 12.400 could no longer satisfy both at once -- it
    # either overshoots the envelope by 0.075 mm (if ARM_LENGTH is derived
    # from tangency) or breaks the hole-pitch construction's own internal
    # assert (if ARM_LENGTH keeps the "2 hole pitches + cap width" form
    # while ARM_Y_LO stays fixed) -- both were tried and both failed
    # (see the report). The two conditions are only simultaneously
    # satisfiable if ARM_Y_LO itself is derived FROM ARM_CAP_R, not held
    # fixed: the arm's inner vertical hole must land at global Y = HOLE_Y[0]
    # (16.000, an independent grid position unaffected by this round), and
    # that hole sits at local X = ARM_CAP_R in the arm's own frame, so
    # ARM_Y_LO = HOLE_Y[0] - ARM_CAP_R. Algebraically this is the same
    # value as `HOLE_X - ARM_CAP_R - 2 * STUD_PITCH` (since HOLE_Y[0] and
    # HOLE_X are 2 * STUD_PITCH apart on the hole line), which is the form
    # used here to keep it visibly tied to the same envelope/pitch inputs
    # ARM_LENGTH above already uses.
    ARM_Y_LO = HOLE_X - ARM_CAP_R - 2 * STUD_PITCH   # 12.325

    # ROUND 73b -- the round-73a cross-check assert that used to live here
    # (`ARM_LENGTH == HALF_Y - ARM_Y_LO`) is RETIRED, not merely relaxed. It
    # asserted the arm's outboard tip lands exactly on HALF_Y -- true only
    # while the X arm-envelope and the Y housing-length coincided at
    # 35.675. They no longer do (HALF_Y = 35.625, ARM_X_OUTER = 35.675), so
    # the arm's actual Y-tip (ARM_Y_LO + ARM_LENGTH, see ARM_Y_HI below) now
    # sits 0.050 mm PAST HALF_Y by design -- the arm's own hole-pitch grid
    # (HOLE_X, STUD_PITCH, ARM_CAP_R) governs its length, per the owner's
    # "strict Technic pattern" direction (item 3), and is independent of
    # the housing's own end-wall length. Keeping the old assert here would
    # fire on every future measurement of either quantity even though
    # nothing is wrong. See ARM_Y_HI immediately below for the arm's real,
    # measured Y-reach and the round-73b implementation report for the
    # built-solid measurement confirming this is a harmless, expected
    # overshoot (not a wall collision -- the arm sits at a different X range
    # than the end walls').
    #
    # The arm's own outboard face in Y, i.e. where its tip's rounded cap
    # actually reaches -- NOT the housing's HALF_Y (see the retired assert
    # above for why those are no longer the same number). Kept for
    # documentation; not read by any builder (the geometry itself is
    # already fully determined by ARM_Y_LO and ARM_LENGTH).
    ARM_Y_HI = ARM_Y_LO + ARM_LENGTH   # 35.675 (== ARM_X_OUTER, by construction)

    # Local-frame -> global-Y translation offset for the arm/bore remap
    # (see _place_arm). Round 43: the arm is now built at its own real
    # length with cap centres ON the hole line, so local X = 0 IS the arm's
    # inboard face and the offset is simply ARM_Y_LO. Rounds 16-42 needed a
    # separate number (12.0) because the arm was built one stud pitch too
    # long and then trimmed back, which put local X = 0 outside the part.
    _ARM_Y_OFFSET = ARM_Y_LO

    # ROUND 73a -- NOT re-derived from ARM_WIDTH. BOSS_DIAMETER already
    # equalled the OLD ARM_WIDTH (7.200) before this round, which reads as
    # a plausible independent Technic-standard boss diameter (the
    # reference's own connector-boss figure) rather than a tracked
    # relationship to this class's own arm cross-section -- no comment or
    # test in this file ties the two together, so this round leaves it as
    # its own literal rather than inventing a coupling that was never
    # stated.
    BOSS_DIAMETER = 7.200

    # ROUND 73b -- BOSS_PROUD is now DERIVED, not its own literal. Owner:
    # "I did not include the bosses. When including them the measurement
    # is 71.7mm" -> boss-tip half-width 35.850 (ARM_BOSS_X_OUTER, defined
    # above alongside ARM_X_OUTER). The proud distance is simply the gap
    # between the two independently-measured half-widths.
    BOSS_PROUD = ARM_BOSS_X_OUTER - ARM_X_OUTER   # 0.175 (was 0.400)

    # --- Horizontal (middle) arm hole, round 43 ---
    # Philo builds it from LDraw's `connhol3` primitive -- the BLIND pin
    # hole, counterbored at one rim only -- not the through-hole `connhole`
    # the two vertical positions use:
    #
    #     1 16 80 0 60   0 -1 0 / 1 0 0 / 0 0 1   connhol3.dat
    #
    # The matrix sends local +Y to global -X, so the counterbored rim is the
    # OUTBOARD one (the boss tip, |X| = 90 LDU = 36.000) and the bore floors
    # inboard at |X| = 72 LDU = 28.800, leaving 0.400 mm of arm behind it
    # before the root bridge and the side wall. Depth is therefore 7.200,
    # not the 8.000 of a through hole.
    #
    # Round 42 had reached the blind conclusion independently but floored at
    # 28.000 with counterbores at BOTH rims; the far flange hollowed out
    # exactly the thin material a blind hole has least of. These figures
    # were originally the reference's own.
    #
    # ROUND 73b -- superseded by a FUNCTIONAL requirement. Owner, verbatim:
    # "The bore for the horizon holes should be 8mm. These need to work
    # with a lego technic pin." This is no longer a cosmetic LDraw copy --
    # a real Technic pin needs the full 8.000 mm to seat and grip.
    MID_BORE_DEPTH = 8.000
    # ROUND 73a -- this was a bare LDraw-measured literal (28.800, off
    # 24851s01) cross-checked against the method's own derivation via an
    # assert. That cross-check went stale that same round (ARM_CAP_R moved
    # off its LDraw value), so it was re-derived from the method's own four
    # inputs instead of asserting against a superseded reference number.
    #
    # ROUND 73b -- re-derived again with MID_BORE_DEPTH = 8.000 and the new
    # BOSS_PROUD = 0.175. The assert in _build_arm_and_bore_local remains a
    # restated identity (defense-in-depth against the two expressions
    # drifting apart), not an independent LDraw fidelity check.
    MID_BORE_FLOOR_X = HOLE_X + ARM_CAP_R + BOSS_PROUD - MID_BORE_DEPTH  # 27.850
    # ROUND 73b -- RE-INTERPRETED, not just re-valued, per the owner's own
    # description: "the horizon hole is not fully connected to the housing,
    # there is a small gap. The thickness including the gap and boss should
    # be 8mm exactly." Read literally against the geometry (see the
    # stack-up in _build_arm_and_bore_local's own comment at the bore): at
    # 8.000 mm the bore's floor lands 0.475 mm PAST the arm's own nominal
    # flat face (ARM_CAP_R from the hole centre) -- i.e. genuinely into the
    # "gap"/root-bridge transition zone the owner is describing, not a
    # defect to shave away. The MEANINGFUL floor guard is therefore no
    # longer "how much of the arm's own bulk survives" (that number is now
    # negative by design) but "how much of the ROOT BRIDGE's own reach
    # survives beyond the bore's floor" -- the true remaining backing
    # material, re-measured on the built solid in the round-73b report.
    # Value UNCHANGED (0.400) -- what changed is what it's measured
    # against; see the assert in _build_arm_and_bore_local.
    MID_BORE_MIN_FLOOR = 0.400

    # --- Latch end (-Y), SS5.2 / SS11 ---
    LATCH_Y = -HALF_Y
    # Round 22 -- thickened from the round-18 single 1.200 mm skin so the
    # wall actually MEETS the cover instead of leaving an open 3.600 mm
    # slot around the leg end. The inner face now lands on
    # PoweredUpHubCover.PLATE_Y_LO (-30.800 mm), i.e. the cover's own plate
    # edge, closing the gap the user flagged.
    #
    # The tongue end carries the mating LIP for the cover's own 6 locating
    # teeth (PoweredUpHubCover.TOOTH_X_BANDS); per the round-22 decision the
    # teeth and their notches both live on the cover, exactly as in the
    # reference, so this class carries no ridges of its own.
    #
    # This does NOT re-thicken the wall where the latch U lives. That band
    # (|X| in [5.600, 19.200] -- the cover's hook legs AND release legs
    # share one hook_width footprint) is cut straight back to the original
    # 1.200 mm skin by _build_latch_clearance, so every verified round-18
    # to round-21 latch interface -- the catch boss, its undercut slot, the
    # keeper nub, the retention ledge -- still sits in exactly the wall it
    # was derived against. The thickening is confined to the three spans
    # BETWEEN and OUTBOARD of the fingers, which is precisely where the
    # gaps were and precisely where the alignment ridges go.
    # ROUND 73 -- owner-measured, superseding round 22's 4.800 (which was
    # itself derived to land exactly on Cover.PLATE_Y_LO, -27.800).
    #
    # ROUND 73b -- value UNCHANGED at 5.000 (owner re-confirmed: "Can we do
    # 5mm on the hook side"). Only the datum it's measured FROM moved
    # (HALF_Y: 35.675 -> 35.625), so the inner face itself moves slightly:
    # LATCH_Y + LATCH_WALL_THICKNESS = -35.625 + 5.000 = -30.625 (was
    # -30.675). Still sits OUTBOARD of the frozen Cover.PLATE_Y_LO (-27.800)
    # by 2.825 mm -- clearance, not a collision.
    #
    # ROUND 74 -- 5.000 -> 6.050, thickened INWARD (LATCH_Y, the OUTER face,
    # is untouched -- only the wall's own thickness grows, so the shell's
    # overall length is unaffected). Required by the same two ground-truth
    # constraints that produced SHELL_Y_OFFSET: with the shell re-datumed,
    # the wall's inner face must land on the frozen Cover hook's own inner
    # face. Measured (`tmp/r74_latch_wall_datum.py`): world outer face
    # -33.800 (= LATCH_Y + SHELL_Y_OFFSET), world inner face -27.750 (=
    # LATCH_Y + LATCH_WALL_THICKNESS + SHELL_Y_OFFSET) -- both match the
    # hook/thumb-pad targets to within 0.020 mm. Kept a SOLID slab, not a
    # two-skin void -- see the design brief's round-74 *Latch-end wall*
    # decision.
    LATCH_WALL_THICKNESS = 6.050   # world: -33.800 -> -27.750
    LATCH_SKIN_THICKNESS = 1.200   # what survives in the latch-U band

    # ROUND 73b -- owner's own cross-check on HALF_Y and the two end-wall
    # thicknesses, verbatim: "The length between the inner walls (flat
    # part, not counting the holes left for the tongues and pegs) is
    # 61.75mm... This leaves 9.5mm for the two walls... 5mm on the hook
    # side and 4.5mm on the tongue side" (71.250 - 61.750 = 9.500 =
    # 5.000 + 4.500). Made impossible to break silently: whichever of
    # HALF_Y / LATCH_WALL_THICKNESS / TONGUE_WALL_THICKNESS changes next,
    # this assert (evaluated at class-body time, i.e. at import) fires
    # immediately rather than leaving a silently-drifted cavity length.
    # "Not counting the holes left for the tongues and pegs" means the
    # tongue rebate (TONGUE_INNER_Y_LOWER) and end-wall trapezoid pegs are
    # explicitly EXEMPT from this identity -- they are deeper, functional
    # cuts into the flat wall this constant describes, not violations of it.
    CAVITY_LENGTH = 61.750

    # The cover's nominal hook footprint, which _build_finger_windows asserts
    # these still equal. Round 61: HI 19.200 -> 17.800, following round 60's
    # hook_width 13.600 -> 12.200. Round 69: 17.800 -> 18.400, following
    # round 69's 12.200 -> 12.800 -- same coupling, same fix, third time. LO
    # is unchanged because it is hook_pitch/2 and does not depend on width.
    # This is NOT a re-datum of the housing (which stays reference-faithful by
    # direction) -- it is the window tracking the hook that passes through it,
    # which is the one thing it is not allowed to stop doing.
    LATCH_WINDOW_X_LO = 5.600
    LATCH_WINDOW_X_HI = 18.400
    LATCH_WINDOW_Z_HI = 3.600
    # Retention land (round 30) -- see _build_latch_land. Proud to within
    # 0.050 mm of the leg's -34.000 baseline, spanning Z strictly below
    # the bead's seated band (Cover.BEAD_Z_LO = 4.750).
    # Round 38: -34.050 -> -34.000. The Cover's U ribbon put the leg's
    # outer face at -33.950 (was -34.000), which cut bead engagement from
    # 0.170 to 0.120 mm and dropped retention at dz = -0.400 to zero.
    # This restores 0.170 mm engagement while keeping the same 0.050 mm
    # running clearance against the leg.
    LATCH_LAND_Y = -34.000
    LATCH_LAND_Z_LO = 3.700
    LATCH_LAND_Z_HI = 4.500

    # --- Tongue end (+Y), SS12 ---
    TONGUE_Y = HALF_Y
    TONGUE_STEP_Z = 1.874
    # ROUND 76 -- moved INBOARD, 33.378 -> 32.525, to close the gaps the
    # owner marked on the tongue side of an annotated top view: *"Tongue
    # side (blue part) should have these gaps covered"*.
    #
    # Measured before the change (`tmp/r76_end_gaps.py`), the gap from the
    # Cover's own tongue edge to this face read 1.003 mm across most of the
    # span, opening to 2.203 at |X| ~ 1/17 and 3.003 at |X| ~ 26 -- the four
    # open bands the owner circled.  The face sat at 35.203 world while the
    # Cover's tongue edge sits at 34.200, so the wall simply stopped short
    # of the tongues instead of covering them.
    #
    # 32.525 local = 34.350 world = the Cover's tongue edge (34.200) plus
    # one running clearance (0.150), so the wall now covers the tongues with
    # the same allowance every other Cover/Housing interface uses rather
    # than a number invented here.
    #
    # SECOND EFFECT, and it is the one the owner asked for two rounds ago:
    # the wall bottoms out where its own inner face crosses the bottom-round
    # arc, so walking the face inboard walks the wall further AROUND that
    # arc -- from Z 0.264 at the old face to ~Z 0.035 at this one.  That is
    # "the bottom curve extends and wraps like a pocket... the end should sit
    # flush with the cover bottom", achieved by extending the curve rather
    # than truncating it (an earlier floored-cutter attempt flattened it and
    # was reverted -- see BOTTOM_ROUND_Z_FLOOR_TONGUE).
    TONGUE_INNER_Y_LOWER = 32.525   # inner face, Z < TONGUE_STEP_Z (the rebate)
    # ROUND 73c -- KEPT UNCHANGED. This is a genuinely DIFFERENT feature from
    # the owner's "first 5mm is narrower" observation below, not the same
    # feature mis-dimensioned -- the evidence is the exact numeric coupling
    # `TONGUE_STEP_Z == PoweredUpHubCover.TIP_Z_LO` (both 1.874), asserted in
    # test_tongue_rebate_matches_cover_tongue. That is not a coincidence: it
    # marks exactly where the Cover's own tongue-tip riser feature begins.
    # Retuning it to 5.000 would decouple this rebate from the real Cover
    # geometry it hooks under. See TONGUE_RELIEF_Z_HI below for the separate,
    # wider relief the owner is actually describing.

    # Nominal back-wall inner face -- exactly coincident with
    # PoweredUpHubCover.TONGUE_Y_HI (34.400 mm), i.e. a bare zero-clearance
    # literal-to-literal butt (round 18, S7). self._tongue_inner_y_upper
    # (below) is the profile-corrected value _build_tongue_wall actually
    # uses. This governs the NARROW tip-clearance band (`TONGUE_STEP_Z` to
    # `tongue_clear_z_hi`, ~2.95 mm) that clears the Cover's own riser as it
    # is inserted -- an independent, still-load-bearing requirement.
    #
    # ROUND 73c -- ATTEMPTED retirement, REVERTED. My first pass at this
    # round merged this band into a single wider relief (see
    # TONGUE_RELIEF_Z_HI/THICKNESS below) on the theory that it was the same
    # feature as the owner's "first 5mm is narrower" observation,
    # mis-dimensioned. Measured on the built solid: that merge INCREASED
    # Housing/Cover seated interference by 49.546 mm^3 (A/B-isolated,
    # `tmp/r73c_cover_triple_ab.py`) -- this band's own old, narrower
    # thickness was doing real clearance work for the Cover's riser/rib
    # mating features that the owner's wider, plate-seating-derived figure
    # (3.000 mm) does not provide (that figure was grounded against
    # `Cover.PLATE_Y_HI`, a DIFFERENT Cover feature than the riser). Kept
    # UNCHANGED; the owner's new relief is added as a genuinely SEPARATE,
    # adjacent band above it instead -- see TONGUE_RELIEF_Z_HI.
    TONGUE_INNER_Y_UPPER = 34.400

    # ROUND 73c -- the owner's separately-described relief, verbatim:
    # "I noticed the wall on the tongue side is stepped. The first 5mm on
    # the Z is narrower. It's difficult to measure due the curve on the
    # outer wall." Then, on follow-up: "Beneath that the tongue side wall
    # is measured around 4 to 4.2mm" (see TONGUE_WALL_THICKNESS below) --
    # read together, this places the visible step's TOP at Z = 5.000, with
    # a DIFFERENT (thinner) wall below it.
    #
    # This is a THIRD, adjacent band -- ABOVE the existing riser-clearance
    # band (`TONGUE_STEP_Z` to `tongue_clear_z_hi`, ~2.95 mm, UNCHANGED, see
    # `TONGUE_INNER_Y_UPPER`'s note), not a replacement for it. The owner's
    # single visible "first 5mm" observation encloses BOTH the rebate
    # (Z < 1.874) and the riser-clearance band (up to ~2.95) as well as this
    # new extension (2.95 to 5.000) -- from outside, a caliper or eye cannot
    # distinguish three internal sub-bands from one, so "the first 5mm is
    # narrower" is consistent with all three existing/added, not evidence
    # that they should collapse into one.
    TONGUE_RELIEF_Z_HI = 5.000

    # The owner could not directly measure this thickness (curved outer
    # wall defeats a flush caliper reading), so it is NOT a measured
    # literal -- it is DERIVED from the frozen Cover, which the owner's own
    # instruction requires: below TONGUE_RELIEF_Z_HI the wall must clear
    # PoweredUpHubCover.PLATE_Y_HI (32.200, frozen), so the relieved
    # thickness must be <= HALF_Y - PLATE_Y_HI = 35.625 - 32.200 = 3.425.
    #
    # A follow-up owner reading grounds the actual value within that bound:
    # the tongue-end gap (outer face -> Cover plate edge) reads ~3.000 with
    # NO visible gap -- i.e. this relief's own thickness IS that reading,
    # because the Cover's plate seats flush into this exact recess. This
    # value is a SOFT number (owner's own words: no direct caliper read),
    # comfortably inside the 3.425 derived cap (0.425 mm margin). This band
    # occupies Z = [tongue_clear_z_hi, TONGUE_RELIEF_Z_HI] -- ABOVE where
    # the Cover's riser itself reaches (RISER_Z_HI = 2.800), a Z-range with
    # no pre-existing clearance requirement -- verified against the built
    # solid in the round-73c report (adding this band alone, without
    # touching the riser-clearance band above, introduces NO new
    # Housing/Cover collision).
    TONGUE_RELIEF_THICKNESS = 3.000
    # ROUND 74 -- the bound is `+ SHELL_Y_OFFSET`, not the bare local
    # HALF_Y. HALF_Y is the tongue outer face's LOCAL (pre-translate) Y;
    # its WORLD position (what actually has to clear the frozen Cover's
    # PLATE_Y_HI) is HALF_Y + SHELL_Y_OFFSET, since the whole shell rides
    # +SHELL_Y_OFFSET further from the latch end and hence further PAST the
    # tongue end's own old position -- the redatum only WIDENS this
    # clearance (35.625 - 32.200 = 3.425 margin 0.425 -> 37.450 - 32.200 =
    # 5.250 margin 2.250), so this bound was never at risk from the redatum;
    # it is kept accurate rather than left silently understating the true
    # clearance.
    assert TONGUE_RELIEF_THICKNESS <= HALF_Y + SHELL_Y_OFFSET - PoweredUpHubCover.PLATE_Y_HI, (
        "the tongue relief's thickness must clear the frozen Cover's own "
        "plate edge (derived bound, not measured) -- see TONGUE_RELIEF_"
        "THICKNESS's own comment"
    )

    # ROUND 73c -- the flat wall's OWN thickness above TONGUE_RELIEF_Z_HI,
    # SUPERSEDES round 73b's 4.500. Owner, first pass: "Can we do... 4.5mm
    # on the tongue side" -- a proposed round number, not yet a caliper
    # reading. Owner, follow-up (this round): "Beneath that the tongue side
    # wall is measured around 4 to 4.2mm" -- an ACTUAL measurement of the
    # real part's wall, taken above the newly-identified step. This is the
    # more authoritative figure for what `_build_tongue_wall`'s main band
    # actually builds, so it supersedes 4.500. The owner gave a RANGE, not
    # a point value -- 4.100 is the range's midpoint, held as a soft
    # nominal (not to be read as more precise than the +-0.100 range it
    # came from).
    TONGUE_WALL_THICKNESS = 4.100

    # ROUND 73c -- the round-73b cross-check identity NO LONGER CLOSES and
    # the strict assert that encoded it has been REMOVED (not loosened) --
    # see the round-73c report for the full arithmetic. Three independently
    # owner-measured quantities (outer length 2*HALF_Y = 71.250, flat
    # cavity length CAVITY_LENGTH = 61.750, and the two end-wall
    # thicknesses LATCH_WALL_THICKNESS + TONGUE_WALL_THICKNESS = 5.000 +
    # 4.100 = 9.100) no longer sum consistently: 71.250 - 61.750 = 9.500,
    # not 9.100 -- a 0.400 mm gap. This is NOT a code bug to silently
    # reconcile by adjusting one of the three; it is reported to the owner
    # as an open question (round-73c report, item C) because the housing's
    # curved ends make all of these approximate reads. Keeping a strict
    # assert here would either force a silent, uninstructed choice of which
    # figure is "wrong," or fail every import -- both worse than removing
    # the now-false claim and reporting the discrepancy honestly.
    # ROUND 74 -- this assert (round 73c's "unchanged" pin at 5.000) is
    # RETIRED, not loosened: LATCH_WALL_THICKNESS legitimately changes this
    # round (5.000 -> 6.050, see its own comment), by explicit owner
    # direction, thickened INWARD only -- it does not touch CAVITY_LENGTH,
    # HALF_Y, or the outer envelope the round-73c arithmetic above was
    # about. A stale `== 5.000` pin left in place would fail on every import
    # from here on for a change that is intentional and already accounted
    # for elsewhere; deleting it (rather than bumping the literal) avoids
    # leaving a second assert nobody re-derives next time this value moves.

    # --- Tongue-end locating ribs (round 46), SS12.2 T1/T2/T3 ---
    # The reference tongue end is a two-skin structure whose skins are
    # joined by ribs, and the lid's tongue is not one slab but FOUR blades
    # that slide into the slots BETWEEN those ribs.  Round 45 cut the four
    # blades on the Cover (PoweredUpHubCover.TONGUE_GAP_X_INNER /
    # .TONGUE_RIB_X_HI); this wall stayed full width, so the slots existed
    # but nothing entered them -- costing the reference's own +/-X location
    # at this end (SS12.2's "Sideways -> located" row).  These are the ribs
    # that enter them.  Nominal X bands, measured (SS12.2 T1/T2/T3):
    #
    #   centre wall   |X| <= 0.800           between the two Tongue A slots
    #   inner ribs    |X| 15.600 .. 17.200   Tongue A / Tongue B divider
    #   outer ribs    |X| 26.000 .. 28.000   Tongue B / shell
    #
    # The outer band's |X| 27.200..28.000 is already the shell side wall;
    # the rib is what fills it inboard to 26.000.
    #
    # Load-bearing status, stated plainly because the reference research is
    # explicit about it (SS12.4, "What the single wall must provide"): the
    # rebate is the retention, and these ribs are the *optional* X-location
    # -- the shell's own side walls at |X| 27.200 already locate the lid,
    # and the ribs only tighten it.  They are built because the Cover now
    # carries the matching slots, so omitting them leaves the mating
    # surface deliberately unpaired; they are NOT what holds the lid on.
    # ROUND 77 -- 0.800 -> 0.900, thickening the centre ridge along X.
    # Owner: *"make the 5 ridges mating the sockets slightly thicker (along
    # X).  Use the sockets thickness as the truth, try leaving 0.4mm gap on
    # the side."*
    #
    # The Cover's centre socket spans X +-TONGUE_GAP_X_INNER (+-1.150,
    # measured 2.300 wide), so the target BUILT half-width is
    # 1.150 - 0.400 = 0.750.  `_build_tongue_ribs` already takes one running
    # clearance off each flank, so the NOMINAL half-width carried here is
    # 0.750 + clr = 0.900 at the default profile -- i.e. the owner's 0.400 is
    # the total per-flank gap, of which 0.150 was already being applied.
    # Built width goes 1.300 -> 1.500.
    TONGUE_RIB_CENTRE_X_HALF = 0.900
    # ROUND 75 -- the inner band is RE-CENTRED on the Cover's own slot, not
    # left on its nominal reference value.  Measured on the built Cover
    # (`tmp/r75b_gap_sweep.py`), the three slots are 2.300 wide and centred at
    # X = 0.000 and +-16.100.  The inner band was (15.600, 17.200), i.e.
    # centre 16.400 -- 0.300 outboard of the slot it enters, which left
    # 0.200 mm on one flank and 0.800 on the other instead of a symmetric
    # 0.350.  Re-centred to 16.100 at the SAME 1.600 width; only the centre
    # moved, so the rib still clears both flanks by 0.350 before clearance.
    # The centre band is already on 0.000 and is unchanged.  The outer band
    # (26.000, 28.000) is the Tongue B / shell divider -- it is NOT one of
    # the three slots and is deliberately untouched.
    # ROUND 77 -- inner band widened 1.600 -> 1.800 nominal, same 16.100
    # centre, for the owner's 0.400 mm per-flank gap (see
    # TONGUE_RIB_CENTRE_X_HALF's note for the clearance arithmetic).  The
    # Cover's inner sockets span X 14.950..17.250 (2.300), so the built
    # ridge becomes 15.350..16.850 (1.500) with exactly 0.400 to each socket
    # flank.  The OUTER band is left alone pending the owner's "strange
    # socket" call -- it sits outboard of the Cover's plate edge (26.165)
    # and so is not mating a Cover socket the way the other four are.
    #
    # ROUND 77, the outer band's upper edge: 28.000 -> WALL_X_OUTER_LOWER,
    # DERIVED rather than restated.  Owner: *"Some strange socket here,
    # remove it"*, corrected to *"it's not a socket, it's a bump"*.
    # Measured: a 0.562 mm^3 lump at X 27.850..28.000, Y 33.150..34.400,
    # Z 0.000..3.000 -- this rib standing 0.150 mm PROUD of the side wall's
    # outer face.
    #
    # It is a stale literal, not a feature.  The band's own comment above
    # says the outer flank "is already the shell side wall", which was true
    # when that face was at 28.000; round 73 moved it to 27.850 (owner's
    # measured 55.700 overall width) and this literal did not follow.  The
    # builder then skips the clearance for exactly this flank ("only the
    # shell's own outer face has nothing to clear"), so the mismatch showed
    # up undiminished as a bump.  Deriving it means the next width change
    # cannot reopen this.
    #
    # ROUND 78 -- a THIRD band added, the side-socket ridge.  Owner: *"For
    # the blue area on the tongue edge, add a small ridge similar to the 3
    # ridges in the middle"*.
    #
    # The side socket runs from the Cover's riser edge (RISER_X_HALF,
    # 25.010, measured ground truth) to its plate edge (PLATE_WIDTH/2,
    # 26.165) -- 1.155 wide.  At the same 0.400 per flank the other ridges
    # now use, the built ridge is 1.155 - 0.800 = 0.355, centred on 25.588;
    # the nominal band carries the builder's own clearance back on top.
    #
    # This is DELIBERATELY under one 0.400 mm nozzle width, on the owner's
    # explicit call ("Build it at 0.340 anyway") after being shown the
    # figure.  A slicer may thin it or drop it; that is accepted, and it is
    # recorded here so a later reader does not "fix" it as an error.
    #
    # ROUND 79 -- the outermost ridge and the old separate outer band are
    # now ONE band, (25.260, WALL_X_OUTER_LOWER).  Owner: *"On the tongue
    # side the first and the last ridges should connect with the inner
    # wall. No cut should present."*, and earlier: *"the ridges on the
    # corners should connect to the long wall (so it's actually a wedge)"*.
    #
    # Round 78 built these as two separate bands -- the side ridge at
    # 25.410..25.765 and the outer band at 26.150..27.500 -- leaving a
    # measured 0.385 mm cut between them, and the side ridge floating clear
    # of the wall.  Merged, the built ridge runs 25.410..27.500: one
    # continuous wedge from the socket out into the side wall, no cut.
    #
    # The inboard flank keeps its 0.400 mm gap to the Cover's riser edge
    # (25.010 + 0.400 = 25.410, unchanged).  The outboard flank
    # deliberately takes NO clearance -- it IS the wall now, which is the
    # whole point, and the builder already skips the clearance for a flank
    # sitting at WALL_X_OUTER_LOWER.
    TONGUE_RIB_X_BANDS = (
        (15.200, 17.000),
        (25.260, WALL_X_OUTER_LOWER),
    )

    def __init__(self, profile: ToleranceProfile | str | None = None) -> None:
        if profile is None or isinstance(profile, str):
            prof = get_profile(profile) if isinstance(profile, str) else get_profile()
        else:
            prof = profile
        self._profile = prof
        self._latch = get_latch_geometry(prof)
        # Round 18, S7: add a running-clearance allowance to the tongue
        # riser-clearance band's inner face -- moving it FURTHER from
        # Cover's tongue tip, i.e. thinning this local wall slightly so the
        # tip has somewhere to actually reach on FDM, instead of a bare
        # zero-clearance literal-to-literal butt. ROUND 73c: reinstated
        # after an attempted retirement regressed Cover clearance by
        # 49.546 mm^3 -- see TONGUE_INNER_Y_UPPER's own note.
        self._tongue_inner_y_upper = self.TONGUE_INNER_Y_UPPER + prof.free.radial

        self._solid = self._build()

    # ------------------------------------------------------------------
    # Top-level assembly
    # ------------------------------------------------------------------

    def _build(self) -> cq.Workplane:
        body = self._build_side_wall(+1).union(self._build_side_wall(-1))
        body = body.union(self._build_latch_wall())
        body = body.union(self._build_tongue_wall())
        body = body.union(self._build_top_deck())

        arm_local, bore_local = self._build_arm_and_bore_local()
        for x_sign in (+1, -1):
            for y_sign in (+1, -1):
                arm, bore = self._place_arm(arm_local, bore_local, x_sign, y_sign)
                body = body.union(arm)
                body = body.cut(bore)

        body = body.cut(self._build_upper_step_in())
        body = body.cut(self._build_side_window(+1))
        body = body.cut(self._build_side_window(-1))
        # After the deck union, not before: above the bay the end-wall
        # socket's floor is deck material, so cutting it earlier would be
        # undone by the union.
        body = body.cut(self._build_end_wall_socket(+1))
        body = body.cut(self._build_end_wall_socket(-1))
        # ROUND 78 -- _build_plate_edge_relief is NO LONGER APPLIED.  It
        # double-counted a clearance that is already inside the measured
        # numbers, and its Y bound was what produced the corner step the
        # owner flagged.  See that method's own docstring for the full
        # reasoning; it is kept, unwired, because the reasoning is worth
        # more than the code.
        body = body.cut(self._build_latch_plate_relief())
        body = body.cut(self._build_cord_port())
        # Last: it rounds the end walls and the tongue ribs, so it has
        # to run after both exist.
        body = body.cut(self._build_bottom_end_round(-1))
        body = body.cut(self._build_bottom_end_round(+1))
        # ROUND 75 -- the tongue-end floor trim is NOT wired in.  See
        # _build_tongue_end_floor_trim's own docstring: both attempts to
        # square the wall off at 0.100 severed the shell into multiple
        # solids.  The wall currently ends at Z = 0.000.

        assert len(body.solids().vals()) == 1, "Expected single solid, got multiple pieces"

        # ROUND 74 -- the one place SHELL_Y_OFFSET is actually applied: a
        # single rigid-body translate of the fully assembled shell, re-
        # datuming it onto the ground-truth Cover/Tray frame. See
        # SHELL_Y_OFFSET's own comment for why this is a translate here
        # rather than an edit to HALF_Y (or the constants derived from it),
        # and for which OTHER constants had to be back-compensated because
        # they anchor to a cross-part ground-truth Y position directly.
        body = body.translate((0.0, self.SHELL_Y_OFFSET, 0.0))
        return body

    # ------------------------------------------------------------------
    # Side walls (X-direction, stepped)
    # ------------------------------------------------------------------

    def _build_side_wall(self, x_sign: int) -> cq.Workplane:
        """One side wall, with the trapezoid mating socket in its outer face.

        ROUND 73b restructure (item 2 decision) -- TWO pieces now, not
        three. The old "thickened band 2" scheme (rounds 50-73a) existed
        solely to give the socket, which sits at fixed Z
        ``[SOCKET_Z_LO, SOCKET_Z_HI]`` = ``[22.000, 24.000]``, a host band
        thicker than the plain lower skin. Now that ``WALL_INNER_STEP_Z``
        has moved to 26.000 (the Tray's own wall top), the socket's Z-band
        sits entirely INSIDE the lower band already -- ``WALL_THICKNESS_LOWER``
        (1.350) is thick enough on its own to host the socket as a blind
        pocket (leaving :attr:`SOCKET_BACKING` -- 0.850 mm as of round 73d,
        previously an unprintable 0.200 mm before that round decoupled the
        socket's own depth -- of floor behind it), so the separate
        thickened band is no longer needed at all. Building it anyway would
        have hit exactly the round-71 trap: ``[WALL_INNER_STEP_Z,
        REF_STEP_Z]`` = ``[26.000, 24.000]`` is INVERTED (an empty/negative
        interval), which OCCT accepts silently and which would have deleted
        the socket's own host material.

        1. ``[0, WALL_INNER_STEP_Z]`` -- full-thickness skin,
           :attr:`WALL_THICKNESS_LOWER` mm, outer face at
           :attr:`WALL_X_OUTER_LOWER`. The socket (see
           :meth:`_build_wall_socket`) is a plain OUTER-face recess cut into
           this band -- it does not care which inner-face band it lands in,
           only that the band is thick enough to host it as a pocket.
        2. ``[WALL_INNER_STEP_Z, DECK_Z]`` -- the narrowed upper section,
           unchanged from round 73a: outer face :attr:`UPPER_X_OUTER`,
           thickness :attr:`WALL_THICKNESS` (the parked group's own,
           untouched section).
        """
        overlap = 0.050

        # ROUND 73b: this reads WALL_THICKNESS_LOWER, NOT the shared
        # WALL_THICKNESS -- band 1's own owner-measured section, independent
        # of the parked socket group's own (unchanged) 0.800 mm section.
        # Runs slightly past the step so the two bands share a genuine
        # volume overlap rather than a coincident face (CLAUDE.md,
        # *Chord-vs-arc ring*).
        # ROUND 81 -- both bands now meet at UPPER_STEP_Z (24.000), NOT at
        # WALL_INNER_STEP_Z (26.000). This MUST track _build_upper_step_in's
        # own z_lo: that cut removes everything outboard of UPPER_X_OUTER
        # above the step, so if the upper band still started at 26.000 the
        # Z band [24.000, 26.000] would have its lower slab cut away with
        # nothing yet built to replace it -- a 2 mm gap severing the shell.
        full = self._x_slab(
            x_sign, self.WALL_X_OUTER_LOWER, self.WALL_THICKNESS_LOWER,
            0.0, self.UPPER_STEP_Z + overlap,
        )
        upper = self._x_slab(
            x_sign, self.UPPER_X_OUTER, self.WALL_THICKNESS,
            self.UPPER_STEP_Z - overlap, self.DECK_Z,
        )
        return (
            full.union(upper)
            .union(self._build_inner_patch(x_sign))
            .cut(self._build_wall_socket(x_sign))
        )

    def _build_inner_patch(self, x_sign: int) -> cq.Workplane:
        """The two inboard thickening patches on one long (+-X) side wall.

        ROUND 81b, from the owner's careful re-measure of the real part: the
        wall is 1.400 mm unpatched and 2.200 mm where patched, i.e.
        :attr:`PATCH_THICKNESS` of material added INBOARD, starting at two
        different heights:

        * a **trapezoid-shaped** patch from :attr:`TRAPEZOID_PATCH_Z_LO`
          (20.000), echoing the outer socket's own flared outline -- owner:
          *"The inner patching should start with the trapezoid shape as
          well"*;
        * a **universal** patch spanning the whole wall length from
          :attr:`UNIVERSAL_PATCH_Z_LO` (22.500).

        The universal patch subsumes the trapezoid one above 22.500, so the
        trapezoid's distinct contribution is the band [20.000, 22.500] --
        which is exactly the region that has to be backed before the socket
        recess (Z 22.000 up) starts eating the wall.

        These heights are INNER-wall geometry only. The outer silhouette
        still steps once at :attr:`UPPER_STEP_Z`; the owner was explicit
        that these Z values must not reshape it (*"Do not change the z shape
        on the outer wall"*). That separation is the reason this is a
        separate builder unioned into the wall rather than extra bands in
        :meth:`_build_side_wall`.

        Both patches ADD material, so a loose bound here is a lump inside
        the battery bay rather than a hole -- but it is still a bound worth
        stating (*Overcuts on the non-waste side*, vibe/INSTRUCTIONS.md):

        * ``X`` runs from :attr:`PATCH_X_INNER` out to
          :attr:`CAVITY_X_HALF_LOWER`, stopping exactly on the unpatched
          cavity face so the patch unions into the wall instead of leaving
          a coincident-face seam.
        * ``Z`` runs up to :attr:`DECK_Z`; above :attr:`UPPER_STEP_Z` the
          step-in cut trims the OUTER face only, and the patch is entirely
          inboard of it, so it survives and keeps the upper band's own
          section continuous with the lower.

        The owner has accepted that these patches reach inboard of the
        Tray's outer wall for now -- a corresponding cut in the Tray's long
        wall is a separate, already-specified task.
        """
        oc = 0.050   # union overlap, never a coincident face
        x_lo = min(x_sign * self.PATCH_X_INNER,
                   x_sign * (self.CAVITY_X_HALF_LOWER + oc))
        x_hi = max(x_sign * self.PATCH_X_INNER,
                   x_sign * (self.CAVITY_X_HALF_LOWER + oc))

        universal = rounded_box(
            width=x_hi - x_lo,
            depth=2 * self.HALF_Y,
            height=self.DECK_Z - self.UNIVERSAL_PATCH_Z_LO,
            corner_r=0.0,
            center=((x_lo + x_hi) / 2.0, 0.0, self.UNIVERSAL_PATCH_Z_LO),
        )

        # The trapezoid patch mirrors the socket's own profile: narrow edge
        # at its start height, flaring to the wide edge at SOCKET_Z_HI, then
        # constant. Drawn in YZ at the patch's inner face and extruded
        # outward, so the flare is expressed once rather than approximated.
        yc = self.SOCKET_Y_CENTER
        y_lo, y_hi = self.SOCKET_Y_HALF_LO, self.SOCKET_Y_HALF_HI
        z_lo, z_flare = self.TRAPEZOID_PATCH_Z_LO, self.SOCKET_Z_HI
        trapezoid = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0.0, 0.0, x_sign * self.PATCH_X_INNER))
            .moveTo(yc - y_lo, z_lo)
            .lineTo(yc + y_lo, z_lo)
            .lineTo(yc + y_hi, z_flare)
            .lineTo(yc - y_hi, z_flare)
            .close()
            # The YZ workplane's normal is +X whatever the sign, so the
            # extrusion must be signed or the -X patch lands outside the part.
            .extrude(x_sign * (self.PATCH_THICKNESS + oc))
        )
        return universal.union(trapezoid)
        """The local pad that rebuilds the wall inboard of one trapezoid.

        ROUND 81. :attr:`SOCKET_DEPTH` now equals
        :attr:`WALL_THICKNESS_LOWER` (both 1.000), so the socket recess cuts
        the plain side wall through completely -- without this pad the
        trapezoid is a window into the battery bay rather than a seat. The
        pad restores :attr:`SOCKET_BACKING_MIN` of section behind the
        socket floor and nothing more.

        Owner scope, verbatim: *"just patch up the trapezoids + z>=24
        portion"* -- so this is deliberately NOT a uniform thickening of the
        side wall. Below the socket the wall keeps its measured
        :attr:`CAVITY_X_HALF_LOWER` inner face untouched; only the socket's
        own footprint and the recessed band above it gain material. That
        confines the accepted Tray conflict (see :attr:`SOCKET_PAD_X_INNER`)
        to the pads instead of spreading it along the whole wall.

        Bounds, each checked rather than assumed (*Overcuts on the non-waste
        side*, vibe/INSTRUCTIONS.md -- this pad ADDS material, so a loose
        bound here shows up as a lump inside the bay, not as a hole):

        * ``X`` spans :attr:`SOCKET_PAD_X_INNER` to
          :attr:`CAVITY_X_HALF_LOWER`, i.e. it stops exactly at the plain
          wall's own inner face and unions into it. It does not reach the
          socket floor, because the material between the cavity face and
          the floor is already wall.
        * ``Y`` covers the socket's WIDE edge (:attr:`SOCKET_Y_HALF_HI`,
          the trapezoid's largest half-width) plus :attr:`_PAD_Y_MARGIN`, so
          the pad is never narrower than the hole it backs at any Z. Using
          the narrow edge here would leave the flared top of the socket
          unbacked -- the failure this margin exists to prevent.
        * ``Z`` runs from the socket's own bottom up to the top of the
          recessed band, so the pad is continuous with the upper section's
          wall rather than a floating island (the single-solid guard in
          ``_build`` is what would catch a break here).
        """
        z_lo = self.SOCKET_Z_LO
        z_hi = self.DECK_Z
        y_half = self.SOCKET_Y_HALF_HI + self._PAD_Y_MARGIN

        x_lo = min(x_sign * self.SOCKET_PAD_X_INNER,
                   x_sign * self.CAVITY_X_HALF_LOWER)
        x_hi = max(x_sign * self.SOCKET_PAD_X_INNER,
                   x_sign * self.CAVITY_X_HALF_LOWER)

        return rounded_box(
            width=x_hi - x_lo,
            depth=2 * y_half,
            height=z_hi - z_lo,
            corner_r=0.0,
            center=((x_lo + x_hi) / 2.0, self.SOCKET_Y_CENTER, z_lo),
        )

    def _build_wall_socket(self, x_sign: int) -> cq.Workplane:
        """The trapezoidal recess in one side wall's outer face.

        Geometry and provenance: :attr:`SOCKET_Z_LO`. Cut inward from the
        outer face by :attr:`SOCKET_DEPTH`, so the floor lands at
        :attr:`SOCKET_FLOOR_X` and the surviving :attr:`SOCKET_BACKING` mm
        of wall inboard of it is a normal, printable section.

        ROUND 73d -- this floor is NO LONGER the same plane as the upper
        section's own outer face (:attr:`UPPER_X_OUTER`). Rounds 50-73c
        made the socket's depth exactly `UPPER_INSET`, so the two were
        coplanar by construction; the owner asked to shrink the recess to
        ~0.5 mm (fixing an unprintable 0.200 mm backing at the old depth)
        without widening the upper shell externally, which decoupled them
        on purpose. See :attr:`SOCKET_DEPTH`'s own comment for the full
        trade and :attr:`UPPER_INSET`'s for why fusing them was rejected.

        The profile stops DEAD at ``SOCKET_Z_HI``: it is a blind recess in
        both Z directions, as in the reference. See the inline note at the
        profile for why the round-50 vertical overcut had to go.
        """
        oc = 1.0
        y_lo, y_hi = self.SOCKET_Y_HALF_LO, self.SOCKET_Y_HALF_HI
        z_lo, z_hi = self.SOCKET_Z_LO, self.SOCKET_Z_HI
        # ROUND 73 -- centred on the Tray's own tab centreline, not on
        # Y = 0. See SOCKET_Y_CENTER.
        yc = self.SOCKET_Y_CENTER

        # NO vertical overcut above z_hi. Rounds 50-54 ran the mouth up to
        # z_hi + oc, which was free air then (the part stopped at 24.000).
        # Round 55 raised DECK_Z to 29.600, so that same overcut would now
        # cut 1.000 mm of real side wall clean off above the step -- the
        # *Overcuts on the non-waste side* pitfall in vibe/INSTRUCTIONS.md,
        # where the overcut direction stayed the same and the thing it
        # pointed at changed underneath it. The socket is a blind recess in
        # both Z directions now, which is also what the reference has.
        profile = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0.0, 0.0, x_sign * self.SOCKET_FLOOR_X))
            .moveTo(yc - y_lo, z_lo)
            .lineTo(yc + y_lo, z_lo)
            .lineTo(yc + y_hi, z_hi)
            .lineTo(yc - y_hi, z_hi)
            .close()
        )
        # The YZ workplane's normal is +X whatever the sign, so the extrusion
        # must be signed or the -X socket is cut out of thin air inboard.
        #
        # ROUND 73d: depth is now SOCKET_DEPTH, its own constant, NOT
        # UPPER_INSET. The socket floor and the upper wall are consequently
        # no longer the same plane -- that coplanarity was a deliberate
        # property of the old fused constant and it is being given up on
        # purpose (see SOCKET_DEPTH's comment). Asserted here rather than
        # left implicit, so that if someone later "restores" the coupling by
        # setting the two equal, the backing-thickness consequence is
        # visible at the point of change instead of surfacing as an
        # unprintable 0.200 mm wall three rounds downstream.
        # ROUND 81 -- reads SOCKET_BACKING_MIN rather than a repeated 0.770
        # literal, and carries a representation epsilon: SOCKET_BACKING is
        # now a difference of two decimals (26.500 - 25.730) that is not
        # exact in binary, so a bare `>=` against the same nominal value
        # fires on 0.7699999999999996. The BOUND IS UNCHANGED -- this is a
        # float-comparison fix, not a relaxation, and the epsilon is 1e-9
        # (a millionth of the tolerance being guarded), far too small to let
        # a real thinning through.
        assert self.SOCKET_BACKING >= self.SOCKET_BACKING_MIN - 1e-9, (
            f"only {self.SOCKET_BACKING:.3f} mm of wall survives behind the "
            f"socket recess (floor at |X| {self.SOCKET_FLOOR_X:.3f}, backing "
            f"pad inner face {self.SOCKET_PAD_X_INNER:.3f}); below "
            f"{self.SOCKET_BACKING_MIN:.3f} this is thinner than a normal "
            "extruded section and the compartment opens into the recess"
        )
        depth = self.SOCKET_DEPTH + oc
        return profile.extrude(x_sign * depth)

    def _build_end_wall_socket(self, y_sign: int) -> cq.Workplane:
        """The trapezoidal recess in one END wall's outer face.

        Geometry and provenance: :attr:`END_SOCKET_Z_LO`. Same construction
        as :meth:`_build_wall_socket` with X and Y exchanged -- profile
        drawn at the socket FLOOR and extruded outward, so the cut is
        bounded inboard by the measured depth and unbounded only towards
        free air.

        Both overcut directions are checked, not assumed (see the
        *Overcuts on the non-waste side* pitfall in vibe/INSTRUCTIONS.md):
        outboard of ``+-HALF_Y`` is outside this part's bounding box (Y
        ends at 35.600), so the outward overcut is safe. There is NO
        vertical overcut: rounds 50-54 ran the mouth 1.000 mm above
        ``z_hi`` because the part stopped at 24.000 and that was free air.
        Round 55 raised ``DECK_Z`` to 29.600 and the same overcut would
        have taken 1.000 mm of real end wall off above the step -- the
        overcut never moved, the thing it pointed at did.
        ``test_wall_sockets_stop_at_the_reference_step_not_at_the_deck``
        asserts the wall survives above the socket. The vertical overcut deliberately extends the
        mouth STRAIGHT up rather than continuing the 45-degree flanks, so
        it cannot widen the socket past ``END_SOCKET_X_HALF_HI``.
        """
        oc = 1.0
        x_lo, x_hi = self.END_SOCKET_X_HALF_LO, self.END_SOCKET_X_HALF_HI
        z_lo, z_hi = self.END_SOCKET_Z_LO, self.SOCKET_Z_HI
        floor = y_sign * (self.HALF_Y - self.END_SOCKET_DEPTH)

        profile = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(0.0, 0.0, -floor))
            .moveTo(-x_lo, z_lo)
            .lineTo(x_lo, z_lo)
            .lineTo(x_hi, z_hi)
            .lineTo(-x_hi, z_hi)
            .close()
        )
        # The XZ workplane's normal is -Y whatever the sign, hence the
        # negated offset above and the negated extrusion here; without both
        # the +Y socket is cut out of thin air outside the part.
        return profile.extrude(-y_sign * (self.END_SOCKET_DEPTH + oc))

    def _x_slab(
        self, x_sign: int, x_outer: float, thickness: float, z_lo: float, z_hi: float
    ) -> cq.Workplane:
        """A wall slab on one X side, outer face at ``x_sign * x_outer``,
        ``thickness`` mm thick, spanning the full Y envelope and
        ``[z_lo, z_hi]``.
        """
        x_inner = x_outer - thickness
        x_lo = min(x_sign * x_outer, x_sign * x_inner)
        x_hi = max(x_sign * x_outer, x_sign * x_inner)
        return rounded_box(
            width=x_hi - x_lo,
            depth=2 * self.HALF_Y,
            height=z_hi - z_lo,
            corner_r=0.0,
            center=((x_lo + x_hi) / 2.0, 0.0, z_lo),
        )

    def _build_latch_plate_relief(self) -> cq.Workplane:
        """Owner-specified running gap between the Cover's plate edge and the
        LATCH end wall, over the plate's own Z band only.

        Round 76, owner (annotated top view): the hook-side bands *"should
        have 1mm gaps"*.  Measured before this cut, all three of them read
        **-0.050 mm** -- an interference, not a gap: the Cover's plate edge
        sits at ``PLATE_Y_LO`` = -27.800 and the latch wall's inner face at
        -27.750, so the wall stood 0.050 inside the plate.

        **Height-limited, and that is the whole point.**  Round 74 set the
        latch wall's inner face from the owner's other ground-truth
        constraint -- the Cover hook's inner face sits flush against it at
        -27.750 -- and the hook engages well above the plate (its own
        material starts around Z 8).  Pulling the face back everywhere would
        satisfy this round's gap and destroy that flush fit.  So the relief
        is bounded to ``PLATE_EDGE_RELIEF_Z_HI``: the wall reads 6.050 thick
        where the hook meets it and 5.000 across the plate band, a step
        rather than a thinner wall.

        Bounds, and why each is safe:

        * ``+Y`` (inboard) takes a small overcut past the wall's own inner
          face so the cutter's end face is not coincident with it -- the
          space inboard here is the battery bay's own void at this height,
          verified by the interference measurement above, not assumed.
        * ``-Y`` stops at the target face; going further would eat the wall
          itself.
        * ``X`` stops at the Cover plate's own half-width plus one running
          clearance -- it is NOT overcut past the shell.  Round 76's first
          version used ``2 * (ARM_X_OUTER + oc)``, i.e. far wider than the
          part, on the "overcut into waste" reflex; the space outboard of
          the plate edge is not waste, it is the outer side wall, and the
          cut punched a through-slot in it (measured: material present at
          |X| 18.55..27.85 at Z 3.000, absent at Z 1.000).  Owner: *"The gap
          should not cut through the outer wall."*  The plate edge is the
          only thing this relief exists to clear, so the plate's own extent
          is the correct bound -- see the overcut-on-the-non-waste-side
          pitfall in ``vibe/INSTRUCTIONS.md``.
        * ``-Z`` is overcut below the bottom face into free air -- waste.
        """
        clr = self._profile.free.radial
        gap = self.LATCH_PLATE_RELIEF_GAP
        oc = 1.0
        # Target face: `gap` OUTBOARD of the Cover's plate edge. Both terms
        # are back-compensated by -SHELL_Y_OFFSET because this is cut in the
        # shell's LOCAL frame but must land on the frozen Cover's own edge.
        target = (PoweredUpHubCover.PLATE_Y_LO - gap) - self.SHELL_Y_OFFSET
        face = self.LATCH_Y + self.LATCH_WALL_THICKNESS
        assert target < face, (
            f"latch plate relief would ADD material: target {target:.3f} is "
            f"not outboard of the wall face {face:.3f}"
        )
        y_lo, y_hi = target, face + 0.200
        z_hi = self.PLATE_EDGE_RELIEF_Z_HI + clr
        # ROUND 79 -- the cut runs out to the LONG WALL'S OWN INNER FACE,
        # not to the plate edge.  Owner: *"The gap along X should start at
        # the inner wall along Y."*
        #
        # Round 77 bounded this at PLATE_WIDTH/2 + clr = 26.315 (the plate
        # edge plus a running clearance), which stopped 0.185 mm short of
        # the wall's inner face at CAVITY_X_HALF_LOWER = 26.500 and left a
        # lip of latch-wall material standing proud of it in the corner.
        # The gap must meet the wall it runs into, so the wall's own inner
        # face is the correct bound.  Still NOT overcut past that face --
        # outboard of it is the side wall itself, which round 77 already
        # punched a through-slot in once.
        x_half = self.CAVITY_X_HALF_LOWER
        return rounded_box(
            width=2 * x_half,
            depth=y_hi - y_lo,
            height=z_hi + oc,
            corner_r=0.0,
            # rounded_box's center.z is the BASE, not the centroid
            # (cq_utils.rounded_box docstring) -- start it below the part so
            # the cut covers the plate's full Z band down to Z = 0.  A first
            # version passed a centroid here and began the cut at Z 0.575,
            # leaving the bottom 0.5 mm of the plate edge still interfering.
            center=(0.0, (y_lo + y_hi) / 2.0, -oc),
        )

    def _build_plate_edge_relief(self) -> cq.Workplane:
        """**RETIRED round 78 -- built but no longer cut into the body.**

        Two owner observations killed it, and they turned out to be one
        defect: *"Tight the [long] wall gap"* and *"there shouldn't be a step
        around the corner either (the long wall should just join the short
        wall directly)"*.

        1. **It double-counted the fit.**  The side wall's inner face is the
           battery cavity wall (``WALL_THICKNESS_LOWER`` is DERIVED from
           ``CAVITY_X_HALF_LOWER``), and the owner's calipers measured a real
           MATING pair: Cover plate 52.330 inside a 52.960 cavity, i.e.
           0.315 mm per side of working clearance already present in those
           two numbers.  That is the same reason
           ``PoweredUpHubCover.fit_clearance()`` returns 0.0 rather than a
           free-fit allowance.  This relief then took a FURTHER
           ``profile.free.radial`` off the same face, giving a measured
           0.485 mm gap where the real part has 0.315.
        2. **Its Y bound was the corner step.**  The cut is bounded to the
           Cover plate's own Y span (deliberately -- an earlier unbounded
           version ate the tongue ribs), so past ``PLATE_Y_HI`` the wall
           reverted to its un-relieved face.  Measured, the inner face ran
           26.650 down the length and then stepped 26.480 -> 26.140 into the
           corner.  Any Y-bounded thinning of this face produces a step
           there by construction; the only way to have no step is to not
           thin it.

        Retiring it leaves a uniform 0.335 mm gap along the whole long wall
        -- tighter than the 0.485 it replaced, no step at the corner, and
        within 0.020 mm of the 0.315 the owner actually measured on the real
        pair.

        Kept rather than deleted because the bounding analysis below is the
        record of a real bug (the round-48 rib-eating overcut) and should not
        have to be rediscovered.

        Original description follows.

        Running clearance for the Cover's plate edge against both side
        walls -- see :attr:`PLATE_EDGE_RELIEF_Z_HI` for why it lives on
        this part and why it is local.

        One cutter per side, taking ``profile.free.radial`` off the wall's
        inner face over the Z band the plate edge occupies. The same knob
        every other Cover/Housing interface routes its fit through, so the
        plate slides on the same allowance as the tongue back wall and the
        round-46 tongue ribs rather than on a number invented here.

        **Bounded in Y to the plate's own span, which is not optional.**
        The first version ran the full Y envelope with a 1.0 mm inboard
        overcut, on the assumption that everything inboard of the wall is
        interior void. It is not: :meth:`_build_tongue_ribs` stands in
        exactly that space from ``PLATE_Y_HI + clearance`` onward, and the
        overcut ate 1.0 mm of the outer rib pair, leaving a 0.05 mm sliver
        of what should be a 1.850 mm rib. The Cover's plate spans only
        ``[PLATE_Y_LO, PLATE_Y_HI]``, so that is the only Y range with an
        edge to relieve, and stopping there clears the ribs by the same
        0.150 mm they are clearanced by.

        Overcuts elsewhere are deliberate and each is bounded by something
        known: inboard in X by ``_RELIEF_X_OVERCUT`` (well short of the
        ribs' own inboard reach), downward in Z past the bottom face, and
        0.200 mm into the latch wall at -Y so the cutter's end face is not
        coincident with that wall's inner face at ``PLATE_Y_LO``.
        Coincident faces are unreliable in the OCCT boolean kernel
        (CLAUDE.md, *Chord-vs-arc ring*). The +Y end stops exactly on
        ``PLATE_Y_HI``, where the only housing face is the tongue wall's
        upper band -- which starts above this cut's own Z, so the two share
        an edge and not a face.
        """
        clr = self._profile.free.radial
        # ROUND 73: band 1's real inner face, WALL_THICKNESS_LOWER -- this
        # relief runs over the plate's own Z span, entirely inside band 1.
        wall_inner = self.WALL_X_OUTER_LOWER - self.WALL_THICKNESS_LOWER
        z_hi = self.PLATE_EDGE_RELIEF_Z_HI + clr
        # ROUND 74 -- both back-compensated by `- SHELL_Y_OFFSET`: this
        # relief is cut in the shell's LOCAL frame and must still land
        # exactly on the frozen Cover's own plate span after the
        # shell-wide translate (see SHELL_Y_OFFSET's own comment). Without
        # this, the relief would drift SHELL_Y_OFFSET past the plate edges
        # it is bounded to.
        y_lo = PoweredUpHubCover.PLATE_Y_LO - 0.200 - self.SHELL_Y_OFFSET
        y_hi = PoweredUpHubCover.PLATE_Y_HI - self.SHELL_Y_OFFSET

        relief = None
        for x_sign in (-1, +1):
            near, far = wall_inner - self._RELIEF_X_OVERCUT, wall_inner + clr
            x_lo = min(x_sign * near, x_sign * far)
            x_hi = max(x_sign * near, x_sign * far)
            cut = rounded_box(
                width=x_hi - x_lo,
                depth=y_hi - y_lo,
                height=z_hi + self._RELIEF_X_OVERCUT,
                corner_r=0.0,
                center=((x_lo + x_hi) / 2.0, (y_lo + y_hi) / 2.0,
                        -self._RELIEF_X_OVERCUT),
            )
            relief = cut if relief is None else relief.union(cut)
        return relief

    def _build_cord_port(self) -> cq.Workplane:
        """The deck opening the battery lead passes through -- see
        :attr:`CORD_PORT_WIDTH` for the sizing and why the orientation is
        forced by the pack rather than chosen.

        Positioned from its outboard edge (flush with the stepped side
        wall) and its -Y edge (the Cover's own ``LATCH_BAND_Y_HI``, which
        is what clears that part's latch structures below), extending
        inboard and +Y from there into open deck.

        Cut with a Z overcut on both ends: the deck is a slab and this
        breaks fully through it, so neither cutter face should be
        coincident with the deck's own top or underside (CLAUDE.md,
        *Chord-vs-arc ring*). The overcut runs into free space above the
        part and into the battery bay below, neither of which holds
        anything -- unlike the round-48 relief, whose inboard overcut
        reached into the tongue ribs. Verified by
        ``test_cord_port_is_a_clear_opening_into_the_battery_bay``.
        """
        oc = 1.0
        m = self.CORD_PORT_MARGIN

        # Flush with the UPPER section's inner face (round 55e), not the
        # lower band's. The port lives in the roof, whose outboard edge is
        # now UPPER_X_OUTER; keeping the old 26.400 would leave a 0.450 mm
        # ligament of roof outboard of the slot AND notch the upper wall
        # it passes. Flush, the roof still simply ends where the wall
        # begins -- which is the reasoning the original figure was chosen
        # for, re-derived against geometry that moved under it.
        # ROUND 83 -- x_hi is the wall's REAL inner face, which round 81b
        # moved. Owner: *"Adjust the hole in the lid so its two edges sit
        # flush with the inner walls."*
        #
        # This edge was always meant to be flush with the inner face (round
        # 55e's own note below says so, and fixed the margin for exactly
        # that reason). It read UPPER_X_INNER (26.200), which WAS that face
        # until round 81b's universal patch thickened the wall inboard to
        # PATCH_X_INNER (25.600) over Z >= UNIVERSAL_PATCH_Z_LO -- and this
        # port's whole Z range (CORD_PORT_Z_LO = 26.000 upward) is inside
        # that band. So the port had been cutting 0.600 mm INTO the wall,
        # leaving 0.800 mm of section where the full 1.400 should stand.
        #
        # A stale constant, not a wrong one: UPPER_X_INNER still correctly
        # describes the upper slab's own inner face; it just stopped being
        # the innermost thing there. Asserted below rather than assumed.
        x_hi = self.PATCH_X_INNER
        # x_lo keeps its ABSOLUTE position -- the owner asked for two edges
        # to move, not for the port to be re-sized around a moving one, so
        # this is anchored to where it already was rather than to x_hi.
        x_lo = self.UPPER_X_INNER - self.CORD_PORT_WIDTH          # 16.200
        assert x_hi <= self.UPPER_X_INNER, (
            f"the cord port's outboard edge ({x_hi:.3f}) is outboard of the "
            f"upper slab's own inner face ({self.UPPER_X_INNER:.3f}) -- it "
            "would cut into the side wall instead of stopping at it"
        )
        # ROUND 74 -- back-compensated by `- SHELL_Y_OFFSET`: this port is
        # cut in the shell's LOCAL frame and its -Y edge must still land
        # exactly on the frozen Cover's own LATCH_BAND_Y_HI after the
        # shell-wide translate (see SHELL_Y_OFFSET's own comment; cross-
        # checked against the built solid by
        # test_cord_port_is_a_clear_opening_into_the_battery_bay).
        # ROUND 83 -- y_hi keeps its absolute position (anchored to the old
        # Cover-registered start plus the port's length); y_lo now lands on
        # the LATCH end wall's own inner face, per the owner's "two edges
        # flush with the inner walls".
        #
        # The old y_lo sat on PoweredUpHubCover.LATCH_BAND_Y_HI (world
        # -30.000). The latch wall spans world [-33.800, -27.750], so that
        # put the port's -Y edge 2.250 mm INSIDE the wall -- the same defect
        # as the X edge above, on the other axis. Flush means stopping at
        # -27.750, i.e. local -HALF_Y + LATCH_WALL_THICKNESS.
        #
        # Local frame, like everything else built before the shell-wide
        # SHELL_Y_OFFSET translate -- so this is written directly in local
        # terms rather than as a world value back-compensated by the offset.
        y_hi = (
            PoweredUpHubCover.LATCH_BAND_Y_HI - self.SHELL_Y_OFFSET
            + self.CORD_PORT_LENGTH
        )                                                          # -11.825
        y_lo = -self.HALF_Y + self.LATCH_WALL_THICKNESS             # -29.575
        assert y_lo < y_hi, (
            f"the cord port's Y span inverted ({y_lo:.3f} >= {y_hi:.3f}) -- "
            "the latch wall now reaches past the port's inboard edge"
        )

        # Z: the cutter spans the whole ROUTE, not just the deck slab.
        #
        # Rounds 49-54 cut only DECK_THICKNESS + 1.000 mm of overcut each
        # way. With the deck at 22.400..24.000 that overcut happened to
        # reach down to 21.400 and swept the channel clear by accident --
        # in particular it removed the liftarms' own 0.050 mm union seam,
        # which pokes inboard past the side wall's 26.400 inner face over
        # Z 22.000..24.000 and sits squarely in this port's X band.
        #
        # Round 55 raised DECK_Z to 29.600, moving the cutter up with it
        # and leaving that seam behind: the deck opening was still clear
        # but the descent was pinched, which is precisely the "a hole is
        # not a route" failure the test for this feature was written to
        # catch, and it caught it.
        #
        # So the lower bound is now stated rather than inherited from an
        # overcut: WALL_INNER_STEP_Z is where the side wall steps its inner
        # face in to 26.400 and therefore where anything can first intrude
        # into this port's X band at all. Below it the wall's inner face is
        # at 27.200, outboard of x_hi, so there is nothing to remove.
        # Bounded, not infinite: the cut stays inside the port's own
        # footprint, which the test's positive controls already pin to the
        # channel beside the pack.
        # ROUND 81b -- reads CORD_PORT_Z_LO, not WALL_INNER_STEP_Z. Those
        # were the same number until this round, when the owner's re-measure
        # dropped the Tray's own long wall to world 22.300. WALL_INNER_STEP_Z
        # derives from Tray.WALL_Z_HI, so leaving this coupled would have
        # dragged the cord port down 3.700 mm as a side effect of a Tray
        # measurement that has nothing to do with where the cord exits.
        z_lo = self.CORD_PORT_Z_LO
        z_hi = self.DECK_Z + oc
        # The margin is applied on three sides, NOT four. Round 55e set the
        # outboard edge flush with the upper wall's inner face so the roof
        # ends where the wall begins -- and then the symmetric +m pushed the
        # cut 0.300 mm PAST it, into the wall, leaving 0.500 mm of roof
        # outboard of the slot instead of the wall's full 0.800 section.
        #
        # This is the *Overcuts on the non-waste side* pitfall one layer down
        # from where it usually bites: not an overcut but a fit margin, and
        # margins are just as directional. On the three inboard sides it opens
        # into the battery bay, which is waste; outboard it opens into the
        # only wall standing between the port and the outside of the part.
        # The clear opening the connector needs is unchanged -- the margin is
        # taken entirely on the inboard side instead of being split.
        x_cut_lo = x_lo - 2 * m
        x_cut_hi = x_hi
        # ROUND 83 -- the SAME directional-margin fix, now on Y too. The
        # margin used to be split symmetrically here (`+ 2 * m` on the depth,
        # centred on the span), which was harmless while y_lo sat in open
        # roof; now that y_lo is flush with the LATCH wall's inner face, half
        # a symmetric margin would push the cut 0.300 mm straight into that
        # wall and undo the flushness the owner just asked for. Margins are
        # directional exactly like overcuts (*Overcuts on the non-waste
        # side*, vibe/INSTRUCTIONS.md): taken entirely on the inboard (+Y)
        # side, which opens into the battery bay -- waste -- rather than
        # into the only wall between the port and the outside of the part.
        y_cut_lo = y_lo
        y_cut_hi = y_hi + 2 * m
        return rounded_box(
            width=x_cut_hi - x_cut_lo,
            depth=y_cut_hi - y_cut_lo,
            height=z_hi - z_lo,
            corner_r=self.CORD_PORT_CORNER_R,
            center=((x_cut_lo + x_cut_hi) / 2.0,
                    (y_cut_lo + y_cut_hi) / 2.0, z_lo),
        )

    def _build_upper_step_in(self) -> cq.Workplane:
        """Everything above :attr:`WALL_INNER_STEP_Z` that lies outside the
        upper-section footprint (round 55b; re-derived round 73b).

        Round 55 raised ``DECK_Z`` to the reference's 29.600 by extruding
        the full 72 x 71.2 lower footprint the whole way, which the user
        then spotted from the wrong side: with the side wall running
        straight past it, the trapezoid mating socket reads as a slot in a
        flat face instead of the recess it is. Rounds 55-73a stepped in at
        the reference's own 24.000 (:attr:`REF_STEP_Z`); round 73b's item-2
        decision moved the wall's own inner step (and, via this cut, the
        WHOLE silhouette's step -- side walls and end walls alike) to
        :attr:`WALL_INNER_STEP_Z` (26.000, the Tray's own wall top) instead.
        Both trapezoid sockets stay at their own fixed, PARKED Z-band
        ([22.000, 24.000]), which is now entirely below this cut's ``z_lo``
        either way -- moving ``z_lo`` cannot touch them.

        Built as a subtraction rather than by re-shaping the wall builders:
        every feature below the step -- the side walls, both end walls, the
        arms, both trapezoid sockets, the pin bores -- is already correct
        and stays untouched, and one cut above the step cannot disturb any
        of it.

        Bounds, and why each is safe (the *Overcuts on the non-waste side*
        pitfall applies with force here, since this removes material by the
        cubic centimetre):

        * ``-Z`` stops DEAD at ``WALL_INNER_STEP_Z``. This is the whole
          correctness condition, and it moved this round: cutting from the
          old 24.000 again would remove 2.000 mm of the now-full-thickness
          lower band (and the socket's own host material, round 71's exact
          trap) that must survive up to the new step. There is no overcut
          on this face.
        * ``+Z`` is free air above the part.
        * X and Y are bounded by the upper footprint on the inside and by a
          generous envelope on the outside, so the cut is exactly
          "everything outboard of the upper section".
        """
        oc = 1.0
        # ROUND 81 -- the silhouette step moved DOWN, 26.000 -> 24.000, on
        # owner instruction, so the trapezoid sockets fall inside the
        # recessed portion instead of sitting in the full-width band below
        # it. This must stay equal to _build_side_wall's own band split; see
        # the note there for what a mismatch severs.
        z_lo = self.UPPER_STEP_Z
        z_hi = self.DECK_Z + oc
        envelope = 40.0   # comfortably past the arms' own |X| = 36.000

        outer = rounded_box(
            width=2 * envelope, depth=2 * envelope, height=z_hi - z_lo,
            corner_r=0.0, center=(0.0, 0.0, z_lo),
        )
        keep = rounded_box(
            width=2 * self.UPPER_X_OUTER,
            depth=self.UPPER_Y_HI - self.UPPER_Y_LO,
            height=(z_hi - z_lo) + 2 * oc,
            corner_r=0.0,
            center=(
                0.0,
                (self.UPPER_Y_LO + self.UPPER_Y_HI) / 2.0,
                z_lo - oc,
            ),
        )
        return outer.cut(keep)

    def _build_tongue_end_floor_trim(self) -> cq.Workplane:
        """Square the tongue-end wall off at ``BOTTOM_ROUND_Z_FLOOR_TONGUE``.

        Round 75, owner: *"The end should sit flush with the cover bottom
        and lives little gap (the tongues should be mostly covered)"*.

        Flooring the bottom-round cutter (see
        :attr:`BOTTOM_ROUND_Z_FLOOR_TONGUE`) recovers the wall material the
        arc used to eat, but it recovers it all the way to ``Z = 0``, i.e.
        coplanar with the Cover's own bottom face.  This takes the last
        0.100 mm back off, so the wall ends just clear of that plane.

        **NOT CURRENTLY WIRED IN -- kept as the record of two failed
        approaches, so the third attempt does not repeat them.**

        1. Adding a slab-below-floor term *inside* the arc cutter destroyed
           the entire tongue-end wall (measured -- no material left at
           Y 35..37).  The arc cutter is built per X-band and is itself the
           result of a ``cut``; unioning a large slab into it changes what
           those per-band booleans subtract.
        2. This cut, applied once to the finished body, severs the shell
           into multiple solids (the ``len(solids) == 1`` guard in
           ``_build`` fires).  The Z 0.000..0.100 layer it removes is
           evidently load-bearing for connectivity somewhere in the
           Y >= BOTTOM_ROUND_CY band -- most likely the tongue-end bottom
           lip at Y 35.5..36.0 reaches the rest of the shell only through
           it.

        Before a third attempt, MEASURE which lump detaches and why, rather
        than narrowing the bounds by trial -- per the tunnel-vision rule in
        ``vibe/INSTRUCTIONS.md``.  The wall presently ends at Z = 0.000,
        coplanar with the Cover's bottom face.

        Bounds, and why each is safe:

        * ``-Z`` is overcut into free air below the part -- waste.
        * ``+Z`` is the floor itself: the whole point of the cut.
        * ``X`` is overcut past the shell on both sides; at this height the
          only material is the tongue end's own bottom lip.
        * The inboard ``Y`` bound is ``BOTTOM_ROUND_CY``, the arc's own
          centre plane -- the same bound the round uses.  It stops the trim
          short of the deck and the tray bay, which sit inboard of it and
          must keep their own bottom faces.  The outboard ``Y`` bound is
          overcut past the shell into free air.
        """
        floor = self.BOTTOM_ROUND_Z_FLOOR_TONGUE
        assert floor is not None, (
            "_build_tongue_end_floor_trim called with no floor set -- guard "
            "the call site, or the cut silently removes the whole bottom"
        )
        oc = 10.0
        y_in = self.BOTTOM_ROUND_CY          # arc centre plane, local frame
        y_out = self.HALF_Y + oc
        return rounded_box(
            width=2 * (self.ARM_X_OUTER + oc),
            depth=y_out - y_in,
            height=floor + oc,
            corner_r=0.0,
            center=(0.0, (y_in + y_out) / 2.0, floor - (floor + oc) / 2.0),
        )

    def _build_bottom_end_round(self, y_sign: int) -> cq.Workplane:
        """The bottom edge round where the shell meets one end plane
        (round 55f). Geometry and provenance: :attr:`BOTTOM_ROUND_R`.

        Cuts the corner material that lies OUTSIDE an arc of
        ``BOTTOM_ROUND_R`` whose axis runs along X -- so the result is the
        arc itself, not a chamfer approximating it.

        Bounds, and why each is safe:

        * **X** takes NO overcut on either side. The bands are the point of
          the feature: at the latch end the middle stays square, and at the
          tongue end only the ribs are rounded, so bleeding 1 mm sideways
          would round segments the reference leaves sharp. Every other
          direction is overcut; this one is bounded exactly.
        * ``-Z`` and the outboard ``Y`` open into free air below and beyond
          the part -- waste, overcut freely.
        * The inboard ``Y`` bound is the arc's own centre plane
          (``BOTTOM_ROUND_CY``), and the ``+Z`` bound is the centre height:
          past those the cutter would leave the arc's quadrant and start
          eating wall that should stay.
        """
        R = self.BOTTOM_ROUND_R
        cy = y_sign * self.BOTTOM_ROUND_CY
        bands = (
            self.BOTTOM_ROUND_X_LATCH if y_sign < 0
            else self.BOTTOM_ROUND_X_TONGUE
        )
        # ROUND 83 -- the latch-end arc must run INTO the hook socket, not
        # stop short of it. _LATCH_ROUND_X_INNER cannot reference
        # LATCH_WINDOW_X_HI at class-body time (defined further down), so
        # the identity is enforced here instead of assumed. Falsifier: move
        # either constant without the other and this fires.
        assert self._LATCH_ROUND_X_INNER == self.LATCH_WINDOW_X_HI, (
            f"the latch-end bottom arc stops at |X| "
            f"{self._LATCH_ROUND_X_INNER:.3f} while the hook socket starts at "
            f"{self.LATCH_WINDOW_X_HI:.3f} -- that strands "
            f"{abs(self._LATCH_ROUND_X_INNER - self.LATCH_WINDOW_X_HI):.3f} mm "
            "of square bottom edge between them, the exact residual round 83 "
            "removed"
        )
        oc = 1.0
        y_out = y_sign * (self.HALF_Y + oc)

        cutter = None
        for x_lo, x_hi, cz in bands:
            corner = rounded_box(
                width=x_hi - x_lo,
                depth=abs(y_out - cy),
                height=cz + oc,
                corner_r=0.0,
                center=((x_lo + x_hi) / 2.0, (cy + y_out) / 2.0, -oc),
            )
            # The arc, as a cylinder along X. Its YZ workplane has xDir = +Y
            # and yDir = +Z, so .center() takes (Y, Z) directly.
            arc = (
                cq.Workplane("YZ")
                .transformed(offset=cq.Vector(0.0, 0.0, x_lo - oc))
                .center(cy, cz)
                .circle(R)
                .extrude((x_hi - x_lo) + 2 * oc)
            )
            band = corner.cut(arc)
            # ROUND 75 -- the tongue end's round is FLOORED, so the wall
            # reaches down to the Cover's bottom instead of being eaten away
            # by the arc.  The owner: "The end should sit flush with the
            # cover bottom and lives little gap (the tongues should be mostly
            # covered)".
            #
            # The shell itself already extends to Z = 0; it was this cutter
            # that removed everything below the arc, and at the wall's own
            # inner face (Y 35.203, where the arc reads Z 0.264) that is
            # exactly how much material was lost.  So the fix is to bound the
            # CUTTER, not to reshape the arc: the radius stays 3.600 and the
            # latch end -- which the owner has approved visually -- is
            # untouched, because this floor applies to the tongue end only.
            floor = self.BOTTOM_ROUND_Z_FLOOR_TONGUE
            if y_sign > 0 and floor is not None:
                # Removing the cutter below `floor` is what stops the arc
                # eating the wall, recovering the material down to the
                # Cover's bottom.
                #
                # ROUND 75, measured consequence -- the wall then stands to
                # Z = 0.000, coplanar with the Cover's bottom face, NOT to
                # `floor`.  Flooring the cutter preserves the shell's own
                # material below the floor; it does not trim to it.  Adding a
                # slab-below-floor to the cutter to square it off at 0.100 was
                # tried and REVERTED: unioning that slab into the arc cutter
                # destroyed the whole tongue-end wall (verified -- no material
                # left at Y 35..37).  A square trim, if wanted, belongs as a
                # single bounded cut on the finished body, not inside this
                # per-band arc cutter.
                below = rounded_box(
                    width=(x_hi - x_lo) + 2 * oc,
                    depth=abs(y_out - cy) + 2 * oc,
                    height=100.0,
                    corner_r=0.0,
                    center=(
                        (x_lo + x_hi) / 2.0,
                        (cy + y_out) / 2.0,
                        floor - 50.0,
                    ),
                )
                band = band.cut(below)
            cutter = band if cutter is None else cutter.union(band)
        assert cutter is not None, (
            f"no bottom-round bands for y_sign={y_sign} -- an empty band list "
            "returns None and fails later as 'Cannot cut type NoneType', which "
            "says nothing about the cause"
        )
        return cutter

    def _build_side_window(self, x_sign: int) -> cq.Workplane:
        """Tab-access cutout through one side wall (SS7.2).

        Round 41 -- **the window is the tab's own outline, offset outward
        by the running clearance.** Same construction as the tab: vertical
        sides, then the ``TAB_ROUND_R`` corner round-over about the same
        centre, then the flat top. Offsetting that outline uniformly by
        ``c`` is exact and needs no re-derivation, because the round-over's
        centre sits at ``(TAB_ROUND_CZ, TAB_LEDGE_Y_HALF)`` and its two
        tangent points are the side and the top -- so the sides move to
        ``PAD_Y_HALF + c``, the top to ``PAD_Z_HI + c``, and the arc keeps
        its centre with radius ``ROUND_R + c``.

        It used to be a three-point piecewise-linear taper sampled off the
        reference (see :attr:`WINDOW_TAPER_PROFILE`'s retired note). Chords
        lie inside the arc they subtend, so that cut was narrower than the
        tab at every intermediate Z, and the tab-bearing part shrank its
        whole tab by 0.320 mm to get through -- deleting reference material
        from the part to accommodate a mis-modelled hole. Cutting the true
        arc is what the chord-vs-arc pitfall in ``vibe/INSTRUCTIONS.md``
        prescribes, and it lets the tab go back to nominal.

        The clearance now lives HERE rather than on the tab, which is the
        right side of a hole/shaft pair for it and restores the tab-bearing
        part to its reference dimensions.

        Round 51 -- **the tab moved from Cover to** :class:`PoweredUpHubBatteryTray`
        (real reference: only tray ``24849`` has this tab, not lid
        ``24853``). This window still cuts the same physical outline; only
        its source class changed. ``TAB_ROUND_CZ`` and ``TAB_PAD_Z_HI`` are
        expressed in the Tray's own LOCAL frame (its bottom face, not
        world Z=0), so both are converted to world Z here via the fixed
        ``+PLATE_THICKNESS`` seating offset ``assemble()`` applies -- the
        Y-valued constants (``TAB_LEDGE_Y_HALF``, ``TAB_PAD_Y_HALF``,
        ``TAB_ROUND_R``) need no such conversion.
        """
        overcut = 1.0  # break cleanly through the wall's X extent
        x_outer = self.WALL_X_OUTER_LOWER + overcut
        # ROUND 73: this window's Z range (up to ~8.4 mm) sits entirely in
        # band 1, so it must cut band 1's own WALL_THICKNESS_LOWER section,
        # not the parked group's WALL_THICKNESS.
        x_inner = self.WALL_X_OUTER_LOWER - self.WALL_THICKNESS_LOWER - overcut
        x_lo = x_sign * min(x_outer, x_inner)
        x_hi = x_sign * max(x_outer, x_inner)
        width = abs(x_hi - x_lo)

        seat = PoweredUpHubCover.PLATE_THICKNESS
        c = self._profile.free.radial
        cz = PoweredUpHubBatteryTray.TAB_ROUND_CZ + seat       # round-over centre Z, world
        ly = PoweredUpHubBatteryTray.TAB_LEDGE_Y_HALF          # round-over centre |Y|
        r = PoweredUpHubBatteryTray.TAB_ROUND_R + c            # offset arc radius
        half = PoweredUpHubBatteryTray.TAB_PAD_Y_HALF + c      # side face
        zhi = PoweredUpHubBatteryTray.TAB_PAD_Z_HI + seat + c  # flat top, world

        # The reference measured this window independently of the tab; if
        # the two ever stop describing one feature, say so here rather than
        # cutting a hole that silently no longer matches what goes through it.
        assert (
            abs(half - c - self.WINDOW_Y_HALF) < 1e-9
            and abs(cz - self.WINDOW_SHOULDER_Z) < 1e-9
        ), (
            "the tray's extraction tab and this class's own reference-measured "
            "window figures have drifted apart"
        )

        # 45-degree point on each round-over, for the three-point arc.
        # Round 71: the tab is no longer centred on Y = 0 -- it tracks the
        # Cover's window sill at TAB_Y_CENTER -- so the window it passes
        # through must move with it. Round 74: read via self.WINDOW_Y_CENTER
        # (already back-compensated by SHELL_Y_OFFSET), not the bare Tray
        # constant directly -- this cut runs in the shell's LOCAL frame and
        # must still land on the Tray's tab centreline after the shell-wide
        # translate.
        yc = self.WINDOW_Y_CENTER
        d = r * math.sqrt(0.5)
        sketch = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0.0, 0.0, min(x_lo, x_hi)))
            .moveTo(yc - half, 0.0)
            .lineTo(yc - half, cz)
            .threePointArc((yc - ly - d, cz + d), (yc - ly, zhi))
            .lineTo(yc + ly, zhi)
            .threePointArc((yc + ly + d, cz + d), (yc + half, cz))
            .lineTo(yc + half, 0.0)
        )
        return sketch.close().extrude(width)

    # ------------------------------------------------------------------
    # Top deck
    # ------------------------------------------------------------------

    def _build_top_deck(self) -> cq.Workplane:
        """Solid cap closing the top -- see class docstring's *Known
        simplifications* for why this is solid rather than a hollow shell.

        **Round 20 correction (finding H1, blocking)**: this slab spans
        ``Z`` in ``[DECK_Z - DECK_THICKNESS, DECK_Z]`` -- the real
        shell's own measured deck, sitting at and below its top face. The
        pre-round-20 version built this slab *above* ``DECK_Z`` (the
        retired ``TOP_Z = 33.800``), which put ~16,270 mm^3 (61% of the
        model's own volume) entirely outside the reference envelope -- see
        the class docstring's *Round 20 correction* note.

        **Round 22**: the slab is FLAT and SOLID by explicit user
        direction -- the top-layer connecting holes (the stud/pin pattern
        that would mate this bottom layer to the second layer) are
        deliberately NOT modelled yet, so nothing perforates it. Its plan
        footprint also widened back to the full Y envelope; see
        :attr:`DECK_Y_LO`. The round-21 note below is kept for the record
        but no longer describes the built geometry.

        **Round 21 correction (finding RH1)**: the deck's own plan
        footprint is narrower than the full housing envelope --
        ``x`` in ``[-WALL_X_OUTER_UPPER, WALL_X_OUTER_UPPER]`` as built,
        which :meth:`_build_upper_step_in` then trims to
        ``+-UPPER_X_OUTER``,
        but ``y`` in ``[DECK_Y_LO, DECK_Y_HI]`` (asymmetric, narrower than
        ``+-HALF_Y``), matching the real shell's own narrowing above the
        end walls' height (see :attr:`END_WALL_Z_HI`). The deck no longer
        spans over the arm band's own Y-reach at all past
        ``y = +-DECK_Y_HI/DECK_Y_LO`` -- confirmed matching the reference,
        whose own deck footprint already excludes the arm region on the
        same figures. Still unions cleanly onto the X-direction side walls
        (:meth:`_build_side_wall`), which are unaffected by this change and
        already span the full ``+-HALF_Y`` depth at this Z range.
        """
        y_span = self.DECK_Y_HI - self.DECK_Y_LO
        return rounded_box(
            width=2 * self.WALL_X_OUTER_UPPER,
            depth=y_span,
            height=self.DECK_THICKNESS,
            corner_r=0.0,
            center=(0.0, (self.DECK_Y_LO + self.DECK_Y_HI) / 2.0, self.DECK_Z - self.DECK_THICKNESS),
        )

    # ------------------------------------------------------------------
    # Arms (composed from PerpendicularHolesLiftarm, per the TL round)
    # ------------------------------------------------------------------

    def _build_arm_and_bore_local(self) -> tuple[cq.Workplane, cq.Workplane]:
        """Build the (+X, +Y)-quadrant arm and its middle-hole bore cutter,
        both still in the class's own **local** frame (X = length,
        Y = width, Z = thickness) -- i.e. *before* the diagonal-mirror
        remap into housing coordinates (see :meth:`_place_arm`).

        Round 43 -- **the arm is a beam and hole cutters, built at the
        reference's own dimensions**, and it is no longer composed from
        :class:`~vibe_cading.lego.technic_beam_perp.PerpendicularHolesLiftarm`.

        That class is calibrated to this project's generic liftarm
        cross-section (``BEAM_WIDTH`` 7.800, cap radius 3.900 seated 0.100
        off the hole line) and its length is fixed at
        ``num_holes * STUD_PITCH`` = 24.000. Philo's arm is none of those:
        18 LDU wide (7.200), cap radius 9 LDU (3.600) centred exactly ON
        the outer hole, total length 23.200. Rounds 16-42 bridged the gap
        by building the generic beam and then squaring it off with three
        flat trims -- which is what chopped the round cap into a 3.440 mm
        flat chord at the tip, flattened the outboard face, and left the
        re-entrant notch where the arm met the end wall.

        Built to the reference's own numbers the cap radius equals the
        half-width and sits on the hole centre, so it comes out exactly
        tangent to ``|X| = 35.600`` and ``Y = 35.600`` on its own. **No
        trims at all** -- the envelope is a consequence of the geometry
        rather than something cut into it afterwards.

        Not a regression in reuse: the holes are still
        :class:`~vibe_cading.lego.cutters.technic_pin_hole.TechnicPinHole`
        cutters, which is where the shared, profile-aware, calibrated
        content actually lives. What is dropped is a *body* whose three
        governing dimensions all had to be overridden.
        """
        half_w = self.ARM_CAP_R
        hole_xs = [half_w + i * STUD_PITCH for i in range(3)]   # 3.6, 11.6, 19.6

        # Stadium: caps centred ON the outer holes, radius = half-width.
        arm = (
            cq.Workplane("XY")
            .sketch()
            .push([(self.ARM_LENGTH / 2.0, 0.0)])
            .rect(self.ARM_LENGTH - 2 * half_w, self.ARM_WIDTH)
            .reset()
            .push([(hole_xs[0], 0.0), (hole_xs[-1], 0.0)])
            .circle(half_w)
            .clean()
            .finalize()
            .extrude(self.ARM_THICKNESS)
        )
        assert abs(arm.val().BoundingBox().xlen - self.ARM_LENGTH) < 1e-9, (
            "the stadium's own length must equal ARM_LENGTH -- if the caps "
            "and the rect disagree the envelope stops being tangent"
        )

        # Round 44 -- square off the INBOARD half, so the arm meets the body
        # on a flat face instead of a tangent cusp.
        #
        # A full stadium touches the end plane at a single point and curves
        # away from it immediately, so where the cap approached the housing it
        # left a sharp re-entrant notch: the body edge ran in at Y = 35.600 to
        # X = 28.400, dropped to Y = 32.000, and only there did the arc begin.
        # That is a stress raiser at the arm's root -- the one place on a
        # cantilever where a notch matters most -- and it prints as a crevice.
        #
        # Filling only local y <= 0 keeps the OUTBOARD corner's R3.600 round
        # (round 43, the reference's own cap) while making the inboard flank
        # straight for the arm's whole length and the two end faces flat. The
        # envelope is untouched: this adds material strictly inside
        # |X| <= HOLE_X and Y in [ARM_Y_LO, HALF_Y], which the cap already
        # bounded.
        arm = arm.union(
            rounded_box(
                width=self.ARM_LENGTH,
                depth=half_w,
                height=self.ARM_THICKNESS,
                corner_r=0.0,
                center=(self.ARM_LENGTH / 2.0, -half_w / 2.0, 0.0),
            )
        )

        # The two vertical holes: through, counterbored at both faces --
        # LDraw `connhole`, which is what Philo uses at these positions.
        through = TechnicPinHole.standard(
            depth=self.ARM_THICKNESS + 2 * TechnicPinHole._ENTRY_OVERCUT,
            profile=self._profile,
        ).to_cutter()
        for x in (hole_xs[0], hole_xs[-1]):
            arm = arm.cut(through.translate((x, 0.0, -TechnicPinHole._ENTRY_OVERCUT)))

        # Round 42 -- NO face dishing. Rounds 20-41 cut the real liftarm's
        # recessed pockets into both faces (floors at local Z 5.378 /
        # 2.622, leaving a 2.756 mm web), blended into each hole by an
        # R3.600 relief and opened between holes by two gap circles. It
        # reproduced the reference's shape faithfully and it is the wrong
        # shape to print: it removes material from the middle of a
        # cantilevered arm's section, exactly where bending stress is
        # highest, and it lays down thin bridged webs on an FDM machine.
        # Per the user's round-42 direction this part keeps the plain beam
        # -- solid full-thickness section, standard pin holes -- as a
        # deliberate, stronger departure from the reference.

        # Root bridge: the class's own BEAM_WIDTH/2 edge (local Y = -3.9,
        # -> global X = 28.1) sits just *outside* the side wall's own
        # outer face (X = 28.0) -- a 0.1 mm gap, since the arm's
        # Cailliau-calibrated cross-section is deliberately not trimmed
        # to LDraw's literal 35.6/36.0 mm figures (see class docstring).
        # Without a bridge the arm floats detached from the wall after
        # the housing-frame remap.
        #
        # Z-dependent two-band bridge (design brief round 17, Escalation
        # 8): the housing's side wall itself is stepped in Z (WALL_STEP_Z
        # = 22.0, global) -- a single reach sized for the *narrower* upper
        # band would also apply at the lower band's Z range, where it
        # over-reaches *past* the lower band's own (deeper) inner face and
        # into what is, below the step, PoweredUpHubBatteryTray's
        # unaffected wall territory rather than housing wall material at
        # all (259.014 mm^3 cross-part interference, independently
        # re-derived and confirmed in the design brief). Reshaping this
        # bridge is Housing's call, not the tray's: the bridge has no
        # LDraw counterpart -- it is this project's own composition
        # geometry, added solely to fuse PerpendicularHolesLiftarm's
        # diagonally-remapped output to the wall, so it is ours to shape
        # (contrast the tray's own wall step, which mirrors Housing's
        # real, load-bearing 25560 geometry and is not touched here).
        #
        # Band A -- local Z in [6.0, 8.0] (-> global Z in [22.0, 24.0],
        # the upper wall band): UNCHANGED from the original single-band
        # reach. This is the band that actually fuses the arm to the
        # wall -- see the numeric margin below.
        # Band B -- local Z in [0.0, 6.0] (-> global Z in [16.0, 22.0],
        # the lower wall band, where the tray's wall sits): round 17
        # (Escalation 8) dropped this band's reach to nothing, which
        # eliminated the tray collision but also left an open 0.100 mm
        # slit between the arm and the wall here (round 20, finding H4 --
        # a hole in a printed part, not merely a fidelity issue). **Fixed
        # by reusing the shared SEAM_MARGIN convention round 19 introduced
        # in PoweredUpHubBatteryTray** (same class of problem: two
        # independently-authored classes' own small boolean-safety
        # overcuts needing a shared budget at their common seam) rather
        # than inventing a new constant: Band B now reaches to
        # X = WALL_X_OUTER_LOWER - WALL_THICKNESS + SEAM_MARGIN (27.300 mm,
        # i.e. 0.100 mm INTO the wall's own lower-band material
        # [27.2, 28.0]) -- a genuine fuse-overlap margin, not the
        # pre-round-17 full reach (which caused the original 259.014 mm^3
        # tray collision, Escalation 8) and not round-17's zero reach
        # (which caused this slit). This does not disconnect the arm:
        # Band A and Band B share one continuous solid via ordinary Z-
        # continuity of the arm body itself, not via bridge material
        # duplicated at every Z -- the original single-band bridge never
        # required that either.
        SEAM_MARGIN = 0.100
        beam_half_width_pre = arm.val().BoundingBox().ymax  # BEAM_WIDTH / 2
        # Local X span matches the trim bounds exactly (0.400..23.600) so
        # the bridge cannot reintroduce the material the envelope trim
        # just removed at either end.
        #
        # ROUND 73b -- RE-DERIVED, not left at its old hardcoded literal.
        # This used to be a bare `-5.650` ("0.05 mm past the upper-band
        # wall's own inner face, WALL_X_OUTER_UPPER - WALL_THICKNESS =
        # 26.400 mm"), a figure from BEFORE round 73a moved
        # WALL_X_OUTER_LOWER (and with it, UPPER_X_OUTER/UPPER_X_INNER) --
        # it was never updated then, so it had already gone stale once
        # (round 73a's real inner face there was 25.900, not 26.400) before
        # round 73b's item-2 restructure changed the picture again: Band A's
        # own global Z-range ([22.0, 24.0]) now sits entirely inside the
        # FULL-thickness band (the item-2 step moved to 26.000), not the
        # narrow upper band at all, so the wall face it should overlap is
        # now the full band's own inner face
        # (WALL_X_OUTER_LOWER - WALL_THICKNESS_LOWER = 26.500), not either
        # of the stale figures above. Reaching only 0.05 mm past THAT face
        # -- the same "minimum for a reliable union" margin the literal
        # always intended -- keeps the same design, corrected to read the
        # wall the arm's Z-range now actually mates with.
        #
        # Verified clear of PoweredUpHubBatteryTray's own wall
        # (WALL_OUTER_X = 26.250, frozen) by 0.200 mm -- see the round-73b
        # implementation report for the built-solid measurement. An earlier
        # version reached to local Y = -6.0 (global X = 26.0), which
        # collided with the Tray's own side wall -- caught by the
        # cross-part verification probe; this derivation is bounded well
        # short of that.
        #
        # The bridge lives on the NEGATIVE-Y side only (Y < -beam_half_width_pre,
        # i.e. beyond the arm's own -Y edge, toward the wall) -- NOT
        # symmetric with the +Y side, which must stay untouched (that is
        # where the hole bores live). An earlier version used
        # `+beam_half_width_pre` for both the depth and centre calc below,
        # which silently spanned the *whole* arm width and refilled the
        # main-hole bores with the root's own material -- caught by the
        # cross-part / hole-presence test suite.
        wall_inner_face_at_band_a = self.WALL_X_OUTER_LOWER - self.WALL_THICKNESS_LOWER
        # ROUND 82 -- Band A now stops INSIDE the wall instead of 0.05 mm
        # PAST its inner face.
        #
        # Owner: *"in the long side inner wall just below the patch line, I
        # saw a small gap (or bump) ... I suspect it's the arms getting
        # through the wall after the width adjustment. Can you adjust the
        # arm so they join the outer wall instead?"* -- correct diagnosis.
        # Band A spans global Z [22.000, 24.000], i.e. exactly "just below
        # the patch line" (UNIVERSAL_PATCH_Z_LO = 22.500), and the old
        # `- 0.05` put its face at 26.350 against a 26.400 cavity: a 0.050 mm
        # ledge standing proud INTO the battery bay, along the whole
        # 23.350 mm arm length, on both long walls.
        #
        # The `- 0.05` was never about reaching the cavity -- it was there so
        # the bridge would have a genuine VOLUMETRIC overlap with the wall
        # rather than terminating on a coincident face (unreliable in the
        # OCCT boolean kernel, *Chord-vs-arc ring* in vibe/INSTRUCTIONS.md).
        # Overshooting inboard is only one way to get that overlap, and it
        # is the one that shows. Stopping SHORT of the inner face buys the
        # same overlap -- the bridge is then entirely buried in wall
        # material, sharing no face with anything -- and leaves the cavity
        # face clean. The fuse gets shallower by 0.075 mm out of ~1.875 mm
        # of reach; its 2.000 mm Z-height, which is what the structural-fuse
        # margin is actually derived from, is untouched.
        #
        # Half of SEAM_MARGIN, not the whole of it, because Band B already
        # sits at a full SEAM_MARGIN inside the same face and the assert
        # after Band B requires Band A to stay strictly deeper.
        root_inner_local_y = (
            wall_inner_face_at_band_a + SEAM_MARGIN / 2.0
        ) - self.HOLE_X
        root_outer_local_y = -beam_half_width_pre
        # Post-fix hardening (round 17, re-derived round 73b): this Z
        # window is the entirety of the structural fuse -- 2.0 mm
        # (ROOT_BAND_A_Z_HI - ROOT_BAND_A_Z_LO) x (reach depth,
        # root_outer_local_y - root_inner_local_y, now ~1.875 mm rather
        # than the pre-round-73b 1.85 mm) x 23.35 mm (arm length) -- see
        # the round-73b report for the exact re-measured margin. If
        # ROOT_BAND_A_Z_LO is ever raised (shrinking Band A) without
        # re-deriving that margin, the guard below fails loudly instead of
        # silently reopening the floating-arm defect.
        # Band B (below) deliberately DOES now reach the wall again (round
        # 20, H4) -- but only by SEAM_MARGIN, not Band A's full depth; the
        # assert after Band B's own construction guards that relationship.
        root = rounded_box(
            width=self.ARM_LENGTH,
            depth=root_outer_local_y - root_inner_local_y,
            height=self.ROOT_BAND_A_Z_HI - self.ROOT_BAND_A_Z_LO,
            corner_r=0.0,
            center=(
                self.ARM_LENGTH / 2.0,
                (root_inner_local_y + root_outer_local_y) / 2.0,
                self.ROOT_BAND_A_Z_LO,
            ),
        )
        assert self.ROOT_BAND_A_Z_LO == self.ARM_THICKNESS - 2.0, (
            "Root bridge Band A must retain its full 2.0 mm Z-height (the "
            "~85.8 mm^3 structural-fuse margin derived in the design "
            "brief's Escalation 8) -- shrinking it reopens the floating-"
            "arm defect the bridge exists to prevent."
        )
        # ROUND 73b -- WALL_STEP_Z is now a LEGACY Z-split marker only (see
        # its own note); this assert still checks a real invariant (Band A's
        # Z-lower-bound must not slide down into Band B's own Z-range), it
        # is just no longer protecting against "the tray's lower-band wall"
        # in the sense the original comment meant -- under item 2's
        # restructure, the Tray's wall now occupies BOTH bands' Z-range
        # (it stands to world Z 26.000, past Band A's own 24.000 cap), so
        # what actually protects the Tray is each band's own re-derived
        # X-reach (see `root_inner_local_y`/`root_b_inner_local_y`), not
        # this Z-split. This assert only guards that the two bands don't
        # swap positions in Z.
        assert self.ROOT_BAND_A_Z_LO >= self.WALL_STEP_Z - self.ARM_Z_LO, (
            "Root bridge Band A must not extend below the historical Z-split "
            "(global Z = WALL_STEP_Z) -- doing so regrows Band A's own "
            "(deeper) X-reach into Band B's Z-range, undoing the two-band "
            "split entirely (design brief Escalation 8)."
        )
        arm = arm.union(root)

        # Band B bridge (round 20, H4) -- see the comment above the SEAM_MARGIN
        # assignment for the derivation. Reach is intentionally SHALLOWER
        # than Band A's (into the wall's own material by SEAM_MARGIN only,
        # not past its inner face) -- this band exists solely to close the
        # slit, not to duplicate Band A's structural-fuse role.
        #
        # ROUND 73b -- reads WALL_THICKNESS_LOWER, NOT the shared
        # WALL_THICKNESS. This was a round-73a staleness bug: band 1's real
        # thickness became WALL_THICKNESS_LOWER (1.350) that round, but this
        # formula kept reading the parked group's own WALL_THICKNESS (0.800)
        # -- under-reaching the real wall by 0.550 mm (found by measurement,
        # not inspection; see the round-73b implementation report).
        root_b_inner_local_y = (
            self.WALL_X_OUTER_LOWER - self.WALL_THICKNESS_LOWER + SEAM_MARGIN
            - self.HOLE_X
        )
        root_b = rounded_box(
            width=self.ARM_LENGTH,
            depth=root_outer_local_y - root_b_inner_local_y,
            height=self.ROOT_BAND_A_Z_LO,  # local Z [0, ROOT_BAND_A_Z_LO], i.e. Band B
            corner_r=0.0,
            center=(self.ARM_LENGTH / 2.0,
                    (root_b_inner_local_y + root_outer_local_y) / 2.0, 0.0),
        )
        assert root_b_inner_local_y > root_inner_local_y, (
            "Band B's reach must stay shallower than Band A's own deeper "
            "reach (root_inner_local_y) -- growing Band B past that point "
            "re-approaches the pre-round-17 full-reach tray collision "
            "(Escalation 8) this two-band split exists to avoid."
        )
        arm = arm.union(root_b)

        # Boss + middle hole, both anchored to the arm's own outboard edge.
        # Round 43: that edge is now the reference's own 3.600 half-width by
        # construction, so nothing needs trimming first and nothing needs to
        # read it back off a bounding box.
        #
        # The boss is built along local Z then rotated -90 deg about X, the
        # "build along Z, rotate onto the width axis" technique the shared
        # liftarm class uses for its own perpendicular holes: local Z (the
        # stacking axis) maps to local Y (width), and a constant local
        # y = -ARM_THICKNESS/2 maps to local Z = +ARM_THICKNESS/2, the
        # hole-axis mid-height. (rotate(-90, X) maps (y, z) -> (z, -y).)
        mid_z = self.ARM_THICKNESS / 2.0
        hole_x_local = hole_xs[1]

        boss_overlap = 0.5  # clean union overlap into the arm's own edge
        boss = cylinder(
            self.BOSS_DIAMETER / 2.0,
            self.BOSS_PROUD + boss_overlap,
            center=(hole_x_local, -mid_z, half_w - boss_overlap),
        ).rotate((0, 0, 0), (1, 0, 0), -90)
        arm = arm.union(boss)

        # The horizontal hole: BLIND, counterbored at the entry rim only --
        # LDraw `connhol3`, which is the primitive Philo actually uses here
        # (the vertical positions get `connhole`, the through-hole variant).
        # See MID_BORE_DEPTH for the derivation off 24851s01 and its
        # round-73b functional supersession.
        boss_tip = half_w + self.BOSS_PROUD                  # local y = +3.850
        floor_local_y = boss_tip - self.MID_BORE_DEPTH       # local y = -4.150

        floor_x = self.HOLE_X + floor_local_y
        assert abs(floor_x - self.MID_BORE_FLOOR_X) < 1e-9, (
            f"the bore floors at |X| = {floor_x:.3f}, not the reference's "
            f"{self.MID_BORE_FLOOR_X:.3f} -- MID_BORE_DEPTH and the boss "
            f"geometry have drifted apart"
        )

        # ROUND 73b -- stack-up along the bore's own axis, boss tip inward,
        # reported explicitly per the owner's request ("Report the stack-up
        # as an explicit list of components with numbers"):
        #
        #   1. boss (BOSS_PROUD)                          0.175 mm
        #   2. arm's own bulk width (ARM_WIDTH)            7.350 mm
        #   3. "the gap" -- past the arm's own nominal      0.475 mm
        #      flat face (half_w from the hole centre),
        #      into the root-bridge transition zone
        #   ------------------------------------------------------
        #   total (== MID_BORE_DEPTH)                      8.000 mm
        #
        # ROUND 73b -- the floor guard is RE-POINTED, not merely re-valued.
        # `arm_inboard_x` (the arm's own bare flat face) is no longer the
        # right thing to measure against: at MID_BORE_DEPTH = 8.000 the
        # floor is 0.475 mm PAST it BY DESIGN (component 3 above, the "gap"
        # the owner explicitly described), so a check against the arm's own
        # face would fail on correct, owner-confirmed geometry. What
        # actually matters structurally is whether real material still
        # backs the floor -- which, past the arm's own face, is the ROOT
        # BRIDGE's own reach (`root_b_inner_local_y`, Band B, since this
        # hole's Z position -- ARM_THICKNESS / 2 -- falls inside Band B's
        # local Z range [0, ROOT_BAND_A_Z_LO]). `root_b_inner_local_y` is
        # already in scope here (computed above, before the boss/bore
        # block) and reaches FURTHER inboard than the bore's own floor by
        # construction (see its own assert against `root_inner_local_y`),
        # so this checks the bore does not floor out past the bridge's own
        # limit -- STOP-and-report territory, not a value to shave, if it
        # ever fires.
        remaining_backing = floor_local_y - root_b_inner_local_y
        assert remaining_backing >= self.MID_BORE_MIN_FLOOR - 1e-9, (
            f"the bore floor ({floor_local_y:.3f} local) leaves only "
            f"{remaining_backing:.3f} mm before the root bridge's own reach "
            f"limit ({root_b_inner_local_y:.3f} local) -- the bore has eaten "
            f"into the structural bridge itself; this needs a design "
            f"decision, not a floor shave"
        )
        # That the bore does NOT reach the cavity is verified on the BUILT
        # solid by test_middle_bore_is_blind -- these asserts pin the inputs,
        # the test pins the outcome.

        # Rotation: +90 deg about X maps (x, y, z) -> (x, -z, y), so the
        # cutter's native +Z bore points along -Y (inboard, away from the
        # boss tip) and its mouth plane lands on y = 0. The translate then
        # puts that mouth on the boss tip at mid-thickness. Note the sign is
        # the OPPOSITE of the boss's own -90 above: the boss is built
        # outward from the arm, this is bored inward into it.
        bore = (
            TechnicPinHole.standard(
                depth=self.MID_BORE_DEPTH,
                profile=self._profile,
                counterbore_ends="entry",
            )
            .to_cutter()
            .rotate((0, 0, 0), (1, 0, 0), 90)
            .translate((hole_x_local, boss_tip, mid_z))
        )

        assert len(arm.solids().vals()) == 1, "Expected single solid, got multiple pieces"
        return arm, bore

    def _place_arm(
        self, arm_local: cq.Workplane, bore_local: cq.Workplane, x_sign: int, y_sign: int
    ) -> tuple[cq.Workplane, cq.Workplane]:
        """Map the (+X, +Y)-quadrant arm/bore into one of the four housing
        quadrants.

        The local -> global remap swaps X and Y (length <-> width, since
        the arm's *length* runs along housing Y while its *width* runs
        along housing X, per ``docs/design_plans/2026-08-19-poweredup-hub-battery-box_ldraw-housing-geometry.md`` SS3.0) --
        an axis swap is a reflection (determinant -1), not achievable by
        any pure rotation, so it is done via ``mirror(mirrorPlane=(1,-1,0))``
        (reflection through the Y = X plane, confirmed empirically to map
        ``(x, y, z) -> (y, x, z)``), followed by the ``(+32, +12, +16)``
        translation that centres hole positions on ``X = 32`` and the
        ``["main", "none", "main"]`` local hole line (X = 4/12/20) on
        ``Y = 16/24/32``.  The other three quadrants are then reached by
        ordinary axis mirrors (no further swap needed, since the arm
        geometry has no handedness -- ``docs/design_plans/2026-08-19-poweredup-hub-battery-box_ldraw-housing-geometry.md``
        SS2.2: "there is no handedness anywhere in the arms").
        """
        def _transform(wp: cq.Workplane) -> cq.Workplane:
            out = wp.mirror(mirrorPlane=(1, -1, 0), basePointVector=(0, 0, 0))
            out = out.translate((self.HOLE_X, self._ARM_Y_OFFSET, self.ARM_Z_LO))
            if y_sign < 0:
                out = out.mirror(mirrorPlane="XZ", basePointVector=(0, 0, 0))
            if x_sign < 0:
                out = out.mirror(mirrorPlane="YZ", basePointVector=(0, 0, 0))
            return out

        return _transform(arm_local), _transform(bore_local)

    # ------------------------------------------------------------------
    # Latch-end wall (-Y) -- single wall, locally thickened catches
    # ------------------------------------------------------------------

    def _build_latch_wall(self) -> cq.Workplane:
        # Round 21 (finding RH1): capped at END_WALL_Z_HI (24.000 mm), not
        # DECK_Z -- which round 22 made the same number; above it the
        # shell narrows to the (unaffected) X-direction side walls' own
        # upper band and the deck's own narrower footprint (see class
        # docstring's *Known simplifications* -> *End-wall Z extent*).
        base = self._y_slab(
            self.LATCH_Y, self.LATCH_WALL_THICKNESS, 0.0, self.END_WALL_Z_HI, inward=True
        )
        # Round 22 -- order matters. Cut the latch-U band back to the
        # original skin FIRST, so everything below runs against the same
        # 1.200 mm wall the round-18..21 catch geometry was derived
        # against, then re-add the catch bosses into that band exactly as
        # before.
        base = base.cut(self._build_latch_clearance())
        base = base.cut(self._build_finger_windows())

        # Round 40: the catch boss / undercut slot / keeper nub are GONE.
        # They were the mating half of a barb-on-the-finger the cover no
        # longer has (round 38 rebuilt the latch as a hairpin spring whose
        # retention is the release-leg bead against _build_latch_land), and
        # they had been dead for two rounds without anyone measuring it:
        # the slot cutter overlapped 0.0000 mm^3 of the built wall, the nub
        # was already not unioned, and the boss's entire remaining effect was
        # a 0.150 mm overhang above the crown that the wall itself already
        # provides. See R40 in the reference-comparison for the measurements.

        # The retention land stands proud of the skin, so it is unioned last.
        base = base.union(self._build_latch_land())

        assert len(base.solids().vals()) == 1, "Expected single solid, got multiple pieces"
        return base

    def _build_latch_land(self) -> cq.Workplane:
        """Retention land: a rail on the latch wall's inner face that the
        cover's release-leg bead snaps over (round 30).

        Round 27 had this backwards. Philo's bead is only 0.220 mm proud and
        this wall's inner face sat at -34.400 -- 0.400 mm off the leg -- so
        nothing could reach it. Instead of correcting the wall, round 27 grew
        a 1.000 mm bead on the *cover* near the leg's anchor; it retained but
        could not be released (64.5 mm of pad travel required, R30). The
        defect was on this side all along.

        The rail stands proud to :attr:`LATCH_LAND_Y`, leaving 0.050 mm
        running clearance against the leg's -34.000 baseline, and spans Z
        only BELOW the bead's seated band. Hence:

        * **seated** -- the bead (z 4.750..5.750) sits above the rail: zero
          interference, so the lid closes without deforming anything;
        * **withdrawal** -- the bead's lower flank drives into the rail's top
          face and resistance grows;
        * **insertion** -- the bead rides over the rail, deflecting the leg
          0.170 mm inboard, then snaps clear;
        * **release** -- pressing the thumb pad deflects the leg inboard, and
          only 0.170 mm is needed. The bead sits at z ~ 5 of an 11.600 mm free
          length, so ~0.4 mm of pad travel suffices.
        """
        from vibe_cading.lego_adapters.poweredup_hub.cover import PoweredUpHubCover

        lg: LatchGeometry = self._latch
        half_w = lg.hook_width / 2.0
        y_wall = self.LATCH_Y + self.LATCH_SKIN_THICKNESS      # -34.400
        depth = y_wall - self.LATCH_LAND_Y
        height = self.LATCH_LAND_Z_HI - self.LATCH_LAND_Z_LO
        assert self.LATCH_LAND_Z_HI < PoweredUpHubCover.BEAD_Z_LO, (
            "the land must sit BELOW the bead's seated band, else the lid "
            "cannot close without interference")

        land = None
        for side in (+1, -1):
            x_center = side * (lg.hook_pitch / 2.0 + half_w)
            rail = rounded_box(
                width=lg.hook_width,
                depth=depth,
                height=height,
                corner_r=0.0,
                center=(x_center, self.LATCH_LAND_Y + depth / 2.0, self.LATCH_LAND_Z_LO),
            )
            land = rail if land is None else land.union(rail)
        return land

    def _build_latch_clearance(self) -> cq.Workplane:
        """Cut the round-22 thickened latch wall back to its original
        :attr:`LATCH_SKIN_THICKNESS` skin across the band the cover's latch
        U occupies -- see :attr:`LATCH_WALL_THICKNESS` for why this exists.

        Z extent is the U's own ``hook_depth`` **plus a running clearance**.

        Round 40 -- it used to be ``engagement_band_hi``, which for the
        current latch geometry is the same number as ``hook_depth``, so the
        wall resumed at exactly the crown's top face: a zero-clearance butt
        against the ceiling that would preload the spring and hold the lid
        off its seat. It survived because it is *invisible to a boolean
        intersection* -- tangent faces enclose no volume, so the seated
        interference test scored it 0.000 mm^3 and passed. Measured
        headroom before the fix was 0.024 mm at the crown apex (the arc
        falls away either side of it), against a 0.150 mm running clearance
        everywhere else on this interface.

        The old wording justified stopping here by ``_build_latch_catch``'s
        ledge re-adding the band above; that method is gone (see the class
        docstring's *Latch interface*), so the constraint is gone with it.

        X extent is the cover's own ``hook_width`` plus a running clearance
        each side -- the hook legs and the release legs share one footprint
        (both are extruded ``hook_width`` about the same ``x_center``), so
        one channel per side clears both.
        """
        lg: LatchGeometry = self._latch
        clearance = self._profile.free.radial
        y_inner = self.LATCH_Y + self.LATCH_WALL_THICKNESS   # -30.800
        y_outer = self.LATCH_Y + self.LATCH_SKIN_THICKNESS   # -34.400
        overcut = 1.0  # break cleanly through the wall's own inner face
        channels = None
        for side in (+1, -1):
            x_center = side * (lg.hook_pitch / 2.0 + lg.hook_width / 2.0)
            channel = rounded_box(
                width=lg.hook_width + 2 * clearance,
                depth=(y_inner + overcut) - y_outer,
                height=lg.hook_depth + clearance,
                corner_r=0.0,
                center=(x_center, (y_outer + y_inner + overcut) / 2.0, 0.0),
            )
            channels = channel if channels is None else channels.union(channel)
        return channels

    def _build_finger_windows(self) -> cq.Workplane:
        """The through-slot the cover's thumb pad passes into.

        Round 40 -- the cut is now ``hook_width`` plus a running clearance
        each side, centred on the hook's own ``x_center``, instead of the
        bare :attr:`LATCH_WINDOW_X_LO` / :attr:`LATCH_WINDOW_X_HI` literals.
        Those literals are the *nominal* footprint (they equal the hook
        footprint exactly, which is asserted below so the two cannot drift),
        and cutting to them gave the pad **0.000 mm of clearance on both X
        edges** -- a 13.600 mm pad into a 13.600 mm slot -- while the U leg's
        own channel next door carried the standard 0.150 mm per side. The
        pad could not enter the window, let alone slide in it once pressed.

        As with the crown headroom (see :meth:`_build_latch_clearance`), a
        zero clearance is invisible to a boolean intersection, so no seated
        test caught it; :func:`test_thumb_pad_has_running_clearance_in_its_window`
        pins the gap directly.
        """
        lg: LatchGeometry = self._latch
        clearance = self._profile.free.radial
        overcut = 1.0
        y_lo = self.LATCH_Y - overcut
        y_hi = self.LATCH_Y + self.LATCH_WALL_THICKNESS + overcut
        half_w = lg.hook_width / 2.0
        nominal = lg.hook_pitch / 2.0 + half_w
        assert (
            abs((nominal - half_w) - self.LATCH_WINDOW_X_LO) < 1e-9
            and abs((nominal + half_w) - self.LATCH_WINDOW_X_HI) < 1e-9
        ), (
            "LATCH_WINDOW_X_LO/HI must stay equal to the cover's own hook "
            "footprint -- they are the nominal span the clearance is added to"
        )
        windows = None
        for side in (+1, -1):
            x_center = side * nominal
            win = rounded_box(
                width=lg.hook_width + 2 * clearance,
                depth=y_hi - y_lo,
                height=self.LATCH_WINDOW_Z_HI,
                corner_r=0.0,
                center=(x_center, (y_lo + y_hi) / 2.0, 0.0),
            )
            windows = win if windows is None else windows.union(win)
        return windows

    # ------------------------------------------------------------------
    # Tongue-end wall (+Y) -- single wall, rebate step only
    # ------------------------------------------------------------------

    def _build_tongue_wall(self) -> cq.Workplane:
        """Four Z bands, plus the round-46 locating ribs
        (:meth:`_build_tongue_ribs`) that stand in the cavity in front of
        them.

        1. ``[0, TONGUE_STEP_Z]`` -- the rebate, inner face at
           :attr:`TONGUE_INNER_Y_LOWER`. This is the lap the cover's
           tongue tip hooks under; unchanged since round 18, and NOT the
           feature the owner described in round 73c (see
           ``TONGUE_STEP_Z``'s own note -- the exact numeric coupling to
           ``PoweredUpHubCover.TIP_Z_LO`` rules that out).
        2. ``[TONGUE_STEP_Z, tongue_clear_z_hi]`` -- the band the cover's
           tongue tip and riser actually occupy, inner face held back at
           :attr:`TONGUE_INNER_Y_UPPER` (+ running clearance). UNCHANGED
           since round 22, and round 73c specifically KEPT it that way
           after an attempted merge into band 3 measurably regressed
           Housing/Cover clearance by 49.546 mm^3 -- see
           ``TONGUE_INNER_Y_UPPER``'s own note for the A/B measurement.
        3. ``[tongue_clear_z_hi, TONGUE_RELIEF_Z_HI]`` -- **new in round
           73c.** The owner's own observation: "the wall on the tongue
           side is stepped, the first 5mm on the Z is narrower." This band
           extends the relief from where band 2 already stops (~2.95 mm,
           above the Cover's own riser reach) out to the owner's stated
           5.000 mm, at :attr:`TONGUE_RELIEF_THICKNESS` (owner-measured
           this round, with a hard derived ceiling from the frozen Cover's
           own plate edge -- see that constant's own comment). This Z-range
           had no pre-existing clearance requirement (nothing Cover-side
           reaches this high), so adding it does not disturb band 2.
        4. ``[TONGUE_RELIEF_Z_HI, END_WALL_Z_HI]`` -- the flat wall's own
           thickness, :attr:`TONGUE_WALL_THICKNESS` (round 73c: 4.100,
           owner-measured directly above the step -- supersedes round
           73b's 4.500, itself a proposed round number rather than a
           caliper reading). This is the tongue-end counterpart of the
           latch end's own :attr:`LATCH_WALL_THICKNESS` thickening.

        Round 46 adds the three mirrored rib pairs that enter the Cover's
        own tongue slots -- see :meth:`_build_tongue_ribs`. They stand
        inboard of band 1, in the cavity the two skins bound in the
        reference, and tie bands 1 and 2 together in Z (their own Z-height
        is independently pinned to ``Cover.RISER_Z_HI``, unaffected by
        round 73c's new band 3).
        """
        lower = self._y_slab(
            self.TONGUE_Y,
            self.TONGUE_Y - self.TONGUE_INNER_Y_LOWER,
            0.0,
            self.TONGUE_STEP_Z,
            inward=False,
        )
        # The cover's riser tops out at RISER_Z_HI; clear it by the
        # project's own running-clearance convention before thickening.
        tongue_clear_z_hi = PoweredUpHubCover.RISER_Z_HI + self._profile.free.radial
        riser_clearance = self._y_slab(
            self.TONGUE_Y,
            self.TONGUE_Y - self._tongue_inner_y_upper,
            self.TONGUE_STEP_Z,
            tongue_clear_z_hi,
            inward=False,
        )
        relief_extension = self._y_slab(
            self.TONGUE_Y,
            self.TONGUE_RELIEF_THICKNESS,
            tongue_clear_z_hi,
            self.TONGUE_RELIEF_Z_HI,
            inward=False,
        )
        upper = self._y_slab(
            self.TONGUE_Y,
            self.TONGUE_WALL_THICKNESS,
            self.TONGUE_RELIEF_Z_HI,
            self.END_WALL_Z_HI,
            inward=False,
        )
        return (
            lower.union(riser_clearance).union(relief_extension).union(upper)
            .union(self._build_tongue_ribs())
        )

    def _build_tongue_ribs(self) -> cq.Workplane:
        """The three mirrored rib pairs that enter the Cover's tongue slots.

        Geometry and provenance: see :attr:`TONGUE_RIB_X_BANDS`.  This
        method owns only the *fit* -- where the nominal reference bands
        get their clearance, and how the ribs tie into the wall bands
        built by :meth:`_build_tongue_wall`.

        **X -- clearance on every flank that faces a Cover blade.**  The
        Cover's slots are cut at the nominal reference walls
        (|X| = 0.800 / 15.600 / 17.200 / 26.000), so a rib built to the
        same nominal is a zero-clearance literal-to-literal butt on both
        flanks and will not enter the slot on FDM.  Each such flank is
        pulled back by ``profile.free.radial`` -- the same running-fit
        knob the tongue's own back wall already routes its insertion
        datum through (ROUND 73c: was :attr:`TONGUE_INNER_Y_UPPER`,
        retired -- see that constant's own note; the concept is unchanged,
        only which constant carries it).  The outer
        band's ``28.000`` flank is the shell's own outer face with no
        Cover material outboard of it, so it takes no clearance.

        **Y -- every rib starts where the Cover's slots actually open.**
        Out to ``TONGUE_INNER_Y_LOWER``, where the rib merges into the
        rebate band; the -Y end is the SAME for all three bands, because
        ``cover.py`` ``_build_tongue()`` cuts all three slots from one
        expression, ``PLATE_Y_HI + TONGUE_GAP_Y_INSET`` (= 33.000).

        ROUND 75 retired the previous per-band story here.  It claimed the
        starts differed -- plate edge outboard of
        ``PoweredUpHubCover.LEDGE_X_HALF``, ``LEDGE_Y_LO`` inboard of it
        for the centre rib -- but both of those constants are 32.200, so
        the branch chose between identical values, and 32.200 is the wrong
        line anyway: inboard of 33.000 the Cover is solid (the blades'
        shared root), so every rib starting at the plate edge buried
        0.800 mm into it.  A sweep of the built Cover
        (``tmp/r75e_slot_open_exact.py``) measures all three slots opening
        at 33.000 with 0.000 spread, which is the positive evidence that
        no per-band variation exists.  All starts then take the same
        running clearance -- the +Y insertion
        stop is the tongue tip against the back wall (ROUND 73c: the
        relief's own inner face, :attr:`TONGUE_RELIEF_THICKNESS`; was
        ``TONGUE_INNER_Y_UPPER``), so a rib butting a Cover face in -Y
        would be a competing stop.

        **Z.**  From the bottom face up to (approximately) ``Cover.
        RISER_Z_HI`` + running clearance -- independently pinned to the
        Cover's own riser height, NOT to :attr:`TONGUE_RELIEF_Z_HI` (round
        73c widened the wall's own relief band well past this rib height,
        but the rib itself only needs to clear the riser it enters,
        computed directly below as ``z_hi``) -- so each rib sits inside
        the rebate band below (in Y) and comfortably inside the (now
        wider) relief band above (in Z) rather than floating.  Both joins
        carry a small overlap:
        coincident union faces are unreliable in the OCCT boolean kernel
        (see CLAUDE.md, *Chord-vs-arc ring*), and the overlap lands
        strictly inside material this method does not own, so it adds no
        volume.
        """
        clr = self._profile.free.radial
        overlap = 0.050

        y_hi = self.TONGUE_INNER_Y_LOWER + overlap
        z_hi = PoweredUpHubCover.RISER_Z_HI + clr + overlap

        # Round 59 moved the Cover's slot walls: its blades narrow and its
        # gaps widen by the lid's own fit clearance, so the slots are no
        # longer AT the nominal reference walls this method's docstring was
        # written against. Pulling back from the nominal would therefore
        # clear the real slot by clr + cover_fit -- the ribs would still fit,
        # but they would locate the lid to twice the intended slop, silently,
        # because nothing here would collide. Track the lid's actual walls
        # instead, so the interleave stays the ONE designed clearance.
        cover_fit = PoweredUpHubCover.fit_clearance(self._profile)

        # (x_lo, x_hi) after clearance, one entry per rib, both signs.
        # The centre band is a GAP in the lid, so its walls move outward by
        # the lid's fit; the rib may grow with them.
        bands: list[tuple[float, float]] = [
            (-self.TONGUE_RIB_CENTRE_X_HALF - cover_fit + clr,
             self.TONGUE_RIB_CENTRE_X_HALF + cover_fit - clr)
        ]
        for nom_lo, nom_hi in self.TONGUE_RIB_X_BANDS:
            # These bands are gaps BETWEEN blades: the blade edge at nom_lo
            # retreats to nom_lo - cover_fit and the one at nom_hi advances
            # to nom_hi + cover_fit, so both walls move outward.
            lo = (nom_lo - cover_fit) + clr
            # Only the shell's own outer face has nothing to clear.
            hi = (nom_hi if nom_hi >= self.WALL_X_OUTER_LOWER
                  else (nom_hi + cover_fit) - clr)
            for sign in (-1.0, 1.0):
                bands.append(tuple(sorted((sign * lo, sign * hi))))

        ribs = None
        for x_lo, x_hi in bands:
            # ROUND 75 -- the rib's inboard start is DERIVED from where the
            # Cover's slots actually open, not from the plate edge.
            #
            # Round 74 read this as `LEDGE_Y_LO if under_ledge else
            # PLATE_Y_HI` -- both of which are 32.200, so the conditional was
            # a distinction without a difference, AND the value was wrong:
            # the slots do not open at the plate edge.  `cover.py`
            # `_build_tongue()` cuts them at
            #     gap_y_lo = PLATE_Y_HI + TONGUE_GAP_Y_INSET = 33.000
            # for ALL three bands from one expression -- which is exactly why
            # a sweep of the built Cover (`tmp/r75e_slot_open_exact.py`) finds
            # every slot opening at 33.000 with 0.000 spread across all three
            # centres and all sampled heights.  Between the plate edge and
            # that line the Cover is SOLID (the blades' shared root, round
            # 66), so a rib starting at 32.200 buries 0.800 mm into it --
            # the measured 4.394 mm^3 bind that
            # `test_tongue_ribs_locate_sideways_without_obstructing_withdrawal`
            # reports at dX = 0.000.
            #
            # Derived, not restated: a housing-side literal 33.000 would be
            # the same stale-literal hazard this file has already been bitten
            # by once (see the round-61/69 PAD_SCALLOP note).  The `- SHELL_
            # Y_OFFSET` back-compensation is unchanged from round 74 -- these
            # ribs are built in the shell's LOCAL frame and must still land on
            # the frozen Cover's feature after the shell-wide translate.
            # `y_hi` is a housing-native constant and rides with the shell.
            y_lo = (
                PoweredUpHubCover.PLATE_Y_HI
                + PoweredUpHubCover.TONGUE_GAP_Y_INSET
            ) - self.SHELL_Y_OFFSET + clr
            rib = rounded_box(
                width=x_hi - x_lo,
                depth=y_hi - y_lo,
                height=z_hi,
                corner_r=0.0,
                center=((x_lo + x_hi) / 2.0, (y_lo + y_hi) / 2.0, 0.0),
            )
            ribs = rib if ribs is None else ribs.union(rib)
        return ribs

    def _y_slab(
        self, y_outer: float, thickness: float, z_lo: float, z_hi: float, *, inward: bool
    ) -> cq.Workplane:
        """A wall slab facing +/-Y, outer face at ``y_outer``, ``thickness``
        mm thick (toward the interior), spanning the nominal X width and
        ``[z_lo, z_hi]``.  ``inward`` is unused directionally (kept for
        call-site clarity -- ``thickness`` is always signed correctly by
        the caller via ``y_outer - inner_face``); both latch (``-Y``) and
        tongue (``+Y``) ends share this helper.
        """
        y_inner = y_outer - thickness if y_outer > 0 else y_outer + thickness
        y_lo = min(y_outer, y_inner)
        y_hi = max(y_outer, y_inner)
        return rounded_box(
            width=2 * self.WALL_X_OUTER_LOWER,  # simplified constant X extent, see docstring
            depth=y_hi - y_lo,
            height=z_hi - z_lo,
            corner_r=0.0,
            center=(0.0, (y_lo + y_hi) / 2.0, z_lo),
        )

    @property
    def solid(self) -> cq.Workplane:
        return self._solid
