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

# Wood screw sizes (Approximate values for #4, #6, #8, #10, and some imperial fractions)
WOOD_SIZES = {
    "#2":   {"major": 2.2, "clearance": 2.5, "tap": 1.5, "flat_head_dia": 4.3, "flat_head_h": 1.3, "pan_head_dia": 4.2, "pan_head_h": 1.4},
    "#4":   {"major": 2.8, "clearance": 3.2, "tap": 2.0, "flat_head_dia": 5.5, "flat_head_h": 1.7, "pan_head_dia": 5.5, "pan_head_h": 1.7},
    "#6":   {"major": 3.5, "clearance": 4.0, "tap": 2.4, "flat_head_dia": 6.8, "flat_head_h": 2.1, "pan_head_dia": 6.8, "pan_head_h": 2.1},
    "#8":   {"major": 4.2, "clearance": 4.8, "tap": 2.8, "flat_head_dia": 8.1, "flat_head_h": 2.5, "pan_head_dia": 8.1, "pan_head_h": 2.5},
    "#10":  {"major": 4.8, "clearance": 5.5, "tap": 3.2, "flat_head_dia": 9.2, "flat_head_h": 2.8, "pan_head_dia": 9.2, "pan_head_h": 2.8},
    "3/16": {"major": 4.76, "clearance": 5.5, "tap": 3.2, "flat_head_dia": 9.0, "flat_head_h": 2.8, "pan_head_dia": 9.0, "pan_head_h": 2.8},
}

class WoodScrew(Screw):
    """Standard wood and self-tapping screws."""
    def __init__(self, size: str, length: float, head_type: str = "flat", drive_type: str = "phillips"):
        if size not in WOOD_SIZES:
            raise ValueError(f"Unsupported wood screw size: {size}. Available: {list(WOOD_SIZES.keys())}")
            
        data = WOOD_SIZES[size]
        self.head_type = head_type.lower()
        
        if self.head_type == "flat":
            self.head_diameter = data["flat_head_dia"]
            self.head_height = data["flat_head_h"]
        elif self.head_type in ["pan", "button", "round"]:
            self.head_type = "pan"
            self.head_diameter = data["pan_head_dia"]
            self.head_height = data["pan_head_h"]
        else:
            raise ValueError(f"WoodScrew usually does not support {head_type}")
            
        self.major_diameter = data["major"]
        self.length = length
        self.clearance_diameter = data["clearance"]
        self.tap_diameter = data["tap"]
        self.head_angle = 82.0 # Standard imperial wood screws are 82 degrees
        self.drive_type = drive_type

    @property
    def solid(self) -> cq.Workplane:
        """Generates the positive physical model of the wood screw (with a tapered tip)."""
        r = self.major_diameter / 2.0
        
        # Wood screws typically have a pointed tip.
        # We will devote the last roughly ~2mm (or 20% of length, whichever is smaller) to a point
        tip_length = min(2.0, self.length * 0.2)
        straight_length = self.length - tip_length
        
        # Base straight shaft
        shaft_straight = cq.Workplane("XY").circle(r).extrude(-straight_length)
        # Tapered tip
        tip = (cq.Workplane("XY", origin=(0, 0, -straight_length))
               .circle(r)
               .workplane(offset=-tip_length)
               .circle(0.1) # practically a point
               .loft())
               
        shaft = shaft_straight.union(tip)
        
        # Build head
        if self.head_type == "flat":
            r1 = self.head_diameter / 2.0
            angle_rad = math.radians(self.head_angle / 2.0)
            physical_cone_height = (r1 - r) / math.tan(angle_rad)
            
            head = cq.Workplane("XY", origin=(0,0,-physical_cone_height)).circle(r).workplane(offset=physical_cone_height).circle(r1).loft()
            return shaft.union(head)
            
        else:
            head = cq.Workplane("XY").circle(self.head_diameter / 2.0).extrude(self.head_height)
            try:
                head = head.edges(">Z").fillet(self.head_height * 0.4)
            except:
                pass
            return shaft.union(head)

    def to_cutter(self, mode: str = "clearance", profile = None):
        from models.print_settings import get_profile
        prof = profile or get_profile()
        radial_allowance = prof.free_fit
        head_recess_depth = prof.z_clearance
        if mode == "clearance":
            shaft_dia = (self.clearance_diameter) + radial_allowance * 2
        elif mode == "tap":
            shaft_dia = (self.tap_diameter) + radial_allowance * 2
        elif mode == "interference":
            shaft_dia = (self.major_diameter) - 0.2 + radial_allowance * 2
        else:
            raise ValueError(f"Unknown mode: {mode}")

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

