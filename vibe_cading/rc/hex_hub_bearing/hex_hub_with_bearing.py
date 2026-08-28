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

"""Fused RC 12 mm hex-hub + MR85-2RS bearing-housing assembly — the actual
printed deliverable.

Coordinate system
------------------
Z = 0 -> ``thickness``                : the fused :class:`HexHubNut` region
                                          (unmodified from its own datum).
Z = -bearing_width + overlap_eps -> 0 : the fused :class:`BearingHexHousing`
                                          region, translated flush against the
                                          nut's bottom face.
Centred at X = 0, Y = 0 on the shared rotation axis.

Design intent
-------------
Per the approved design brief
(``docs/design_plans/2026-08-25-rc-hex-hub-bearing_design.md``, D2/D2a Round
2), :class:`HexHubNut` and :class:`~vibe_cading.rc.hex_hub_bearing.bearing_hex_housing.BearingHexHousing`
are **not** a two-part assembly joined by a register/spigot feature -- they
print as a single fused body.  This wrapper builds both components, positions
the housing flush against the nut's bottom face with a small (0.02 mm
nominal) overlap epsilon, and ``.union()``s them.  The overlap epsilon is a
fixed geometric boolean-robustness margin (Known Modelling Pitfalls: two
solids sharing an *exactly* coincident planar face are a well-known OCCT
boolean reliability risk) -- it is **not** a fit-grade / tolerance-profile
value, since there is no separable mating surface to correct for print
shrink/growth.

A single continuous through passage runs the length of the fused body: a
6 mm-nominal (6.30 mm printed on ``fdm_standard``) free-running-clearance
bore through the nut region, and an 8 mm-nominal (8.30 mm printed, ``free``
fit) bearing pocket through the housing region.  Per design brief D8
(Round 4) these serve a single uniform 5 mm-nominal stub axle throughout --
the printed diameters differ because the two regions serve different
features (an axle-clearance hole vs. a bearing-OD pocket), not because the
axle itself steps in diameter.

The nut region also carries its own blind bearing pocket, sunk into its
outward (top, wheel-facing) face, sized for the identical MR85-2RS bearing
seated on the shaft side -- both bearings use ``free`` fit grade, so the
fused body seats two user-replaceable bearings the same way at each end.
"""

from __future__ import annotations

import cadquery as cq

from vibe_cading.rc.hex_hub_bearing.bearing_hex_housing import BearingHexHousing
from vibe_cading.rc.hex_hub_bearing.hex_hub_nut import HexHubNut


class HexHubWithBearing:
    """Fused hex-hub-nut + bearing-housing single-print body.

    Parameters
    ----------
    hex_across_flats : float
        Forwarded to :class:`HexHubNut`. Default 12.0 mm.
    thickness : float
        Forwarded to :class:`HexHubNut` as its axial thickness. Default 6.0 mm.
    bore_diameter : float
        Forwarded to :class:`HexHubNut` as its nominal through-bore diameter.
        Default 6.0 mm (design brief D8, Round 4 correction — was 4.0 mm).
    hex_chamfer : float
        Forwarded to :class:`HexHubNut`. Default 0.5 mm.
    housing_od : float
        Forwarded to :class:`~vibe_cading.rc.hex_hub_bearing.bearing_hex_housing.BearingHexHousing`.
        Default 12.0 mm.
    bearing_id : float
        Forwarded to the housing. Default 5.0 mm (MR85-2RS).  Not forwarded
        to the nut's own hex-side pocket, which (like the housing's own
        pocket) only cuts the bearing's OD envelope.
    bearing_od : float
        Forwarded to *both* the housing and the nut's hex-side bearing
        pocket, so both ends of the fused body seat the identical bearing.
        Default 8.0 mm (MR85-2RS).
    bearing_width : float
        Forwarded to the housing as its own total height, and used here to
        compute the flush-join translation. Also forwarded to the nut's
        hex-side pocket, which is blind and uses this only to size the
        pocket's depth (it does not affect the nut's own thickness).
        Default 2.5 mm (MR85-2RS).
    overlap_eps : float
        Fixed boolean-robustness overlap (mm) applied at the flush join
        between the two components (design brief D2a). Default 0.02 mm --
        not profile-derived, since this is not a printed-vs-printed mating
        fit.
    profile : str | None
        Tolerance profile name from ``print_profiles.json``, forwarded to
        both component classes so the whole fused body reads one consistent
        tolerance profile. ``None`` uses the globally-configured default.
    """

    def __init__(
        self,
        hex_across_flats: float = 12.0,
        thickness: float = 6.0,
        bore_diameter: float = 6.0,
        hex_chamfer: float = 0.5,
        housing_od: float = 12.0,
        bearing_id: float = 5.0,
        bearing_od: float = 8.0,
        bearing_width: float = 2.5,
        overlap_eps: float = 0.02,
        profile: str | None = None,
    ) -> None:
        self.overlap_eps = float(overlap_eps)
        # Forward the same `profile` argument (name or None) to both
        # components so they each resolve an identical ToleranceProfile and
        # the whole fused body reads one consistent tolerance profile.
        # Sub-component objects are the single source of truth for their own
        # dimensions (read via self.hex_nut / self.housing) rather than also
        # duplicating each forwarded value as a flattened wrapper attribute
        # -- matches AxleHexHubAdapter's storage shape.
        self.hex_nut = HexHubNut(
            hex_across_flats=hex_across_flats,
            thickness=thickness,
            bore_diameter=bore_diameter,
            bearing_od=bearing_od,
            bearing_width=bearing_width,
            hex_chamfer=hex_chamfer,
            profile=profile,
        )
        self.housing = BearingHexHousing(
            housing_od=housing_od,
            bearing_id=bearing_id,
            bearing_od=bearing_od,
            bearing_width=bearing_width,
            profile=profile,
        )
        self._solid = self._build()

    # ── Build ───────────────────────────────────────────────────────────

    def _build(self) -> cq.Workplane:
        # HexHubNut needs no translation -- its own local Z = 0 (bottom
        # face) already sits at the assembly's Z = 0.
        nut = self.hex_nut.solid

        # BearingHexHousing is translated so its top face lands overlap_eps
        # past global Z = 0, rather than exactly coincident with it (design
        # brief Assembly Datum / D2a).
        housing_positioned = self.housing.solid.translate(
            (0, 0, -self.housing.bearing_width + self.overlap_eps)
        )

        fused = nut.union(housing_positioned)

        assert len(fused.solids().vals()) == 1, (
            "HexHubWithBearing: expected a single fused solid -- the "
            ".union() between HexHubNut and BearingHexHousing did not "
            "produce a single contiguous body. Check overlap_eps."
        )
        return fused

    @property
    def solid(self) -> cq.Workplane:
        """The fused CadQuery solid.  Z = 0 is the flush join between the
        hex-nut and housing regions (see module docstring for the full
        coordinate span)."""
        return self._solid
