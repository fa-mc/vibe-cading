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

"""Fastener drive geometry cutters.

The drives subtree implements :class:`vibe_cading.mechanical.protocols.CutterProtocol`
— each concrete class exposes ``to_cutter(profile=None)`` returning a
boolean-subtraction solid sized for one of the standard drive
recesses (Hex, Slotted, Phillips, Torx).

Phase 4 renamed the historical ``.cutter`` property to ``.to_cutter()``
so the drive cutters share the unified call signature with every
other cutter producer in the library.
"""

import math
from abc import ABC, abstractmethod
import cadquery as cq

from vibe_cading.print_settings import ToleranceProfile


# Class-level entry overcut for drive recess cutters.  All drive cutters
# are blind (the recess has a defined floor at -depth), but the entry
# face at Z=0 is overcut by 0.1 mm so the cutter cleanly clears the
# fastener head's external face.  100 mm is unnecessary here — a 0.1 mm
# overcut suffices because callers always translate the cutter to sit
# at the head's external face precisely.
_DRIVE_ENTRY_OVERCUT: float = 0.1


class FastenerDrive(ABC):
    """Abstract base class for all fastener drive geometry cutters.

    Each standard drive type implements specific sizes (e.g. PH1, M3
    Hex) so users don't need to guess geometric parameters.

    The ABC remains in place under Phase 4; Phase 5 may replace it with
    a ``typing.Protocol`` if the Screw/Nut Protocol conversion settles
    on the same shape.
    """

    @abstractmethod
    def to_cutter(self, profile: ToleranceProfile | None = None) -> cq.Workplane:
        """Returns a solid cutter starting slightly above Z=0 (entry overcut)
        and extending to the required depth in -Z.

        :param profile: Currently unused — drive dimensions are
            constructor-driven.  Accepted to satisfy ``CutterProtocol``.
        """
        pass


class HexDrive(FastenerDrive):
    """Standard hexagon socket drive (e.g. for Allen bolts)."""

    _THROUGH: bool = False  # blind cutter with bounded entry overcut

    def __init__(self, across_flats: float, depth: float):
        self.across_flats = across_flats
        self.depth = depth

    def to_cutter(self, profile: ToleranceProfile | None = None) -> cq.Workplane:
        # CadQuery's polygon takes circumscribed diameter:
        # diameter = 2 * r = across_flats / cos(30°).
        diameter = self.across_flats / math.cos(math.radians(30))
        return (
            cq.Workplane("XY")
            .workplane(offset=_DRIVE_ENTRY_OVERCUT)  # small Z entry overcut
            .polygon(6, diameter)
            .extrude(-(self.depth + _DRIVE_ENTRY_OVERCUT))
        )


class SlottedDrive(FastenerDrive):
    """Standard flat-head slotted drive."""

    _THROUGH: bool = False

    def __init__(self, length: float, width: float, depth: float):
        self.length = length
        self.width = width
        self.depth = depth

    def to_cutter(self, profile: ToleranceProfile | None = None) -> cq.Workplane:
        return (
            cq.Workplane("XY")
            .workplane(offset=_DRIVE_ENTRY_OVERCUT)
            .rect(self.length + 0.2, self.width)  # +0.2 length for slight X overcut
            .extrude(-(self.depth + _DRIVE_ENTRY_OVERCUT))
        )


class PhillipsDrive(FastenerDrive):
    """Realistic cross-shaped Phillips drive based on standardized PH profiles.

    Constructed by unioning tapered rectangles and a central cone for a
    correct pocket.
    """

    _THROUGH: bool = False

    # ISO Phillips standard approximations (diameter, width, depth)
    PH_SIZES = {
        "PH00": (2.0, 0.6, 1.0),
        "PH0":  (3.0, 0.8, 1.5),
        "PH1":  (4.5, 1.2, 2.5),
        "PH2":  (6.0, 1.5, 3.5),
        "PH3":  (8.0, 2.0, 5.0),
    }

    def __init__(self, diameter: float, width: float, depth: float):
        self.diameter = diameter
        self.width = width
        self.depth = depth

    @classmethod
    def from_size(cls, size: str) -> "PhillipsDrive":
        """Instantiate a Phillips drive cutter based on industry standard (e.g. 'PH1', 'PH2')."""
        size = size.upper()
        if size not in cls.PH_SIZES:
            raise ValueError(f"Unknown Phillips size: {size}. Available sizes: {list(cls.PH_SIZES.keys())}")
        d, w, h = cls.PH_SIZES[size]
        return cls(diameter=d, width=w, depth=h)

    def to_cutter(self, profile: ToleranceProfile | None = None) -> cq.Workplane:
        # A robust Phillips cutter: tapered rectangles + central support.
        # This prevents CadQuery from struggling with intersecting tapered 2D wires.
        depth_val = -(self.depth + _DRIVE_ENTRY_OVERCUT)
        w = cq.Workplane("XY", origin=(0, 0, _DRIVE_ENTRY_OVERCUT))

        # 20-degree taper (close to ISO 53° total included angle).
        t_ang = 20
        arm1 = w.rect(self.diameter, self.width).extrude(depth_val, taper=t_ang)
        arm2 = w.rect(self.width, self.diameter).extrude(depth_val, taper=t_ang)

        # Intersecting centre to prevent collapse artifacts at the very bottom.
        center = w.circle(self.width * 0.8).extrude(depth_val, taper=t_ang)

        return arm1.union(arm2).union(center)


class TorxDrive(FastenerDrive):
    """Torx (6-point star) drive geometry for socket head screws.

    Standard sizes follow ISO 10664 / DIN 3391 specifications.
    Modeled as a 6-pointed star with tapered extrusion (8 degrees).
    """

    _THROUGH: bool = False

    # Standard Torx sizes: name -> (point-to-point diameter mm, depth mm)
    TORX_SIZES = {
        "T5":  (1.42, 1.0),
        "T6":  (1.70, 1.2),
        "T8":  (2.31, 1.6),
        "T10": (2.74, 2.0),
        "T15": (3.27, 2.3),
        "T20": (3.86, 2.5),
        "T25": (4.43, 3.0),
        "T30": (5.52, 3.5),
    }

    def __init__(self, point_to_point_diameter: float, depth: float, taper_angle: float = 8.0):
        self.point_to_point_diameter = float(point_to_point_diameter)
        self.depth = float(depth)
        self.taper_angle = float(taper_angle)

    @classmethod
    def from_size(cls, size: str) -> "TorxDrive":
        size = size.upper()
        if size not in cls.TORX_SIZES:
            raise ValueError(f"Unknown Torx size: {size}. Available sizes: {list(cls.TORX_SIZES.keys())}")
        diameter, depth = cls.TORX_SIZES[size]
        return cls(point_to_point_diameter=diameter, depth=depth)

    def _build_star_profile(self) -> list:
        points = []
        radius_outer = self.point_to_point_diameter / 2.0
        radius_inner = radius_outer * 0.7  # inner valley

        for i in range(12):
            angle_deg = i * 30.0
            angle_rad = math.radians(angle_deg)
            r = radius_outer if i % 2 == 0 else radius_inner
            x = r * math.cos(angle_rad)
            y = r * math.sin(angle_rad)
            points.append((x, y))
        return points

    def to_cutter(self, profile: ToleranceProfile | None = None) -> cq.Workplane:
        star_points = self._build_star_profile()
        wp = cq.Workplane("XY", origin=(0, 0, _DRIVE_ENTRY_OVERCUT))
        wp = wp.polyline(star_points).close()
        depth_val = -(self.depth + _DRIVE_ENTRY_OVERCUT)
        return wp.extrude(depth_val, taper=self.taper_angle)
