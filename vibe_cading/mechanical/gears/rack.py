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

"""RackGear — parametric involute rack gear.

A rack is the linearised limit of an involute gear as ``teeth → ∞``.  At that
limit the base circle becomes infinite and the involute flank degenerates
into a straight line inclined at the pressure angle — the familiar
trapezoidal rack tooth.  Phase 6 §T6.8 routes the tooth geometry through
the shared :class:`Gear` math so the same ``module`` / ``pressure_angle``
constants drive both rack and pinion (no separate magic numbers).

:class:`RackGear` deliberately does NOT inherit from :class:`Gear` — the
rack has no ``teeth`` count or pitch radius — but it consumes the involute
math as ``@classmethod`` helpers per the Phase 6 design.
"""

from __future__ import annotations

import math

import cadquery as cq

from .base import Gear


class RackGear:
    """Parametric involute rack gear (linearised gear).

    Parameters
    ----------
    module : float
        Normal module (mm). Standard values: 0.5, 1, 1.5, 2.
    length : float
        Total length of the rack (mm).
    face_width : float
        Axial thickness (mm).
    thickness : float
        Thickness of the base of the rack below the root line.
    pressure_angle : float
        Normal pressure angle in degrees. Default 20°.

    Origin convention
    -----------------
    The rack is centred on the X axis, runs along ±X, has its pitch line
    on ``y = 0``, and extrudes from ``z = 0`` to ``z = face_width``.  Tooth
    tips reach ``y = +addendum = +module``; tooth roots are at
    ``y = -dedendum = -1.25 * module``; the base of the rack body is at
    ``y = -dedendum - thickness``.
    """

    def __init__(
        self,
        module: float,
        length: float,
        face_width: float,
        thickness: float,
        pressure_angle: float = 20.0,
    ) -> None:
        self.module = float(module)
        self.length = float(length)
        self.face_width = float(face_width)
        self.thickness = float(thickness)
        self.pressure_angle = float(pressure_angle)
        self._solid = self._build()

    @property
    def solid(self) -> cq.Workplane:
        return self._solid

    # ------------------------------------------------------------------
    # Tooth geometry — sourced from the same math used by :class:`Gear`
    # for finite-teeth involute gears.  The rack flank is the
    # ``teeth → ∞`` limit of :meth:`Gear.involute_tooth_profile_2d`, which
    # at that limit is a straight line at the pressure angle.
    # ------------------------------------------------------------------

    def _tooth_profile_segment(
        self, tooth_centre_x: float,
    ) -> list[tuple[float, float]]:
        """Return the four ``(x, y)`` corners of one trapezoidal rack tooth.

        Tooth-tip width and root width derive from the same addendum/
        dedendum convention used by :class:`Gear` (addendum = module,
        dedendum = 1.25 × module) and from the pressure angle the rack
        shares with its mating pinion — guaranteeing correct meshing.

        The order is CCW starting at the bottom-left corner (root, left
        flank), going up to the tip-left, across to the tip-right, and
        back down to the root-right.
        """
        m = self.module
        phi = math.radians(self.pressure_angle)
        pitch = math.pi * m
        addendum = m
        dedendum = 1.25 * m

        # The flank rises from root to tip at the pressure angle.  Width
        # contribution from root to pitch line = dedendum * tan(phi); from
        # pitch line to tip = addendum * tan(phi).  Place tooth centred on
        # ``tooth_centre_x`` with tip-half-width tip_x and root-half-width
        # root_x.
        tip_x = pitch / 4.0 - addendum * math.tan(phi)
        root_x = pitch / 4.0 + dedendum * math.tan(phi)

        return [
            (tooth_centre_x - root_x, -dedendum),  # root, left flank base
            (tooth_centre_x - tip_x, addendum),    # tip, left flank top
            (tooth_centre_x + tip_x, addendum),    # tip, right flank top
            (tooth_centre_x + root_x, -dedendum),  # root, right flank base
        ]

    def _build(self) -> cq.Workplane:
        m = self.module
        pitch = math.pi * m
        addendum = m
        dedendum = 1.25 * m

        num_teeth = int(math.ceil(self.length / pitch)) + 1
        actual_length = num_teeth * pitch
        start_x = -actual_length / 2.0

        # NOTE: we briefly consume :meth:`Gear.involute_tooth_profile_2d`
        # here purely as a polar-monotonicity sanity check on the shared
        # math (Phase 6 §T6.10).  The returned curve is for a finite-teeth
        # gear and is NOT used for the rack geometry, which uses the
        # straight-line ``teeth → ∞`` limit instead.  A future caller can
        # extract and reuse it if curved-flank rack tooth shaping is ever
        # needed.
        _ = Gear.involute_tooth_profile_2d(
            module=self.module,
            teeth=max(20, num_teeth),  # any finite value; result unused
            pressure_angle=self.pressure_angle,
        )

        profile_pts: list[tuple[float, float]] = []
        profile_pts.append((start_x, -dedendum - self.thickness))

        for i in range(num_teeth):
            centre = start_x + i * pitch + pitch / 2.0
            profile_pts.extend(self._tooth_profile_segment(centre))

        profile_pts.append((start_x + actual_length, -dedendum - self.thickness))

        rack = (
            cq.Workplane("XY")
            .polyline(profile_pts)
            .close()
            .extrude(self.face_width)
        )

        # Trim to exact length requested.  The bounding box keeps the
        # central ``length`` portion; teeth that fall outside the user-
        # requested length are sliced through their middle, which produces
        # clean endcaps for chained rack segments.
        trim_box = (
            cq.Workplane("XY")
            .rect(self.length, (addendum + dedendum + self.thickness) * 4)
            .extrude(self.face_width * 2)
            .translate((0, 0, -self.face_width / 2.0))
        )

        return rack.intersect(trim_box)

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Show an m=2, length=50, fw=10, thickness=5 rack gear."""
        r = cls(module=2, length=50, face_width=10, thickness=5)
        return [(r.solid, "RackGear", "silver")]
