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

Per that design, this is an exact copy of the real ``25560`` shell
(``72.0 x 71.2 x 33.8 mm``) with a scoped, deliberate departure at the two
lid-retention regions only: the latch end (``-Y``) and the tongue end
(``+Y``) each carry a single wall instead of LEGO's real two-skin
sandwich construction, per the design's *Single wall at BOTH ends*
section.  Everything else -- overall envelope, the four liftarm arms, the
twelve pin holes, the wall step at height 22.0 mm, the side windows, the
port ribs -- is an exact copy.
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
    there, up to :attr:`TOP_Z` (33.800 mm). X is centred on the housing's
    mid-width (hole plane at ``X = +-32.000``); Y follows the same frame as
    the Cover (latch end at ``-Y``, tongue end at ``+Y``).

    Kept, as an exact copy (design brief *Housing*):
        - Overall envelope 72.0 x 71.2 x 33.8 mm (with the arm bosses
          included in the 72.0 mm X figure).
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
        - **Top deck** modelled as a solid slab (:attr:`DECK_Z` to
          :attr:`TOP_Z`) rather than a hollow shell -- the real deck's
          thickness is genuinely unreadable from LDraw (no underside face
          modelled anywhere in the part chain), so a solid cap is the
          conservative choice, not a guess at an unknown wall thickness.
          The corrugated AA-cell cradle ceiling, the four connector-port
          keying ribs, and the one asymmetric screw boss on the deck are
          all omitted -- purely cosmetic/non-interface features, per the
          design brief's own "Explicitly NOT decided by this TL round"
          note leaving the middle-hole neck relief as a Designer/Developer
          fidelity call (also omitted here for the same reason).
        - **Side windows** simplified from LDraw's ramped-end trapezoid
          profile to a single flat-topped rectangular cutout, using the
          more generous of the two profile's heights (16.0 mm, the ramped
          ends' peak) -- this only ever removes *more* material than the
          real part, never less, so it cannot introduce an unintended
          interference. **Re-verified round 18 (finding C4)**: this
          simplification was previously *masking*
          :class:`~vibe_cading.lego_adapters.poweredup_hub.battery_tray.PoweredUpHubBatteryTray`'s
          S2 Z-datum error (the tab ledge would not have passed the real,
          ramped window profile) -- now that S2 is corrected, the tab
          ledge's real Z-band clears this flat 16.0 mm window with margin
          to spare (re-confirmed by the cross-part tests below), so the
          masking relationship is now moot rather than live.
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
        - **End-wall Z extent** (latch and tongue walls) built full-height,
          ``Z`` in ``[0, DECK_Z]`` (``0..29.6 mm``), rather than the real
          part's own, shorter two-skin sandwich extent (``3.6..22.0 mm``
          per ``tmp/ldraw-housing-geometry.md``) -- round 18, finding C3.
          Additive-only (never removes material the real part has), and
          this class's own single-wall departure already scopes the
          latch/tongue ends away from an exact copy (see *Single wall at
          BOTH ends* above), so the extra height is harmless, not a new
          interference risk -- declared here per this project's
          Experimental Integrity convention rather than left silent.
        - **Arm cross-section** stays at the class's own
          Cailliau-calibrated ``BEAM_WIDTH`` (7.8 mm, vs. LDraw's
          idealised 7.2 mm) -- the design brief's explicit "not changed,
          deliberately" ruling (real moulded liftarms measure 7.4-7.8 mm;
          LDraw's 7.2 mm is a grid-snapped idealisation) still governs the
          shared :class:`PerpendicularHolesLiftarm` class itself, and the
          arm's *root* region (root-bridge/wall-overlap logic, hidden
          internal structure) still reads the class's own untrimmed
          ``BEAM_WIDTH / 2`` edge. **The outboard edge is a documented
          exception** (design brief round 16, Escalation 7): because
          Success Criterion #1 already pins the housing's overall X
          envelope to exactly ``72.0 mm``, a housing-local, one-sided
          ``.cut()`` trims the arm's outboard face to LDraw's literal
          ``3.600 mm`` half-width before the boss/middle-bore code reads
          it -- so the boss and middle bore land at the real
          ``35.6/36.0 mm`` figures, not the class's own ``3.9 mm``
          Cailliau half-width, on this one (outboard) edge only.

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
    TOP_Z = 33.800
    DECK_Z = 29.600

    # --- Side walls (X-direction, stepped -- SS4) ---
    WALL_THICKNESS = 0.800
    WALL_STEP_Z = 22.000
    WALL_X_OUTER_LOWER = 28.000   # |X| outer face, Z < WALL_STEP_Z
    WALL_X_OUTER_UPPER = 27.200   # |X| outer face, Z >= WALL_STEP_Z

    # --- Side windows, simplified (SS7.2) ---
    WINDOW_Y_HALF = 12.400
    WINDOW_Z_HI = 16.000  # simplified to the ramped ends' peak, see docstring

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
    # window (thickness axis, pre-_place_arm) where the root bridge still
    # reaches the wall. Local Z in [ROOT_BAND_A_Z_LO, ARM_THICKNESS] maps
    # to global Z in [WALL_STEP_Z, TOP_Z] (both ends via the +ARM_Z_LO
    # offset _place_arm applies), i.e. exactly the wall's upper band.
    # Below ROOT_BAND_A_Z_LO (Band B, global Z in [ARM_Z_LO, WALL_STEP_Z],
    # the wall's lower band -- where the tray's own wall sits) no bridge
    # material is added at all; see _build_arm_and_bore_local's own
    # comment for the full derivation and the ~85.8 mm^3 margin proving
    # Band A alone still fuses the arm to the wall.
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
        # rounding is buried at the step corner, well under FDM
        # tolerance, and does not change any externally-visible dimension.
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
        """Tab-access cutout through one side wall (SS7.2, simplified --
        see class docstring).
        """
        overcut = 1.0  # break cleanly through the wall's X extent
        x_outer = self.WALL_X_OUTER_LOWER + overcut
        x_inner = self.WALL_X_OUTER_LOWER - self.WALL_THICKNESS - overcut
        x_lo = x_sign * min(x_outer, x_inner)
        x_hi = x_sign * max(x_outer, x_inner)
        return rounded_box(
            width=abs(x_hi - x_lo),
            depth=2 * self.WINDOW_Y_HALF,
            height=self.WINDOW_Z_HI,
            corner_r=0.0,
            center=((x_lo + x_hi) / 2.0, 0.0, 0.0),
        )

    # ------------------------------------------------------------------
    # Top deck
    # ------------------------------------------------------------------

    def _build_top_deck(self) -> cq.Workplane:
        """Solid cap closing the top -- see class docstring's *Known
        simplifications* for why this is solid rather than a hollow shell.
        """
        return rounded_box(
            width=2 * self.WALL_X_OUTER_UPPER,
            depth=2 * self.HALF_Y,
            height=self.TOP_Z - self.DECK_Z,
            corner_r=0.0,
            center=(0.0, 0.0, self.DECK_Z),
        )

    # ------------------------------------------------------------------
    # Arms (composed from PerpendicularHolesLiftarm, per the TL round)
    # ------------------------------------------------------------------

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
        # the lower wall band, where the tray's wall sits): NO bridge box
        # at all. The arm's own trimmed edge is left as-is; nothing here
        # reaches toward the wall, so this band cannot collide with the
        # tray (interference goes to exactly 0.0 mm^3, not a reduced
        # figure). This does not disconnect the arm: Band A and Band B
        # (where present) share one continuous solid via ordinary Z-
        # continuity of the arm body itself, not via bridge material
        # duplicated at every Z -- the original single-band bridge never
        # required that either.
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
        # Band A) without re-deriving that margin, or Band B regrows a
        # wall-reaching extension without re-deriving the tray-clearance
        # argument, the guard below fails loudly instead of silently
        # reopening either defect.
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
        base = self._y_slab(
            self.LATCH_Y, self.LATCH_WALL_THICKNESS, 0.0, self.DECK_Z, inward=True
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
        boss = rounded_box(
            width=lg.hook_width,
            depth=y_slot_inner - self.LATCH_Y,
            height=z_hi - z_lo,
            corner_r=0.0,
            center=(x_center, (self.LATCH_Y + y_slot_inner) / 2.0, z_lo),
        )

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
        upper = self._y_slab(
            self.TONGUE_Y,
            self.TONGUE_Y - self._tongue_inner_y_upper,
            self.TONGUE_STEP_Z,
            self.DECK_Z,
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
