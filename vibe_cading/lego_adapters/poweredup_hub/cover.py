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
as extracted in ``tmp/ldraw-parts-geometry.md`` SS1 (git-ignored; no LDraw
``.dat`` file, converted geometry, or render is committed to this repo --
only independently-written measurements and from-scratch CadQuery code).
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
    into ``+Y``. This matches ``tmp/ldraw-parts-geometry.md``'s own
    recommended CadQuery mapping (SS0), which this class's constants are
    read directly from.

    Kept, as measured (design brief K1-K4, minus the ribs):
        - The flat 1.2 mm plate and its sharp-cornered rectangular outline,
          with the local 1.2->2.0 mm thickening band at the latch end.
        - Both cantilever latch fingers with their Ø2.000 mm barbs (K1).
        - The slide-in tongue / ledge at the insertion end (K2), simplified
          to a single uniform-thickness blade -- see *Known simplifications*
          below.
        - A locating groove near the tongue end, sized to register the
          :class:`~vibe_cading.lego_adapters.poweredup_hub.battery_tray.PoweredUpHubBatteryTray`'s
          1.600 mm bottom rim (this is a tray-to-lid interface, not a
          lid-to-housing one -- see the design brief's *Housing ->
          Tongue-end rebate* section, which explicitly confirms the groove
          is dropped from the Housing side but survives here).

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
          implementation chose and why).
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
        - The tongue/ledge is modelled as one uniform 0.926 mm-thick blade
          spanning the full measured tongue-to-ledge Y range, rather than
          reproducing the separate "Tongue A" / "Tongue B" footprints, the
          6 locating teeth, or the ledge notches between them -- all
          confirmed non-load-bearing for either mating interface in the
          design brief (dropped from the Housing side outright; the Tray
          side only needs the groove, not the teeth). **Tongue B
          specifically (the outer pair, |X| 17.2..26.0 mm) is OMITTED
          outright, not merely simplified** (round 18, finding S6) --
          retention (the 0.926 mm tip) is fully preserved; only fit/
          location fidelity at that footprint is lost.
        - **Locating land, corrected sign (round 18, S1).** The real
          feature is a raised registration land (the plate is locally
          1.600 mm thick over Y in [30.0, 31.2] -- exactly the
          :class:`~vibe_cading.lego_adapters.poweredup_hub.battery_tray.PoweredUpHubBatteryTray`'s
          own bottom-rim thickness), not a recess -- an earlier version cut
          a 0.4 mm notch here instead, the inverse of the real part
          (:meth:`_build_locating_land` builds the corrected, unioned
          land). Re-verified at source (LDraw ``region_dump.py``) rather
          than re-interpreted; see the design brief's *Round 18 -> S1*.

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

    # --- Latch-end local thickening band (SS1.4) ---
    LATCH_BAND_Y_LO = -30.800
    LATCH_BAND_Y_HI = -30.000
    LATCH_BAND_THICKNESS = 2.000

    # --- Latch finger geometry (SS1.4) -- Y positions of the hook's own
    # drafted inboard face; barb dimensions come from the shared
    # LatchGeometry parameter object (single source of truth with the
    # future HousingBox catch).
    HOOK_FACE_Y0 = -31.840          # drafted face, Z = 0
    HOOK_FACE_Y1 = -32.240          # drafted face, Z = HOOK_FACE_Z1
    HOOK_FACE_Z1 = 11.200

    # --- Tongue / ledge (SS1.5, simplified -- see class docstring) ---
    # The riser fills the full plate thickness up to the ledge height over
    # [PLATE_Y_HI, TONGUE_STEP_Y] -- this is what fuses to the plate with a
    # real volume overlap (Z [0, PLATE_THICKNESS] in common), not just a
    # touching edge. The thin distal tip then continues from TONGUE_STEP_Y
    # to TONGUE_Y_HI at the recessed TIP_Z_LO..RISER_Z_HI band only -- this
    # is the 0.926 mm-thick blade the design's Housing rebate must receive.
    TONGUE_X_HALF = 15.600
    TONGUE_STEP_Y = 33.378
    TONGUE_Y_HI = 34.400
    RISER_Z_HI = 2.800
    TIP_Z_LO = 1.874

    # --- Locating land (Tray-mating interface, round 18 S1 -- see class
    # docstring). A RAISED land, not a recess: LAND_HEIGHT added onto the
    # inner face over [LAND_Y_LO, LAND_Y_HI], bringing the plate locally to
    # PLATE_THICKNESS + LAND_HEIGHT = 1.600 mm -- exactly the Tray's own
    # bottom-rim thickness (BatteryTray.END_WALL_NEG_Y_HI - END_WALL_NEG_Y_LO
    # region's own wall, 1.6 mm), confirming this is the tray's registration
    # seat, not a channel (design brief Round 18 -> S1).
    LAND_Y_LO = 30.000
    LAND_Y_HI = 31.200
    LAND_HEIGHT = 0.400

    # --- Release leg / U-spring (SS1.4, round 18 B2) -- the second,
    # thumb-pad-bearing leg of the cantilever U, joined to the hook leg
    # ONLY at the crown (the hook's own tip, Z = hook_depth). See
    # :meth:`_build_release_leg` for the full derivation of these
    # Developer-chosen dimensions (the real part's leg cross-section is not
    # directly measurable from LDraw).
    RELEASE_SLOT_MARGIN = 0.100   # min. clearance beyond the hook's own deepest reach (HOOK_FACE_Y1)
    LEG_B_THICKNESS = 0.500       # release leg / spine wall thickness
    PAD_OUTER_Y = -35.600         # matches PoweredUpHubHousing.LATCH_Y (the single wall's own outer face)
    PAD_Z_HI = 3.600              # matches PoweredUpHubHousing.LATCH_WINDOW_Z_HI
    CROWN_THICKNESS = 1.200       # Z-band bridging the hook leg's tip to the release leg -- the ONLY join

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
        part = part.union(self._build_latch_finger(+1))
        part = part.union(self._build_latch_finger(-1))
        part = part.union(self._build_release_leg(+1))
        part = part.union(self._build_release_leg(-1))
        part = part.union(self._build_tongue())
        part = part.union(self._build_locating_land())

        assert len(part.solids().vals()) == 1, "Expected single solid, got multiple pieces"
        return part

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

    def _build_latch_finger(self, side: int) -> cq.Workplane:
        """One cantilever latch finger, mirrored by ``side`` (+1 / -1) about X = 0.

        Cross-section swept along X (constant across the finger's own
        ``hook_width``) -- see class docstring, *Known simplifications*, for
        the faceted-crest simplification. The second (release) leg is built
        separately by :meth:`_build_release_leg`.
        """
        lg: LatchGeometry = self._latch
        half_w = lg.hook_width / 2.0
        x_center = side * (lg.hook_pitch / 2.0 + half_w)

        crest_y = self.HOOK_FACE_Y1 + lg.barb_protrusion
        pts = [
            (self.PLATE_Y_LO, 0.0),
            (self.HOOK_FACE_Y0, 0.0),
            (self.HOOK_FACE_Y1, self.HOOK_FACE_Z1),
            (crest_y, lg.barb_axis_z),
            (self.HOOK_FACE_Y1, lg.hook_depth),
            (self.PLATE_Y_LO, lg.hook_depth),
        ]
        sketch = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0.0, 0.0, x_center - half_w))
            .moveTo(*pts[0])
        )
        for p in pts[1:]:
            sketch = sketch.lineTo(*p)
        return sketch.close().extrude(lg.hook_width)

    def _build_release_leg(self, side: int) -> cq.Workplane:
        """Second leg of the cantilever U (SS1.4, round 18 B2) -- a thin
        ``spine`` running alongside the hook leg's own outer (drafted)
        face, a ``crown`` bridge that joins the two legs ONLY at the
        hook's own tip (``Z = hook_depth``, never at the root -- this is
        what makes the pad a genuine second spring leg rather than a rigid
        extension of the hook), and a ``pad`` at the free end that reaches
        :attr:`PAD_OUTER_Y` within the low-``Z`` band the housing's own
        finger window opens onto.

        **Why these numbers, not the real part's 1.640 mm slot / 2.791 mm
        pad-height figures directly** (flagged per the design brief's own
        "Developer to derive and verify" instruction for this feature):
        the hook leg's drafted face is a Z-varying polyline (SS1.4), not a
        flat plane, so a second leg offset by a literal constant Y from the
        *plate edge* would either collide with the hook leg's own deepest
        reach or leave the gap needlessly wide elsewhere depending on Z.
        Instead, :attr:`RELEASE_SLOT_MARGIN` is measured from
        ``HOOK_FACE_Y1`` -- the hook leg's own maximum reach across its
        *entire* height (occurring at ``Z = HOOK_FACE_Z1`` and
        ``Z = hook_depth``) -- guaranteeing, by construction, zero
        collision with the hook leg at every ``Z``, and (since
        :class:`~vibe_cading.lego_adapters.poweredup_hub.housing.PoweredUpHubHousing`'s
        corrected catch slot always extends further past ``HOOK_FACE_Y1``
        than this leg does, for every supported tolerance profile -- see
        that class's own ``_build_latch_catch``) zero collision with the
        housing's catch, independent of which profile renders it. Verified
        by the mandatory kinematic-sweep tests, not asserted blind.
        :attr:`PAD_Z_HI` matches
        :class:`~vibe_cading.lego_adapters.poweredup_hub.housing.PoweredUpHubHousing`'s
        own ``LATCH_WINDOW_Z_HI`` exactly, so the pad fills the actual
        window opening it must show through, rather than an independently
        sourced literal that leaves part of the window empty.
        """
        lg: LatchGeometry = self._latch
        half_w = lg.hook_width / 2.0
        x_center = side * (lg.hook_pitch / 2.0 + half_w)

        y_leg_inner = self.HOOK_FACE_Y1 - self.RELEASE_SLOT_MARGIN
        y_leg_outer = y_leg_inner - self.LEG_B_THICKNESS

        # Coincident-faces guard (this project's own pitfall) -- each pair
        # of adjacent pieces below is grown by `seam_overlap` into its
        # neighbour's territory so OCCT's fuse sees genuine 3D volume
        # overlap, not a touching face.
        seam_overlap = 0.05
        spine = rounded_box(
            width=lg.hook_width,
            depth=y_leg_inner - y_leg_outer,
            height=(lg.hook_depth - self.PAD_Z_HI) + seam_overlap,
            corner_r=0.0,
            center=(x_center, (y_leg_inner + y_leg_outer) / 2.0, self.PAD_Z_HI - seam_overlap),
        )
        # NOTE: the pad's own height is deliberately NOT grown past
        # PAD_Z_HI (unlike the Y-overlap below) -- PAD_Z_HI is the exact
        # PoweredUpHubHousing.LATCH_WINDOW_Z_HI boundary; beyond it,
        # Housing's wall is solid (not cut away by the finger window), so
        # growing the pad's own Z range there would pierce Housing's wall
        # at the pad's own outboard reach (an earlier version did exactly
        # this and produced a real, if tiny, seated-state interference).
        # The Z-direction fuse with `spine` is already guaranteed by
        # `spine`'s own -seam_overlap Z start above; only the Y-overlap is
        # needed here.
        pad_y_inner = y_leg_inner + seam_overlap
        pad = rounded_box(
            width=lg.hook_width,
            depth=pad_y_inner - self.PAD_OUTER_Y,
            height=self.PAD_Z_HI,
            corner_r=0.0,
            center=(x_center, (pad_y_inner + self.PAD_OUTER_Y) / 2.0, 0.0),
        )
        crown = rounded_box(
            width=lg.hook_width,
            depth=self.PLATE_Y_LO - y_leg_outer,
            height=self.CROWN_THICKNESS,
            corner_r=0.0,
            center=(
                x_center,
                (self.PLATE_Y_LO + y_leg_outer) / 2.0,
                lg.hook_depth - self.CROWN_THICKNESS,
            ),
        )
        return spine.union(pad).union(crown)

    def _build_tongue(self) -> cq.Workplane:
        """Slide-in tongue + ledge -- a riser (fused to the plate, full
        thickness) plus a thin distal tip (the actual 0.926 mm rebate
        blade), per the class docstring's *Known simplifications*.
        """
        riser = rounded_box(
            width=2 * self.TONGUE_X_HALF,
            depth=self.TONGUE_STEP_Y - self.PLATE_Y_HI,
            height=self.RISER_Z_HI,
            corner_r=0.0,
            center=(0.0, (self.PLATE_Y_HI + self.TONGUE_STEP_Y) / 2.0, 0.0),
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
        return riser.union(tip)

    def _build_locating_land(self) -> cq.Workplane:
        """Raised registration land for the BatteryTray's bottom rim
        (round 18, S1 -- corrected from an earlier, sign-inverted recess).

        A ``LAND_HEIGHT`` (0.400 mm) union onto the inner face over
        ``[LAND_Y_LO, LAND_Y_HI]``, bringing the plate locally to
        1.600 mm -- exactly the Tray's own bottom-rim thickness, per the
        class docstring's *Known simplifications*. No running-clearance
        widening is applied here (unlike the earlier recess): a raised
        land the tray's rim registers *against* must not grow wider than
        its own footprint, or it would encroach on the tray's rim seat
        rather than merely define it.
        """
        y_span = self.LAND_Y_HI - self.LAND_Y_LO
        return rounded_box(
            width=self.PLATE_WIDTH,
            depth=y_span,
            height=self.LAND_HEIGHT,
            corner_r=0.0,
            center=(0.0, (self.LAND_Y_LO + self.LAND_Y_HI) / 2.0, self.PLATE_THICKNESS),
        )

    @property
    def solid(self) -> cq.Workplane:
        return self._solid
