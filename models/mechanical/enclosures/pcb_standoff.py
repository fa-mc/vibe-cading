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
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class PcbStandoffs:
    """
    Parametric PCB Standoffs.
    Generates an array of cylindrical mounting pillars with pilot holes.
    The primary interface (bottom of the pillars) sits at Z=0.
    """
    positions: List[Tuple[float, float]]
    height: float = 6.0
    outer_diameter: float = 5.0
    hole_diameter: float = 2.4  # Pilot hole for M3 self-tapping screw
    hole_depth: float = 5.0

    @property
    def solid(self) -> cq.Workplane:
        """
        Returns the additive geometry for the standoffs.
        """
        if not self.positions:
            return cq.Workplane("XY")

        # Create the base pillars
        result = cq.Workplane("XY").pushPoints(self.positions).circle(self.outer_diameter / 2).extrude(self.height)

        from models.mechanical.holes import ClearanceHole
        from models.print_settings import get_profile
        prof = get_profile()
        
        
        # hole_diameter is already the intended size including clearances for pilot.
        # But we create a ClearanceHole going down into the standoff.
        # It's at Z=self.height.
        hole_def = ClearanceHole(self.hole_diameter, self.hole_depth, prof)
        # Note: the ClearanceHole points into -Z.
        # Translate to height and apply at all positions
        hole_cutter = hole_def.to_cutter(overcut=1.0).translate((0, 0, self.height))
        
        for pos in self.positions:
            result = result.cut(hole_cutter.translate((pos[0], pos[1], 0)))
        return result
