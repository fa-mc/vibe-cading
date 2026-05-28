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

"""12 mm hex free-spinning wheel hub for RC cars (front axle / non-driven).

Coordinate system
-----------------
Z = 0            : bottom face (inner bearing seat — knuckle side)
Z = ``height``   : top face (outer bearing seat — wheel side)
Hub centred at X = 0, Y = 0.

Design intent
-------------
This is a **free-spinning** hub: the hub body rotates around a *fixed* axle
on two MR85-2RS ball bearings (OD 8 mm, ID 5 mm, width 2.5 mm), one seated
at each end.  The axle does not rotate and is not driven — it is typically a
stub axle pressed or bolted into a steering knuckle.  The 6 mm centre bore
provides free running clearance for the 5 mm stub axle while transferring
radial and axial wheel loads through the two bearings.

This arrangement is standard on the non-driven front wheels of 2WD RWD RC
cars (e.g. buggies, truggies) where no torque needs to be transmitted to the
front axle.  It is distinct from the driven rear hubs found on the same cars,
which bind to a rotating dogbone or hex drive shaft.

The outer profile is a regular hexagon with ``hex_across_flats`` measured
flat-to-flat — the "12 mm hex" standard used by most 1:10-scale RC wheels.
"""

from __future__ import annotations

import math

import cadquery as cq

from vibe_cading.print_settings import get_profile

# ── MR85-2RS standard dimensions ──────────────────────────────────────────────
MR85_OD = 8.0   # mm – outer diameter
MR85_ID = 5.0   # mm – inner (shaft) diameter
MR85_W  = 2.5   # mm – axial width


class FreespinHexHub:
    """12 mm hex free-spinning wheel hub for RC front axles (non-driven).

    The hub body rotates freely around a fixed stub axle on two MR85-2RS
    ball bearings, one seated in each end face.  This is the standard
    front-wheel arrangement on 2WD RWD 1:10-scale RC cars: the axle is
    static and the hub (with wheel attached) spins on the bearings.

    The outer profile is a hexagonal prism — the "12 mm hex" interface
    accepted by most 1:10-scale RC wheels.

    Parameters
    ----------
    hex_across_flats : float
        Hex outer profile measured flat-to-flat (mm).  Default 12.0 mm
        matches the standard RC 1:10-scale wheel hex mounting system.
    height : float
        Total axial length of the hub (mm).  Default 16.0 mm.
    bearing_od : float
        Outer diameter of the bearing (mm).  Default 8.0 mm for MR85-2RS.
    bearing_width : float
        Axial width of the bearing (mm).  Default 2.5 mm for MR85-2RS.
    bore_diameter : float
        Centre bore diameter (mm).  Provides free running clearance around
        the fixed stub axle; default 6.0 mm gives ~0.5 mm radial clearance
        on a 5 mm axle.  The bore does *not* transmit torque.
    hex_chamfer : float
        Chamfer size applied to all sharp edges of the hex prism (mm).
        Breaks the 6 vertical corners and the 12 perimeter edges on the
        top and bottom faces.  Default 0.5 mm.
    profile : str | None
        Tolerance profile name from ``print_profiles.json``.  ``None``
        uses the globally-configured default (``PRINT_PROFILE``
        env var, falling back to ``fdm_standard``).

        The bearing pocket uses **free_fit** radial clearance so the
        bearing drops in and pops out by hand on a typical FDM print.
        Switch to ``slip_fit`` for a snugger seat, or ``press_fit`` for
        an interference fit.
    """

    def __init__(
        self,
        hex_across_flats: float = 12.0,
        height: float = 16.0,
        bearing_od: float = MR85_OD,
        bearing_width: float = MR85_W,
        bore_diameter: float = 6.0,
        hex_chamfer: float = 0.5,
        profile: str | None = None,
    ) -> None:
        self.hex_across_flats = float(hex_across_flats)
        self.height           = float(height)
        self.bearing_od       = float(bearing_od)
        self.bearing_width    = float(bearing_width)
        self.bore_diameter         = float(bore_diameter)
        self.hex_chamfer      = float(hex_chamfer)
        self._prof            = get_profile(profile)
        self._solid           = self._build()

    # ── Derived geometry ───────────────────────────────────────────────────

    @property
    def _hex_circumdia(self) -> float:
        """Circumscribed circle diameter (vertex-to-vertex) of the hex (mm).

        CadQuery's ``polygon(nSides, diameter)`` uses the circumscribed
        diameter (tip-to-tip), so we convert from the user-facing
        across-flats measurement:
            AF = circumdia × cos(30°)  →  circumdia = AF / cos(30°)
        """
        return self.hex_across_flats / math.cos(math.radians(30))

    @property
    def _pocket_dia(self) -> float:
        """Bearing pocket inner diameter after applying free-fit clearance (mm).

        ``free.radial`` is a *radial* value (×2 for diameter).  This gives
        ~0.3 mm total diameter play — enough for the bearing to drop in and
        pop out by hand on an FDM print without press-fitting tools.
        """
        return self.bearing_od + 2.0 * self._prof.free.radial

    @property
    def _pocket_depth(self) -> float:
        """Bearing pocket axial depth (mm).

        ``free.axial`` prevents the bearing face from binding against the
        pocket floor.  An extra 0.5 mm is added so the bearing sits fully
        proud of the hex face and is easy to press flush by hand.
        """
        return self.bearing_width + self._prof.free.axial + 0.5

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self) -> cq.Workplane:
        # ── 1. Hexagonal prism (Z = 0 → height) ───────────────────────────
        part = (
            cq.Workplane("XY")
            .polygon(6, self._hex_circumdia)
            .extrude(self.height)
        )

        # ── 2. Centre bore (through) ───────────────────────────────────────
        # The bore must be strictly wider than the shaft so it spins freely;
        # bore_diameter defaults to 6 mm for a 5 mm shaft (0.5 mm radial clearance).
        part = (
            part
            .faces("<Z")       # Z = 0, outward normal → −Z
            .workplane()
            .circle(self.bore_diameter / 2.0)
            .cutThruAll()
        )

        # ── 3. Bearing pocket – bottom (Z = 0, cuts in +Z direction) ──────
        # cutBlind with a negative distance cuts against the workplane normal
        # (inward), so the pocket opens at the bottom face and terminates
        # _pocket_depth mm into the body.
        part = (
            part
            .faces("<Z")
            .workplane()
            .circle(self._pocket_dia / 2.0)
            .cutBlind(-self._pocket_depth)
        )

        # ── 4. Bearing pocket – top (Z = height, cuts in −Z direction) ────
        part = (
            part
            .faces(">Z")       # Z = height, outward normal → +Z
            .workplane()
            .circle(self._pocket_dia / 2.0)
            .cutBlind(-self._pocket_depth)
        )

        # ── 5. Chamfer all sharp hex edges ────────────────────────────────
        # |Z  → the 6 vertical corner edges along the prism length.
        # <Z and >Z ring → the 12 perimeter edges on the bottom/top faces
        #   (6 per face), excluding the inner bore circles which are already
        #   smooth cylinders.
        if self.hex_chamfer > 0:
            part = part.edges("|Z").chamfer(self.hex_chamfer)
            part = (
                part
                .edges("<Z").chamfer(self.hex_chamfer)
                .edges(">Z").chamfer(self.hex_chamfer)
            )

        assert len(part.solids().vals()) == 1, (
            "FreespinHexHub: expected a single contiguous solid — check pocket "
            "depth vs. total height."
        )
        return part

    @property
    def solid(self) -> cq.Workplane:
        """The CadQuery solid.  Z = 0 is the bottom bearing seat face."""
        return self._solid
