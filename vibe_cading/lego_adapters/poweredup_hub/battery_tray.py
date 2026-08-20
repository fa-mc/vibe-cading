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

"""PoweredUpHubBatteryTray -- battery cradle for the Powered Up hub battery box.

Dimensions are read from the LDraw parts library (CC BY 4.0, author
Philippe Hurbain) part ``24849`` / ``24849c01`` ("Electric Technic Battery
Holder Cover" / its contact-bearing variant), as extracted in
``tmp/ldraw-parts-geometry.md`` SS2 (git-ignored; no LDraw ``.dat`` file,
converted geometry, or render is committed to this repo -- only
independently-written measurements and from-scratch CadQuery code). Full
design rationale:
``docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md``,
*Multi-part structure -> Battery tray*.

The real part's own LDraw comment (``// Internal structure is simplified``)
scopes its *whole* part -- reliable only for the outer envelope, wall
thicknesses, the side extraction tabs, the end walls, rim/frame positions,
and the 14.4 mm cell pitch / 51.2 mm bay length. Per that design, this class
sizes nothing off the unreliable (simplified) regions: the corrugated shelf,
cell dividers, and side stiffener plates are deleted outright (not
re-measured), and the new floor / strap holders are sized against the
Spektrum SPMX812SH2 pack's own confirmed dimensions, not against the
tray's simplified internal geometry.
"""

from __future__ import annotations

import cadquery as cq

from vibe_cading.cq_utils import rounded_box
from vibe_cading.lego_adapters.poweredup_hub.cover import PoweredUpHubCover
from vibe_cading.print_settings import ToleranceProfile, get_profile


class PoweredUpHubBatteryTray:
    """Battery cradle repurposed from LEGO tray ``24849`` for a 2S LiPo pack.

    Origin / datum
    ---------------
    ``(0, 0, 0)`` is the tray's **bottom face** -- the physical mating datum
    where it seats against the
    :class:`~vibe_cading.lego_adapters.poweredup_hub.cover.PoweredUpHubCover`'s
    inner face (or, in the future ``HousingBox`` assembly, the housing's
    interior floor -- not built here). Every feature extrudes ``+Z``. X is
    centred on the tray's mid-width; Y follows the real tray's own frame
    (matching the Cover's Y convention, since both share one LDraw parent
    frame per ``tmp/ldraw-parts-geometry.md`` SS0): the ``-Y`` end wall sits
    near the Cover's latch end, the ``+Y`` end wall near the Cover's tongue
    end.

    Wall enumeration and the removal decision (design brief, round 13
    resolution -- the inverse of the literal "front and end" reading):
        - Both **outer end walls are KEPT**, nominally at ``-30.400..
          -28.800`` mm (``-Y``) and ``29.200..30.800`` mm (``+Y``), each
          1.600 mm thick (``+Y`` simplified to a uniform 1.600 mm rather
          than the real part's 29.200/29.600 mm stepped inner face -- see
          *Known simplifications*). The ``-Y`` wall additionally carries
          :attr:`RELIEF` (see below, round 18 B3(b)) -- both its faces
          shift ``-Y`` together, so its *nominal* position above is not
          its as-built position; see :meth:`__init__`.
        - Both **internal transverse partitions are REMOVED** (they, not
          the end walls, bound the 51.2 mm cell bay -- removing only them
          gives the exact 58.000 mm clear length the 58 mm pack needs).
        - Both **longitudinal side walls are KEPT**, 0.800 mm thick, with
          their extraction tabs intact (K5).
        - The **corrugated shelf**, the **4 longitudinal cell dividers**,
          the **2 electrical contacts**, and the **side stiffener plates**
          (which intrude into the pack's own volume) are all REMOVED.

    Because 58.000 mm of clear length against a 58 mm pack is zero-slack,
    :attr:`RELIEF` (1.5 mm, within the design's stated 1-2 mm range) is
    added to the ``-Y`` end wall -- both its inner AND outer face shift
    ``-Y`` together, so the wall keeps its full 1.6 mm thickness (a
    structurally sound extension of the tray's own footprint) rather than
    locally thinning the wall to a fraction of a millimetre (which a
    same-thickness inner-face-only pocket would do, and which this
    Developer judged unprintable -- see *Known simplifications*).
    **Side corrected round 18 (B3(b))**: an earlier version applied the
    relief to the ``+Y`` wall instead, which drove it straight into
    :class:`~vibe_cading.lego_adapters.poweredup_hub.cover.PoweredUpHubCover`'s
    own tongue riser (``14.976 mm^3`` of hard overlap in the seated
    assembly) -- the ``-Y`` end has no equivalent rigid riser to collide
    with at this tray's height band.

    New features (design brief, not LEGO-derived):
        - **Floor**, raised on :attr:`FLOOR_STANDOFF` (round 18, S5 --
          corrected from an earlier flush-to-the-rim floor that left zero
          routing clearance beneath it), spanning the tray's full interior
          cavity -- the real part has none (only a ~10 % peripheral rim,
          per ``tmp/ldraw-parts-geometry.md`` SS2.6). The standoff opens a
          crawl-space between the floor's underside and the tray's own
          bottom rim (which, once seated in ``assemble()``, is the Cover's
          own inner face) big enough for a strap to route through.
        - **Strap holders**: two full-through slots in the floor, each
          ``STRAP_WIDTH`` (20.5 mm, the round-8-confirmed opening for a
          20 mm strap) wide, positioned symmetrically about the tray's own
          Y-centre -- a strap can now pass down through one slot, under
          the raised floor, and back up through the other.

    Known simplifications (documented deviations, all cosmetic /
    non-load-bearing unless noted):
        - The ``+Y`` end wall's real stepped inner face (29.200 mm for the
          lower compartment, 29.600 mm for the upper) is simplified to a
          single uniform inner face at 29.200 mm (before relief) -- the
          more generous of the two, so this only ever *adds* clear volume,
          never removes it.
        - The tray's real vertical wall/top-frame transition (plain wall to
          22.400 mm, a separate top-frame feature at 27.600/28.000 mm,
          figures quoted in the LDraw table's own lid-face-relative frame)
          is simplified to one wall extruded straight to :attr:`WALL_Z_HI`
          (26.400 mm in this class's own bottom-rim-relative frame --
          corrected round 18, S2, from an earlier 28.000 mm that had been
          transcribed directly off the LDraw table without re-basing it)
          -- structurally equivalent, and the real transition is a
          cosmetic frame detail, not a mating surface. **Not uniform
          in X**, though: above :attr:`WALL_STEP_Z` the wall steps inward
          to clear :class:`~vibe_cading.lego_adapters.poweredup_hub.housing.PoweredUpHubHousing`'s
          own real wall step -- a functional (interference-avoiding), not
          cosmetic, departure from the original uniform-wall
          simplification -- see :attr:`WALL_STEP_Z`'s own comment and
          design brief round 16, Escalation 5.
        - The ``+Z`` guide rails (K6) and the top-outer-corner rounds
          (R1.600) are not modelled -- both are secondary LEGO-to-LEGO
          engagement/cosmetic features with no role in the LiPo-pack /
          strap retention this repurposed tray now serves.
        - The extraction tabs' R3.600 mm corner rounds and the recessed
          quarter-round detail in the finger ledge are not modelled -- the
          tabs' functional envelope (pad/ledge proud-ness, grip ribs) is
          fully preserved; only the corner cosmetics are simplified.
        - **Relief placement, corrected round 18 (B3(b))** -- the design
          brief originally left "not yet which one" open; this Developer's
          first choice (``+Y``) collided with the Cover's tongue riser, so
          the Designer's round-18 ruling moved it to the ``-Y`` (latch-end)
          wall instead. Applied there only.
        - **Strap thickness is an explicit open assumption**
          (:attr:`STRAP_THICKNESS_ASSUMED` = 1.8 mm, the midpoint of the
          design's stated 1.5-2 mm range) -- flagged per the task brief,
          not a measured or user-confirmed value like :attr:`STRAP_WIDTH`.

    Parameters
    ----------
    profile:
        Manufacturing tolerance profile, applied to the strap-holder slots'
        running clearance (``profile.free.radial``) and to the upper wall
        band's outer-face clearance off Housing's own inner face (also
        ``profile.free.radial`` -- see :attr:`WALL_STEP_Z`). Accepts a
        :class:`~vibe_cading.print_settings.ToleranceProfile` instance, a
        profile name string, or ``None`` for the process-global default.
    """

    # --- Outer shell (SS2.2) ---
    WALL_OUTER_X = 27.200
    WALL_INNER_X = 26.400
    # Corrected round 18 (S2, -1.600 mm) -- was 28.000 mm, transcribed
    # directly off the LDraw table's lid-face-relative Z = 0; see the side
    # extraction tabs' own comment above for the full datum-frame reasoning.
    WALL_Z_HI = 26.400  # simplified uniform wall height, see docstring

    # --- Upper-band wall step (round 16, Escalation 5) ---
    # Housing's own real inner-cavity wall (housing.py WALL_STEP_Z = 22.000,
    # world Z) steps inward at that height, and the tray's own Z=0 datum
    # sits 1.200 mm below world Z (seated on the Cover's PLATE_THICKNESS),
    # so the housing step maps to this tray's own local Z = 22.000 - 1.200
    # = 20.800 mm. Above that local Z, the tray's wall (previously uniform
    # 27.200/26.400 mm the whole height) numerically overlapped Housing's
    # own upper-band wall material (26.400-27.200 mm) -- a 960.4 mm^3
    # interference, not mere tight clearance. Fix: step the tray's own
    # wall inward by the same 0.800 mm Housing itself steps by, so the
    # upper band sits flush inside Housing's own upper-band inner face
    # (26.400 mm) instead of on top of its wall.
    WALL_STEP_Z = 20.800
    WALL_OUTER_X_UPPER_NOMINAL = 26.400  # before the profile clearance gap, see __init__
    WALL_INNER_X_UPPER = 25.600

    # --- End walls (kept, SS2.2) ---
    END_WALL_NEG_Y_LO = -30.400
    END_WALL_NEG_Y_HI = -28.800
    END_WALL_POS_Y_LO_NOMINAL = 29.200  # simplified to the lower (more generous) face
    END_WALL_POS_Y_HI_NOMINAL = 30.800

    # --- Relief (round-13 "1-2 mm" requirement, developer's choice of
    # magnitude; round-18 B3(b) corrected the SIDE) ---
    # Applied to the -Y (latch-end) wall, not +Y (tongue-end): the audit
    # found +Y placement drove the wall straight into
    # PoweredUpHubCover's own tongue riser (Y in [32.00, 32.30], Z in
    # [1.20, 2.80]) -- 14.976 mm^3 of hard overlap (design brief round 18,
    # B3). The -Y end has no equivalent rigid riser at the tray's height
    # band to collide with.
    RELIEF = 1.5

    # --- Side extraction tabs, KEPT exactly per envelope (SS2.3) ---
    # Z bands corrected round 18 (S2, -1.600 mm from every 24849-derived Z
    # constant): tmp/ldraw-parts-geometry.md SS0 states 24849's own Z = 0 is
    # the LID's outer face, with the tray's own physical structure (bottom
    # rim) starting 1.600 mm above that -- but this class's Z = 0 is its OWN
    # bottom rim (see class docstring's *Origin / datum*), so every Z value
    # transcribed directly off the LDraw table needs -1.600 mm to express it
    # correctly in THIS class's own frame. assemble()'s +1.200 mm seating
    # translate (Cover.PLATE_THICKNESS) is unrelated and untouched -- the
    # error was entirely in these constants, not the seating transform.
    TAB_PAD_X = 28.000
    TAB_PAD_Y_HALF = 12.000
    TAB_PAD_Z_HI = 5.600
    TAB_LEDGE_X = 28.400
    TAB_LEDGE_Y_HALF = 8.400
    TAB_LEDGE_Z_LO = 5.600
    TAB_LEDGE_Z_HI = 6.800
    GRIP_RIB_X = 28.320
    GRIP_RIB_Y_HALF = 8.800
    GRIP_RIB_1_Z = (0.320, 1.280)
    GRIP_RIB_2_Z = (2.320, 3.280)

    # --- New floor ---
    FLOOR_THICKNESS = 1.5  # design-proposed, ~1.5 mm
    # Standoff height (round 18, S5) -- the floor is raised off the tray's
    # own bottom rim by this much, opening a routing crawl-space beneath it
    # so a strap can pass down through one holder slot, under the floor,
    # and back up through the other. Sized to clear
    # STRAP_THICKNESS_ASSUMED with the same running clearance the holder
    # slots themselves use, rather than sitting flush on the rim (which,
    # per the audit, left zero clearance -- the floor's underside was
    # coplanar with the Cover's own inner face in assemble()).
    FLOOR_STANDOFF = 2.500

    # --- New strap holders ---
    STRAP_WIDTH = 20.5  # round-8 confirmed opening, for a 20 mm strap
    STRAP_THICKNESS_ASSUMED = 1.8  # UNCONFIRMED -- see class docstring
    STRAP_HOLDER_Y = 18.0  # +-Y position of the two holder slots

    def __init__(self, profile: ToleranceProfile | str | None = None) -> None:
        if profile is None or isinstance(profile, str):
            prof = get_profile(profile) if isinstance(profile, str) else get_profile()
        else:
            prof = profile
        self._profile = prof

        # +Y end wall faces, after applying the relief. Both faces shift
        # together (+Y, outward) so the wall keeps its full thickness
        # rather than locally thinning.
        #
        # Side AND Z-extent both corrected round 18, verified against the
        # actual built geometry (not re-derived blind): the design brief's
        # B3(b) ruling moved the relief from +Y to -Y, reasoning that "the
        # -Y (latch) end has no equivalent rigid riser to collide with" --
        # true only of the *thickening band* (Z <= ~2.0 mm world) that
        # ruling was written against. Once B2's cantilever U (the release
        # leg / thumb pad, reaching Y = -35.6 mm across the FULL Z in
        # [0, hook_depth=13] mm) was actually built, moving the relief to
        # -Y instead drove the wall straight into that structure --
        # measured 373+ mm^3, an order of magnitude worse than the +Y
        # collision B3(b) was trying to avoid. This is a genuinely new
        # finding, not a restatement of B3: B3(b) was written and correct
        # against the geometry that existed at the time; B2 (specified and
        # built in the SAME round) changed the -Y end's own envelope after
        # the fact. Reverted to +Y, but Z-restricted (a further, Developer-
        # derived refinement B3(b) itself didn't need, since it never
        # anticipated the low-Z-only tongue riser conflict a *uniform*
        # +Y relief still creates): below RELIEF_Z_LO the wall stays at its
        # NOMINAL (un-relieved) position, clearing
        # PoweredUpHubCover's tongue riser (Y in [32.00, 32.30], Z in
        # [1.20, 2.80] world -- local Z in [0.00, 1.60]); at/above it, the
        # relieved position governs. The pack itself never needs the extra
        # 1.5 mm down there anyway: FLOOR_STANDOFF (2.500 mm local) already
        # keeps the pack's own resting surface well above RELIEF_Z_LO.
        self.RELIEF_Z_LO = 1.700  # local Z, clears the tongue riser with margin
        self._end_wall_pos_y_lo = self.END_WALL_POS_Y_LO_NOMINAL + self.RELIEF
        self._end_wall_pos_y_hi = self.END_WALL_POS_Y_HI_NOMINAL + self.RELIEF

        # Upper-band wall step (round 16, Escalation 5): the outer face
        # gets an explicit, tolerance-aware running-clearance gap off
        # Housing's own upper-band inner face, routed through the active
        # profile rather than a bare literal (this project's tolerance-
        # profile convention) -- the inner face (WALL_INNER_X_UPPER) needs
        # no such gap, since it only bounds the tray's own cavity.
        self._wall_outer_x_upper = self.WALL_OUTER_X_UPPER_NOMINAL - prof.free.radial

        self._solid = self._build()

    def _build(self) -> cq.Workplane:
        part = self._build_shell()
        part = part.cut(self._build_cover_feature_relief())
        part = part.union(self._build_floor())
        part = part.union(self._build_extraction_tab(+1))
        part = part.union(self._build_extraction_tab(-1))
        part = part.cut(self._build_strap_holders())

        assert len(part.solids().vals()) == 1, "Expected single solid, got multiple pieces"
        return part

    def _cavity_y_span(self, *, relieved: bool = True) -> tuple[float, float]:
        """Inner (cavity-facing) Y bounds -- both partitions removed.

        ``relieved=True`` (the default, used everywhere except the
        low-``Z`` band below :attr:`RELIEF_Z_LO`) includes :attr:`RELIEF`
        on the ``+Y`` face; ``relieved=False`` returns the nominal,
        un-relieved span.
        """
        y_hi = self._end_wall_pos_y_lo if relieved else self.END_WALL_POS_Y_LO_NOMINAL
        return (self.END_WALL_NEG_Y_HI, y_hi)

    def _build_shell(self) -> cq.Workplane:
        """Outer envelope minus the inner cavity, stacked as three Z-bands.

        Two axes are independently stepped:

        - **X** (round 16, Escalation 5): the lower X-band keeps the
          tray's original uniform wall; the upper X-band
          (``Z >= WALL_STEP_Z``) steps inward to clear Housing's own wall
          -- see the ``WALL_STEP_Z`` / ``WALL_OUTER_X_UPPER_NOMINAL`` /
          ``WALL_INNER_X_UPPER`` class-attribute comment.
        - **Y** (round 18, B3(b)): the ``+Y`` end wall is un-relieved below
          :attr:`RELIEF_Z_LO` (clearing PoweredUpHubCover's tongue riser)
          and relieved at/above it (giving the pack its needed clear
          length) -- see :attr:`RELIEF_Z_LO`'s own comment in
          :meth:`__init__`.

        These two steps don't align in Z, so this is genuinely three
        bands, not two: [0, RELIEF_Z_LO] (lower X, un-relieved Y),
        [RELIEF_Z_LO, WALL_STEP_Z] (lower X, relieved Y), and
        [WALL_STEP_Z, WALL_Z_HI] (upper X, relieved Y).
        """
        # Corrected round 18 (S8). PoweredUpHubHousing's own analogous wall
        # step (housing.py's _build_side_wall) uses the SAME
        # coincident-faces-guard technique, independently, which makes
        # Housing's own *lower* band's nominal reach (X up to
        # WALL_X_OUTER_LOWER = 28.0, unfudged) coexist with its *upper*
        # band's own -0.05 mm Z-start fudge across world Z in
        # [21.95, 22.00] -- i.e. Housing's own combined cross-section is
        # WIDER than its nominal stepped profile for that last 0.05 mm
        # before the step. This class's lower band, if left to reach its
        # own full WALL_STEP_Z (world 22.00) unshortened, sits inside that
        # same window with its own WIDE (pre-step) cross-section -- an
        # earlier version tried moving the seam overlap from the outer to
        # the inner face here, which left the residual unchanged (it was
        # never about which face carried the overlap; it was two
        # INDEPENDENT classes' own seam fudges landing in the same Z
        # window). The real fix: keep this class's WIDE lower-band
        # cross-section entirely clear of that window by stopping it
        # `SEAM_MARGIN` before the nominal step, with the NARROW upper
        # band's own coincident-faces overlap starting far enough before
        # that Housing's fudge zone is comfortably clear too.
        SEAM_MARGIN = 0.100
        overlap = 0.05

        band0 = self._shell_band(
            self.WALL_OUTER_X, self.WALL_INNER_X, 0.0, self.RELIEF_Z_LO + overlap,
            relieved=False,
        )
        band1 = self._shell_band(
            self.WALL_OUTER_X, self.WALL_INNER_X,
            self.RELIEF_Z_LO, self.WALL_STEP_Z - SEAM_MARGIN,
            relieved=True,
        )
        band2 = self._shell_band(
            self._wall_outer_x_upper,
            self.WALL_INNER_X_UPPER - 2 * overlap,
            self.WALL_STEP_Z - SEAM_MARGIN - overlap,
            self.WALL_Z_HI,
            relieved=True,
        )
        return band0.union(band1).union(band2)

    def _shell_band(
        self,
        outer_x: float,
        inner_x: float,
        z_lo: float,
        z_hi: float,
        *,
        relieved: bool,
    ) -> cq.Workplane:
        """One Z-band of the outer-wall ring: an outer box minus an inner
        cavity box -- ``outer_x``/``inner_x`` set this band's X extent;
        ``relieved`` selects whether the ``+Y`` end wall (both its outer
        and cavity-facing faces) sits at its nominal or B3(b)-relieved
        position for this band (see :meth:`_cavity_y_span`).
        """
        cavity_y_lo, cavity_y_hi = self._cavity_y_span(relieved=relieved)
        y_lo_outer = self.END_WALL_NEG_Y_LO
        y_hi_outer = self._end_wall_pos_y_hi if relieved else self.END_WALL_POS_Y_HI_NOMINAL
        outer = rounded_box(
            width=2 * outer_x,
            depth=y_hi_outer - y_lo_outer,
            height=z_hi - z_lo,
            corner_r=0.0,
            center=(0.0, (y_lo_outer + y_hi_outer) / 2.0, z_lo),
        )
        # Break cleanly through this band's own top/bottom Z faces (see
        # cq_utils overcut convention) -- harmless beyond the band's own
        # footprint, since `cut()` only removes material `outer` actually
        # has (bounded by `outer`'s own [z_lo, z_hi] extent), so this
        # cannot reach into the neighbouring band's already-built solid.
        band_overcut = 0.5
        inner = rounded_box(
            width=2 * inner_x,
            depth=cavity_y_hi - cavity_y_lo,
            height=(z_hi - z_lo) + 2 * band_overcut,
            corner_r=0.0,
            center=(0.0, (cavity_y_lo + cavity_y_hi) / 2.0, z_lo - band_overcut),
        )
        return outer.cut(inner)

    def _build_cover_feature_relief(self) -> cq.Workplane:
        """Relief pockets clearing two of :class:`PoweredUpHubCover`'s own
        raised, low-``Z`` features that this class's flat-bottomed end
        walls would otherwise collide with once seated in ``assemble()``
        (round 18 finding, surfaced only once B3(b) and S1 were both built
        together -- neither collision is addressed anywhere in the design
        brief's own text, since S1's land didn't exist as a raised feature
        until this round and B3(a)'s "re-verify after S2" prediction did
        not anticipate a *Y-position* conflict, only a *Z-datum* one):

        - The latch-end thickening band
          (``LATCH_BAND_Y_LO``/``_Y_HI``, world Z in
          ``[PLATE_THICKNESS, LATCH_BAND_THICKNESS]``) sits directly under
          this class's own ``-Y`` end wall footprint -- this is B3(a),
          confirmed to survive the S2 fix unchanged (S2 only re-based the
          tray's own tab/wall-height Z constants; it never touched either
          part's Y-position, which is what this collision is about).
        - The locating land (``LAND_Y_LO``/``_Y_HI``, round 18 S1's
          corrected raised registration seat, world Z in
          ``[PLATE_THICKNESS, PLATE_THICKNESS + LAND_HEIGHT]``) sits
          directly under this class's own ``+Y`` end wall footprint -- a
          new collision, since S1 turned this feature from a recess
          (never collided with anything) into a raised land.

        Both relief footprints are read directly from
        :class:`PoweredUpHubCover`'s own constants (never re-typed as
        literals) and converted to this class's local frame via the fixed
        ``+PLATE_THICKNESS`` seating offset ``assemble()`` applies -- so
        the two parts can never silently diverge, mirroring this project's
        existing precedent for one class deriving geometry from another's
        published constants (e.g. ``PoweredUpHubHousing``'s own latch
        catch, derived from this same ``PoweredUpHubCover`` class).
        """
        seat = PoweredUpHubCover.PLATE_THICKNESS  # this class's local Z=0 == world Z=seat
        overcut = 0.5

        def _relief(y_lo: float, y_hi: float, world_z_hi: float) -> cq.Workplane:
            local_z_hi = world_z_hi - seat
            return rounded_box(
                width=2 * self.WALL_OUTER_X + 2 * overcut,
                depth=y_hi - y_lo,
                height=local_z_hi + overcut,
                corner_r=0.0,
                center=(0.0, (y_lo + y_hi) / 2.0, -overcut),
            )

        band = _relief(
            PoweredUpHubCover.LATCH_BAND_Y_LO,
            PoweredUpHubCover.LATCH_BAND_Y_HI,
            PoweredUpHubCover.LATCH_BAND_THICKNESS,
        )
        land = _relief(
            PoweredUpHubCover.LAND_Y_LO,
            PoweredUpHubCover.LAND_Y_HI,
            PoweredUpHubCover.PLATE_THICKNESS + PoweredUpHubCover.LAND_HEIGHT,
        )
        return band.union(land)

    def _build_floor(self) -> cq.Workplane:
        """Floor shelf, raised on :attr:`FLOOR_STANDOFF` (round 18, S5) so a
        strap has routing clearance beneath it. A small overlap sinks the
        floor's own Z start below the standoff height, guaranteeing a
        genuine 3D overlap with the side/end walls it fuses to (which span
        the full height here) rather than a coincident touching face.
        """
        cavity_y_lo, cavity_y_hi = self._cavity_y_span()
        seam_overlap = 0.05
        return rounded_box(
            width=2 * self.WALL_INNER_X,
            depth=cavity_y_hi - cavity_y_lo,
            height=self.FLOOR_THICKNESS + seam_overlap,
            corner_r=0.0,
            center=(0.0, (cavity_y_lo + cavity_y_hi) / 2.0, self.FLOOR_STANDOFF - seam_overlap),
        )

    def _build_extraction_tab(self, side: int) -> cq.Workplane:
        """One side extraction tab (K5): pad + finger ledge + two grip ribs."""
        x_wall = side * self.WALL_OUTER_X

        # Pad: a slab from the side wall's own outer face to the tab's
        # proud face (side * TAB_PAD_X) -- min/max keeps this correct for
        # both side=+1 and side=-1 without duplicating the sign logic.
        x_lo = min(x_wall, side * self.TAB_PAD_X)
        x_hi = max(x_wall, side * self.TAB_PAD_X)
        pad = rounded_box(
            width=x_hi - x_lo,
            depth=2 * self.TAB_PAD_Y_HALF,
            height=self.TAB_PAD_Z_HI,
            corner_r=0.0,
            center=((x_lo + x_hi) / 2.0, 0.0, 0.0),
        )

        ledge_x_lo = min(x_wall, side * self.TAB_LEDGE_X)
        ledge_x_hi = max(x_wall, side * self.TAB_LEDGE_X)
        ledge = rounded_box(
            width=ledge_x_hi - ledge_x_lo,
            depth=2 * self.TAB_LEDGE_Y_HALF,
            height=self.TAB_LEDGE_Z_HI - self.TAB_LEDGE_Z_LO,
            corner_r=0.0,
            center=((ledge_x_lo + ledge_x_hi) / 2.0, 0.0, self.TAB_LEDGE_Z_LO),
        )

        tab = pad.union(ledge)
        for z_lo, z_hi in (self.GRIP_RIB_1_Z, self.GRIP_RIB_2_Z):
            rib_x_lo = min(x_wall, side * self.GRIP_RIB_X)
            rib_x_hi = max(x_wall, side * self.GRIP_RIB_X)
            rib = rounded_box(
                width=rib_x_hi - rib_x_lo,
                depth=2 * self.GRIP_RIB_Y_HALF,
                height=z_hi - z_lo,
                corner_r=0.0,
                center=((rib_x_lo + rib_x_hi) / 2.0, 0.0, z_lo),
            )
            tab = tab.union(rib)
        return tab

    def _build_strap_holders(self) -> cq.Workplane:
        """Two full-depth slots through the floor, sized to the confirmed
        20.5 mm strap opening with a running clearance on the strap's
        thickness dimension (unconfirmed, see class docstring).
        """
        clearance = self._profile.free.radial
        slot_depth = self.STRAP_THICKNESS_ASSUMED + 2 * clearance
        overcut = 1.0  # break cleanly through the (now-raised) floor's Z extent
        slots = None
        for y_center in (-self.STRAP_HOLDER_Y, self.STRAP_HOLDER_Y):
            slot = rounded_box(
                width=self.STRAP_WIDTH,
                depth=slot_depth,
                height=self.FLOOR_THICKNESS + 2 * overcut,
                corner_r=0.0,
                center=(0.0, y_center, self.FLOOR_STANDOFF - overcut),
            )
            slots = slot if slots is None else slots.union(slot)
        return slots

    @property
    def solid(self) -> cq.Workplane:
        return self._solid
