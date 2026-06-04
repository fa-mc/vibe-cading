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

"""
Hexagonal Standoffs / Spacers (standard PCB/electronics mounting hardware).
"""
from __future__ import annotations

from typing import Literal

import cadquery as cq

from vibe_cading.print_settings import ToleranceProfile, get_profile


class HexStandoff:
    """Standard Hexagonal Standoff (Spacer) used for mounting PCBs."""
    DIMENSIONS = {
        "M2": {"width_flats": 4.0, "nominal_diameter": 2.0},
        "M2.5": {"width_flats": 5.0, "nominal_diameter": 2.5},
        "M3": {"width_flats": 5.5, "nominal_diameter": 3.0},
        "M4": {"width_flats": 7.0, "nominal_diameter": 4.0},
        "4-40": {"width_flats": 4.76, "nominal_diameter": 2.8},
        "6-32": {"width_flats": 6.35, "nominal_diameter": 3.5},
    }

    def __init__(self, width_flats: float, length: float, nominal_diameter: float, type_: Literal["F-F", "M-F", "M-M"] = "F-F", thread_length: float = 6.0):
        self.width_flats = float(width_flats)
        self.length = float(length)
        self.nominal_diameter = float(nominal_diameter)
        self.type_ = type_.upper()
        self.thread_length = float(thread_length)
        self.radius = self.width_flats / 1.7320508075688772

    @classmethod
    def from_size(cls, size: Literal["M2", "M2.5", "M3", "M4", "4-40", "6-32"], length: float = 10.0, type_: Literal["F-F", "M-F", "M-M"] = "F-F", thread_length: float = 6.0) -> "HexStandoff":
        if size not in cls.DIMENSIONS:
            raise ValueError(f"Unknown standoff size {size}. Supported: {list(cls.DIMENSIONS.keys())}")
        dims = cls.DIMENSIONS[size]
        return cls(
            width_flats=dims["width_flats"],
            length=length,
            nominal_diameter=dims["nominal_diameter"],
            type_=type_,
            thread_length=thread_length
        )

    @property
    def solid(self) -> cq.Workplane:
        body = cq.Workplane("XY").polygon(6, self.radius * 2).extrude(self.length)
        if self.type_ in ["F-F", "M-F"]:
            depth = self.length if self.type_ == "F-F" else self.length / 2.0
            body = body.faces(">Z").workplane().circle(self.nominal_diameter / 2.0).cutBlind(-depth)
            
        if self.type_ in ["M-F", "M-M"]:
            stud = cq.Workplane("XY").circle(self.nominal_diameter / 2.0).extrude(-self.thread_length)
            body = body.union(stud)

        if self.type_ == "M-M":
            stud2 = (cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, self.length))
                     .circle(self.nominal_diameter / 2.0).extrude(self.thread_length))
            body = body.union(stud2)

        return body

    def to_cutter(self, profile: ToleranceProfile | None = None) -> cq.Workplane:
        """Pocket cutter sized to slip-fit the standoff body.

        Tolerances are pulled from the supplied ``profile`` (or the
        env-configured default).  The ``free`` grade carries the radial
        and axial allowances since the standoff is intended as a loose
        clearance fit.
        """
        prof = profile or get_profile()
        radial_allowance = prof.free.radial
        depth_allowance = prof.free.axial
        r = self.radius + radial_allowance
        return cq.Workplane("XY").polygon(6, r * 2).extrude(self.length + depth_allowance)

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Show an M3 15 mm F-F standoff next to an M3 15 mm M-F standoff."""
        ff = cls.from_size("M3", 15, "F-F")
        mf = cls.from_size("M3", 15, "M-F", thread_length=6.0)
        return [
            (ff.solid.translate((-10, 0, 0)), "M3 15mm F-F", "royalblue"),
            (mf.solid.translate(( 10, 0, 0)), "M3 15mm M-F", "gold"),
        ]
