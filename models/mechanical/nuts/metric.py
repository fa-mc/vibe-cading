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
Standard metric nuts.
Includes Hex nuts (ISO 4032), Nyloc nuts (DIN 985), and Square nuts (DIN 562).
"""
from __future__ import annotations
import cadquery as cq
from .base import Nut

class MetricHexNut(Nut):
    """Standard Metric Hex Nut generator (ISO 4032 / DIN 934)."""
    DIMENSIONS = {
        "M2": {"thread_diameter": 2.0, "width_flats": 4.0, "thickness": 1.6},
        "M2.5": {"thread_diameter": 2.5, "width_flats": 5.0, "thickness": 2.0},
        "M3": {"thread_diameter": 3.0, "width_flats": 5.5, "thickness": 2.4},
        "M4": {"thread_diameter": 4.0, "width_flats": 7.0, "thickness": 3.2},
        "M5": {"thread_diameter": 5.0, "width_flats": 8.0, "thickness": 4.7},
        "M6": {"thread_diameter": 6.0, "width_flats": 10.0, "thickness": 5.2},
        "M8": {"thread_diameter": 8.0, "width_flats": 13.0, "thickness": 6.8},
    }

    def __init__(self, width_flats: float, thickness: float, thread_diameter: float = 0.0):
        self.width_flats = float(width_flats)
        self.thickness = float(thickness)
        self.thread_diameter = float(thread_diameter)
        self.radius = self.width_flats / 1.7320508075688772

    @classmethod
    def from_size(cls, size: str) -> "MetricHexNut":
        if size not in cls.DIMENSIONS:
            raise ValueError(f"Unknown nut size {size}. Supported: {list(cls.DIMENSIONS.keys())}")
        dims = cls.DIMENSIONS[size]
        return cls(width_flats=dims["width_flats"], thickness=dims["thickness"], thread_diameter=dims.get("thread_diameter", float(size[1:])))

    @property
    def solid(self) -> cq.Workplane:
        base = cq.Workplane("XY").polygon(6, self.radius * 2).extrude(self.thickness)
        if self.thread_diameter > 0.0:
            hole_cutter = cq.Workplane("XY").circle(self.thread_diameter / 2.0).extrude(self.thickness + 2.0)
            hole_cutter = hole_cutter.translate((0, 0, -1.0))
            base = base.cut(hole_cutter)
        return base

    def to_cutter(self, profile = None) -> cq.Workplane:
        from models.print_settings import get_profile
        prof = profile or get_profile()
        depth_allowance = prof.z_clearance
        from models.mechanical.holes import CaptiveNutPocket
        pocket = CaptiveNutPocket(self.width_flats, self.thickness + depth_allowance, prof)
        # The pocket translates down by `-thickness` internally, so to match old behaviour (extruding UP from XY):
        # We need to translate the cut tool up by its thickness so it sits at Z=0 and goes to +h
        return pocket.to_cutter(overcut=0).translate((0, 0, self.thickness + depth_allowance))

    def to_captive_slot(self, slot_length: float, radial_allowance: float = 0.15, depth_allowance: float = 0.2) -> cq.Workplane:
        r = self.radius + radial_allowance
        h = self.thickness + depth_allowance
        base = cq.Workplane("XY").polygon(6, r * 2).extrude(h)
        chan_width = self.width_flats + (radial_allowance * 2)
        channel = (cq.Workplane("XY").transformed(offset=cq.Vector(0, -slot_length/2, 0))
                   .rect(chan_width, slot_length).extrude(h))
        return base.union(channel)

class MetricNylocNut(MetricHexNut):
    """Standard Metric Nyloc Nut generator (DIN 985)."""
    DIMENSIONS = {
        "M2.5": {"thread_diameter": 2.5, "width_flats": 5.0, "thickness": 3.8},
        "M3": {"thread_diameter": 3.0, "width_flats": 5.5, "thickness": 4.0},
        "M4": {"thread_diameter": 4.0, "width_flats": 7.0, "thickness": 5.0},
        "M5": {"thread_diameter": 5.0, "width_flats": 8.0, "thickness": 5.0},
        "M6": {"thread_diameter": 6.0, "width_flats": 10.0, "thickness": 6.0},
        "M8": {"thread_diameter": 8.0, "width_flats": 13.0, "thickness": 8.0},
    }

class MetricSquareNut(Nut):
    """Standard Metric Square Nut generator (DIN 562)."""
    DIMENSIONS = {
        "M2": {"thread_diameter": 2.0, "width_flats": 4.0, "thickness": 1.2},
        "M2.5": {"thread_diameter": 2.5, "width_flats": 5.0, "thickness": 1.6},
        "M3": {"thread_diameter": 3.0, "width_flats": 5.5, "thickness": 1.8},
        "M4": {"thread_diameter": 4.0, "width_flats": 7.0, "thickness": 2.2},
        "M5": {"thread_diameter": 5.0, "width_flats": 8.0, "thickness": 2.7},
        "M6": {"thread_diameter": 6.0, "width_flats": 10.0, "thickness": 3.2},
    }

    def __init__(self, width_flats: float, thickness: float, thread_diameter: float = 0.0):
        self.width_flats = float(width_flats)
        self.thickness = float(thickness)
        self.thread_diameter = float(thread_diameter)

    @classmethod
    def from_size(cls, size: str) -> "MetricSquareNut":
        if size not in cls.DIMENSIONS:
            raise ValueError(f"Unknown nut size {size}. Supported: {list(cls.DIMENSIONS.keys())}")
        dims = cls.DIMENSIONS[size]
        return cls(width_flats=dims["width_flats"], thickness=dims["thickness"], thread_diameter=dims.get("thread_diameter", float(size[1:])))

    @property
    def solid(self) -> cq.Workplane:
        base = cq.Workplane("XY").rect(self.width_flats, self.width_flats).extrude(self.thickness)
        if self.thread_diameter > 0.0:
            hole_cutter = cq.Workplane("XY").circle(self.thread_diameter / 2.0).extrude(self.thickness + 2.0)
            hole_cutter = hole_cutter.translate((0, 0, -1.0))
            base = base.cut(hole_cutter)
        return base

    def to_cutter(self, profile = None) -> cq.Workplane:
        from models.print_settings import get_profile
        prof = profile or get_profile()
        radial_allowance = prof.free_fit
        depth_allowance = prof.z_clearance
        w = self.width_flats + (radial_allowance * 2)
        h = self.thickness + depth_allowance
        return cq.Workplane("XY").rect(w, w).extrude(h)

    def to_captive_slot(self, slot_length: float, radial_allowance: float = 0.15, depth_allowance: float = 0.2) -> cq.Workplane:
        w = self.width_flats + (radial_allowance * 2)
        h = self.thickness + depth_allowance
        base = cq.Workplane("XY").rect(w, w).extrude(h)
        channel = (cq.Workplane("XY").transformed(offset=cq.Vector(0, -slot_length/2, 0))
                   .rect(w, slot_length).extrude(h))
        return base.union(channel)

if __name__ == "__main__":
    from ocp_vscode import show
    hex_nut = MetricHexNut.from_size("M3")
    nyloc_nut = MetricNylocNut.from_size("M3")
    square_nut = MetricSquareNut.from_size("M3")
    show(hex_nut.solid.translate((-10, 0, 0)), nyloc_nut.solid.translate((0, 0, 0)), square_nut.solid.translate((10, 0, 0)))
