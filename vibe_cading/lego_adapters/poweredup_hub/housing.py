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
    HALF_Y = 35.600
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
    DECK_STUDS = 3
    DECK_Z = DECK_STUDS * STUD_PITCH   # 24.000
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
    PLATE_EDGE_RELIEF_Z_HI = max(
        PoweredUpHubCover.PLATE_THICKNESS,
        PoweredUpHubCover.GROOVE_THICKNESS,
        PoweredUpHubCover.LATCH_BAND_THICKNESS,
    )
    WALL_X_OUTER_LOWER = 28.000   # |X| outer face, Z < WALL_STEP_Z
    WALL_X_OUTER_UPPER = 27.200   # |X| outer face inside the socket, and above it
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
    # 29.600; this part stops at DECK_Z = 24.000, so its top edge IS the top
    # of the part and the socket reads as a notch open upward -- which is what
    # makes it usable as a cap register.
    SOCKET_Z_LO = 22.000          # == the old WALL_STEP_Z, now a local datum
    SOCKET_Y_HALF_LO = 9.200      # narrow (lower) edge half-width
    SOCKET_Y_HALF_HI = 11.200     # wide (upper) edge half-width, at DECK_Z
    WALL_INNER_STEP_Z = 21.200    # where the wall doubles to 1.600 mm

    # Round 22: the end walls run the shell's full height, which is now
    # the same 24.000 mm they were already capped at by round 21 (RH1) --
    # the number is unchanged, but its MEANING is: it used to be "the real
    # end wall stops here, below the deck", and is now "the end wall
    # reaches the deck". Derived from DECK_Z rather than re-typed so the
    # two cannot drift apart.
    END_WALL_Z_HI = DECK_Z

    # --- Side windows (SS7.2, round 20 H3, round 21 RH3, round 41) ---
    # The window is the SAME OUTLINE as the cover's side handle, offset
    # outward by the running clearance -- see _build_side_window. These two
    # constants are the reference's own measurements of it, kept as the
    # cross-check that this class and the cover still describe one feature
    # (asserted in _build_side_window, not merely documented here).
    WINDOW_Y_HALF = 12.000        # flat half-width, Z <= WINDOW_SHOULDER_Z
    WINDOW_SHOULDER_Z = 4.800     # where the corner round-over begins
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
    CORD_PORT_CORNER_R = 1.000
    CORD_PORT_MARGIN = 0.300

    # --- Pin-hole / arm map (SS1, SS2) ---
    HOLE_X = 32.000
    HOLE_Y = (16.000, 24.000, 32.000)   # inner / middle / outer, one quadrant
    HOLE_AXIS_Z = 20.000
    ARM_THICKNESS = 8.000                # -> PerpendicularHolesLiftarm(thickness=...)
    ARM_Z_LO = HOLE_AXIS_Z - ARM_THICKNESS / 2   # 16.000
    ARM_Y_LO = 12.400                    # inboard flat face (envelope trim)
    ARM_Y_HI = HALF_Y                    # 35.600, outboard face

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

    # Local-frame -> global-Y translation offset for the arm/bore remap
    # (see _place_arm). Round 43: the arm is now built at its own real
    # length with cap centres ON the hole line, so local X = 0 IS the arm's
    # inboard face and the offset is simply ARM_Y_LO. Rounds 16-42 needed a
    # separate number (12.0) because the arm was built one stud pitch too
    # long and then trimmed back, which put local X = 0 outside the part.
    _ARM_Y_OFFSET = ARM_Y_LO

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
    ARM_LENGTH = 23.200         # 2 x hole pitch + 2 x cap radius
    ARM_WIDTH = 7.200           # = 2 x ARM_CAP_R; the reference's own 18 LDU
    ARM_CAP_R = ARM_WIDTH / 2.0

    BOSS_DIAMETER = 7.200
    BOSS_PROUD = 0.400          # beyond the arm's own ARM_WIDTH/2 edge, see docstring

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
    # exactly the thin material a blind hole has least of. These figures are
    # the reference's own.
    MID_BORE_DEPTH = 7.200
    MID_BORE_FLOOR_X = 28.800   # |X| the bore stops at, measured from 24851s01
    MID_BORE_MIN_FLOOR = 0.400  # arm material that must survive behind it

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
    LATCH_WALL_THICKNESS = 4.800   # -35.600 -> -30.800
    LATCH_SKIN_THICKNESS = 1.200   # what survives in the latch-U band

    LATCH_WINDOW_X_LO = 5.600
    LATCH_WINDOW_X_HI = 19.200
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
    TONGUE_INNER_Y_LOWER = 33.378   # inner face, Z < TONGUE_STEP_Z (the rebate)
    # Nominal back-wall inner face -- exactly coincident with
    # PoweredUpHubCover.TONGUE_Y_HI (34.400 mm), i.e. a bare zero-clearance
    # literal-to-literal butt (round 18, S7). Every other Cover/Housing
    # interface routes its insertion datum through profile.free.radial;
    # this one didn't, making the tongue's insertion stop unreachable on
    # FDM. self._tongue_inner_y_upper (below) is the profile-corrected
    # value actually used by _build_tongue_wall -- this class constant is
    # kept for its docstring/reference value only.
    TONGUE_INNER_Y_UPPER = 34.400

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
    TONGUE_RIB_CENTRE_X_HALF = 0.800
    TONGUE_RIB_X_BANDS = ((15.600, 17.200), (26.000, 28.000))

    def __init__(self, profile: ToleranceProfile | str | None = None) -> None:
        if profile is None or isinstance(profile, str):
            prof = get_profile(profile) if isinstance(profile, str) else get_profile()
        else:
            prof = profile
        self._profile = prof
        self._latch = get_latch_geometry(prof)
        # Round 18, S7: add a running-clearance allowance to the tongue
        # back wall's inner face -- moving it FURTHER from Cover's tongue
        # tip (TONGUE_Y_HI = 34.400 mm, unchanged), i.e. thinning this
        # local wall slightly so the tip has somewhere to actually reach on
        # FDM, instead of a bare zero-clearance literal-to-literal butt.
        # (An earlier version subtracted here instead, which moved the
        # inner face TOWARD the tip and thickened the wall -- the opposite
        # of clearance -- and measurably collided with Cover's tongue tip.)
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

        body = body.cut(self._build_side_window(+1))
        body = body.cut(self._build_side_window(-1))
        body = body.cut(self._build_plate_edge_relief())
        body = body.cut(self._build_cord_port())

        assert len(body.solids().vals()) == 1, "Expected single solid, got multiple pieces"
        return body

    # ------------------------------------------------------------------
    # Side walls (X-direction, stepped)
    # ------------------------------------------------------------------

    def _build_side_wall(self, x_sign: int) -> cq.Workplane:
        """One side wall, with the trapezoid mating socket in its outer face.

        Three pieces, per the reference (see :attr:`SOCKET_Z_LO`):

        1. ``[0, WALL_INNER_STEP_Z]`` -- plain 0.800 mm skin, outer face at
           :attr:`WALL_X_OUTER_LOWER`.
        2. ``[WALL_INNER_STEP_Z, DECK_Z]`` -- the wall doubles to 1.600 mm
           by stepping its INNER face inboard to
           ``WALL_X_OUTER_UPPER - WALL_THICKNESS``. This is what lets the
           socket be a pocket rather than a hole.
        3. The socket itself, cut out of that thickened band.

        Rounds 16-49 instead built band 2 as a 0.800 mm skin recessed to
        ``WALL_X_OUTER_UPPER``, i.e. the socket's own depth applied along
        the whole wall. That is why this part had no socket: it was all
        socket. The correction adds material outboard over
        ``[SOCKET_Z_LO, DECK_Z]`` everywhere the trapezoid is not.
        """
        overlap = 0.050
        inner_upper = self.WALL_X_OUTER_UPPER - self.WALL_THICKNESS   # 26.400

        # Band 1 runs slightly past the step. Its X span is a subset of band
        # 2's, so the extra 0.050 mm is a genuine volume overlap that changes
        # no face -- unlike the round-20 H5 trick it replaces, which widened
        # an externally-visible face to buy the same overlap.
        lower = self._x_slab(
            x_sign, self.WALL_X_OUTER_LOWER, self.WALL_THICKNESS,
            0.0, self.WALL_INNER_STEP_Z + overlap,
        )
        thickened = self._x_slab(
            x_sign, self.WALL_X_OUTER_LOWER,
            self.WALL_X_OUTER_LOWER - inner_upper,        # 1.600
            self.WALL_INNER_STEP_Z, self.DECK_Z,
        )
        return lower.union(thickened).cut(self._build_wall_socket(x_sign))

    def _build_wall_socket(self, x_sign: int) -> cq.Workplane:
        """The trapezoidal recess in one side wall's outer face.

        Geometry and provenance: :attr:`SOCKET_Z_LO`. Cut from
        :attr:`WALL_X_OUTER_UPPER` outward, so the surviving 0.800 mm of
        wall inboard of it is a normal section and the socket floor lands
        on the same plane the reference measures.

        The profile is extended vertically above ``DECK_Z`` rather than by
        continuing the 45-degree flanks, so the overcut cannot widen the
        socket's mouth beyond its measured ``SOCKET_Y_HALF_HI``.
        """
        oc = 1.0
        y_lo, y_hi = self.SOCKET_Y_HALF_LO, self.SOCKET_Y_HALF_HI
        z_lo, z_hi = self.SOCKET_Z_LO, self.DECK_Z

        profile = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0.0, 0.0, x_sign * self.WALL_X_OUTER_UPPER))
            .moveTo(-y_lo, z_lo)
            .lineTo(y_lo, z_lo)
            .lineTo(y_hi, z_hi)
            .lineTo(y_hi, z_hi + oc)
            .lineTo(-y_hi, z_hi + oc)
            .lineTo(-y_hi, z_hi)
            .close()
        )
        # The YZ workplane's normal is +X whatever the sign, so the extrusion
        # must be signed or the -X socket is cut out of thin air inboard.
        depth = self.WALL_X_OUTER_LOWER - self.WALL_X_OUTER_UPPER + oc
        return profile.extrude(x_sign * depth)

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

    def _build_plate_edge_relief(self) -> cq.Workplane:
        """Running clearance for the Cover's plate edge against both side
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
        wall_inner = self.WALL_X_OUTER_LOWER - self.WALL_THICKNESS
        z_hi = self.PLATE_EDGE_RELIEF_Z_HI + clr
        y_lo = PoweredUpHubCover.PLATE_Y_LO - 0.200
        y_hi = PoweredUpHubCover.PLATE_Y_HI

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

        x_hi = self.WALL_X_OUTER_UPPER - self.WALL_THICKNESS      # 26.400
        x_lo = x_hi - self.CORD_PORT_WIDTH
        y_lo = PoweredUpHubCover.LATCH_BAND_Y_HI                  # -30.000
        y_hi = y_lo + self.CORD_PORT_LENGTH

        return rounded_box(
            width=(x_hi - x_lo) + 2 * m,
            depth=(y_hi - y_lo) + 2 * m,
            height=self.DECK_THICKNESS + 2 * oc,
            corner_r=self.CORD_PORT_CORNER_R,
            center=(
                (x_lo + x_hi) / 2.0,
                (y_lo + y_hi) / 2.0,
                self.DECK_Z - self.DECK_THICKNESS - oc,
            ),
        )

    def _build_side_window(self, x_sign: int) -> cq.Workplane:
        """Tab-access cutout through one side wall (SS7.2).

        Round 41 -- **the window is the cover's own side-handle outline,
        offset outward by the running clearance.** Same construction as the
        tab: vertical sides, then the ``HANDLE_ROUND_R`` corner round-over
        about the same centre, then the flat top. Offsetting that outline
        uniformly by ``c`` is exact and needs no re-derivation, because the
        round-over's centre sits at ``(HANDLE_ROUND_CZ, HANDLE_LEDGE_Y_HALF)``
        and its two tangent points are the side and the top -- so the sides
        move to ``PAD_Y_HALF + c``, the top to ``PAD_Z_HI + c``, and the arc
        keeps its centre with radius ``ROUND_R + c``.

        It used to be a three-point piecewise-linear taper sampled off the
        reference (see :attr:`WINDOW_TAPER_PROFILE`'s retired note). Chords
        lie inside the arc they subtend, so that cut was narrower than the
        tab at every intermediate Z, and the cover shrank its whole tab by
        0.320 mm to get through -- deleting reference material from the part
        to accommodate a mis-modelled hole. Cutting the true arc is what the
        chord-vs-arc pitfall in ``vibe/INSTRUCTIONS.md`` prescribes, and it
        lets the tab go back to nominal.

        The clearance now lives HERE rather than on the tab, which is the
        right side of a hole/shaft pair for it and restores the cover to its
        reference dimensions.
        """
        overcut = 1.0  # break cleanly through the wall's X extent
        x_outer = self.WALL_X_OUTER_LOWER + overcut
        x_inner = self.WALL_X_OUTER_LOWER - self.WALL_THICKNESS - overcut
        x_lo = x_sign * min(x_outer, x_inner)
        x_hi = x_sign * max(x_outer, x_inner)
        width = abs(x_hi - x_lo)

        c = self._profile.free.radial
        cz = PoweredUpHubCover.HANDLE_ROUND_CZ          # round-over centre Z
        ly = PoweredUpHubCover.HANDLE_LEDGE_Y_HALF      # round-over centre |Y|
        r = PoweredUpHubCover.HANDLE_ROUND_R + c        # offset arc radius
        half = PoweredUpHubCover.HANDLE_PAD_Y_HALF + c  # side face
        zhi = PoweredUpHubCover.HANDLE_PAD_Z_HI + c     # flat top

        # The reference measured this window independently of the tab; if
        # the two ever stop describing one feature, say so here rather than
        # cutting a hole that silently no longer matches what goes through it.
        assert (
            abs(half - c - self.WINDOW_Y_HALF) < 1e-9
            and abs(cz - self.WINDOW_SHOULDER_Z) < 1e-9
        ), (
            "the cover's side handle and this class's own reference-measured "
            "window figures have drifted apart"
        )

        # 45-degree point on each round-over, for the three-point arc.
        d = r * math.sqrt(0.5)
        sketch = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0.0, 0.0, min(x_lo, x_hi)))
            .moveTo(-half, 0.0)
            .lineTo(-half, cz)
            .threePointArc((-ly - d, cz + d), (-ly, zhi))
            .lineTo(ly, zhi)
            .threePointArc((ly + d, cz + d), (half, cz))
            .lineTo(half, 0.0)
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
        ``x`` in ``[-WALL_X_OUTER_UPPER, WALL_X_OUTER_UPPER]`` (unchanged)
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
        # just removed at either end.  Depth reaches only 0.05 mm past the
        # upper-band wall's own inner face (WALL_X_OUTER_UPPER -
        # WALL_THICKNESS = 26.400 mm, -> local Y = -5.650) -- the minimum
        # needed to genuinely overlap the upper wall band ([26.4, 27.2])
        # for a reliable union, without intruding further into the cavity
        # than necessary.  An earlier version reached to local Y = -6.0
        # (global X = 26.0), which collided with PoweredUpHubBatteryTray's
        # own side wall -- caught by the cross-part verification probe.
        # The bridge lives on the NEGATIVE-Y side only (Y < -beam_half_width_pre,
        # i.e. beyond the arm's own -Y edge, toward the wall) -- NOT
        # symmetric with the +Y side, which must stay untouched (that is
        # where the hole bores live). An earlier version used
        # `+beam_half_width_pre` for both the depth and centre calc below,
        # which silently spanned the *whole* arm width (-5.65..+3.9) and
        # refilled the main-hole bores with the root's own material --
        # caught by the cross-part / hole-presence test suite.
        root_inner_local_y = -5.650
        root_outer_local_y = -beam_half_width_pre
        # Post-fix hardening (round 17): this Z window is the entirety of
        # the structural fuse -- 2.0 mm (ROOT_BAND_A_Z_HI - ROOT_BAND_A_Z_LO)
        # x 1.85 mm (reach depth, root_outer_local_y - root_inner_local_y)
        # x 23.2 mm (arm length) ~= 85.8 mm^3, see the design brief's own
        # margin derivation. If ROOT_BAND_A_Z_LO is ever raised (shrinking
        # Band A) without re-deriving that margin, the guard below fails
        # loudly instead of silently reopening the floating-arm defect.
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
        assert self.ROOT_BAND_A_Z_LO >= self.WALL_STEP_Z - self.ARM_Z_LO, (
            "Root bridge Band A must not extend below the wall step "
            "(global Z = WALL_STEP_Z) -- doing so regrows a wall-reaching "
            "extension into Band B's Z-range, which the tray's lower-band "
            "wall occupies (design brief Escalation 8)."
        )
        arm = arm.union(root)

        # Band B bridge (round 20, H4) -- see the comment above the SEAM_MARGIN
        # assignment for the derivation. Reach is intentionally SHALLOWER
        # than Band A's (into the wall's own material by SEAM_MARGIN only,
        # not past its inner face) -- this band exists solely to close the
        # slit, not to duplicate Band A's structural-fuse role.
        root_b_inner_local_y = (
            self.WALL_X_OUTER_LOWER - self.WALL_THICKNESS + SEAM_MARGIN - self.HOLE_X
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
        # See MID_BORE_DEPTH for the derivation off 24851s01.
        boss_tip = half_w + self.BOSS_PROUD                  # local y = +4.000
        floor_local_y = boss_tip - self.MID_BORE_DEPTH       # local y = -3.200

        floor_x = self.HOLE_X + floor_local_y
        assert abs(floor_x - self.MID_BORE_FLOOR_X) < 1e-9, (
            f"the bore floors at |X| = {floor_x:.3f}, not the reference's "
            f"{self.MID_BORE_FLOOR_X:.3f} -- MID_BORE_DEPTH and the boss "
            f"geometry have drifted apart"
        )
        arm_inboard_x = self.HOLE_X - half_w                 # 28.400
        assert floor_x - arm_inboard_x >= self.MID_BORE_MIN_FLOOR - 1e-9, (
            f"the bore leaves only {floor_x - arm_inboard_x:.3f} mm of arm "
            f"behind its floor; the reference leaves "
            f"{self.MID_BORE_MIN_FLOOR:.3f} mm"
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
        """Three Z bands (round 22 adds the third), plus the round-46
        locating ribs (:meth:`_build_tongue_ribs`) that stand in the
        cavity in front of them.

        1. ``[0, TONGUE_STEP_Z]`` -- the rebate, inner face at
           :attr:`TONGUE_INNER_Y_LOWER`. This is the lap the cover's
           tongue tip hooks under; unchanged.
        2. ``[TONGUE_STEP_Z, tongue_clear_z_hi]`` -- the band the cover's
           tongue tip and riser actually occupy, inner face held back at
           :attr:`TONGUE_INNER_Y_UPPER` (+ running clearance); unchanged.
        3. ``[tongue_clear_z_hi, END_WALL_Z_HI]`` -- **new in round 22.**
           Above the riser there is nothing to clear, so the wall thickens
           inward to the cover's own plate edge
           (``PoweredUpHubCover.PLATE_Y_HI``), closing the open slot the
           user flagged at this end. This is the tongue-end counterpart of
           the latch end's own :attr:`LATCH_WALL_THICKNESS` thickening --
           and it needs no clearance channel, because the tongue is a
           low feature (it tops out at ``RISER_Z_HI``) rather than a
           full-height one like the latch U.

        Round 46 adds the three mirrored rib pairs that enter the Cover's
        own tongue slots -- see :meth:`_build_tongue_ribs`. They stand
        inboard of band 1, in the cavity the two skins bound in the
        reference, and tie bands 1 and 3 together in Z.
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
        middle = self._y_slab(
            self.TONGUE_Y,
            self.TONGUE_Y - self._tongue_inner_y_upper,
            self.TONGUE_STEP_Z,
            tongue_clear_z_hi,
            inward=False,
        )
        upper = self._y_slab(
            self.TONGUE_Y,
            self.TONGUE_Y - PoweredUpHubCover.PLATE_Y_HI,
            tongue_clear_z_hi,
            self.END_WALL_Z_HI,
            inward=False,
        )
        return lower.union(middle).union(upper).union(self._build_tongue_ribs())

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
        datum through (see :attr:`TONGUE_INNER_Y_UPPER`).  The outer
        band's ``28.000`` flank is the shell's own outer face with no
        Cover material outboard of it, so it takes no clearance.

        **Y -- each rib starts where its own slot actually opens.**  Out
        to ``TONGUE_INNER_Y_LOWER``, where the rib merges into the rebate
        band; but the -Y end is per-band, because the Cover's slots are
        not all open to the same depth.  Outboard of
        ``PoweredUpHubCover.LEDGE_X_HALF`` the slot runs back to the plate
        edge (``PLATE_Y_HI``).  Inboard of it -- which is the centre rib
        -- the Cover's castellated ledge closes the slot off at
        ``LEDGE_Y_LO``: its notch floor (``NOTCH_FLOOR_Z``) is a
        continuous full-ledge-width band over ``[TEETH_Y_LO, TEETH_Y_HI]``
        and crosses the centre, so a centre rib run back to the plate edge
        collides with it (measured: 0.130 mm^3 of interference).  Both
        starts then take the same running clearance -- the +Y insertion
        stop is the tongue tip against the back wall at
        ``TONGUE_INNER_Y_UPPER``, so a rib butting a Cover face in -Y
        would be a competing stop.

        **Z.**  From the bottom face up to the same ``tongue_clear_z_hi``
        the wall's upper band starts at, so each rib is continuous with
        the rebate band below (in Y) and the thickened upper band above
        (in Z) rather than floating.  Both joins carry a small overlap:
        coincident union faces are unreliable in the OCCT boolean kernel
        (see CLAUDE.md, *Chord-vs-arc ring*), and the overlap lands
        strictly inside material this method does not own, so it adds no
        volume.
        """
        clr = self._profile.free.radial
        overlap = 0.050

        y_hi = self.TONGUE_INNER_Y_LOWER + overlap
        z_hi = PoweredUpHubCover.RISER_Z_HI + clr + overlap

        # (x_lo, x_hi) after clearance, one entry per rib, both signs.
        bands: list[tuple[float, float]] = [
            (-self.TONGUE_RIB_CENTRE_X_HALF + clr, self.TONGUE_RIB_CENTRE_X_HALF - clr)
        ]
        for nom_lo, nom_hi in self.TONGUE_RIB_X_BANDS:
            lo = nom_lo + clr
            # Only the shell's own outer face has nothing to clear.
            hi = nom_hi if nom_hi >= self.WALL_X_OUTER_LOWER else nom_hi - clr
            for sign in (-1.0, 1.0):
                bands.append(tuple(sorted((sign * lo, sign * hi))))

        ribs = None
        for x_lo, x_hi in bands:
            under_ledge = max(abs(x_lo), abs(x_hi)) <= PoweredUpHubCover.LEDGE_X_HALF
            y_lo = (
                PoweredUpHubCover.LEDGE_Y_LO if under_ledge
                else PoweredUpHubCover.PLATE_Y_HI
            ) + clr
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
