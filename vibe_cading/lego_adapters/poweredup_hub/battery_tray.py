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
Philippe Hurbain) part ``24849`` ("Electric Technic Battery Holder Cover"),
as extracted in
``docs/design_plans/2026-08-19-poweredup-hub-battery-box_ldraw-parts-geometry.md``
SS2, plus fresh ray-cast measurement against a locally-dumped, uncommitted
STL (``tmp/ldraw/ref_tray.stl`` -- no LDraw ``.dat`` file, converted
geometry, or render is committed to this repo, only independently-written
measurements and from-scratch CadQuery code).

**Round 51 -- resurrected and reshaped.** A version of this class existed
from round 13 through round 22, when it was deleted because a full 4-walled
tray plus a floor plus a strap could not fit under the 3-stud bottom-layer
cap (``git show <pre-deletion sha>^:.../battery_tray.py`` recovers the
retired file; its own numbers are NOT copied blind here -- see the
per-constant provenance comments below, since the wall step, the deck
thickness, and the tab profile have all changed since). Its extraction tabs
were re-homed onto :class:`~vibe_cading.lego_adapters.poweredup_hub.cover.PoweredUpHubCover`
at the same time; **this round moves them back**, which is a return to the
real reference's own division of labour -- 24849 (this tray) carries the
tab, 24853 (the lid) never did, and Cover only grew one as a stand-in once
the tray was gone.

**U shape, by user direction (round 51):** both END walls (LEGO's
transverse partitions AND the tray's own end caps) are gone outright,
leaving only the two long side walls (with the tabs) and the floor -- a
channel, open at both ends, rather than the old design's closed box. This
is not a simplification of the reference so much as a simplification of
*this class*: every collision this file fought from round 13 to round 22 --
the tongue riser, the latch-end release leg, the raised locating land --
was a collision between a flat-bottomed END wall and one of
:class:`~vibe_cading.lego_adapters.poweredup_hub.cover.PoweredUpHubCover`'s
own raised, low-Z features. Remove the end wall and the collision class
disappears with it; nothing here needs a relief cut.

The real part's own LDraw comment (``// Internal structure is simplified``)
scopes its *whole* part -- reliable only for the outer envelope, wall
thicknesses, the side extraction tabs, and the 14.4 mm cell pitch. This
class sizes nothing off the unreliable (simplified) regions: the corrugated
shelf, cell dividers, side stiffener plates and both end walls are deleted
outright (not re-measured); the floor and the strap channel are sized
against the Spektrum SPMX812SH2 pack and a nominal keeper strap, not
against the tray's simplified internal geometry.

**Deferred, by explicit user direction (round 51):** whether this tray
plus its floor actually FITS under the current 3-stud
(``PoweredUpHubHousing.DECK_Z`` = 24.000 mm) housing, alongside the
20.900 mm pack, is an open question this class does not answer -- the user
asked to design the tray first and revisit the housing's height
afterward. Inserting this tray's floor between the Cover and the pack
consumes headroom the housing did not budget for (the housing's own
interior was already only 0.300 mm proud of the bare pack with no tray at
all -- see ``tests/lego_adapters/test_poweredup_hub_housing.py``'s
``test_interior_clears_the_target_battery``); it will not fit until the
housing's height is revisited. This class's own tests therefore verify its
structural correctness and its seating against Housing/Cover, but do NOT
assert the pack clears above this tray's floor.
"""

from __future__ import annotations

import cadquery as cq

from vibe_cading.cq_utils import rounded_box
from vibe_cading.lego_adapters.poweredup_hub.cover import PoweredUpHubCover
from vibe_cading.print_settings import ToleranceProfile, get_profile


class PoweredUpHubBatteryTray:
    """U-channel battery cradle: two side walls carrying the real tab from
    LEGO tray ``24849``. Open at both ends -- see the module docstring's
    *U shape* section.

    **Round 55 -- one piece again, with the strap channel cut INTO a thick
    floor.** Round 54 split the whole floor out into a separately-printed,
    glued-in plate on printability grounds; the user reverted that ("merge
    the tray back together") and supplied the design that actually solves
    the printability problem, in a marked-up sketch:

    * the floor is integral and its underside is **flush with this class's
      own ``Z = 0`` bottom rim** -- no standoff, so the part prints
      directly on the bed with nothing bridged;
    * a strap corridor is cut **clear through** it, joining the two
      round-53 strap slots into one continuous opening (the sketch's
      centre band);
    * a shallow rebate is taken out of the floor's **top** face on both
      Y-flanks of that corridor (the sketch's hatched bands -- "make this
      area thinner");
    * :class:`~vibe_cading.lego_adapters.poweredup_hub.battery_tray_cap.PoweredUpHubBatteryTrayCap`,
      a small flat plate exactly :attr:`STRAP_CAP_THICKNESS` thick, drops
      into that rebate from above and glues down flush with the floor's
      top face -- roofing the corridor and turning it into the channel the
      strap runs in.

    **The channel is UNDER the plate**, floored by
    :class:`PoweredUpHubCover`'s own face and roofed by the cap. That
    orientation is load-bearing in two ways, and getting it upside-down
    (as a first attempt at this round did) breaks both: a rebate in the
    TOP face opens upward, so the floor under it prints straight off the
    bed with nothing overhanging, whereas an underside rebate would leave
    the flanks bridging 1.200 mm up in the air -- reintroducing the exact
    printability fault this redesign removes. And with the cap flush at
    the top, the pack lands on one continuous surface rather than on a
    floor with a 20.500 mm slot down the middle of it. The user's
    constraint, verbatim: *"You cannot make the tray bottom completely
    hollow, it's difficult to print."*

    **Rejected alternative** (the user's own second suggestion, so recorded
    rather than silently dropped): routing the strap through slots in the
    lower side walls to avoid a second part entirely. It does not fit --
    this tray's lower-band outer face is at ``|X| = 27.200`` and
    ``PoweredUpHubHousing``'s lower-band inner face is *also* 27.200, so a
    strap leaving sideways has exactly zero mm of space to run in.

    Origin / datum
    ---------------
    ``(0, 0, 0)`` is the tray's **bottom face** -- the physical mating
    datum where it seats against
    :class:`~vibe_cading.lego_adapters.poweredup_hub.cover.PoweredUpHubCover`'s
    inner (top) face. In :func:`~vibe_cading.lego_adapters.poweredup_hub.assembly.assemble`
    this class is translated up by ``PoweredUpHubCover.PLATE_THICKNESS``
    (1.200 mm) -- its own local Z is *not* the world Z the Housing and
    Cover classes share. Every feature extrudes ``+Z`` from there. X is
    centred on the tray's mid-width (matching Housing/Cover); Y follows the
    same frame (latch end at ``-Y``, tongue end at ``+Y``). The floor is
    part of this same solid and its underside sits exactly ON that
    ``Z = 0`` rim; the cap plate shares the same datum, filling the
    underside rebate flush.

    Parameters
    ----------
    profile:
        Manufacturing tolerance profile. Used for the upper wall band's
        running clearance off Housing's own inner face, and the wall's own
        top clearance under Housing's deck (:attr:`_wall_z_hi`). Accepts a
        :class:`~vibe_cading.print_settings.ToleranceProfile` instance, a
        profile name string, or ``None`` for the process-global default.
    """

    # --- Side walls (SS2.2), lower X-band -- unaffected by any round-51
    # change: Housing's lower-band inner face (WALL_X_OUTER_LOWER -
    # WALL_THICKNESS = 28.000 - 0.800 = 27.200) has been the same number
    # since the reference's own "exact copy" envelope was first measured,
    # and this tray still rides directly against it.
    WALL_OUTER_X = 27.200
    WALL_INNER_X = 26.400

    # --- Upper X-band: Housing's own wall doubles in thickness above its
    # own WALL_INNER_STEP_Z, stepping its INNER face in to 26.400 while
    # keeping the same 27.200/28.000 outer faces below it (see
    # PoweredUpHubHousing._build_side_wall) -- so this tray's wall must
    # step its OUTER face in to stay clear of that thickened band, exactly
    # the escalation the retired file's own round-16 comment describes.
    # WALL_STEP_Z below is hand-derived from Housing's own constant rather
    # than imported live: Housing imports THIS class (for the side window
    # / tab derivation, round 51), so this class importing Housing back
    # would cycle. Re-derive by hand if PoweredUpHubHousing.WALL_INNER_STEP_Z
    # (currently 21.200, world) or PoweredUpHubCover.PLATE_THICKNESS (this
    # class's own seat offset) ever change.
    WALL_STEP_Z = 20.000   # == 21.200 (Housing.WALL_INNER_STEP_Z, world) - 1.200 (seat)
    #
    # Round 55e: 26.400 -> 26.050. Housing deepened its side trapezoid to
    # 1.150 mm so a future cover gets a 1.000 mm wall, and derived the
    # doubled band's inner face from that socket floor -- moving Housing's
    # own inner face, which THIS band rides against, in by 0.350. Held at
    # 26.400 the tray's wall would foul it by 0.200 mm everywhere above
    # world Z = 21.200; nothing in this class would notice, since the
    # single-solid and seating checks are about this part alone. What
    # catches it is test_seats_against_housing_and_cover_with_zero_interference.
    #
    # The inner face moves the same 0.350 so the band keeps its section.
    # Housing's inner face is now UNIFORM from WALL_INNER_STEP_Z to DECK_Z
    # (its doubled band and its upper section share it), so this band still
    # needs no further step of its own despite the housing now being 5.6 mm
    # taller than when it was written.
    WALL_OUTER_X_UPPER_NOMINAL = 26.050
    WALL_INNER_X_UPPER = 25.250
    WALL_THICKNESS = WALL_OUTER_X - WALL_INNER_X   # 0.800, both bands

    # --- Y span (round 51) -- the U's open ends. ---
    # Both raised Cover features that the old END walls used to collide
    # with (LATCH_BAND, ending at Y = -30.000; the locating groove/land,
    # starting at Y = 30.000) bound this tray's own Y-reach instead of
    # being relief-cut around: stopping SAFETY_MARGIN short of each means
    # the wall footprint never overlaps either raised band, by construction
    # rather than by a cutter this class would otherwise need. Derived live
    # from Cover (safe: Cover does not import this class or Housing).
    _SAFETY_MARGIN = 0.100
    WALL_Y_LO = PoweredUpHubCover.LATCH_BAND_Y_HI + _SAFETY_MARGIN    # -29.900
    WALL_Y_HI = PoweredUpHubCover.GROOVE_Y_LO - _SAFETY_MARGIN        # 29.900

    # --- Floor (rounds 52-53, restored and re-datumed in round 55) ---
    # Not reference-derived: LDraw 24849's own floor is inside the part's
    # self-declared "internal structure is simplified" region, so these are
    # sized against the payload (Spektrum SPMX812SH2 pack) and a nominal
    # keeper strap instead.
    #
    # NO STANDOFF, unlike rounds 52-53. The floor's underside is flush with
    # this class's own Z = 0 bottom rim, so the part prints directly on the
    # bed with no bridged span -- which is the printability objection round
    # 54 tried (wrongly) to answer by splitting the whole floor off as a
    # separate part. The strap's routing space is no longer a gap UNDER a
    # raised shelf; it is a channel cut INTO a thick floor (see
    # STRAP_CHANNEL_* below). Net stack under the pack: 2.700 mm here vs.
    # rounds 52-53's 2.700 + 1.500 = 4.200 mm, i.e. 1.500 mm of headroom
    # recovered -- which matters, since the housing's height is sized off
    # exactly this number plus the pack.
    FLOOR_THICKNESS = 2.700

    # --- Strap channel + the separate cap plate (round 55, user sketch) ---
    # 20.0 mm nominal strap width (user-supplied) + 0.500 mm so the strap
    # is not pinched in its own slot.
    STRAP_WIDTH = 20.500
    # Slot X positions: the strap runs ALONGSIDE the two extraction tabs
    # (i.e. across X, over the pack's top), which is the round-53 direction
    # correction -- round 52's first attempt put both slots at X = 0 with
    # Y offsets, making two local loops beside the pack that retained
    # nothing. 22.000 clears the pack's own half-width (32.0 / 2 = 16.0),
    # so the span genuinely crosses over the battery.
    STRAP_HOLDER_X = 22.000
    # User-measured on the actual strap: "less than 1.5 mm". Taken as the
    # 1.500 upper bound rather than a guess below it -- a channel sized to
    # a thinner strap than the one that ships is the failure that cannot
    # be fixed after printing.
    STRAP_THICKNESS_TARGET = 1.500
    # Clear height of the channel. User-specified outright ("channel just
    # need 1.5mm"), NOT derived from STRAP_THICKNESS_TARGET plus a margin:
    # the strap measures under 1.500 and the user sized the channel from
    # the real part, so an added margin here would only spend headroom the
    # housing has to pay for. STRAP_THICKNESS_TARGET still drives the
    # corridor's WIDTH in X (the slot the strap turns up through), where a
    # running clearance is genuinely needed.
    STRAP_CHANNEL_HEIGHT = 1.500
    # The cap plate roofs the channel; its thickness IS the depth of the
    # rebate it drops into, so it finishes flush with the floor's TOP face
    # and adds nothing to the seated stack.
    STRAP_CAP_THICKNESS = FLOOR_THICKNESS - STRAP_CHANNEL_HEIGHT           # 1.200
    # Rebate margin in Y each side of the channel: the ledge the cap
    # actually glues down onto. 5.000 mm gives ~200 mm^2 of bond area per
    # side, and it is a face-to-face glue joint in shear, not an edge one.
    STRAP_CAP_MARGIN_Y = 5.000
    STRAP_CAP_Y_HALF = STRAP_WIDTH / 2.0 + STRAP_CAP_MARGIN_Y              # 15.250
    #: Z of the cap's underside once seated, in this class's own frame --
    #: i.e. the height of the channel roof above the Cover's face. The cap
    #: goes in from ABOVE and finishes flush with the floor's TOP face, so
    #: the pack lands on one continuous surface.
    STRAP_CAP_Z = FLOOR_THICKNESS - STRAP_CAP_THICKNESS                    # 1.500

    # --- Side extraction tabs -- the real tab from LDraw tray 24849
    # (SS2.3), ported from PoweredUpHubCover's own round-47 implementation
    # (the improved 3-edge-border profile) at the point this round moved it
    # back off Cover (round 22 had re-homed it there for lack of a tray to
    # put it on). Hardcoded here, not derived live from Cover, because
    # Cover no longer carries this feature at all as of this round --
    # values are copied, not referenced, so there is nothing left on
    # Cover to drift out of sync with.
    #
    # X/Y figures transfer unchanged from Cover's own (world-frame)
    # HANDLE_* values. Every Z figure is re-based by this class's own seat,
    # PLATE_THICKNESS (1.200 mm, PoweredUpHubCover.PLATE_THICKNESS at the
    # time of the port) -- Cover's Z = 0 was the lid's OUTER face
    # (world Z = 0), while this class's Z = 0 sits 1.200 mm above that, so
    # world Z = local Z + 1.200 and every constant below is (Cover's old
    # HANDLE_*_Z value) - 1.200.
    TAB_ROOT_X = 27.200        # side-wall face the tab stands on
    TAB_PAD_X = 28.000         # 0.800 mm proud
    TAB_PAD_Y_HALF = 12.000    # 24.000 long
    TAB_PAD_Z_HI = 7.200       # == 8.400 (Cover's old world value) - 1.200
    TAB_LEDGE_X = 28.400       # 1.200 mm proud -- the border's own face
    TAB_LEDGE_Y_HALF = 8.400   # the corner round-over's centre |Y|
    TAB_RIB_X = 28.320         # 0.320 mm proud of the pad
    TAB_RIB_Y_HALF = 8.800
    TAB_RIB_1_Z = (0.720, 1.680)   # == (1.920, 2.880) - 1.200
    TAB_RIB_2_Z = (2.720, 3.680)   # == (3.920, 4.880) - 1.200
    TAB_ROUND_R = 3.600
    TAB_ROUND_CZ = 3.600      # == 4.800 (Cover's old world value) - 1.200
    TAB_FRAME_WIDTH = 1.200   # uniform border width, see the retired
    # PoweredUpHubCover._build_side_handle docstring (round 47) for the
    # full derivation of this border from the tab's own outline.

    def __init__(self, profile: ToleranceProfile | str | None = None) -> None:
        if profile is None or isinstance(profile, str):
            prof = get_profile(profile) if isinstance(profile, str) else get_profile()
        else:
            prof = profile
        self._profile = prof

        # Upper-band wall step: an explicit, tolerance-aware running-
        # clearance gap off Housing's own upper-band inner face (this
        # project's tolerance-profile convention -- never a bare literal).
        self._wall_outer_x_upper = self.WALL_OUTER_X_UPPER_NOMINAL - prof.free.radial

        # Wall top: Housing's deck underside (DECK_Z - DECK_THICKNESS =
        # 29.600 - 1.600 = 28.000, world -- hand-derived, not imported, for
        # the same cycle-avoidance reason as WALL_STEP_Z above) minus this
        # class's own seat offset, minus a running (axial) clearance so the
        # tray's wall does not touch Housing's deck.
        #
        # Round 55 applied the revisit this comment was written for
        # (22.400 -> 28.000, when DECK_Z went 24.000 -> 29.600). Worth
        # flagging what that changed BESIDES the number: this formula used
        # to express a genuine constraint -- the housing was so short that
        # the wall reached the deck and stopped there. It no longer is. The
        # pack's top now sits at local Z = FLOOR_THICKNESS + 20.900 =
        # 23.600 and this puts the wall at 26.600, so the wall stands
        # 3.000 mm proud of the thing it cradles for no reason other than
        # "that is where the deck happens to be". It is retained because
        # more lateral support is not harmful and the housing constrains
        # the wall anyway -- but if this ever needs a reason rather than an
        # inheritance, size it off the pack, not the deck.
        _housing_deck_underside_world = 28.000
        self._wall_z_hi = (
            _housing_deck_underside_world
            - PoweredUpHubCover.PLATE_THICKNESS
            - prof.free.axial
        )
        assert self._wall_z_hi > self.WALL_STEP_Z, (
            "the housing's current interior is too short for even the "
            "upper wall band to exist -- re-check _housing_deck_underside_world"
        )

        # Strap corridor width in X at its two ends -- the strap's own
        # nominal thickness plus running clearance both sides, i.e. the
        # round-53 slot width, kept unchanged.
        self._strap_slot_x = self.STRAP_THICKNESS_TARGET + 2 * prof.free.radial
        # The cap plate spans BETWEEN the two corridor ends, not under
        # them: the strap has to reach the tray's interior somewhere, and
        # those two ends are where it does. Stopping the rebate at the
        # corridor ends' inner edges leaves them open top-to-bottom.
        self._cap_x_half, _ = self.cap_rebate_half_extents(prof)

        self._solid = self._build()

    @classmethod
    def cap_rebate_half_extents(
        cls, profile: ToleranceProfile
    ) -> tuple[float, float]:
        """``(x_half, y_half)`` of the underside rebate the cap plate
        glues into, for the given tolerance profile.

        Public because
        :class:`~vibe_cading.lego_adapters.poweredup_hub.battery_tray_cap.PoweredUpHubBatteryTrayCap`
        is sized off exactly this pocket and must not re-derive it from a
        copy of the formula -- a mating pair whose two halves compute the
        same dimension independently is one edit away from silently not
        fitting. The cap subtracts its own running clearance from these.
        """
        slot_x = cls.STRAP_THICKNESS_TARGET + 2 * profile.free.radial
        return (cls.STRAP_HOLDER_X - slot_x / 2.0, cls.STRAP_CAP_Y_HALF)

    def _build(self) -> cq.Workplane:
        part = self._build_side_wall(+1).union(self._build_side_wall(-1))
        part = part.union(self._build_floor())
        part = part.union(self._build_extraction_tab(+1))
        part = part.union(self._build_extraction_tab(-1))
        part = part.cut(self._build_strap_channel())
        part = part.cut(self._build_cap_rebate())

        # One piece again as of round 55: the floor is what joins the two
        # otherwise-disconnected side walls, so this assertion is also the
        # regression net for the floor's own seam overlaps.
        assert len(part.solids().vals()) == 1, (
            "Expected single solid, got multiple pieces"
        )
        return part

    def _build_side_wall(self, x_sign: int) -> cq.Workplane:
        """One side wall: two X-stepped slabs, both spanning the tray's
        full (open-ended) Y reach -- see class docstring's *U shape*.

        The two bands do NOT share any X range: Housing's own cavity
        genuinely narrows above the step (its inner face moves from
        27.200 to 26.400, see the class-level comment), so this wall's
        entire cross-section must sit further inboard above the step than
        below it -- the lower band's solid material (X in
        ``[WALL_INNER_X, WALL_OUTER_X]``) and the upper band's
        (``[WALL_INNER_X_UPPER, _wall_outer_x_upper]``) are disjoint by
        construction, not by an oversight. A plain Z-overlap between two
        X-disjoint slabs does not connect them (this failed the first time
        this method was written: 4 solids, not 1). The fix is a small
        bridge slab AT the seam, wide enough in X to be a superset of both
        bands' footprints, so it genuinely overlaps solid material on both
        sides of the step.
        """
        # `lower` and `bridge` both stop AT WALL_STEP_Z, never past it: at
        # this wide (WALL_OUTER_X) cross-section, Housing's own cavity is
        # only legal below the step (Housing's inner face steps from
        # 27.200 to 26.400 there) -- a first version let `lower` and
        # `bridge` overshoot the step by `overlap` for seam safety, which
        # is exactly backwards here: it drove this wall 0.05 mm into
        # Housing's own thickened wall material (4.784 mm^3, caught by
        # Tray x Housing interference, not by the single-solid assert,
        # which does not know about Housing at all). The overlap that
        # keeps the three pieces connected lives entirely on `bridge`'s Z
        # range and on staying at-or-below WALL_STEP_Z, never past it.
        overlap = 0.050
        lower = self._x_slab(
            x_sign, self.WALL_OUTER_X, self.WALL_THICKNESS,
            0.0, self.WALL_STEP_Z,
        )
        upper = self._x_slab(
            x_sign, self._wall_outer_x_upper,
            self._wall_outer_x_upper - self.WALL_INNER_X_UPPER,
            self.WALL_STEP_Z - overlap, self._wall_z_hi,
        )
        bridge = self._x_slab(
            x_sign, self.WALL_OUTER_X, self.WALL_OUTER_X - self.WALL_INNER_X_UPPER,
            self.WALL_STEP_Z - overlap, self.WALL_STEP_Z,
        )
        return lower.union(upper).union(bridge)

    def _x_slab(
        self, x_sign: int, x_outer: float, thickness: float, z_lo: float, z_hi: float
    ) -> cq.Workplane:
        """A wall slab on one X side, outer face at ``x_sign * x_outer``,
        ``thickness`` mm thick, spanning the tray's full Y reach and
        ``[z_lo, z_hi]``.
        """
        x_inner = x_outer - thickness
        x_lo = min(x_sign * x_outer, x_sign * x_inner)
        x_hi = max(x_sign * x_outer, x_sign * x_inner)
        return rounded_box(
            width=x_hi - x_lo,
            depth=self.WALL_Y_HI - self.WALL_Y_LO,
            height=z_hi - z_lo,
            corner_r=0.0,
            center=((x_lo + x_hi) / 2.0, (self.WALL_Y_LO + self.WALL_Y_HI) / 2.0, z_lo),
        )

    def _build_floor(self) -> cq.Workplane:
        """Floor slab, underside flush with this class's own ``Z = 0``
        bottom rim (no standoff -- see the class docstring), spanning the
        same Y reach as the walls (nothing bounds Y at either end -- see
        *U shape*) and the lower band's own inner X face.

        The X seam overlap runs the slab a hair INTO each side wall's
        material so the union is a genuine solid bond rather than two
        coincident faces; it is safe in that direction because the walls
        are what it overlaps (occupied space we own), not Housing's.
        """
        seam_overlap = 0.050
        return rounded_box(
            width=2 * (self.WALL_INNER_X + seam_overlap),
            depth=self.WALL_Y_HI - self.WALL_Y_LO,
            height=self.FLOOR_THICKNESS,
            corner_r=0.0,
            center=(0.0, (self.WALL_Y_LO + self.WALL_Y_HI) / 2.0, 0.0),
        )

    def _build_strap_channel(self) -> cq.Workplane:
        """The strap corridor: ONE opening cut clear through the floor,
        ``STRAP_WIDTH`` wide in Y and running in X from one strap slot to
        the other (the sketch's centre band -- "completely cut ... so the
        strap holder sockets got connected").

        The two round-53 slots at ``X = +-STRAP_HOLDER_X`` are now this
        corridor's own ends: it spans ``|X| <= STRAP_HOLDER_X +
        _strap_slot_x / 2``, which is exactly the union of the old slot
        pair with the span between them, so the strap's entry/exit
        positions are unchanged (still outboard of the pack's own
        16.000 mm half-width) while the material between them is gone.

        Cut through, not blind: the corridor is open top-to-bottom before
        the cap goes in, which is what makes it printable -- there is no
        roof to bridge, because the roof is a separately-printed part.
        Both Z faces are therefore waste-side and take an overcut.
        """
        overcut = 1.0
        return rounded_box(
            width=2 * (self.STRAP_HOLDER_X + self._strap_slot_x / 2.0),
            depth=self.STRAP_WIDTH,
            height=self.FLOOR_THICKNESS + 2 * overcut,
            corner_r=0.0,
            center=(0.0, 0.0, -overcut),
        )

    def _build_cap_rebate(self) -> cq.Workplane:
        """The shallow underside rebate the cap plate glues into (the
        sketch's hatched flanks -- "make the blue shadowed area thinner").

        ``STRAP_CAP_THICKNESS`` deep, taken off the floor's **TOP** face,
        so a cap of exactly that thickness finishes flush with the floor's
        top and the pack lands on one continuous surface.

        **Why the top and not the underside** (an earlier version of this
        round had it the other way up, and the user corrected it): a
        pocket in the top face opens upward, so the floor beneath it
        prints straight off the bed with nothing overhanging. Rebating the
        UNDERSIDE instead would have left the flanks starting 1.200 mm up
        in the air, bridging the pocket -- reintroducing exactly the
        printability fault this whole redesign exists to remove. It also
        puts the channel where it belongs: *under* the plate, roofed by
        it and floored by the Cover.

        Bounds, and why each is safe to overcut or not:

        * ``+Z`` opens into the tray's own interior -- pure void, overcut
          freely.
        * ``-Z`` must stop DEAD at :attr:`STRAP_CAP_Z`. It is a blind
          pocket; overcutting downward would break through into the
          channel and there would be nothing left for the cap to glue to.
        * X and Y stop short of the side walls by construction
          (``STRAP_CAP_Y_HALF`` = 15.250 and the X half below is ~20.850,
          both well inside ``WALL_INNER_X`` = 26.400), so this pocket
          never reaches material that is doing another job. Verified by
          ``test_cap_rebate_stays_clear_of_the_side_walls``.
        """
        overcut = 1.0
        return rounded_box(
            width=2 * self._cap_x_half,
            depth=2 * self.STRAP_CAP_Y_HALF,
            height=self.STRAP_CAP_THICKNESS + overcut,
            corner_r=0.0,
            center=(0.0, 0.0, self.STRAP_CAP_Z),
        )

    def _build_extraction_tab(self, side: int) -> cq.Workplane:
        """One side extraction tab: pad + raised 3-edge border + two grip
        ribs -- ported from
        :meth:`~vibe_cading.lego_adapters.poweredup_hub.cover.PoweredUpHubCover._build_side_handle`,
        the improved round-47 profile (see class-level TAB_* comment for
        the Z re-basing). Kept as one method rather than importing Cover's
        builder directly, since Cover's version is expressed in world Z
        and this class's own frame differs by the fixed seat offset.
        """
        cz, ly = self.TAB_ROUND_CZ, self.TAB_LEDGE_Y_HALF

        def _outline(x_at: float, inset: float) -> cq.Workplane:
            yh = self.TAB_PAD_Y_HALF - inset
            r = self.TAB_ROUND_R - inset
            zhi = self.TAB_PAD_Z_HI - inset
            d = r * 0.7071
            return (
                cq.Workplane("YZ")
                .transformed(offset=cq.Vector(0.0, 0.0, side * x_at))
                .moveTo(-yh, 0.0)
                .lineTo(-yh, cz)
                .threePointArc((-ly - d, cz + d), (-ly, zhi))
                .lineTo(ly, zhi)
                .threePointArc((ly + d, cz + d), (yh, cz))
                .lineTo(yh, 0.0)
                .close()
            )

        pad = _outline(self.TAB_ROOT_X, 0.0).extrude(
            side * (self.TAB_PAD_X - self.TAB_ROOT_X)
        )

        oc = 1.0
        frame_depth = self.TAB_LEDGE_X - self.TAB_PAD_X
        frame = _outline(self.TAB_PAD_X, 0.0).extrude(side * frame_depth)
        frame = frame.cut(
            _outline(self.TAB_PAD_X - oc, self.TAB_FRAME_WIDTH)
            .extrude(side * (frame_depth + 2 * oc))
        )
        tab = pad.union(frame)

        def _band(x_face, y_half, z_lo, z_hi):
            x_lo = min(side * self.TAB_PAD_X, side * x_face)
            x_hi = max(side * self.TAB_PAD_X, side * x_face)
            return rounded_box(
                width=x_hi - x_lo,
                depth=2 * y_half,
                height=z_hi - z_lo,
                corner_r=0.0,
                center=((x_lo + x_hi) / 2.0, 0.0, z_lo),
            )

        for z_lo, z_hi in (self.TAB_RIB_1_Z, self.TAB_RIB_2_Z):
            tab = tab.union(_band(self.TAB_RIB_X, self.TAB_RIB_Y_HALF, z_lo, z_hi))
        return tab

    @property
    def solid(self) -> cq.Workplane:
        return self._solid
