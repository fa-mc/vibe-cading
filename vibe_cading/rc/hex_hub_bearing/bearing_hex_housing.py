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

"""MR85-2RS bearing-bore housing cylinder — the other component of the fused
hex-hub + bearing-housing assembly (see
:mod:`vibe_cading.rc.hex_hub_bearing.hex_hub_with_bearing`).

Coordinate system
------------------
Z = 0                    : bottom (non-mating, axle-entry) face.
Z = ``bearing_width``    : top (mating) face — plain flat, no register feature.
Centred at X = 0, Y = 0 on the shared rotation axis.

Design intent
-------------
A plain cylinder sized to free-fit-house one MR85-2RS ball bearing
(5 x 8 x 2.5 mm ID x OD x width), reusing
:meth:`vibe_cading.mechanical.bearings.Bearing.outer_pocket` (design brief
D4/D6) rather than hand-rolling a clearance-added circle.  Uses ``free`` fit
grade (user-replaceable, drop-in/pop-out by hand) rather than ``press``, so
this bearing matches the same fit as the hex-side pocket added to
:class:`~vibe_cading.rc.hex_hub_bearing.hex_hub_nut.HexHubNut` — both ends of
the assembly seat the identical bearing the same way.  No register/spigot
feature — per the approved design brief
(``docs/design_plans/2026-08-25-rc-hex-hub-bearing_design.md``, D2a Round 2),
this class is normally consumed as one half of
:class:`~vibe_cading.rc.hex_hub_bearing.hex_hub_with_bearing.HexHubWithBearing`.
It remains independently buildable/exportable per the project's Multi-Part
Assemblies rule.
"""

from __future__ import annotations

import cadquery as cq

from vibe_cading.mechanical.bearings import Bearing
from vibe_cading.print_settings import get_profile

# ── MR85-2RS standard dimensions ───────────────────────────────────────────
MR85_ID = 5.0  # mm - inner (shaft) diameter
MR85_OD = 8.0  # mm - outer diameter
MR85_W = 2.5   # mm - axial width


class BearingHexHousing:
    """Cylindrical housing sized to free-fit-house one MR85-2RS bearing.

    Parameters
    ----------
    housing_od : float
        Outer diameter of the housing cylinder (mm).  Default 12.0 mm.
    bearing_id : float
        Bearing inner (shaft) diameter (mm).  Default 5.0 mm for MR85-2RS.
        Not consumed by the housing's own cut geometry (the housing only
        cuts the bearing's OD envelope) — recorded because it fully
        identifies the bearing and is forwarded to :class:`Bearing`.
    bearing_od : float
        Bearing outer diameter (mm).  Default 8.0 mm for MR85-2RS —
        the nominal size the housing's pocket is cut around.
    bearing_width : float
        Axial width of the bearing (mm), also the housing's own total
        height (design brief: matches the bearing width exactly, so the
        bearing sits flush both faces with no overhang).  Default 2.5 mm.
    profile : str | None
        Tolerance profile name from ``print_profiles.json``.  ``None``
        uses the globally-configured default.  The bearing pocket uses
        ``free`` fit grade, radial + axial — this bearing is intended to
        be user-replaceable (drop-in/pop-out by hand), matching the same
        fit grade as the hex-side bearing pocket added to
        :class:`~vibe_cading.rc.hex_hub_bearing.hex_hub_nut.HexHubNut` so
        both ends of the assembly seat the identical bearing the same way.
    """

    def __init__(
        self,
        housing_od: float = 12.0,
        bearing_id: float = MR85_ID,
        bearing_od: float = MR85_OD,
        bearing_width: float = MR85_W,
        profile: str | None = None,
    ) -> None:
        self.housing_od = float(housing_od)
        self.bearing_id = float(bearing_id)
        self.bearing_od = float(bearing_od)
        self.bearing_width = float(bearing_width)
        self._prof = get_profile(profile)
        self._solid = self._build()

    # ── Build ───────────────────────────────────────────────────────────

    def _build(self) -> cq.Workplane:
        bearing = Bearing(self.bearing_id, self.bearing_od, self.bearing_width)

        # ── 1. Plain cylinder (Z = 0 -> bearing_width) ──────────────────
        housing = (
            cq.Workplane("XY")
            .circle(self.housing_od / 2.0)
            .extrude(self.bearing_width)
        )

        # ── 2. Bearing pocket, free-fit clearance, through-cut ───────────
        # Bearing.outer_pocket() extrudes one-sided from Z = 0 to
        # Z = thickness + free.axial (bearings.py:103-109).  Applied
        # directly to a housing also built from Z = 0, the cutter's
        # *bottom* face would be exactly coincident with the housing's
        # bottom face -- the "coincident planar face" pitfall (see project
        # Known Modelling Pitfalls: Blind Holes / Internal Geometry
        # Under-visibility).  Because this pocket is a through-cut (both
        # faces are functionally entry faces), centre the free.axial
        # overcut symmetrically across both faces by translating the
        # cutter down by half the axial allowance before cutting
        # (design brief D4).
        pocket = bearing.outer_pocket(profile=self._prof, fit="free").translate(
            (0, 0, -self._prof.free.axial / 2.0)
        )
        housing = housing.cut(pocket)

        assert len(housing.solids().vals()) == 1, (
            "BearingHexHousing: expected a single contiguous solid."
        )
        return housing

    @property
    def solid(self) -> cq.Workplane:
        """The CadQuery solid.  Z = 0 is the bottom (axle-entry) face."""
        return self._solid
