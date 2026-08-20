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
    all cosmetic / non-load-bearing -- flagged per this project's
    Experimental Integrity convention rather than silently applied):
        - The latch fingers are modelled as a single continuous cantilever
          hook (root -> drafted face -> barb -> tip -> back to root). The
          real part's separate pressable "thumb pad" (the outer skin
          continuing past a 1.64 mm release slot to Y = -35.6 mm) is not
          reproduced -- it is a release-ergonomics feature, not part of the
          barb/hook retention geometry the future ``HousingBox`` catch must
          mate with (which is fully preserved: hook width/pitch, barb
          diameter/position/protrusion, engagement band, draft).
        - The barb's true R1.000 mm cylindrical bead (157.5 deg arc) is
          approximated as a faceted (straight-edged) crest at the same
          position and protrusion, not a true arc -- a cosmetic rounding
          simplification, consistent with this project's chamfer/fillet
          simplification convention (see CLAUDE.md, *Reverse-engineering
          from STEP files*).
        - The tongue/ledge is modelled as one uniform 0.926 mm-thick blade
          spanning the full measured tongue-to-ledge Y range, rather than
          reproducing the separate "Tongue A" / "Tongue B" footprints, the
          6 locating teeth, or the ledge notches between them -- all
          confirmed non-load-bearing for either mating interface in the
          design brief (dropped from the Housing side outright; the Tray
          side only needs the groove, not the teeth).
        - The locating groove's exact cross-section is this Developer's own
          interpretation of an ambiguous LDraw table entry (the source
          table states a Y-band and a nominal "1.6 mm" depth figure without
          fully disambiguating which face the material is removed from);
          implemented here as a shallow rectangular recess in the inner
          face, sized against the Tray's own bottom-rim thickness via
          :func:`~vibe_cading.print_settings.get_profile`. Flagged in the
          design brief's Implementation Status for Designer confirmation.

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

    # --- Locating groove (Tray-mating interface -- see class docstring) ---
    GROOVE_Y_LO = 30.000
    GROOVE_Y_HI = 31.200
    GROOVE_DEPTH = 0.400  # removed from the inner face, see docstring

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
        part = part.union(self._build_tongue())
        part = part.cut(self._build_locating_groove())

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
        the faceted-crest / no-thumb-pad simplifications.
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

    def _build_locating_groove(self) -> cq.Workplane:
        """Shallow registration recess for the BatteryTray's bottom rim.

        See class docstring's *Known simplifications* for the interpretation
        this implements. Widened by ``profile.free.radial`` (a registration
        slide fit, not a retention surface) so the tray's rim seats without
        binding.
        """
        y_span = self.GROOVE_Y_HI - self.GROOVE_Y_LO
        clearance = self._profile.free.radial
        return rounded_box(
            width=self.PLATE_WIDTH + 2 * clearance,
            depth=y_span,
            height=self.GROOVE_DEPTH + clearance,
            corner_r=0.0,
            center=(
                0.0,
                (self.GROOVE_Y_LO + self.GROOVE_Y_HI) / 2.0,
                self.PLATE_THICKNESS - self.GROOVE_DEPTH,
            ),
        )

    @property
    def solid(self) -> cq.Workplane:
        return self._solid
