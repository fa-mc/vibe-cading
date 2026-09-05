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
from vibe_cading.lego_adapters.poweredup_hub.latch_geometry import (
    get_latch_geometry,
)
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
    this tray's lower-band outer face and ``PoweredUpHubHousing``'s
    lower-band inner face were the same number (27.200), so a strap leaving
    sideways had exactly zero mm of space to run in. Round 72 moved this
    tray's face to 26.250 (owner-measured), which opens a nominal 0.950 mm
    -- still far too little for a strap, and against the REAL housing the
    gap is the running clearance (~0.230 a side), so the rejection stands.

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
        Manufacturing tolerance profile. Since round 57 removed the upper
        wall band, the only thing it sizes here is the strap corridor's
        running clearance (``free.radial`` on each side of the strap's own
        thickness) and, through :meth:`cap_rebate_half_extents`, the cap
        plate's fit in its rebate. The wall itself is now profile-independent
        -- it ends at the plain constant :attr:`WALL_Z_HI`. Accepts a
        :class:`~vibe_cading.print_settings.ToleranceProfile` instance, a
        profile name string, or ``None`` for the process-global default.
    """

    # --- Side walls (SS2.2), lower X-band.
    #
    # ROUND 72 -- OWNER-MEASURED, superseding the derivation below.
    # 52.500 outer-to-outer across the two side walls, measured on the real
    # tray, so each outer face is at 26.250.
    #
    # What it replaces, and why that was wrong: this used to be 27.200,
    # derived from OUR Housing's lower-band inner face
    # (WALL_X_OUTER_LOWER - WALL_THICKNESS = 28.000 - 0.800), on the note
    # that the figure "has been the same number since the reference's own
    # 'exact copy' envelope was first measured". That is exactly the failure
    # this part has now hit four times: the LDraw reference was wrong about
    # the hardware in width, hook height, latch depth and compartment
    # height, and a constant derived from it inherits the error while
    # LOOKING well-founded. The Housing's own cavity width (54.400) is
    # itself unverified and known too wide against a real-housing reading of
    # 52.960 -- so this constant is no longer allowed to depend on it.
    #
    # 52.500 in a 52.960 cavity leaves 0.460 total, i.e. 0.230 a side, which
    # is a plausible running clearance and an independent corroboration of
    # both numbers.
    # ROUND 72 -- wall thickened 0.800 -> 2.000 on the owner's report that the
    # printed tray feels "too filmy" in the hand. That is a tactile reading of
    # a real printed part, which outranks any derivation.
    #
    # It goes INBOARD, because WALL_OUTER_X is the measured drop-in datum and
    # cannot move. On a 0.4 mm nozzle 0.800 is two perimeters (no infill
    # between them -- it IS a film); 2.000 is five, and flexural stiffness
    # goes as thickness cubed, so this is ~15x stiffer rather than 2.5x.
    #
    # Honest caveat, per the Designer: some of the floppiness is probably the
    # SHAPE, not the section. This tray is an open U -- both end walls were
    # removed in round 51 to clear a real Cover collision -- and an open
    # channel twists in a way no wall thickness fully fixes. If it still feels
    # twisty after this print, the next lever is a cross-rib or a thicker
    # floor, NOT another thickness bump; re-adding the end walls is off the
    # table (they were removed for a geometric reason, not a preference).
    WALL_OUTER_X = 26.250                          # 52.500 / 2, owner-measured
    WALL_INNER_X = WALL_OUTER_X - 2.000            # 24.250

    # --- Wall top (round 57): the wall STOPS where Housing's cavity
    # narrows, instead of following it inboard.
    #
    # Housing's own wall doubles in thickness above its WALL_INNER_STEP_Z,
    # stepping its INNER face in to 26.400. Rounds up to 55 tracked that
    # with a second, narrower wall band (outer face 26.050 - clearance,
    # inner 25.250) stacked above this one. That band's X span was
    # DISJOINT from this one's -- 25.250..25.900 sits entirely inboard of
    # this band's 26.400 inner face -- so the two were joined only by a
    # hairline horizontal ledge at the seam. Legal as a solid, and the
    # single-solid assert passed; but on a printer it is a 0.650 mm wall
    # standing on a 0.500 mm ledge with nothing under its inboard half.
    # The user saw it as a floating region and asked for the narrow part to
    # be removed outright, which is what this constant now expresses: one
    # wall band, full thickness, ending at the step.
    #
    # Hand-derived from Housing's constant rather than imported live:
    # Housing imports THIS class (for the side window / tab derivation,
    # round 51), so importing Housing back would cycle. Re-derive by hand
    # if PoweredUpHubHousing.WALL_INNER_STEP_Z (currently 21.200, world) or
    # PoweredUpHubCover.PLATE_THICKNESS (this class's seat offset) change.
    # ROUND 70: 20.000 -> 26.000, the owner's measured tray height. This is
    # now an OWNER-SPECIFIED figure, not a derivation from Housing's cavity
    # step -- so the round-57 note above (which derived it as
    # Housing.WALL_INNER_STEP_Z - the seat) no longer governs.
    #
    # ROUND 73: 26.000 -> 24.800. The owner test-fitted the round-72 tray in
    # the REAL housing and confirmed width and height match it -- so 26.000 is
    # the COMPARTMENT's height, not the tray's. The real housing's top cover
    # carries snap-fits that come down into the top of that compartment, and
    # the tray has to leave room for them.
    #
    # The 1.200 is therefore NOT a clearance or a fudge: it is the snap-fit
    # allowance the owner measured off the real assembly. Deliberately kept as
    # its own named constant rather than folded into a smaller WALL_Z_HI,
    # because the two numbers now have different owners -- CAVITY_HEIGHT is
    # what the Housing must provide (and is exported to it as ground truth,
    # see the class docstring), while this wall is what the Tray may occupy.
    # Collapsing them would lose exactly the distinction the owner drew.
    #: Clear height of the real housing's battery compartment, measured from
    #: the Cover's inner face. Round-72 tray was built to this and fitted, so
    #: it is now GROUND TRUTH FOR THE HOUSING, which must be re-datumed to
    #: provide it. Read by PoweredUpHubHousing; do not re-derive it there.
    CAVITY_HEIGHT = 26.000
    #: Vertical room the top cover's snap-fits need at the top of the
    #: compartment -- owner-measured on the real assembly (round 73).
    SNAP_FIT_ALLOWANCE = 1.200
    WALL_Z_HI = CAVITY_HEIGHT - SNAP_FIT_ALLOWANCE                         # 24.800
    WALL_THICKNESS = WALL_OUTER_X - WALL_INNER_X   # 0.800

    # --- Y span (round 51) -- the U's open ends. ---
    # Both raised Cover features that the old END walls used to collide
    # with (LATCH_BAND, ending at Y = -30.000; the locating groove/land,
    # starting at Y = 30.000) bound this tray's own Y-reach instead of
    # being relief-cut around: stopping SAFETY_MARGIN short of each means
    # the wall footprint never overlaps either raised band, by construction
    # rather than by a cutter this class would otherwise need. Derived live
    # from Cover (safe: Cover does not import this class or Housing).
    # ROUND 70 -- re-datumed to the Cover's BODY, 60.000 long by the owner's
    # measurement, and a real bug fixed on the way.
    #
    # THE BUG: WALL_Y_LO derived from PoweredUpHubCover.LATCH_BAND_Y_HI, which
    # since round 61 is written in the Cover's LATCH FRAME and translated at
    # build time. This class read the raw constant, so it placed the wall
    # against -29.600 while the band is actually built at -26.600 -- putting
    # the tray's end 1.700 mm OUTBOARD of the Cover's own plate edge, hanging
    # off the part. Round 61 introduced the frame and never propagated it
    # here; nothing caught it because the tray's own single-solid and
    # dimensional checks are all internal, and the seated-interference test
    # that would have seen it is one of the 13 xfailed cross-datum tests.
    #
    # THE FIX, and why it is a re-datum rather than a +3.000: the owner's
    # 60.000 is exactly the Cover's body length, so these now derive from the
    # BODY EDGES themselves. That is the same span as "between the two lines'
    # OUTER faces" -- the lines sit at [-27.800, -26.600] and [31.000, 32.200],
    # so their outer faces are 60.000 apart. Deriving from PLATE_Y_LO/HI means
    # no frame translation is involved at all, so this class can no longer be
    # wrong about which frame a Cover constant lives in.
    #
    # CONSEQUENCE, handled in _build_line_reliefs: the floor now lands ON both
    # raised lines (0.800 and 0.400 proud). It is relieved over each.
    WALL_Y_LO = PoweredUpHubCover.PLATE_Y_LO     # -27.800
    WALL_Y_HI = PoweredUpHubCover.PLATE_Y_HI     #  32.200

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
    # ROUND 72 -- the whole strap assembly (corridor, cap rebate, and hence
    # the cap plate) is CENTRE-ALIGNED WITH THE SIDE TABS by owner direction,
    # not left on Y = 0.
    #
    # Read from the Cover's window sill rather than from TAB_Y_CENTER purely
    # because of class-body evaluation order -- the tab block is defined
    # below this one, so naming TAB_Y_CENTER here would be a NameError. It is
    # the SAME datum, and __init__ asserts the two agree so this cannot drift
    # into two different "centres" if one of them is ever re-pointed.
    STRAP_Y_CENTER = PoweredUpHubCover.WINDOW_SILL_Y_CENTER                # 2.000
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
    # ROUND 71 -- the tab is DERIVED FROM THE COVER, which is now ground truth.
    #
    # The Cover is frozen; the Tray and Housing come backward to it. The tab's
    # Y length and position are therefore no longer this class's own numbers:
    # they are the Cover's window sill, read live. That also closes the
    # round-64 flag -- the sill was moved to 23.500 wide at centre +2.000 while
    # the tab stayed 24.000 at centre 0.000, so the sill overhung the window
    # (which the Housing cuts FROM this tab) by 1.750 on its +Y edge. Deriving
    # both from one source makes that mismatch unrepresentable rather than
    # merely fixed.
    # ROUND 72 -- these four were literals (27.200 / 28.000 / 28.400 /
    # 28.320) that silently encoded the OLD wall face. The tab stands ON the
    # side wall, so when WALL_OUTER_X moved 27.200 -> 26.250 a literal root
    # would have left the tab floating 0.950 mm outboard of the wall it is
    # supposed to grow from -- geometry that still unions into one solid and
    # still passes every dimensional check on the tab itself. Derived now, so
    # the proud offsets (what the tab actually IS: 0.800 pad, 1.200 border,
    # 0.320 rib) survive any further move of the wall.
    TAB_ROOT_X = WALL_OUTER_X          # side-wall face the tab stands on
    TAB_PAD_X = TAB_ROOT_X + 0.800     # 0.800 mm proud
    TAB_PAD_Y_HALF = PoweredUpHubCover.WINDOW_SILL_WIDTH / 2.0    # 11.750
    TAB_Y_CENTER = PoweredUpHubCover.WINDOW_SILL_Y_CENTER          # 2.000
    # Owner-measured 7.500 from the BOTTOM OF THE COVER, i.e. world Z. This
    # class's own frame is the tray's underside, one PLATE_THICKNESS above
    # that, so the local value is the measurement less the seat offset.
    TAB_PAD_Z_HI = 7.500 - PoweredUpHubCover.PLATE_THICKNESS       # 6.300
    TAB_LEDGE_X = TAB_ROOT_X + 1.200   # the border's own face
    TAB_RIB_X = TAB_PAD_X + 0.320      # 0.320 mm proud of the pad
    TAB_RIB_Y_HALF = 8.800
    TAB_RIB_1_Z = (0.720, 1.680)   # == (1.920, 2.880) - 1.200
    TAB_RIB_2_Z = (2.720, 3.680)   # == (3.920, 4.880) - 1.200
    TAB_ROUND_R = 3.600
    # ROUND 71 -- these two are DERIVED, and the invariant they express is the
    # whole reason the tab's corners are true round-overs.
    #
    # The outline's corner is a threePointArc from (yh, cz) via a 45-degree
    # point to (ly, zhi). Those three points lie on a circle of radius
    # TAB_ROUND_R centred at (ly, cz) ONLY IF
    #
    #       TAB_ROUND_R == yh - ly == zhi - cz
    #
    # At the original numbers all three were 3.600 and it was an exact quarter
    # circle. Nothing said so, and a first round-71 attempt set the height from
    # the owner's measurement and merely SCALED cz -- leaving 11.750 - 8.400 =
    # 3.350 against 6.300 - 3.150 = 3.150 against r = 3.600, three different
    # values. OCCT drew an arc through them regardless; it just was not the arc
    # intended. Measured on the built solid it bulged 0.062 mm past each side
    # and 0.102 mm past the top -- which is how it was caught, since the tab
    # then failed to match the sill it was supposed to equal.
    #
    # Deriving both keeps the invariant true for the inset (frame) pass too:
    # inset shrinks yh, zhi and r by the same amount while ly and cz hold, so
    # all three stay equal automatically.
    TAB_LEDGE_Y_HALF = TAB_PAD_Y_HALF - TAB_ROUND_R    # 8.150, round-over centre |Y|
    TAB_ROUND_CZ = TAB_PAD_Z_HI - TAB_ROUND_R          # 2.700, round-over centre Z
    TAB_FRAME_WIDTH = 1.200   # uniform border width, see the retired
    # PoweredUpHubCover._build_side_handle docstring (round 47) for the
    # full derivation of this border from the tab's own outline.

    def __init__(self, profile: ToleranceProfile | str | None = None) -> None:
        if profile is None or isinstance(profile, str):
            prof = get_profile(profile) if isinstance(profile, str) else get_profile()
        else:
            prof = profile
        self._profile = prof

        # Round 57 removed the upper wall band, and with it the two fields
        # that existed only to place it: the clearance-adjusted upper outer
        # face, and a wall top derived from Housing's deck underside. The
        # wall's top is now the plain class constant WALL_Z_HI -- Housing's
        # own step -- so nothing here depends on the deck's height any more.
        #
        # Consequence worth knowing rather than rediscovering: the wall no
        # longer reaches the pack's top (local Z = FLOOR_THICKNESS + 20.900
        # = 23.600, against a 20.000 wall). Above WALL_Z_HI the pack is
        # confined by Housing's own cavity wall, not by this part.

        # Strap corridor width in X at its two ends -- the strap's own
        # nominal thickness plus running clearance both sides, i.e. the
        # round-53 slot width, kept unchanged.
        self._strap_slot_x = self.STRAP_THICKNESS_TARGET + 2 * prof.free.radial
        # The cap plate spans BETWEEN the two corridor ends, not under
        # them: the strap has to reach the tray's interior somewhere, and
        # those two ends are where it does. Stopping the rebate at the
        # corridor ends' inner edges leaves them open top-to-bottom.
        self._cap_x_half, _ = self.cap_rebate_half_extents(prof)

        # Round 72: STRAP_Y_CENTER has to be read from the Cover directly
        # (class-body ordering -- see its own comment), so this is what stops
        # it and TAB_Y_CENTER silently becoming two different "centres".
        # Falsifier: re-point either one at a different datum and this fires.
        assert self.STRAP_Y_CENTER == self.TAB_Y_CENTER, (
            f"the strap assembly is centred at Y = {self.STRAP_Y_CENTER} but "
            f"the side tabs are at Y = {self.TAB_Y_CENTER}; they are required "
            "to be the same datum (owner: 'center align with the side tabs')"
        )
        # The rebate MOVED in Y this round, toward +Y. Its clearance from the
        # side walls used to be symmetric and comfortable; it is now
        # asymmetric, and the walls themselves moved inboard 0.950 in the
        # same round. Two independent changes shrinking the same margin is
        # exactly when a "well inside" comment stops being true, so assert it
        # rather than restate it.
        _reb_y_hi = self.STRAP_Y_CENTER + self.STRAP_CAP_Y_HALF
        _reb_y_lo = self.STRAP_Y_CENTER - self.STRAP_CAP_Y_HALF
        assert self.WALL_Y_LO < _reb_y_lo and _reb_y_hi < self.WALL_Y_HI, (
            f"the cap rebate spans Y [{_reb_y_lo:.3f}, {_reb_y_hi:.3f}], "
            f"outside the tray's own Y span "
            f"[{self.WALL_Y_LO:.3f}, {self.WALL_Y_HI:.3f}]"
        )
        assert self._cap_x_half < self.WALL_INNER_X, (
            f"the cap rebate reaches |X| = {self._cap_x_half:.3f}, into the "
            f"side walls' inner face at {self.WALL_INNER_X:.3f}"
        )
        # The strap corridor reaches FURTHER out in X than the cap rebate does
        # -- it is the tightest interior feature against the wall, and it was
        # the one thing here with no guard. Round 72 thickened the wall
        # inboard by 1.200, which spends margin on exactly this clearance, so
        # it gets an assertion rather than a comment. Currently 24.250 -
        # 22.900 = 1.350 mm.
        _corridor_x_half = self.STRAP_HOLDER_X + self._strap_slot_x / 2.0
        assert _corridor_x_half < self.WALL_INNER_X, (
            f"the strap corridor reaches |X| = {_corridor_x_half:.3f}, into "
            f"the side walls' inner face at {self.WALL_INNER_X:.3f} -- the "
            "wall has been thickened past what the strap route allows"
        )

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
        part = part.cut(self._build_line_reliefs())
        part = part.cut(self._build_hook_notches())

        # One piece again as of round 55: the floor is what joins the two
        # otherwise-disconnected side walls, so this assertion is also the
        # regression net for the floor's own seam overlaps.
        assert len(part.solids().vals()) == 1, (
            "Expected single solid, got multiple pieces"
        )
        return part

    def _build_side_wall(self, x_sign: int) -> cq.Workplane:
        """One side wall: a single full-thickness slab spanning the tray's
        full (open-ended) Y reach -- see class docstring's *U shape*.

        One band, not two. It stops AT :attr:`WALL_Z_HI` and never goes
        past it: above that height Housing's cavity narrows to an inner
        face of 26.400, so this wall's wide (``WALL_OUTER_X``) section is
        only legal below the step. (Round 72: that 26.400 is OUR Housing's
        number and is itself unverified -- this wall's own face is now the
        owner-measured 26.250 and no longer derives from it. The Housing's
        Z re-datum is a separate open item; see WALL_INNER_STEP_Z there.) Following the narrowing upward is what
        round 55 did, and it produced a wall whose upper band shared no X
        range with its lower one -- see the class-level comment on
        :attr:`WALL_Z_HI` for why that is gone.

        Overshooting the step is the other failure mode this bound
        prevents: a version that let the slab run `overlap` past it for
        seam safety drove the wall 0.05 mm into Housing's thickened band
        (4.784 mm^3 -- caught by Tray x Housing interference, not by the
        single-solid assert, which knows nothing about Housing).
        """
        return self._x_slab(
            x_sign, self.WALL_OUTER_X, self.WALL_THICKNESS,
            0.0, self.WALL_Z_HI,
        )

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

    def _build_line_reliefs(self) -> cq.Workplane:
        """Underside pockets clearing the Cover's two raised locating lines
        (round 70).

        Rounds 51-69 kept this tray's Y reach SHORT of both raised bands, so
        it never touched them. The owner's 60.000 length spans the Cover's
        whole body, which puts the floor directly over both -- the latch band
        standing 0.800 proud of the plate and the tongue-end line 0.400. Left
        alone that is a hard interference: the tray would rock on two supports
        of different height and never seat.

        Relieved rather than the tray being raised to sit ON them, because
        they are NOT the same height. Seating on the taller latch band would
        leave the tongue end 0.400 mm in the air -- a rocking part that still
        passes every dimensional check. Relieved, the tray keeps a single flat
        seat on the plate itself, which is the only surface that is level
        across the whole span.

        Each pocket is the line's own footprint grown by a running clearance
        on the three faces that matter, and cut with an overcut on the
        outboard/underside faces, which open into free space. The INBOARD
        face is bounded by the line's own extent rather than overcut -- past
        it is the tray's own floor, and an unbounded pocket there would eat
        the seat this exists to protect.
        """
        c = self._profile.free.radial
        overcut = 1.0
        # The Cover's latch-end line lives in its LATCH frame; translate it
        # the same way the Cover does. This is the single place this class
        # touches that frame, and it does so explicitly -- see WALL_Y_LO for
        # the bug that came from reading the raw constant.
        latch_dy = PoweredUpHubCover.PLATE_Y_LO - PoweredUpHubCover.LATCH_DATUM_Y
        lines = (
            (PoweredUpHubCover.LATCH_BAND_Y_LO + latch_dy,
             PoweredUpHubCover.LATCH_BAND_Y_HI + latch_dy,
             PoweredUpHubCover.LATCH_BAND_THICKNESS),
            (PoweredUpHubCover.GROOVE_Y_LO,
             PoweredUpHubCover.GROOVE_Y_HI,
             PoweredUpHubCover.GROOVE_THICKNESS),
        )

        pockets = None
        for y_lo, y_hi, cover_thickness in lines:
            # How far the line stands proud of the plate == how deep the
            # pocket must be, plus a clearance so the two never touch.
            proud = cover_thickness - PoweredUpHubCover.PLATE_THICKNESS
            depth = proud + c
            outboard = y_lo < 0.0
            p_lo = (y_lo - overcut) if outboard else (y_lo - c)
            p_hi = (y_hi + c) if outboard else (y_hi + overcut)
            pocket = rounded_box(
                width=4 * self.WALL_OUTER_X,      # clear across, waste in X
                depth=p_hi - p_lo,
                height=depth + overcut,
                corner_r=0.0,
                center=(0.0, (p_lo + p_hi) / 2.0, -overcut),
            )
            pockets = pocket if pockets is None else pockets.union(pocket)

        assert pockets is not None, "no line reliefs built"
        return pockets

    def _build_hook_notches(self) -> cq.Workplane:
        """Clear the Cover's two latch fingers where they stand proud of the
        plate edge (round 70).

        The Cover's finger is deliberately built 0.050 mm INBOARD of its own
        plate edge, so that it fuses to the plate by volume instead of meeting
        it on a coincident face (see ``PoweredUpHubCover.__init__``'s fusion
        assertion). At the old length this tray stopped well short and never
        met it. At the owner's 60.000 -- which is the plate edge exactly --
        that 0.050 mm becomes a real interference: measured 2.1875 mm^3 in two
        lumps at ``X = +-[5.750, 18.250]``, i.e. precisely the hook footprint.

        A 0.050 mm overlap is small enough to look like noise and be
        "tolerance-adjusted" away. It is not noise: the parts genuinely cannot
        assemble, and the fix belongs on THIS part because the Cover's overlap
        is load-bearing -- removing it there would unfuse the latch from the
        lid.

        Cut over the hook's NOMINAL footprint plus a clearance each side, not
        the printed one: the printed hook is already narrower by the lateral
        running clearance, so notching to nominal leaves that clearance intact
        rather than consuming it.
        """
        lg = get_latch_geometry(self._profile)
        c = self._profile.free.radial
        overcut = 1.0

        # Where the Cover's finger actually stands, in the built frame.
        latch_dy = PoweredUpHubCover.PLATE_Y_LO - PoweredUpHubCover.LATCH_DATUM_Y
        finger_inner = (
            PoweredUpHubCover.U_FINGER_CL_Y
            + PoweredUpHubCover.FINGER_WALL / 2.0
            + latch_dy
        )
        y_hi = finger_inner + c
        y_lo = self.WALL_Y_LO - overcut

        assert y_hi > self.WALL_Y_LO, (
            f"the finger's inner face ({finger_inner:.3f}) is outboard of the "
            f"tray's own end ({self.WALL_Y_LO:.3f}) -- there is nothing to "
            "notch, so this cutter would remove material for no reason"
        )

        x_lo = lg.hook_pitch / 2.0 - c
        x_hi = lg.hook_pitch / 2.0 + lg.hook_width + c

        notches = None
        for sign in (-1.0, 1.0):
            lo, hi = sorted((sign * x_lo, sign * x_hi))
            notch = rounded_box(
                width=hi - lo,
                depth=y_hi - y_lo,
                height=self.WALL_Z_HI + 2 * overcut,
                corner_r=0.0,
                center=((lo + hi) / 2.0, (y_lo + y_hi) / 2.0, -overcut),
            )
            notches = notch if notches is None else notches.union(notch)
        return notches

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
            center=(0.0, self.STRAP_Y_CENTER, -overcut),
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
          both well inside ``WALL_INNER_X`` = 25.450), so this pocket
          never reaches material that is doing another job. Verified by
          ``test_cap_rebate_stays_clear_of_the_side_walls``.
        """
        overcut = 1.0
        return rounded_box(
            width=2 * self._cap_x_half,
            depth=2 * self.STRAP_CAP_Y_HALF,
            height=self.STRAP_CAP_THICKNESS + overcut,
            corner_r=0.0,
            center=(0.0, self.STRAP_Y_CENTER, self.STRAP_CAP_Z),
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
        yc = self.TAB_Y_CENTER

        # The corner is a TRUE round-over only while
        #     TAB_ROUND_R == yh - ly == zhi - cz
        # holds -- see TAB_LEDGE_Y_HALF / TAB_ROUND_CZ. Asserted at both the
        # outer pass and the inset (frame) pass, because the inset reduces yh,
        # zhi and r together and the equality must survive that.
        #
        # This is not decoration: violating it does NOT raise anywhere in
        # OCCT. threePointArc happily fits a circle through any three
        # non-collinear points, so the failure is a silently wrong shape --
        # which is exactly how round 71's first attempt shipped a tab 0.124 mm
        # too long and 0.102 mm too tall.
        for _inset in (0.0, self.TAB_FRAME_WIDTH):
            _r = self.TAB_ROUND_R - _inset
            _yh = self.TAB_PAD_Y_HALF - _inset
            _zhi = self.TAB_PAD_Z_HI - _inset
            assert abs((_yh - ly) - _r) < 1e-9 and abs((_zhi - cz) - _r) < 1e-9, (
                f"the tab's corner is not a true round-over at inset "
                f"{_inset:.3f}: radius {_r:.3f}, but yh - ly = {_yh - ly:.3f} "
                f"and zhi - cz = {_zhi - cz:.3f}. All three must be equal or "
                "the arc is some other circle and the tab silently changes size"
            )

        def _outline(x_at: float, inset: float) -> cq.Workplane:
            yh = self.TAB_PAD_Y_HALF - inset
            r = self.TAB_ROUND_R - inset
            zhi = self.TAB_PAD_Z_HI - inset
            d = r * 0.7071
            return (
                cq.Workplane("YZ")
                .transformed(offset=cq.Vector(0.0, 0.0, side * x_at))
                .moveTo(yc - yh, 0.0)
                .lineTo(yc - yh, cz)
                .threePointArc((yc - ly - d, cz + d), (yc - ly, zhi))
                .lineTo(yc + ly, zhi)
                .threePointArc((yc + ly + d, cz + d), (yc + yh, cz))
                .lineTo(yc + yh, 0.0)
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
                center=((x_lo + x_hi) / 2.0, self.TAB_Y_CENTER, z_lo),
            )

        for z_lo, z_hi in (self.TAB_RIB_1_Z, self.TAB_RIB_2_Z):
            tab = tab.union(_band(self.TAB_RIB_X, self.TAB_RIB_Y_HALF, z_lo, z_hi))
        return tab

    @property
    def solid(self) -> cq.Workplane:
        return self._solid
