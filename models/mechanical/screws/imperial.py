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
from .base import Screw

IMPERIAL_SIZES = {
    "4-40": {"major_dia": 2.845, "socket_head_dia": 5.2, "socket_head_h": 2.8, "flat_head_dia": 5.7, "flat_head_h": 1.7, "pan_head_dia": 5.5, "pan_head_h": 2.0},
    "6-32": {"major_dia": 3.505, "socket_head_dia": 5.7, "socket_head_h": 3.5, "flat_head_dia": 7.1, "flat_head_h": 2.1, "pan_head_dia": 7.0, "pan_head_h": 2.5},
    "8-32": {"major_dia": 4.166, "socket_head_dia": 6.8, "socket_head_h": 4.1, "flat_head_dia": 8.5, "flat_head_h": 2.5, "pan_head_dia": 8.0, "pan_head_h": 3.0},
    "10-24": {"major_dia": 4.826, "socket_head_dia": 7.9, "socket_head_h": 4.8, "flat_head_dia": 9.8, "flat_head_h": 2.9, "pan_head_dia": 9.5, "pan_head_h": 3.4},
    "1/4-20": {"major_dia": 6.350, "socket_head_dia": 9.5, "socket_head_h": 6.3, "flat_head_dia": 13.0, "flat_head_h": 3.9, "pan_head_dia": 12.5, "pan_head_h": 4.4},
}

class ImperialMachineScrew(Screw):
    """Standard Unified Thread Standard (UTS) Imperial machine screws."""
    def __init__(
        self,
        length: float,
        major_diameter: float,
        head_diameter: float,
        head_height: float,
        head_type: str = "socket",
        drive_type: str = "hex",
        head_angle: float = 82.0
    ):
        self.length = float(length)
        self.major_diameter = float(major_diameter)
        self.head_diameter = float(head_diameter)
        self.head_height = float(head_height)
        self.head_type = head_type.lower()
        self.drive_type = drive_type
        self.head_angle = float(head_angle)

    @classmethod
    def from_size(cls, size: str, length: float, head_type: str = "socket", drive_type: str = "hex") -> "ImperialMachineScrew":
        size = size.lower()
        if size not in IMPERIAL_SIZES:
            raise ValueError(f"Unsupported imperial size: {size}. Available: {list(IMPERIAL_SIZES.keys())}")
        
        data = IMPERIAL_SIZES[size]
        head_type = head_type.lower()

        if head_type == "flat":
            head_dia = data["flat_head_dia"]
            head_h = data["flat_head_h"]
            head_angle = 82.0
        elif head_type == "socket":
            head_dia = data["socket_head_dia"]
            head_h = data["socket_head_h"]
            head_angle = 82.0
        elif head_type in ["pan", "button"]:
            head_dia = data["pan_head_dia"]
            head_h = data["pan_head_h"]
            head_angle = 82.0
        else:
            raise ValueError(f"Unsupported head type: {head_type}. Choose 'socket', 'flat', or 'pan'.")

        return cls(
            length=length,
            major_diameter=data["major_dia"],
            head_diameter=head_dia,
            head_height=head_h,
            head_type=head_type,
            drive_type=drive_type,
            head_angle=head_angle
        )

    @property
    def solid(self) -> cq.Workplane:
        if self.head_type == "flat":
            r1 = self.head_diameter / 2.0
            r2 = self.major_diameter / 2.0
            head = cq.Workplane("XY").circle(r1).workplane(offset=-self.head_height).circle(r2).loft()
        else:
            if self.head_type == "socket":
                head = cq.Workplane("XY").circle(self.head_diameter / 2.0).extrude(self.head_height)
            elif self.head_type in ["pan", "button"]:
                head_cyl = cq.Workplane("XY").circle(self.head_diameter / 2.0).extrude(self.head_height - 0.5)
                comp = (cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, self.head_height - 0.5))
                        .circle(self.head_diameter / 2.0).workplane(offset=0.5).circle(self.head_diameter / 3.0).loft())
                head = head_cyl.union(comp)

        shaft_z = -self.head_height if self.head_type == "flat" else 0.0
        shaft_len = self.length - self.head_height if self.head_type == "flat" else self.length
        shaft = cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, shaft_z)).circle(self.major_diameter / 2.0).extrude(-shaft_len)

        return head.union(shaft)

    def to_cutter(self, mode: str = "clearance", profile = None):
        from models.print_settings import get_profile
        prof = profile or get_profile()
        radial_allowance = prof.free_fit
        head_recess_depth = prof.z_clearance
        if mode == "clearance":
            shaft_dia = (self.major_diameter) + (radial_allowance + 0.15) * 2
        elif mode == "tap":
            shaft_dia = (self.major_diameter) + (-0.15 + radial_allowance) * 2
        elif mode == "interference":
            shaft_dia = (self.major_diameter) + (-0.3 + radial_allowance) * 2
        else:
            raise ValueError("Unsupported cutter mode")

        from models.mechanical.holes import CounterboreHole
        from models.print_settings import ToleranceProfile
        
        custom_prof = ToleranceProfile(
            name="legacy_override",
            
            
            free_fit=radial_allowance,
            z_clearance=head_recess_depth
        , press_fit=0.0, slip_fit=0.0)
        
        hole = CounterboreHole(
            shaft_diameter=shaft_dia,
            shaft_depth=self.length,
            head_diameter=self.head_diameter,
            head_depth=self.head_height,
            head_type="cylinder" if self.head_type != "flat" else "cone",
            head_angle=self.head_angle if self.head_type == "flat" else 90.0,
            profile=custom_prof
        )
        return hole.to_cutter()

