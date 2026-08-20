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
extracted in ``tmp/ldraw-housing-geometry.md`` (git-ignored; no LDraw
``.dat`` file, converted geometry, or render is committed to this repo --
only independently-written measurements and from-scratch CadQuery code).
Full design rationale:
``docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md``,
*Multi-part structure -> Housing*.

Per that design, this is an exact copy of the real ``25560`` shell's own
**shell envelope** -- ``72.0 x 71.2 x 29.6 mm`` -- with a scoped,
deliberate departure at the two lid-retention regions only: the latch end
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
``3,469.6 mm^2`` of up-facing area -- is at ``Z = 29.6``.  The class's
overall height is therefore ``DECK_Z`` (``29.6 mm``), not the retired
``TOP_Z`` (``33.8 mm``) figure quoted by rounds 1-19.
"""

from __future__ import annotations

import cadquery as cq

from vibe_cading.cq_utils import cylinder, rounded_box
from vibe_cading.lego.technic_beam_perp import PerpendicularHolesLiftarm
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
    share one LDraw parent frame (``tmp/ldraw-housing-geometry.md`` SS11.1:
    the lid-to-housing LDraw transform is a pure translation with no
    rotation and no sign flip, and that translation is already baked into
    each class's own ``Z = 0`` datum). Every feature extrudes ``+Z`` from
    there, up to :attr:`DECK_Z` (29.600 mm -- the shell's own top face, not
    the LDraw part's bounding box; see *Round 20 correction* above). X is
    centred on the housing's mid-width (hole plane at ``X = +-32.000``);
    Y follows the same frame as the Cover (latch end at ``-Y``, tongue end
    at ``+Y``).

    Kept, as an exact copy (design brief *Housing*):
        - Overall envelope 72.0 x 71.2 x 29.6 mm (with the arm bosses
          included in the 72.0 mm X figure) -- the shell's own envelope,
          not the LDraw part's bounding box (round 20, H1).
        - Stepped side walls (0.8 mm, outward step at height 22.0 mm).
        - Four arms -- literally LDraw 3-hole liftarms, reusing
          :class:`~vibe_cading.lego.technic_beam_perp.PerpendicularHolesLiftarm`
          per the TL round's decision (composed, not a class-contract
          change) -- with the real 12-hole pin map, the middle-hole boss,
          and the one-sided three-step middle bore.
        - Two side windows (tray-tab access), simplified to a single
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
          the groove survives on :class:`PoweredUpHubCover`, which mates
          with the tray, not the housing).

    Known simplifications (documented deviations, all cosmetic /
    non-load-bearing unless noted, per this project's Experimental
    Integrity convention):
        - **Top deck** modelled as a solid slab, ``DECK_THICKNESS``
          (2.082 mm) thick, spanning ``Z`` in
          ``[DECK_Z - DECK_THICKNESS, DECK_Z]`` (``[27.518, 29.600]``)
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
          corrected here. **Re-verified round 18 (finding C4)**: this
          simplification was previously *masking*
          :class:`~vibe_cading.lego_adapters.poweredup_hub.battery_tray.PoweredUpHubBatteryTray`'s
          S2 Z-datum error (the tab ledge would not have passed the real,
          ramped window profile) -- now that S2 is corrected, the tab
          ledge's real Z-band clears this corrected, shorter window with
          margin to spare (re-confirmed by the cross-part tests below), so
          the masking relationship is now moot rather than live.
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
          ``tmp/ldraw-housing-geometry.md``, not a modelling gap here.
        - **End-wall Z extent** (latch and tongue walls), ``Z`` in
          ``[0, END_WALL_Z_HI]`` (``0..24.0 mm``) -- round 18 (finding C3)
          originally built these full-height to ``DECK_Z`` (``29.6 mm``,
          a documented additive-only simplification); round 21 (finding
          RH1) corrects this to the real end wall's own measured height
          (``24.0 mm``, matching the reference exactly) -- this was the
          single largest remaining visual difference after round 20's H1
          fix. This class's own single-wall departure still scopes the
          latch/tongue ends away from an exact copy of LEGO's two-skin
          sandwich (``3.6..22.0 mm`` per ``tmp/ldraw-housing-geometry.md``)
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
        - **Arm faces dished** (round 20, H2): the reference cuts a
          shallow relief pocket into both faces of each arm, between the
          pin-hole positions, blended into each hole/boss by an
          R3.600 mm cylindrical relief -- see :meth:`_dish_arm_faces` for
          the Developer-derived construction and its own docstring for the
          exact-fit reasoning (the pocket half-width and the relief radius
          are not independent numbers -- they are self-consistent, per
          that method's docstring).

    Latch catch derivation
    -----------------------
    The catch's Y-depth placement is **derived from
    :class:`PoweredUpHubCover`'s own built geometry** (its
    ``HOOK_FACE_Y1`` constant plus the shared
    :class:`~vibe_cading.lego_adapters.poweredup_hub.latch_geometry.LatchGeometry`'s
    ``barb_protrusion``), not re-typed as a literal -- this keeps the two
    parts' mating geometry synchronised at the source, per the design
    brief's *Latch catch -- derived design* section and the TL round's Q2
    ruling (single shared parameter object, not shared geometry). The
    design's own illustrative "~2.6 mm local wall" figure is a *stated
    minimum*, not the literal placement -- reaching the barb's own
    computed crest position requires more local material than that
    (documented at the constant below); the code asserts the minimum
    floor is met, not the illustrative figure exactly.

    The catch is modelled as a **slot**, not a pocket cut into an
    otherwise-solid boss -- an earlier iteration used the latter and
    failed the cross-part verification (the finger's *drafted face*,
    not just its barb crest, occupies the engagement-band height; see
    :meth:`_build_latch_catch`'s own docstring for the full derivation).
    The retention ledge falls out of this slot's own bounds rather than
    from a separately-modelled sloped ramp -- :attr:`LatchGeometry.ramp_angle_deg`
    is therefore **not** geometrically realised as a distinct surface in
    this class (the slot's own generous, constant-cross-section mouth
    makes a separate lead-in unnecessary for interference-free assembly);
    this is flagged honestly rather than silently ignoring the field.

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
    # DECK_Z is the housing's own overall height -- the real shell's top
    # face (round 20, H1). TOP_Z (33.800 mm) is RETIRED: it was the LDraw
    # part's bounding box, reached only by two 26.9 mm^2 connector-port
    # tubes now ruled out of scope, not by the shell itself -- nothing
    # should build above DECK_Z any more.
    DECK_Z = 29.600
    # Round 21 (finding E11-a): DECK_THICKNESS is no longer a bare literal.
    # Round 20's H1 fix used 27.518 mm as the deck's underside -- but that
    # figure was round 20's OWN prior extraction explicitly flagged as the
    # *centre value of a corrugated ceiling* whose off-centre thickness was
    # NOT determined; applying it as a global flat plane collides with the
    # Tray's own top face (26.400 + PoweredUpHubCover.PLATE_THICKNESS =
    # 27.600 mm). DECK_THICKNESS_NOMINAL (2.000 mm) is the zero-clearance
    # figure (DECK_Z - 2.000 = 27.600, flush with the tray's top); the
    # instance's own running clearance (see __init__) is subtracted from it
    # so the deck's underside clears the tray by the project's own
    # profile.free.radial convention, like every other cross-part
    # clearance in this brief, rather than a bare literal touch. This
    # remains a conservative, honest simplification -- a flat plane where
    # the real part corrugates -- not an attempt to fabricate the
    # undetermined off-centre profile (see *Known simplifications* below).
    DECK_THICKNESS_NOMINAL = 2.000

    # Round 21 (finding RH1) -- the deck's own plan footprint is narrower
    # than the full housing envelope: the real shell narrows to the
    # inner-skin line above the end walls' own height (see END_WALL_Z_HI
    # below), so the deck top face spans only this asymmetric Y range (the
    # X half-width is unchanged -- it already matches WALL_X_OUTER_UPPER
    # exactly). Asymmetric because the housing's own Y frame is (latch end
    # at -Y, tongue end at +Y), matching the Cover's frame, not a
    # symmetric envelope.
    DECK_Y_LO = -32.000
    DECK_Y_HI = 33.200

    # --- Side walls (X-direction, stepped -- SS4) ---
    WALL_THICKNESS = 0.800
    WALL_STEP_Z = 22.000
    WALL_X_OUTER_LOWER = 28.000   # |X| outer face, Z < WALL_STEP_Z
    WALL_X_OUTER_UPPER = 27.200   # |X| outer face, Z >= WALL_STEP_Z

    # Round 21 (finding RH1) -- the latch-end and tongue-end walls (built by
    # _build_latch_wall / _build_tongue_wall) stop here, not at DECK_Z: the
    # real end walls span Z 0..24.000 mm; above that the shell narrows to
    # the deck's own (narrower) footprint (see DECK_Y_LO/DECK_Y_HI above).
    # The X-direction side walls (_build_side_wall) are unaffected -- they
    # already reach DECK_Z, and their own upper band already narrows in X
    # (WALL_X_OUTER_UPPER) at WALL_STEP_Z, matching the reference's own
    # narrowing there; only the two END walls were over-height.
    END_WALL_Z_HI = 24.000

    # --- Side windows, tapered (SS7.2, round 20 H3, round 21 RH3) ---
    WINDOW_Y_HALF = 12.000        # flat half-width, Z <= WINDOW_SHOULDER_Z
    WINDOW_SHOULDER_Z = 4.800     # where the ramped taper begins
    # Piecewise-linear taper, (z, half_width) pairs read directly off the
    # reference between WINDOW_SHOULDER_Z and the flat top (the last
    # entry). The real part's ramped-end trapezoid profile, corrected from
    # an earlier flat 16.0 mm rectangle (round 20), then re-corrected
    # round 21 (finding H3/RH3): `24851.dat` carries a genuine PLANAR face
    # at Z = 8.400 (26.9 mm^2, y +-8.400) -- not a point apex (round 20's
    # 8.500 mm figure replaced the reference's own flat top with one) --
    # and the taper at Z = 8.0 is 0.690 mm wider than round 20 built
    # (9.966 mm half-width, not 9.276). The last profile entry IS the flat
    # top's own edge (half-width 8.400 at Z = 8.400): the sweep below
    # connects it straight across to its own mirror instead of converging
    # to a point, reproducing the reference's flat 16.8 mm-wide top face.
    WINDOW_TAPER_PROFILE = ((6.000, 11.761), (8.000, 9.966), (8.400, 8.400))

    # --- Pin-hole / arm map (SS1, SS2) ---
    HOLE_X = 32.000
    HOLE_Y = (16.000, 24.000, 32.000)   # inner / middle / outer, one quadrant
    HOLE_AXIS_Z = 20.000
    ARM_THICKNESS = 8.000                # -> PerpendicularHolesLiftarm(thickness=...)
    ARM_Z_LO = HOLE_AXIS_Z - ARM_THICKNESS / 2   # 16.000
    ARM_Y_LO = 12.400                    # inboard flat face (envelope trim)
    ARM_Y_HI = HALF_Y                    # 35.600, outboard face

    # Real LDraw arm half-width (round 16, Escalation 7) -- the local-frame
    # Y bound the outboard width trim cuts above. Distinct from the class's
    # own Cailliau-calibrated BEAM_WIDTH/2 (3.9 mm); see
    # _build_arm_and_bore_local's width-trim comment.
    ARM_WIDTH_TRIM_Y = 3.600

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
    # (see _place_arm): local hole-line X positions (4/12/20, the class's
    # STUD_PITCH*i + STUD_PITCH/2 formula) must land on global Y = 16/24/32,
    # so the offset is 16 - 4 = 12 (NOT ARM_Y_LO=12.400 -- the envelope
    # trim at local X=0.400 is a *different* number from this hole-line
    # offset, and conflating them was an early implementation bug caught
    # by the cross-part verification probe).
    _ARM_Y_OFFSET = 12.0

    BOSS_DIAMETER = 7.200
    BOSS_PROUD = 0.400          # beyond the arm's own BEAM_WIDTH/2 edge, see docstring

    # Round 21 (finding H2/RH2) -- the arm-dish gap-opening circle radius,
    # centred at each inter-hole midpoint (not at any hole position) to
    # widen the dish's own plan footprint without disturbing the exact
    # R3.6 hole reliefs. See _dish_arm_faces's own docstring for the full
    # derivation and topology-safety note.
    _DISH_GAP_OPEN_RADIUS = 2.000
    MID_BORE_CB_DIAMETER = 6.400
    MID_BORE_CB_DEPTH = 0.800
    MID_BORE_DIAMETER = 4.800
    MID_BORE_GUIDED_LEN = 6.400
    MID_BORE_RELIEF_DIAMETER = 7.200
    _MID_BORE_BREAKTHROUGH = 15.0  # generous relief overcut, see _build_arms docstring

    # --- Latch end (-Y), SS5.2 / SS11 ---
    LATCH_Y = -HALF_Y
    LATCH_WALL_THICKNESS = 1.200
    LATCH_WINDOW_X_LO = 5.600
    LATCH_WINDOW_X_HI = 19.200
    LATCH_WINDOW_Z_HI = 3.600
    _LATCH_CATCH_Z_MARGIN = 3.0   # boss Z-band margin around the engagement band
    # Round 21 (finding E11-c (1)) -- the real part's own inner-skin depth
    # at the latch end; the catch boss retreats to this Y outside the barb
    # window (see _build_latch_catch), leaving y in [-34.4, leg] clear.
    _LATCH_CATCH_RETREAT_Y = -34.400

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

    # --- Post-fix hardening (TL round Q2's promoted constraint) ---
    _MIN_MATERIAL_BEHIND_UNDERCUT = 1.8  # mm, round-8 FDM precedent

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

        # Round 21, finding E11-a: the deck's underside clears the tray's
        # own top face (26.400 + Cover.PLATE_THICKNESS = 27.600 mm) by the
        # project's own running-clearance convention, not a bare literal
        # touch -- see DECK_THICKNESS_NOMINAL's own comment above.
        self._deck_thickness = self.DECK_THICKNESS_NOMINAL - prof.free.radial

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

        assert len(body.solids().vals()) == 1, "Expected single solid, got multiple pieces"
        return body

    # ------------------------------------------------------------------
    # Side walls (X-direction, stepped)
    # ------------------------------------------------------------------

    def _build_side_wall(self, x_sign: int) -> cq.Workplane:
        """One stepped side wall (SS4): 0.8 mm thick, full Y span, with the
        outward 0.8 mm step at :attr:`WALL_STEP_Z`.
        """
        lower = self._x_slab(
            x_sign, self.WALL_X_OUTER_LOWER, self.WALL_THICKNESS, 0.0, self.WALL_STEP_Z
        )
        # The upper band's outer face (27.2 mm) is numerically identical to
        # the lower band's *inner* face (28.0 - 0.8 = 27.2 mm) -- the two
        # slabs' X-extents are adjacent, sharing only the single line
        # X = 27.2 at Z = WALL_STEP_Z, not a 2D face or any 3D volume.
        # OCCT's boolean fuse does not merge solids that only touch along
        # an edge (this project's own "coincident faces" pitfall), so a
        # tiny construction-only overlap (widen the upper band's outer
        # face and drop its Z start slightly) is added here to guarantee
        # a genuine overlapping union -- the resulting 0.05 mm ledge
        # rounding is buried at the step corner, well under FDM tolerance.
        # **Correction (round 20, H5)**: an earlier version of this comment
        # claimed this "does not change any externally-visible dimension" --
        # it does: the upper band's outer face becomes 27.250 mm instead of
        # the nominal 27.200 mm, and that face IS the part's exterior
        # (435.7 mm^2 of externally-visible area). Accepted as sub-print-
        # resolution (0.050 mm), not a defect -- but the comment must not
        # claim it is invisible.
        overlap = 0.05
        upper = self._x_slab(
            x_sign,
            self.WALL_X_OUTER_UPPER + overlap,
            self.WALL_THICKNESS + overlap,
            self.WALL_STEP_Z - overlap,
            self.DECK_Z,
        )
        return lower.union(upper)

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

    def _build_side_window(self, x_sign: int) -> cq.Workplane:
        """Tab-access cutout through one side wall (SS7.2), a piecewise-
        linear taper matching the reference's ramped-end trapezoid profile
        (round 20, finding H3 -- corrected from an earlier flat-topped
        rectangle whose own comment mis-stated the peak height; see class
        docstring's *Known simplifications*).

        Built the same way :meth:`_build_latch_finger` builds its own
        swept cross-section: a closed polyline in the YZ plane (this
        window's Y/Z profile), extruded along X through the wall's full
        thickness (with a generous overcut so the cut breaks cleanly
        through both wall faces).
        """
        overcut = 1.0  # break cleanly through the wall's X extent
        x_outer = self.WALL_X_OUTER_LOWER + overcut
        x_inner = self.WALL_X_OUTER_LOWER - self.WALL_THICKNESS - overcut
        x_lo = x_sign * min(x_outer, x_inner)
        x_hi = x_sign * max(x_outer, x_inner)
        width = abs(x_hi - x_lo)

        # The last WINDOW_TAPER_PROFILE entry is the flat top's own edge
        # (round 21, RH3) -- connecting the forward taper's last point
        # straight across to the reversed taper's first point (the SAME
        # entry, mirrored) draws a flat top segment instead of converging
        # to a point apex, reproducing the reference's genuine planar face.
        half = self.WINDOW_Y_HALF
        pts = [(-half, 0.0), (-half, self.WINDOW_SHOULDER_Z)]
        for z, hw in self.WINDOW_TAPER_PROFILE:
            pts.append((-hw, z))
        for z, hw in reversed(self.WINDOW_TAPER_PROFILE):
            pts.append((hw, z))
        pts.append((half, self.WINDOW_SHOULDER_Z))
        pts.append((half, 0.0))

        sketch = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0.0, 0.0, min(x_lo, x_hi)))
            .moveTo(*pts[0])
        )
        for p in pts[1:]:
            sketch = sketch.lineTo(*p)
        return sketch.close().extrude(width)

    # ------------------------------------------------------------------
    # Top deck
    # ------------------------------------------------------------------

    def _build_top_deck(self) -> cq.Workplane:
        """Solid cap closing the top -- see class docstring's *Known
        simplifications* for why this is solid rather than a hollow shell.

        **Round 20 correction (finding H1, blocking)**: this slab spans
        ``Z`` in ``[DECK_Z - self._deck_thickness, DECK_Z]`` -- the real
        shell's own measured deck, sitting at and below its top face. The
        pre-round-20 version built this slab *above* ``DECK_Z`` (the
        retired ``TOP_Z = 33.800``), which put ~16,270 mm^3 (61% of the
        model's own volume) entirely outside the reference envelope -- see
        the class docstring's *Round 20 correction* note.

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
            height=self._deck_thickness,
            corner_r=0.0,
            center=(0.0, (self.DECK_Y_LO + self.DECK_Y_HI) / 2.0, self.DECK_Z - self._deck_thickness),
        )

    # ------------------------------------------------------------------
    # Arms (composed from PerpendicularHolesLiftarm, per the TL round)
    # ------------------------------------------------------------------

    def _dish_arm_faces(self, arm: cq.Workplane) -> cq.Workplane:
        """Shallow relief pocket on both faces (top and bottom) of the arm,
        between the pin-hole positions -- round 20, finding H2.

        Reference-derived numbers (``tmp/reference-comparison.md`` H2, read
        off LDraw's ``rect3.dat`` / ``1-4cyli.dat``): pocket floors at
        global ``Z = 21.378`` (top) / ``18.622`` (bottom) -- local
        ``Z = 5.378`` / ``2.622`` here, since ``global Z = local Z +
        ARM_Z_LO`` -- leaving a ``2.756 mm`` web at the pocket floor
        (``21.378 - 18.622``), footprint local ``Y`` in
        ``[-2.546, 2.546]`` (global ``X`` in ``[29.454, 34.546]``, centred
        on the hole axis ``X = 32``), blended into each hole/boss position
        by an ``R3.600 mm`` cylindrical relief centred on the hole axis.

        **Why a full-radius relief circle subtracted from the pocket
        cutter reproduces the reference's own numbers exactly, not just
        approximately** (the self-consistency check that grounds this
        construction, since the design brief explicitly delegates the
        exact cutter construction to the Developer): the relief radius
        (``R = BOSS_DIAMETER / 2 = 3.600 mm``) and the pocket half-width
        (``2.546 mm``) satisfy ``2.546 = 3.600 * cos(45 deg)`` -- i.e. the
        pocket rectangle's own Y-bound is exactly where a ``R3.6`` circle
        centred on the hole axis crosses at 45 degrees. Subtracting the
        union of three such circles (one per hole position, local
        ``X = 4/12/20``) from the rectangular pocket cutter therefore
        produces, at each end of the arm, a **full-thickness rail of
        exactly ``1.054 mm``** between the trim boundary (local
        ``X = 0.400`` / ``23.600``) and the nearest relief circle's own
        45-degree crossing (local ``X = 1.454`` / ``22.546``) -- matching
        the reference's own quoted "1.054 mm full-thickness edge rail at
        the arm's own perimeter" to the micron. This is strong evidence
        the construction below is not merely plausible but the actual
        geometric relationship LDraw's own polygon encodes.

        Developer-derived construction (not a literal re-derivation of
        LDraw's exact ``rect3.dat`` polygon) -- **verified via
        ``section_slicer.py --axis Y`` through one arm** before treating
        this as final, per the design brief's own instruction for
        genuinely new 3D relief features.

        **Round 21 correction (finding H2/RH2)**: the cross-section above
        (floors, rails, pocket walls) is confirmed exact and untouched.
        The *plan* footprint was wrong: with all three hole positions
        using the same ``R3.600`` relief circle, the two inter-hole gaps
        (8.0 mm hole pitch minus two ``R3.6`` reaches) were only
        ``8.0 - 2*3.6 = 0.8 mm`` wide -- reproducing the reference's own
        ``0.84 mm``-measured footprint almost exactly, but the reference's
        real gaps are ``~4.0 mm`` each. **Shrinking either hole's own
        R3.6 relief circle was tried and rejected**: at the two OUTER
        holes it would reopen the exact ``1.054 mm`` end rail derived
        above; at the MIDDLE hole (local ``X = 12``, the ``"none"``
        position) it disconnects the arm into multiple solids -- despite
        that position carrying no *vertical* pin bore, it is where the
        *horizontal* middle bore is later cut through (see
        :meth:`_build_arm_and_bore_local`), and that bore's own relief
        section is close enough in size to the R3.6 dish relief that
        shrinking the latter leaves an isolated post the bore then severs
        into two disconnected end-caps (caught by this class's own
        single-solid assert, not silently missed).

        **The construction that works**: leave all three ``R3.600``
        relief circles untouched, and additionally subtract two small,
        independent "gap-opening" circles of radius
        :attr:`_DISH_GAP_OPEN_RADIUS` (2.000 mm), centred at each
        inter-hole *midpoint* (local ``X = 8`` / ``16``, not at any hole
        centre) from the relief union before it protects the band -- i.e.
        the relief protects everything within R3.6 of a hole EXCEPT where
        a gap-opening circle also reaches. Centring the gap-opening
        circles away from the hole positions (rather than shrinking the
        hole-centred circles themselves) keeps full-radius material
        directly around every hole -- including the middle hole's own
        bore -- so this stays topologically safe (verified empirically:
        single-solid holds up to a gap-opening radius well past the value
        used here). The gap-opening circle's own diameter sets the open
        width directly (``2 * 2.000 = 4.000 mm``), independent of the
        flanking holes' own relief reach. Both reliefs stay plain circles
        (curved in plan -- the "curved blend, not vertical wall" spec for
        the pocket's own outer rim), so the boundary between recessed and
        full-thickness material is a circular arc everywhere, never a
        straight cut.
        """
        pocket_half_y = 2.546          # local Y -> global X in [29.454, 34.546]
        relief_radius = self.BOSS_DIAMETER / 2.0  # 3.600 mm, see docstring
        hole_x_locals = (4.0, 12.0, 20.0)  # the arm's own 3 hole/boss positions
        gap_x_locals = (8.0, 16.0)         # inter-hole midpoints, see docstring
        overcut = 0.05

        top_floor_local_z = 21.378 - self.ARM_Z_LO      # 5.378
        bottom_floor_local_z = 18.622 - self.ARM_Z_LO   # 2.622

        def _pocket(z_lo: float, z_hi: float) -> cq.Workplane:
            band = rounded_box(
                width=23.2, depth=2 * pocket_half_y, height=z_hi - z_lo,
                corner_r=0.0, center=(12.0, 0.0, z_lo),
            )
            relief = None
            for hx in hole_x_locals:
                cyl = cylinder(relief_radius, z_hi - z_lo, center=(hx, 0.0, z_lo))
                relief = cyl if relief is None else relief.union(cyl)
            gap_open = None
            for gx in gap_x_locals:
                cyl = cylinder(self._DISH_GAP_OPEN_RADIUS, z_hi - z_lo, center=(gx, 0.0, z_lo))
                gap_open = cyl if gap_open is None else gap_open.union(cyl)
            return band.cut(relief.cut(gap_open))

        top_pocket = _pocket(top_floor_local_z, self.ARM_THICKNESS + overcut)
        bottom_pocket = _pocket(-overcut, bottom_floor_local_z)
        return arm.cut(top_pocket).cut(bottom_pocket)

    def _build_arm_and_bore_local(self) -> tuple[cq.Workplane, cq.Workplane]:
        """Build the (+X, +Y)-quadrant arm and its middle-hole bore cutter,
        both still in the class's own **local** frame (X = length,
        Y = width, Z = thickness) -- i.e. *before* the diagonal-mirror
        remap into housing coordinates (see :meth:`_place_arm`).

        Per the TL round's decision (design brief *Reusable classes -> TL
        round -> Q1*), the shared class provides only the hole pattern,
        pitch, axis alternation, and the ``thickness``/``"none"`` knobs;
        the real arm's length (23.2 vs. the class's 24.0 mm), the
        middle-hole boss, and the three-step middle bore are all
        housing-local, composed here.
        """
        arm = PerpendicularHolesLiftarm(
            3, ["main", "none", "main"], profile=self._profile, thickness=self.ARM_THICKNESS
        ).solid

        # Envelope trim (TL round, Q1(c)): the class's own 4.0 mm end
        # offset (STUD_PITCH/2) leaves 0.4 mm of surplus end cap at each
        # end relative to the real 23.2 mm arm.  Hole centres are at local
        # X = 4/12/20 mapping to global Y = 16/24/32 with a +12 mm offset
        # (see _place_arm), so the real inboard/outboard faces
        # (Y = 12.400 / 35.600) land at local X = 0.400 / 23.600.  Neither
        # cut can clip a counterbore (outermost reaches local X = 23.1,
        # innermost 0.9 -- both inside the trim bounds), per the TL
        # round's own clearance derivation.
        trim_lo = rounded_box(width=20.0, depth=20.0, height=40.0, corner_r=0.0,
                               center=(-10.0, 0.0, -16.0))
        trim_hi = rounded_box(width=20.0, depth=20.0, height=40.0, corner_r=0.0,
                               center=(33.6, 0.0, -16.0))
        arm = arm.cut(trim_lo).cut(trim_hi)

        # Face dishing (round 20, H2) -- applied before the root bridge/
        # width trim/boss below, since none of those touch this pocket's
        # own local-Y band ([-2.546, 2.546], well clear of both the root
        # bridge's negative-Y reach and the boss/mid-bore's positive-Y
        # edge).
        arm = self._dish_arm_faces(arm)

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
            width=23.2,
            depth=root_outer_local_y - root_inner_local_y,
            height=self.ROOT_BAND_A_Z_HI - self.ROOT_BAND_A_Z_LO,
            corner_r=0.0,
            center=(
                12.0,
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
            width=23.2,
            depth=root_outer_local_y - root_b_inner_local_y,
            height=self.ROOT_BAND_A_Z_LO,  # local Z [0, ROOT_BAND_A_Z_LO], i.e. Band B
            corner_r=0.0,
            center=(12.0, (root_b_inner_local_y + root_outer_local_y) / 2.0, 0.0),
        )
        assert root_b_inner_local_y > root_inner_local_y, (
            "Band B's reach must stay shallower than Band A's own deeper "
            "reach (root_inner_local_y) -- growing Band B past that point "
            "re-approaches the pre-round-17 full-reach tray collision "
            "(Escalation 8) this two-band split exists to avoid."
        )
        arm = arm.union(root_b)

        # Width envelope trim (round 16, Escalation 7): the class's own
        # Cailliau-calibrated BEAM_WIDTH (7.8 mm, half-width 3.9 mm) puts
        # the arm's outboard face 0.3 mm past the real LDraw half-width
        # (3.6 mm), which this brief's Success Criterion #1 already pins
        # the housing's overall X envelope against exactly (72.0 mm) -- a
        # harder datum than the "not changed, deliberately" ruling that
        # keeps the class's own cross-section shape (see class docstring's
        # *Known simplifications*). One-sided cut on the outboard
        # (positive-local-y) side only, at local y > ARM_WIDTH_TRIM_Y.
        # Deliberately applied AFTER the root bridge above (which reads
        # BoundingBox().ymax as a proxy for the *inboard* edge's
        # magnitude, still the untrimmed 3.9 mm -- correct, since the
        # inboard/root-bridge side is untouched by this fix) and BEFORE
        # the boss/mid-bore code below (which reads beam_half_width off
        # this now-trimmed body, so it self-corrects to the real 3.6 mm
        # edge with no further changes -- design brief round 16, Conflict
        # 2 resolution). Trimming before the root-bridge read would
        # corrupt beam_half_width_pre's inboard magnitude to the wrong
        # (outboard-trimmed) value.
        trim_width_hi = rounded_box(
            width=40.0, depth=40.0, height=40.0, corner_r=0.0,
            center=(12.0, self.ARM_WIDTH_TRIM_Y + 20.0, -16.0),
        )
        arm = arm.cut(trim_width_hi)

        # Boss + middle bore, both anchored to the arm's own outboard edge
        # -- now the real LDraw 35.6/36.0 mm figures, not the class's own
        # BEAM_WIDTH/2, since the width trim above runs first (design
        # brief round 16, Conflict 2 resolution; see class docstring).
        # Built along local Z then rotated -90 deg about the X-axis, the
        # same "build along Z, rotate onto the width axis" technique
        # PerpendicularHolesLiftarm itself uses for its "perp" holes --
        # this maps local Z (stacking axis) -> local Y (width) and a
        # constant local y = -ARM_THICKNESS/2 -> local Z = +ARM_THICKNESS/2
        # (mid-thickness, the hole-axis height), confirmed empirically
        # (rotate(-90, X-axis) on the local-Z axis maps (y, z) -> (z, -y)).
        beam_half_width = arm.val().BoundingBox().ymax  # BEAM_WIDTH / 2, read from the body
        mid_z = self.ARM_THICKNESS / 2.0
        hole_x_local = 12.0  # "none" position (index 1): STUD_PITCH*1 + STUD_PITCH/2

        boss_overlap = 0.5  # clean union overlap into the arm's own edge
        boss = cylinder(
            self.BOSS_DIAMETER / 2.0,
            self.BOSS_PROUD + boss_overlap,
            center=(hole_x_local, -mid_z, beam_half_width - boss_overlap),
        ).rotate((0, 0, 0), (1, 0, 0), -90)
        arm = arm.union(boss)

        boss_tip = beam_half_width + self.BOSS_PROUD
        entry_overcut = 0.05
        y_mouth = boss_tip + entry_overcut
        y_cb_inner = y_mouth - (self.MID_BORE_CB_DEPTH + entry_overcut)
        y_guided_inner = y_cb_inner - self.MID_BORE_GUIDED_LEN
        y_relief_inner = y_guided_inner - self._MID_BORE_BREAKTHROUGH

        def _seg(diameter: float, y_lo: float, y_hi: float) -> cq.Workplane:
            return cylinder(diameter / 2.0, y_hi - y_lo, center=(hole_x_local, -mid_z, y_lo))

        bore = (
            _seg(self.MID_BORE_CB_DIAMETER, y_cb_inner, y_mouth)
            .union(_seg(self.MID_BORE_DIAMETER, y_guided_inner, y_cb_inner))
            .union(_seg(self.MID_BORE_RELIEF_DIAMETER, y_relief_inner, y_guided_inner))
        ).rotate((0, 0, 0), (1, 0, 0), -90)

        assert len(arm.solids().vals()) == 1, "Expected single solid, got multiple pieces"
        return arm, bore

    def _place_arm(
        self, arm_local: cq.Workplane, bore_local: cq.Workplane, x_sign: int, y_sign: int
    ) -> tuple[cq.Workplane, cq.Workplane]:
        """Map the (+X, +Y)-quadrant arm/bore into one of the four housing
        quadrants.

        The local -> global remap swaps X and Y (length <-> width, since
        the arm's *length* runs along housing Y while its *width* runs
        along housing X, per ``tmp/ldraw-housing-geometry.md`` SS3.0) --
        an axis swap is a reflection (determinant -1), not achievable by
        any pure rotation, so it is done via ``mirror(mirrorPlane=(1,-1,0))``
        (reflection through the Y = X plane, confirmed empirically to map
        ``(x, y, z) -> (y, x, z)``), followed by the ``(+32, +12, +16)``
        translation that centres hole positions on ``X = 32`` and the
        ``["main", "none", "main"]`` local hole line (X = 4/12/20) on
        ``Y = 16/24/32``.  The other three quadrants are then reached by
        ordinary axis mirrors (no further swap needed, since the arm
        geometry has no handedness -- ``tmp/ldraw-housing-geometry.md``
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
        # DECK_Z (29.600 mm) -- the real end wall stops there; above it the
        # shell narrows to the (unaffected) X-direction side walls' own
        # upper band and the deck's own narrower footprint (see class
        # docstring's *Known simplifications* -> *End-wall Z extent*).
        base = self._y_slab(
            self.LATCH_Y, self.LATCH_WALL_THICKNESS, 0.0, self.END_WALL_Z_HI, inward=True
        )
        base = base.cut(self._build_finger_windows())

        for side in (+1, -1):
            boss, pocket, nub = self._build_latch_catch(side)
            base = base.union(boss)
            base = base.cut(pocket)
            # The keeper nub MUST be unioned back in AFTER the slot cut --
            # it sits inside the slot's own footprint by construction (see
            # _build_latch_catch's docstring), so applying it before the
            # cut would just have the slot cutter remove it again.
            base = base.union(nub)

        assert len(base.solids().vals()) == 1, "Expected single solid, got multiple pieces"
        return base

    def _build_finger_windows(self) -> cq.Workplane:
        overcut = 1.0
        y_lo = self.LATCH_Y - overcut
        y_hi = self.LATCH_Y + self.LATCH_WALL_THICKNESS + overcut
        windows = None
        for side in (+1, -1):
            x_lo = side * self.LATCH_WINDOW_X_LO
            x_hi = side * self.LATCH_WINDOW_X_HI
            win = rounded_box(
                width=abs(x_hi - x_lo),
                depth=y_hi - y_lo,
                height=self.LATCH_WINDOW_Z_HI,
                corner_r=0.0,
                center=((x_lo + x_hi) / 2.0, (y_lo + y_hi) / 2.0, 0.0),
            )
            windows = win if windows is None else windows.union(win)
        return windows

    def _build_latch_catch(self, side: int) -> tuple[cq.Workplane, cq.Workplane, cq.Workplane]:
        """One latch-end catch: ``(boss, slot, nub)`` -- the finger-
        clearance boss, its undercut slot cutter, and the round-18
        retention keeper nub that re-adds solid material inside the slot's
        own footprint after the slot cut runs (caller order matters: union
        boss, cut slot, THEN union nub -- see :meth:`_build_latch_wall`).
        Derived from :class:`PoweredUpHubCover`'s own barb geometry per the
        design brief's *Latch catch -- derived design* section and the
        class docstring's *Latch catch derivation* note.

        Cross-part verification (a static boolean intersection of the
        built :class:`PoweredUpHubCover` against this class) caught an
        earlier version of this method: it built a *solid* boss reaching
        only to the barb's own crest position (``HOOK_FACE_Y1 +
        barb_protrusion``), which collides with the finger's own **drafted
        face** -- the finger's rigid body is *not* a thin wire at the
        crest, it is a wedge whose drafted face reaches ``HOOK_FACE_Y1``
        (deeper / more outboard than the crest) across the whole
        engagement-band height.  The fix models the catch as a genuine
        **slot**, not a pocket cut into an otherwise-solid boss:
        finger-clearance is a rectangular cut sized to the finger's own
        worst-case (deepest) reach across the engagement band, with the
        **undercut** measured from that same worst-case reach (not from
        the crest) -- so retention depth is real material *behind* the
        finger's own natural shape, verified interference-free by
        construction.  The **retention ledge** falls out for free: the
        boss stays solid for ``Z > engagement_band_hi`` (the finger has no
        material above its own ``hook_depth`` there), forming a shelf the
        barb cannot rise past without deflecting.
        """
        lg: LatchGeometry = self._latch

        clearance = self._profile.free.radial  # running clearance, not a retention surface
        y_slot_inner = PoweredUpHubCover.PLATE_Y_LO + clearance
        y_slot_outer = PoweredUpHubCover.HOOK_FACE_Y1 - clearance - lg.undercut_depth

        local_wall = y_slot_outer - self.LATCH_Y  # material behind the pocket's deepest point
        assert local_wall >= self._MIN_MATERIAL_BEHIND_UNDERCUT, (
            f"Latch catch local wall ({local_wall:.3f} mm) is thinner than the "
            f"undercut-depth-sets-a-floor rule requires "
            f"({self._MIN_MATERIAL_BEHIND_UNDERCUT:.3f} mm) -- "
            f"see the design brief's 'The wall-thickness conflict' section."
        )

        x_center = side * (lg.hook_pitch / 2.0 + lg.hook_width / 2.0)

        # Boss: local thickening from the outer face out to y_slot_inner
        # (past where the barb needs to reach), confined to the hook's own
        # X footprint and a Z band bracketing the engagement band with
        # margin for the finger's drafted face above/below it.
        z_lo = lg.engagement_band_lo - self._LATCH_CATCH_Z_MARGIN
        z_hi = lg.engagement_band_hi + self._LATCH_CATCH_Z_MARGIN

        # Round 21 (finding E11-c (1)): the boss used to reach y_slot_inner
        # across the WHOLE [z_lo, z_hi] band. The round-20 release-leg
        # correction (C1-C3) now places the leg's own material exactly in
        # the Y-band this boss's outer portion (behind the undercut, i.e.
        # material the slot cut below does NOT remove) occupies below the
        # barb -- 21.324 mm^3 of new interference, root-caused to this
        # class's own round-14 single-wall departure (the real part's inner
        # skin leaves y [-34.4, -32.0] clear for exactly this leg).
        # Z-banded retreat, matching round 18's original "Z-localised
        # keeper nub" recommendation: OUTSIDE a tight window bracketing
        # the barb (engagement_band_lo..hi -- the barb's own physical
        # extent, not an arbitrary margin), cap the reach at
        # _LATCH_CATCH_RETREAT_Y (-34.400 mm, the reference's own
        # inner-skin depth, not an arbitrary retreat) instead of
        # y_slot_inner -- leaving y in [-34.4, leg's own position] clear.
        # INSIDE the window, retain the full y_slot_inner reach (the slot
        # cut below still removes finger clearance regardless; keeping the
        # boss at full depth there is what feeds the undercut-depth-sets-
        # a-floor assert its required backing). Above engagement_band_hi
        # (the retention-ledge band, z_hi's own upper portion) also keeps
        # full reach, unaffected -- that band never appeared in the
        # measured collision.
        seam = 0.05  # coincident-faces guard between adjacent Z bands
        retreat_y = self._LATCH_CATCH_RETREAT_Y
        boss_below_window = rounded_box(
            width=lg.hook_width,
            depth=retreat_y - self.LATCH_Y,
            height=(lg.engagement_band_lo + seam) - z_lo,
            corner_r=0.0,
            center=(x_center, (self.LATCH_Y + retreat_y) / 2.0, z_lo),
        )
        boss_window_and_ledge = rounded_box(
            width=lg.hook_width,
            depth=y_slot_inner - self.LATCH_Y,
            height=z_hi - (lg.engagement_band_lo - seam),
            corner_r=0.0,
            center=(x_center, (self.LATCH_Y + y_slot_inner) / 2.0, lg.engagement_band_lo - seam),
        )
        boss = boss_below_window.union(boss_window_and_ledge)

        # Slot: clears the finger's full swept cross-section across the
        # engagement band and provides the undercut depth behind its
        # deepest (drafted-face) reach.  Bounded to
        # [engagement_band_lo - margin, engagement_band_hi] so the boss
        # stays solid above engagement_band_hi, forming the retention
        # ledge (see method docstring) -- the finger has zero material
        # above its own hook_depth, so this cannot interfere with it.
        #
        # Width uses hook_width, NOT the narrower catch_width: the
        # finger's own extrusion spans its full hook_width (13.6 mm), so
        # a catch_width-wide slot (13.3 mm, per LatchGeometry's own
        # "clear the hook's side walls without rubbing" formula) leaves a
        # ~0.15 mm boss sliver at each X edge that collides with the
        # finger there -- caught by the cross-part verification probe.
        # catch_width remains available on the shared LatchGeometry object
        # for any future lateral-guide refinement; it is not applied here.
        slot = rounded_box(
            width=lg.hook_width,
            depth=y_slot_inner - y_slot_outer,
            height=lg.engagement_band_hi - z_lo,
            corner_r=0.0,
            center=(x_center, (y_slot_outer + y_slot_inner) / 2.0, z_lo),
        )

        # Retention keeper nub (round 18, B1 -- the actual fix): before this,
        # y_slot_inner bounded BOTH the boss and the slot, so no material
        # ever separated the "deflection pocket" side of the slot from the
        # finger's own root -- zero retention (audit findings B1/S4).
        #
        # y_lip is derived from the corrected LatchGeometry.barb_protrusion
        # (see that module's own docstring) via PoweredUpHubCover's own
        # HOOK_FACE_Y1 -- crest_y_relaxed = HOOK_FACE_Y1 + barb_protrusion
        # (the barb's undeflected resting Y), then y_lip = crest_y_relaxed
        # - lg.undercut_depth. The nub re-adds solid material across
        # Y in [y_lip, y_slot_inner] -- the sub-band of the slot closest to
        # the finger's own root -- while Y in [y_slot_outer, y_lip] stays
        # open as the barb's deflection pocket (retreat room). Z-localised
        # tightly around barb_axis_z (NOT the full engagement band) per the
        # design brief's own explicit warning: a full-band lip re-collides
        # with the finger's drafted-face flanks near Z = engagement_band_lo
        # / _hi, which is exactly the round-14->15 regression this slot
        # topology was rebuilt to avoid. The nub's Z half-width is kept at
        # the lip Y depth's own natural taper: solving where the finger's
        # own drafted-face polyline crosses Y = y_lip on each side of
        # barb_axis_z bounds how far the nub can safely reach in Z before
        # colliding with material the finger has at ITS OWN root-ward
        # (non-deflected) position -- verified empirically via
        # section_slicer.py and the mandatory kinematic-sweep tests below,
        # not hand-derived blind (see the design brief's own instruction).
        crest_y_relaxed = PoweredUpHubCover.HOOK_FACE_Y1 + lg.barb_protrusion
        y_lip = crest_y_relaxed - lg.undercut_depth

        # The nub's Y-span [y_lip, y_slot_inner] never touches the slot's
        # own outboard remainder of `boss` (Y <= y_slot_outer) -- that gap
        # (Y in [y_slot_outer, y_lip]) is the deflection pocket, and must
        # stay open. So the nub is instead connected in Z: its top edge
        # reaches (with a coincident-faces overlap) into
        # engagement_band_hi, where `boss` is still solid across its own
        # full Y-span (the slot cutter's own height stops at
        # engagement_band_hi -- see the slot's own height above) -- this is
        # the existing "retention ledge" the class docstring already
        # describes, and the nub fuses directly onto its underside rather
        # than floating disconnected in space.
        nub_reach = 0.500  # how far below engagement_band_hi the nub extends
        seam_overlap = 0.05
        nub_z_lo = lg.engagement_band_hi - nub_reach
        nub_z_hi = lg.engagement_band_hi + seam_overlap
        nub = rounded_box(
            width=lg.hook_width,
            depth=y_slot_inner - y_lip,
            height=nub_z_hi - nub_z_lo,
            corner_r=0.0,
            center=(x_center, (y_lip + y_slot_inner) / 2.0, nub_z_lo),
        )

        return boss, slot, nub

    # ------------------------------------------------------------------
    # Tongue-end wall (+Y) -- single wall, rebate step only
    # ------------------------------------------------------------------

    def _build_tongue_wall(self) -> cq.Workplane:
        lower = self._y_slab(
            self.TONGUE_Y,
            self.TONGUE_Y - self.TONGUE_INNER_Y_LOWER,
            0.0,
            self.TONGUE_STEP_Z,
            inward=False,
        )
        # Round 21 (finding RH1): capped at END_WALL_Z_HI, not DECK_Z --
        # see _build_latch_wall's own comment for the shared rationale.
        upper = self._y_slab(
            self.TONGUE_Y,
            self.TONGUE_Y - self._tongue_inner_y_upper,
            self.TONGUE_STEP_Z,
            self.END_WALL_Z_HI,
            inward=False,
        )
        return lower.union(upper)

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
