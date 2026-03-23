"""
Standard metric nuts.
Includes Hex nuts (ISO 4032), Nyloc nuts (DIN 985), and Square nuts (DIN 562).
"""

from __future__ import annotations

import cadquery as cq
from .base import Nut

class MetricHexNut(Nut):
    """Standard Metric Hex Nut generator (ISO 4032 / DIN 934)."""

    # Typical ISO 4032 / DIN 934 dimensions (Size: (Width Across Flats, Thickness))
    DIMENSIONS = {
        "M2": {"width_flats": 4.0, "thickness": 1.6},
        "M2.5": {"width_flats": 5.0, "thickness": 2.0},
        "M3": {"width_flats": 5.5, "thickness": 2.4},
        "M4": {"width_flats": 7.0, "thickness": 3.2},
        "M5": {"width_flats": 8.0, "thickness": 4.7},
        "M6": {"width_flats": 10.0, "thickness": 5.2},
        "M8": {"width_flats": 13.0, "thickness": 6.8},
    }

    def __init__(self, size: str = "M3"):
        if size not in self.DIMENSIONS:
            raise ValueError(f"Unknown nut size {size}. Supported: {list(self.DIMENSIONS.keys())}")

        dims = self.DIMENSIONS[size]
        self.size = size
        self.width_flats = dims["width_flats"]
        self.thickness = dims["thickness"]

        # Calculate the circumscribed radius (corner to corner) from the flat-to-flat distance
        # Hexagon flat-to-flat = sqrt(3) * R
        self.radius = self.width_flats / 1.7320508075688772

    @property
    def solid(self) -> cq.Workplane:
        return (
            cq.Workplane("XY")
            .polygon(6, self.radius * 2)
            .extrude(self.thickness)
        )

    def to_cutter(self, radial_allowance: float = 0.15, depth_allowance: float = 0.2) -> cq.Workplane:
        r = self.radius + radial_allowance
        h = self.thickness + depth_allowance
        return (
            cq.Workplane("XY")
            .polygon(6, r * 2)
            .extrude(h)
        )

    def to_captive_slot(self, slot_length: float, radial_allowance: float = 0.15, depth_allowance: float = 0.2) -> cq.Workplane:
        r = self.radius + radial_allowance
        h = self.thickness + depth_allowance

        base = cq.Workplane("XY").polygon(6, r * 2).extrude(h)
        chan_width = self.width_flats + (radial_allowance * 2)
        channel = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, -slot_length/2, 0))
            .rect(chan_width, slot_length)
            .extrude(h)
        )
        return base.union(channel)

class MetricNylocNut(MetricHexNut):
    """Standard Metric Nyloc Nut generator (DIN 985).

    Shares the hex profile of standard nuts but is significantly taller
    due to the nylon locking ring.
    """

    # DIN 985 dimensions (Size: (Width Across Flats, Overall Height))
    DIMENSIONS = {
        "M2.5": {"width_flats": 5.0, "thickness": 3.8},
        "M3": {"width_flats": 5.5, "thickness": 4.0},
        "M4": {"width_flats": 7.0, "thickness": 5.0},
        "M5": {"width_flats": 8.0, "thickness": 5.0},
        "M6": {"width_flats": 10.0, "thickness": 6.0},
        "M8": {"width_flats": 13.0, "thickness": 8.0},
    }

    # Inherits everything else from MetricHexNut


class MetricSquareNut(Nut):
    """Standard Metric Square Nut generator (DIN 562).

    Extremely popular in 3D printing (Prusa, Voron) because they do not
    rotate inside rectangular printed captive slots.
    """

    # DIN 562 dimensions (Size: (Width Across Flats, Thickness))
    DIMENSIONS = {
        "M2": {"width_flats": 4.0, "thickness": 1.2},
        "M2.5": {"width_flats": 5.0, "thickness": 1.6},
        "M3": {"width_flats": 5.5, "thickness": 1.8},
        "M4": {"width_flats": 7.0, "thickness": 2.2},
        "M5": {"width_flats": 8.0, "thickness": 2.7},
        "M6": {"width_flats": 10.0, "thickness": 3.2},
    }

    def __init__(self, size: str = "M3"):
        if size not in self.DIMENSIONS:
            raise ValueError(f"Unknown nut size {size}. Supported: {list(self.DIMENSIONS.keys())}")

        dims = self.DIMENSIONS[size]
        self.size = size
        self.width_flats = dims["width_flats"]
        self.thickness = dims["thickness"]

    @property
    def solid(self) -> cq.Workplane:
        return (
            cq.Workplane("XY")
            .rect(self.width_flats, self.width_flats)
            .extrude(self.thickness)
        )

    def to_cutter(self, radial_allowance: float = 0.15, depth_allowance: float = 0.2) -> cq.Workplane:
        w = self.width_flats + (radial_allowance * 2)
        h = self.thickness + depth_allowance
        return (
            cq.Workplane("XY")
            .rect(w, w)
            .extrude(h)
        )

    def to_captive_slot(self, slot_length: float, radial_allowance: float = 0.15, depth_allowance: float = 0.2) -> cq.Workplane:
        w = self.width_flats + (radial_allowance * 2)
        h = self.thickness + depth_allowance

        base = cq.Workplane("XY").rect(w, w).extrude(h)
        channel = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, -slot_length/2, 0))
            .rect(w, slot_length)
            .extrude(h)
        )
        return base.union(channel)

if __name__ == "__main__":
    from ocp_vscode import show

    hex_nut = MetricHexNut("M3")
    nyloc_nut = MetricNylocNut("M3")
    square_nut = MetricSquareNut("M3")

    show(
        hex_nut.solid.translate((-10, 0, 0)),
        nyloc_nut.solid.translate((0, 0, 0)),
        square_nut.solid.translate((10, 0, 0)),
        names=["M3 Hex", "M3 Nyloc", "M3 Square"]
    )