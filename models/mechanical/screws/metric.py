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

import cadquery as cq
import math
from .base import Screw

METRIC_SIZES = {
    "M2":   {"major": 2.0, "clearance": 2.2, "tap": 1.6, "flat_head_dia": 3.8,  "flat_head_h": 1.2, "socket_head_dia": 3.8,  "socket_head_h": 2.0, "pan_head_dia": 4.0, "pan_head_h": 1.6},
    "M2.5": {"major": 2.5, "clearance": 2.7, "tap": 2.1, "flat_head_dia": 4.7,  "flat_head_h": 1.5, "socket_head_dia": 4.5,  "socket_head_h": 2.5, "pan_head_dia": 5.0, "pan_head_h": 2.1},
    "M3":   {"major": 3.0, "clearance": 3.2, "tap": 2.5, "flat_head_dia": 5.5,  "flat_head_h": 1.7, "socket_head_dia": 5.5,  "socket_head_h": 3.0, "pan_head_dia": 5.6, "pan_head_h": 2.4},
    "M4":   {"major": 4.0, "clearance": 4.3, "tap": 3.3, "flat_head_dia": 8.4,  "flat_head_h": 2.7, "socket_head_dia": 7.0,  "socket_head_h": 4.0, "pan_head_dia": 8.0, "pan_head_h": 3.1},
    "M5":   {"major": 5.0, "clearance": 5.3, "tap": 4.2, "flat_head_dia": 9.3,  "flat_head_h": 2.7, "socket_head_dia": 8.5,  "socket_head_h": 5.0, "pan_head_dia": 9.5, "pan_head_h": 3.7},
}

class MetricMachineScrew(Screw):
    """Standard ISO metric machine screws."""
    def __init__(
        self,
        length: float,
        major_diameter: float,
        head_diameter: float,
        head_height: float,
        clearance_diameter: float,
        tap_diameter: float,
        head_type: str = "socket",
        drive_type: str = "hex",
        head_angle: float = 90.0
    ):
        self.length = float(length)
        self.major_diameter = float(major_diameter)
        self.head_diameter = float(head_diameter)
        self.head_height = float(head_height)
        self.clearance_diameter = float(clearance_diameter)
        self.tap_diameter = float(tap_diameter)
        self.head_type = head_type.lower()
        self.drive_type = drive_type
        self.head_angle = float(head_angle)

    @classmethod
    def from_size(cls, size: str, length: float, head_type: str = "socket", drive_type: str = "hex") -> "MetricMachineScrew":
        """Factory method to create a MetricMachineScrew from a standardized string identifier (e.g., 'M3')."""
        size = size.upper()
        if size not in METRIC_SIZES:
            raise ValueError(f"Unsupported metric size: {size}. Available: {list(METRIC_SIZES.keys())}")
            
        data = METRIC_SIZES[size]
        head_type = head_type.lower()
        
        if head_type == "flat":
            head_dia = data["flat_head_dia"]
            head_h = data["flat_head_h"]
        elif head_type == "socket":
            head_dia = data["socket_head_dia"]
            head_h = data["socket_head_h"]
        elif head_type in ["pan", "button"]:
            head_dia = data["pan_head_dia"]
            head_h = data["pan_head_h"]
        else:
            raise ValueError(f"Unknown head type: {head_type}")
            
        return cls(
            length=length,
            major_diameter=data["major"],
            head_diameter=head_dia,
            head_height=head_h,
            clearance_diameter=data["clearance"],
            tap_diameter=data["tap"],
            head_type=head_type,
            drive_type=drive_type,
            head_angle=90.0,
        )

    @property
    def solid(self) -> cq.Workplane:
        """Generates the positive physical model of the metric screw."""
        shaft = cq.Workplane("XY").circle(self.major_diameter / 2).extrude(-self.length)
        
        if self.head_type == "flat":
            r1 = self.head_diameter / 2.0
            r2 = self.major_diameter / 2.0
            angle_rad = math.radians(self.head_angle / 2.0)
            physical_cone_height = (r1 - r2) / math.tan(angle_rad)
            head = cq.Workplane("XY", origin=(0,0,-physical_cone_height)).circle(r2).workplane(offset=physical_cone_height).circle(r1).loft()
            return shaft.union(head)
            
        else:
            if self.head_type == "socket":
                head = cq.Workplane("XY").circle(self.head_diameter / 2.0).extrude(self.head_height)
            elif self.head_type in ["pan", "button"]:
                head = cq.Workplane("XY").circle(self.head_diameter / 2.0).extrude(self.head_height)
                try:
                    head = head.edges(">Z").fillet(self.head_height * 0.4)
                except:
                    pass
            return shaft.union(head)

    def to_cutter(self, mode: str = "clearance", radial_allowance: float = 0.0, head_recess_depth: float = 0.0) -> cq.Workplane:
        """Generates a boolean subtraction tool (cutter) for this metric screw."""
        if mode == "clearance":
            shaft_radius = (self.clearance_diameter / 2.0) + radial_allowance
        elif mode == "tap":
            shaft_radius = (self.tap_diameter / 2.0) + radial_allowance
        elif mode == "interference":
            shaft_radius = (self.major_diameter / 2.0) - 0.1 + radial_allowance
        else:
            raise ValueError(f"Unknown mode: {mode}")

        overcut = 100.0
        shaft_cutter = cq.Workplane("XY", origin=(0,0, -(self.length + overcut))).circle(shaft_radius).extrude(self.length + overcut + 1)
        
        head_radius = (self.head_diameter / 2.0) + max(0.0, radial_allowance)
        z_offset = -head_recess_depth
        
        if self.head_type == "flat":
            angle_rad = math.radians(self.head_angle / 2.0)
            cone_height = (head_radius - shaft_radius) / math.tan(angle_rad)
            cone = (cq.Workplane("XY", origin=(0, 0, z_offset - cone_height))
                    .circle(shaft_radius).workplane(offset=cone_height).circle(head_radius).loft())
            head_overcut = cq.Workplane("XY", origin=(0, 0, z_offset)).circle(head_radius).extrude(overcut)
            head_cutter = cone.union(head_overcut)
        else:
            head_cutter = cq.Workplane("XY", origin=(0, 0, z_offset)).circle(head_radius).extrude(max(self.head_height, overcut))
            
        return shaft_cutter.union(head_cutter)

if __name__ == "__main__":
    from ocp_vscode import show
    screw1 = MetricMachineScrew.from_size("M3", length=10, head_type="socket")
    screw2 = MetricMachineScrew.from_size("M3", length=10, head_type="flat")
    show(screw1.solid.translate((-5, 0, 0)), screw2.solid.translate((5, 0, 0)), names=["Socket", "Flat"])
