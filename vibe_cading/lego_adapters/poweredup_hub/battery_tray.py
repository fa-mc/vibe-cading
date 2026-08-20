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
        - Both **outer end walls are KEPT** (``-Y``: kept exactly at
          ``-30.400..-28.800`` mm, 1.600 mm thick; ``+Y``: kept at
          ``29.200..30.800`` mm nominal thickness, simplified to a uniform
          1.600 mm rather than the real part's 29.200/29.600 mm stepped
          inner face -- see *Known simplifications*).
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
    added to the ``+Y`` end wall -- both its inner AND outer face shift
    ``+Y`` together, so the wall keeps its full 1.6 mm thickness (a
    structurally sound extension of the tray's own footprint) rather than
    locally thinning the wall to a fraction of a millimetre (which a
    same-thickness inner-face-only pocket would do, and which this
    Developer judged unprintable -- see *Known simplifications*).

    New features (design brief, not LEGO-derived):
        - **Floor** at ``Z in [0, FLOOR_THICKNESS]``, spanning the tray's
          full interior cavity -- the real part has none (only a ~10 %
          peripheral rim, per ``tmp/ldraw-parts-geometry.md`` SS2.6).
        - **Strap holders**: two full-through slots in the floor, each
          ``STRAP_WIDTH`` (20.5 mm, the round-8-confirmed opening for a
          20 mm strap) wide, positioned symmetrically about the tray's own
          Y-centre.

    Known simplifications (documented deviations, all cosmetic /
    non-load-bearing unless noted):
        - The ``+Y`` end wall's real stepped inner face (29.200 mm for the
          lower compartment, 29.600 mm for the upper) is simplified to a
          single uniform inner face at 29.200 mm (before relief) -- the
          more generous of the two, so this only ever *adds* clear volume,
          never removes it.
        - The tray's real vertical wall/top-frame transition (plain wall to
          22.400 mm, a separate top-frame feature at 27.600/28.000 mm) is
          simplified to one wall extruded straight to :attr:`WALL_Z_HI`
          (28.000 mm) -- structurally equivalent, and the real transition
          is a cosmetic frame detail, not a mating surface. **Not uniform
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
        - **Relief placement is this Developer's choice, not the design's**
          -- the design brief explicitly leaves "not yet which one" open.
          Applied to the ``+Y`` (tongue-end-side) wall only.
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
    WALL_Z_HI = 28.000  # simplified uniform wall height, see docstring

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

    # --- Relief (round-13 "1-2 mm" requirement, developer's choice) ---
    RELIEF = 1.5

    # --- Side extraction tabs, KEPT exactly per envelope (SS2.3) ---
    TAB_PAD_X = 28.000
    TAB_PAD_Y_HALF = 12.000
    TAB_PAD_Z_HI = 7.200
    TAB_LEDGE_X = 28.400
    TAB_LEDGE_Y_HALF = 8.400
    TAB_LEDGE_Z_LO = 7.200
    TAB_LEDGE_Z_HI = 8.400
    GRIP_RIB_X = 28.320
    GRIP_RIB_Y_HALF = 8.800
    GRIP_RIB_1_Z = (1.920, 2.880)
    GRIP_RIB_2_Z = (3.920, 4.880)

    # --- New floor ---
    FLOOR_THICKNESS = 1.5  # design-proposed, ~1.5 mm

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

        # +Y end wall faces, after applying the relief (see docstring).
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
        part = part.union(self._build_floor())
        part = part.union(self._build_extraction_tab(+1))
        part = part.union(self._build_extraction_tab(-1))
        part = part.cut(self._build_strap_holders())

        assert len(part.solids().vals()) == 1, "Expected single solid, got multiple pieces"
        return part

    def _cavity_y_span(self) -> tuple[float, float]:
        """Inner (cavity-facing) Y bounds -- both partitions removed, relief applied."""
        return (self.END_WALL_NEG_Y_HI, self._end_wall_pos_y_lo)

    def _build_shell(self) -> cq.Workplane:
        """Outer envelope minus the inner cavity -- both side walls (X)
        and both end walls (Y) fall out of one subtraction per band, since
        their thicknesses are just the outer-vs-inner face gap on each
        axis. Built as two stacked X-bands (round 16, Escalation 5): the
        lower band keeps the tray's original uniform wall; the upper band
        (Z >= WALL_STEP_Z) steps inward to clear Housing's own wall -- see
        the WALL_STEP_Z / WALL_OUTER_X_UPPER_NOMINAL / WALL_INNER_X_UPPER
        class-attribute comment for the interference this resolves. The
        Y-direction end walls are identical in both bands -- this is an
        X-axis-only fix.
        """
        lower = self._shell_band(self.WALL_OUTER_X, self.WALL_INNER_X, 0.0, self.WALL_STEP_Z)
        # Coincident-faces guard at the step seam -- the same OCCT
        # boolean-fuse pitfall PoweredUpHubHousing._build_side_wall's own
        # comment documents for its analogous wall step: widen the upper
        # band's wall footprint by a tiny construction-only `overlap` and
        # drop its Z start by the same amount, so the two bands share a
        # genuine overlapping volume at the seam rather than touching only
        # along the Z = WALL_STEP_Z plane (which OCCT's fuse does not
        # reliably merge). The 0.05 mm ledge this leaves at the step
        # corner is well under FDM tolerance and does not change any
        # externally-visible dimension.
        overlap = 0.05
        upper = self._shell_band(
            self._wall_outer_x_upper + overlap,
            self.WALL_INNER_X_UPPER - overlap,
            self.WALL_STEP_Z - overlap,
            self.WALL_Z_HI,
        )
        return lower.union(upper)

    def _shell_band(
        self, outer_x: float, inner_x: float, z_lo: float, z_hi: float
    ) -> cq.Workplane:
        """One Z-band of the outer-wall ring: an outer box minus an inner
        cavity box, both sharing the tray's Y footprint (``_cavity_y_span``)
        -- ``outer_x``/``inner_x`` set this band's X extent only.
        """
        y_lo_outer = self.END_WALL_NEG_Y_LO
        y_hi_outer = self._end_wall_pos_y_hi
        outer = rounded_box(
            width=2 * outer_x,
            depth=y_hi_outer - y_lo_outer,
            height=z_hi - z_lo,
            corner_r=0.0,
            center=(0.0, (y_lo_outer + y_hi_outer) / 2.0, z_lo),
        )
        cavity_y_lo, cavity_y_hi = self._cavity_y_span()
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

    def _build_floor(self) -> cq.Workplane:
        cavity_y_lo, cavity_y_hi = self._cavity_y_span()
        return rounded_box(
            width=2 * self.WALL_INNER_X,
            depth=cavity_y_hi - cavity_y_lo,
            height=self.FLOOR_THICKNESS,
            corner_r=0.0,
            center=(0.0, (cavity_y_lo + cavity_y_hi) / 2.0, 0.0),
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
        overcut = 1.0  # break cleanly through the floor's Z extent
        slots = None
        for y_center in (-self.STRAP_HOLDER_Y, self.STRAP_HOLDER_Y):
            slot = rounded_box(
                width=self.STRAP_WIDTH,
                depth=slot_depth,
                height=self.FLOOR_THICKNESS + 2 * overcut,
                corner_r=0.0,
                center=(0.0, y_center, -overcut),
            )
            slots = slot if slots is None else slots.union(slot)
        return slots

    @property
    def solid(self) -> cq.Workplane:
        return self._solid
