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

"""12 mm RC hex-wheel-adapter nut — one component of the fused hex-hub +
bearing-housing assembly (see :mod:`vibe_cading.rc.hex_hub_bearing.hex_hub_with_bearing`).

Coordinate system
------------------
Z = 0                : bottom (mating) face — plain flat, no register feature.
Z = ``thickness``    : top face — outward-facing chamfered hex, wheel-hex interface.
Centred at X = 0, Y = 0 on the hex prism's own rotation axis.

Design intent
-------------
A standard 1:10-scale RC "12 mm hex" wheel-hub adapter: a hexagonal prism
with a through-bore for a shaft/axle to pass through, plus a blind bearing
pocket sunk into its outward (top) face so it seats the *same* MR85-2RS
bearing that :class:`~vibe_cading.rc.hex_hub_bearing.bearing_hex_housing.BearingHexHousing`
seats on the shaft side.  The pocket is blind (not through) because the
bottom face is the union seam with the housing and must stay flat; it
follows :class:`~vibe_cading.rc.freespin_hex_hub.FreespinHexHub`'s existing
blind-pocket convention (bore cut through-all first at the narrower shaft-
clearance diameter, then the wider bearing-OD pocket cut blind from the
outward face, so the bore's end is swallowed by — and centred within — the
pocket floor).  No register/spigot feature — per the approved design brief
(``docs/design_plans/2026-08-25-rc-hex-hub-bearing_design.md``, D2a Round 2),
this class is normally consumed as one half of
:class:`~vibe_cading.rc.hex_hub_bearing.hex_hub_with_bearing.HexHubWithBearing`,
which ``.union()``s it flush against the housing.
It remains independently buildable/exportable per the project's Multi-Part
Assemblies rule.
"""

from __future__ import annotations

import math

import cadquery as cq

from vibe_cading.print_settings import get_profile

# ── MR85-2RS standard dimensions (hex-side bearing pocket) ────────────────
MR85_OD = 8.0  # mm - outer diameter
MR85_W = 2.5   # mm - axial width


class HexHubNut:
    """12 mm hex wheel-hub adapter nut with a free-fit through-bore and a
    blind hex-side bearing pocket.

    Parameters
    ----------
    hex_across_flats : float
        Hex outer profile measured flat-to-flat (mm).  Default 12.0 mm —
        the standard RC 1:10-scale wheel hex mounting convention.
    thickness : float
        Axial thickness of the hex prism (mm).  Default 6.0 mm.
    bore_diameter : float
        Nominal centre bore diameter (mm) for the shaft/axle to pass
        through.  Default 6.0 mm (design brief D8, Round 4 correction —
        was 4.0 mm).  The *printed* bore is wider — see :attr:`_bore_dia`.
        Note (design brief D8, revised Round 4): this now matches
        :class:`~vibe_cading.rc.freespin_hex_hub.FreespinHexHub`'s
        established convention — a generous free-running-clearance bore
        around a single uniform 5 mm-nominal stub axle.  The MR85-2RS
        bearing that :class:`BearingHexHousing` seats carries the axle via
        its 5 mm ID (a slip fit on the bearing's *inner* race); this bore
        never contacts the axle at all, it just needs clearance to pass
        through.  There is no stepped/shouldered-shaft assumption.
    bearing_od : float
        Outer diameter of the hex-side bearing (mm).  Default 8.0 mm for
        MR85-2RS — the same bearing seated on the shaft side by
        :class:`BearingHexHousing`.
    bearing_width : float
        Axial width of the hex-side bearing (mm).  Default 2.5 mm for
        MR85-2RS.  Only used to size the pocket's depth (see
        :attr:`_pocket_depth`) — this pocket is blind, so unlike
        :class:`BearingHexHousing` it does not also set the part's own
        overall thickness.
    hex_chamfer : float
        Chamfer size applied to all sharp hex edges (mm).  Default 0.5 mm,
        matching :class:`~vibe_cading.rc.freespin_hex_hub.FreespinHexHub`'s
        existing default for visual/print-edge consistency across the
        RC-hex-part family.
    profile : str | None
        Tolerance profile name from ``print_profiles.json``.  ``None``
        uses the globally-configured default.  The through-bore and the
        bearing pocket both use ``free`` fit grade — the shaft/axle passes
        through loosely (design brief D5), and the bearing drops in/pops
        out by hand rather than being press-fit, matching the shaft-side
        bearing's fit grade so both ends of the assembly seat the
        identical bearing the same way.
    """

    def __init__(
        self,
        hex_across_flats: float = 12.0,
        thickness: float = 6.0,
        bore_diameter: float = 6.0,
        bearing_od: float = MR85_OD,
        bearing_width: float = MR85_W,
        hex_chamfer: float = 0.5,
        profile: str | None = None,
    ) -> None:
        self.hex_across_flats = float(hex_across_flats)
        self.thickness = float(thickness)
        self.bore_diameter = float(bore_diameter)
        self.bearing_od = float(bearing_od)
        self.bearing_width = float(bearing_width)
        self.hex_chamfer = float(hex_chamfer)
        self._prof = get_profile(profile)
        self._solid = self._build()

    # ── Derived geometry ────────────────────────────────────────────────

    @property
    def _hex_circumdia(self) -> float:
        """Circumscribed circle diameter (vertex-to-vertex) of the hex (mm).

        CadQuery's ``polygon(nSides, diameter)`` takes the circumscribed
        diameter (tip-to-tip); convert from the user-facing across-flats
        measurement: ``AF = circumdia * cos(30deg)``.
        """
        return self.hex_across_flats / math.cos(math.radians(30))

    @property
    def _bore_dia(self) -> float:
        """Printed through-bore diameter after applying ``free`` radial clearance (mm).

        ``free.radial`` is a half-extra allowance on radius; doubled here
        for the diameter, per design brief D5.
        """
        return self.bore_diameter + 2.0 * self._prof.free.radial

    @property
    def _pocket_dia(self) -> float:
        """Hex-side bearing pocket diameter after ``free`` radial clearance (mm).

        Mirrors :attr:`~vibe_cading.rc.freespin_hex_hub.FreespinHexHub._pocket_dia`
        — ``free.radial`` gives ~0.3 mm total diameter play on ``fdm_standard``
        so the bearing drops in and pops out by hand.
        """
        return self.bearing_od + 2.0 * self._prof.free.radial

    @property
    def _pocket_depth(self) -> float:
        """Hex-side bearing pocket axial depth (mm).

        Mirrors :attr:`~vibe_cading.rc.freespin_hex_hub.FreespinHexHub._pocket_depth`
        exactly: ``free.axial`` prevents the bearing face from binding
        against the pocket floor, and the extra flat 0.5 mm margin (not a
        fit-grade value) lets the bearing sit proud of the hex face so it
        can be pressed flush by hand.
        """
        return self.bearing_width + self._prof.free.axial + 0.5

    # ── Build ───────────────────────────────────────────────────────────

    def _build(self) -> cq.Workplane:
        assert self._pocket_depth < self.thickness, (
            "HexHubNut: bearing pocket depth "
            f"({self._pocket_depth:.3f} mm) must be less than the part "
            f"thickness ({self.thickness:.3f} mm), or the pocket would "
            "break through the bottom (union-seam) face."
        )

        # ── 1. Hexagonal prism (Z = 0 -> thickness) ────────────────────
        part = (
            cq.Workplane("XY")
            .polygon(6, self._hex_circumdia)
            .extrude(self.thickness)
        )

        # ── 2. Through-bore, free-fit clearance ─────────────────────────
        part = (
            part
            .faces("<Z")
            .workplane()
            .circle(self._bore_dia / 2.0)
            .cutThruAll()
        )

        # ── 3. Hex-side bearing pocket, blind, free-fit clearance ────────
        # Cut *after* the through-bore (narrower) so the pocket (wider)
        # swallows the bore's top opening, leaving the bore's end as a
        # smaller-diameter step centred in the pocket floor — the same
        # sequencing `FreespinHexHub` relies on for its two blind pockets.
        # `cutBlind` with a negative distance cuts against the workplane
        # normal (inward from Z = thickness, downward), so the pocket
        # opens at the top face and terminates `_pocket_depth` mm into the
        # body, well clear of the bottom union-seam face (asserted above).
        part = (
            part
            .faces(">Z")
            .workplane()
            .circle(self._pocket_dia / 2.0)
            .cutBlind(-self._pocket_depth)
        )

        # ── 4. Chamfer all sharp hex edges ──────────────────────────────
        # `.edges("<Z")` / `.edges(">Z")` select every edge lying entirely
        # in the bottom / top plane -- this includes the 6 hex perimeter
        # edges on both faces, the bore's bottom circular entry edge
        # (`<Z`, still a through-cut end), and now the bearing pocket's
        # circular entry edge (`>Z`) rather than the bore's -- the bore's
        # own top edge no longer lies in the Z = thickness plane, since
        # step 3 swallowed it into the pocket floor.  This mirrors
        # `vibe_cading.rc.freespin_hex_hub.FreespinHexHub`'s identical
        # chamfer pattern, and is a deliberate, print-friendly side effect,
        # not an oversight: it adds a small lead-in chamfer to both the
        # bore's bottom opening and the bearing pocket's top opening.  It
        # only touches the outermost 0.5 mm of depth on each end -- the
        # bulk mid-thickness bore diameter (what Test 3 measures) is
        # unaffected, since it's governed by the through-cut radius, not
        # the chamfer.
        if self.hex_chamfer > 0:
            part = part.edges("|Z").chamfer(self.hex_chamfer)
            part = (
                part
                .edges("<Z").chamfer(self.hex_chamfer)
                .edges(">Z").chamfer(self.hex_chamfer)
            )

        assert len(part.solids().vals()) == 1, (
            "HexHubNut: expected a single contiguous solid."
        )
        return part

    @property
    def solid(self) -> cq.Workplane:
        """The CadQuery solid.  Z = 0 is the bottom (mating) face."""
        return self._solid
