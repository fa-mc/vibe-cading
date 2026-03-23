"""
Hammer T-Nuts (often used for aluminium 2020/3030 extrusions).
"""

from __future__ import annotations

import cadquery as cq
from .base import Nut

class TNut(Nut):
    """Standard sliding/hammer T-Nut for 2020 V-Slot Aluminum Extrusions.

    Generates a T-Nut geometry and a matching cross-shaped captive slot cutter
    so T-Nuts can be embedded inside plastic parts as robust anchor points.
    """

    # Standard dimensions for 2020 V-Slot T-Nuts
    DIMENSIONS = {
        "M3": {"length": 10.0, "width": 6.0, "thickness": 4.0, "step_width": 4.0, "step_height": 1.5},
        "M4": {"length": 10.0, "width": 6.0, "thickness": 4.0, "step_width": 4.0, "step_height": 1.5},
        "M5": {"length": 10.0, "width": 6.0, "thickness": 4.0, "step_width": 4.0, "step_height": 1.5},
    }

    def __init__(self, size: str = "M4"):
        if size not in self.DIMENSIONS:
            raise ValueError(f"Unknown T-nut size {size}. Supported: {list(self.DIMENSIONS.keys())}")

        dims = self.DIMENSIONS[size]
        self.size = size
        self.length = dims["length"]
        self.width = dims["width"]
        self.thickness = dims["thickness"]
        self.step_width = dims["step_width"]
        self.step_height = dims["step_height"]
        self.base_thickness = self.thickness - self.step_height

    @property
    def solid(self) -> cq.Workplane:
        base = cq.Workplane("XY").rect(self.width, self.length).extrude(self.base_thickness)
        step = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, self.base_thickness))
            .rect(self.step_width, self.length)
            .extrude(self.step_height)
        )
        return base.union(step)

    def to_cutter(self, radial_allowance: float = 0.15, depth_allowance: float = 0.2) -> cq.Workplane:
        w_allow = self.width + (radial_allowance * 2)
        l_allow = self.length + (radial_allowance * 2)
        step_w_allow = self.step_width + (radial_allowance * 2)

        base = cq.Workplane("XY").rect(w_allow, l_allow).extrude(self.base_thickness + (depth_allowance/2))
        step = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, self.base_thickness + (depth_allowance/2)))
            .rect(step_w_allow, l_allow)
            .extrude(self.step_height + (depth_allowance/2))
        )
        return base.union(step)

    def to_captive_slot(self, slot_length: float, radial_allowance: float = 0.15, depth_allowance: float = 0.2) -> cq.Workplane:
        """
        Extrude the T-nut cutter shape down the Y axis to form a sliding slot.
        """
        w_allow = self.width + (radial_allowance * 2)
        l_allow = self.length + (radial_allowance * 2)
        step_w_allow = self.step_width + (radial_allowance * 2)

        base_h = self.base_thickness + (depth_allowance/2)
        step_h = self.step_height + (depth_allowance/2)
        total_h = base_h + step_h

        # Primary pocket
        pocket = self.to_cutter(radial_allowance, depth_allowance)

        # Channel to slide it in
        chan_base = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, -slot_length/2, 0))
            .rect(w_allow, slot_length)
            .extrude(base_h)
        )
        chan_step = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, -slot_length/2, base_h))
            .rect(step_w_allow, slot_length)
            .extrude(step_h)
        )
        return pocket.union(chan_base).union(chan_step)

if __name__ == "__main__":
    from ocp_vscode import show

    tnut = TNut("M4")
    show(
        tnut.solid.translate((-10, 0, 0)),
        tnut.to_captive_slot(15).translate((10, 0, 0)),
        names=["M4 T-Nut", "Captive Slot"]
    )