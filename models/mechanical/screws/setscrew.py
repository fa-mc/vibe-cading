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

SET_SCREW_SIZES = {
    "M2": {"major": 2.0, "tap": 1.6, "clearance": 2.2},
    "M2.5": {"major": 2.5, "tap": 2.1, "clearance": 2.7},
    "M3": {"major": 3.0, "tap": 2.5, "clearance": 3.2},
    "M4": {"major": 4.0, "tap": 3.3, "clearance": 4.3},
    "M5": {"major": 5.0, "tap": 4.2, "clearance": 5.3},
}

class SetScrew(Screw):
    """
    Headless grub screws / set screws typically used for trapping shafts or locking gears.
    """
    def __init__(
        self,
        length: float,
        major_diameter: float,
        clearance_diameter: float,
        tap_diameter: float,
        drive_type: str = "hex"
    ):
        self.length = float(length)
        self.major_diameter = float(major_diameter)
        self.clearance_diameter = float(clearance_diameter)
        self.tap_diameter = float(tap_diameter)
        self.drive_type = drive_type

    @classmethod
    def from_size(cls, size: str, length: float, drive_type: str = "hex") -> "SetScrew":
        size = size.upper()
        if size not in SET_SCREW_SIZES:
            raise ValueError(f"Unsupported grub screw size: {size}. Available: {list(SET_SCREW_SIZES.keys())}")
        data = SET_SCREW_SIZES[size]
        return cls(
            length=length,
            major_diameter=data["major"],
            clearance_diameter=data["clearance"],
            tap_diameter=data["tap"],
            drive_type=drive_type
        )

    @property
    def solid(self) -> cq.Workplane:
        return cq.Workplane("XY").circle(self.major_diameter / 2).extrude(-self.length)

    def to_cutter(self, mode: str = "tap", profile = None):
        from models.print_settings import get_profile
        prof = profile or get_profile()
        radial_allowance = prof.free_fit
        head_recess_depth = prof.z_clearance
        if mode == "tap":
            shaft_dia = (self.tap_diameter) + radial_allowance * 2
        elif mode == "clearance":
            shaft_dia = (self.clearance_diameter) + radial_allowance * 2
        else:
            raise ValueError("SetScrew to_cutter mode must be 'tap' or 'clearance'")

        from models.mechanical.holes import ClearanceHole
        from models.print_settings import ToleranceProfile
        
        custom_prof = ToleranceProfile(
            name="legacy_override",
            
            
            free_fit=radial_allowance,
            z_clearance=head_recess_depth
        , press_fit=0.0, slip_fit=0.0)
        
        hole = ClearanceHole(
            diameter=shaft_dia,
            depth=self.length,
            profile=custom_prof
        )
        
        # We need to translate the hole cutter down by head_recess_depth to match old behavior
        # where it started at -head_recess_depth
        return hole.to_cutter().translate((0, 0, -head_recess_depth))

if __name__ == "__main__":
    from ocp_vscode import show
    grub = SetScrew.from_size("M3", 4)
    show(
        grub.solid.translate((-5, 0, 0)),
        grub.to_cutter(mode="tap").translate((5, 0, 0)),
        names=["M3 Grub", "Tap Cutter"]
    )
