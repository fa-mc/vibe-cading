"""
Hammer T-Nuts (often used for aluminium 2020/3030 extrusions).
"""
from __future__ import annotations
import cadquery as cq
from .base import Nut

class TNut(Nut):
    """Standard sliding/hammer T-Nut for 2020 V-Slot Aluminum Extrusions."""
    DIMENSIONS = {
        "M3": {"length": 10.0, "width": 6.0, "thickness": 4.0, "step_width": 4.0, "step_height": 1.5},
        "M4": {"length": 10.0, "width": 6.0, "thickness": 4.0, "step_width": 4.0, "step_height": 1.5},
        "M5": {"length": 10.0, "width": 6.0, "thickness": 4.0, "step_width": 4.0, "step_height": 1.5},
    }

    def __init__(self, length: float, width: float, thickness: float, step_width: float, step_height: float):
        self.length = float(length)
        self.width = float(width)
        self.thickness = float(thickness)
        self.step_width = float(step_width)
        self.step_height = float(step_height)
        self.base_thickness = self.thickness - self.step_height

    @classmethod
    def from_size(cls, size: str) -> "TNut":
        if size not in cls.DIMENSIONS:
            raise ValueError(f"Unknown T-nut size {size}. Supported: {list(cls.DIMENSIONS.keys())}")
        dims = cls.DIMENSIONS[size]
        return cls(
            length=dims["length"],
            width=dims["width"],
            thickness=dims["thickness"],
            step_width=dims["step_width"],
            step_height=dims["step_height"]
        )

    @property
    def solid(self) -> cq.Workplane:
        base = cq.Workplane("XY").rect(self.width, self.length).extrude(self.base_thickness)
        step = (cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, self.base_thickness))
                .rect(self.step_width, self.length).extrude(self.step_height))
        return base.union(step)

    def to_cutter(self, radial_allowance: float = 0.15, depth_allowance: float = 0.2) -> cq.Workplane:
        w_allow = self.width + (radial_allowance * 2)
        l_allow = self.length + (radial_allowance * 2)
        step_w_allow = self.step_width + (radial_allowance * 2)
        base = cq.Workplane("XY").rect(w_allow, l_allow).extrude(self.base_thickness + (depth_allowance/2))
        step = (cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, self.base_thickness + (depth_allowance/2)))
                .rect(step_w_allow, l_allow).extrude(self.step_height + (depth_allowance/2)))
        return base.union(step)

    def to_captive_slot(self, slot_length: float, radial_allowance: float = 0.15, depth_allowance: float = 0.2) -> cq.Workplane:
        w_allow = self.width + (radial_allowance * 2)
        step_w_allow = self.step_width + (radial_allowance * 2)
        base_h = self.base_thickness + (depth_allowance/2)
        step_h = self.step_height + (depth_allowance/2)

        pocket = self.to_cutter(radial_allowance, depth_allowance)
        chan_base = (cq.Workplane("XY").transformed(offset=cq.Vector(0, -slot_length/2, 0))
                     .rect(w_allow, slot_length).extrude(base_h))
        chan_step = (cq.Workplane("XY").transformed(offset=cq.Vector(0, -slot_length/2, base_h))
                     .rect(step_w_allow, slot_length).extrude(step_h))
        return pocket.union(chan_base).union(chan_step)

if __name__ == "__main__":
    from ocp_vscode import show
    tnut = TNut.from_size("M4")
    show(tnut.solid.translate((-10, 0, 0)), tnut.to_captive_slot(15).translate((10, 0, 0)))
