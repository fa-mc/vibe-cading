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
Hammer T-Nuts (often used for aluminium 2020/3030 extrusions).
"""
from __future__ import annotations
import cadquery as cq

class TNut:
    """Standard sliding/hammer T-Nut for 2020 V-Slot Aluminum Extrusions."""
    DIMENSIONS = {
        "M3": {"thread_diameter": 3.0, "length": 10.0, "width": 6.0, "thickness": 4.0, "step_width": 4.0, "step_height": 1.5},
        "M4": {"thread_diameter": 4.0, "length": 10.0, "width": 6.0, "thickness": 4.0, "step_width": 4.0, "step_height": 1.5},
        "M5": {"thread_diameter": 5.0, "length": 10.0, "width": 6.0, "thickness": 4.0, "step_width": 4.0, "step_height": 1.5},
    }

    def __init__(self, length: float, width: float, thickness: float, step_width: float, step_height: float, thread_diameter: float = 0.0):
        self.length = float(length)
        self.width = float(width)
        self.thickness = float(thickness)
        self.step_width = float(step_width)
        self.step_height = float(step_height)
        self.thread_diameter = float(thread_diameter)
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
            step_height=dims["step_height"],
            thread_diameter=dims.get("thread_diameter", float(size[1:]))
        )

    @property
    def solid(self) -> cq.Workplane:
        base = cq.Workplane("XY").rect(self.width, self.length).extrude(self.base_thickness)
        step = (cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, self.base_thickness))
                .rect(self.step_width, self.length).extrude(self.step_height))
        solid = base.union(step)
        if self.thread_diameter > 0.0:
            hole_cutter = cq.Workplane("XY").circle(self.thread_diameter / 2.0).extrude(self.thickness + 2.0)
            hole_cutter = hole_cutter.translate((0, 0, -1.0))
            solid = solid.cut(hole_cutter)
        return solid

    def to_cutter(self, profile=None) -> cq.Workplane:
        """Boolean-subtraction tool for trapping the T-nut.

        :param profile: Optional :class:`ToleranceProfile`.  Reads
            ``profile.free.radial`` for the lateral pocket inflation and
            ``profile.free.axial`` for the depth inflation (per side).
            Defaults to ``get_profile()`` so call-time callers can omit.
        """
        from vibe_cading.print_settings import get_profile
        prof = profile if profile is not None else get_profile()
        radial_allowance = prof.free.radial
        depth_allowance = prof.free.axial
        w_allow = self.width + (radial_allowance * 2)
        l_allow = self.length + (radial_allowance * 2)
        step_w_allow = self.step_width + (radial_allowance * 2)
        base = cq.Workplane("XY").rect(w_allow, l_allow).extrude(self.base_thickness + (depth_allowance/2))
        step = (cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, self.base_thickness + (depth_allowance/2)))
                .rect(step_w_allow, l_allow).extrude(self.step_height + (depth_allowance/2)))
        return base.union(step)

    def to_captive_slot(self, slot_length: float, profile=None) -> cq.Workplane:
        """T-nut-specific extension: returns a captive sliding-slot cutter.

        Not part of :class:`NutProtocol` — it's a nut-family-specific
        convenience for trapping the T-nut into a sliding channel.
        """
        from vibe_cading.print_settings import get_profile
        prof = profile if profile is not None else get_profile()
        radial_allowance = prof.free.radial
        depth_allowance = prof.free.axial
        w_allow = self.width + (radial_allowance * 2)
        step_w_allow = self.step_width + (radial_allowance * 2)
        base_h = self.base_thickness + (depth_allowance/2)
        step_h = self.step_height + (depth_allowance/2)

        pocket = self.to_cutter(profile=prof)
        chan_base = (cq.Workplane("XY").transformed(offset=cq.Vector(0, -slot_length/2, 0))
                     .rect(w_allow, slot_length).extrude(base_h))
        chan_step = (cq.Workplane("XY").transformed(offset=cq.Vector(0, -slot_length/2, base_h))
                     .rect(step_w_allow, slot_length).extrude(step_h))
        return pocket.union(chan_base).union(chan_step)

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Show an M4 T-nut beside its 15 mm captive-slot cutter."""
        tnut = cls.from_size("M4")
        return [
            (tnut.solid.translate((-10, 0, 0)),              "M4 TNut",       "royalblue"),
            (tnut.to_captive_slot(15).translate((10, 0, 0)), "Captive Slot",  "gold"),
        ]
