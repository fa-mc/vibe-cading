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
from dataclasses import dataclass, field
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

        # Create the pilot holes
        result = (
            result.faces(">Z")
            .workplane()
            .pushPoints(self.positions)
            .hole(self.hole_diameter, self.hole_depth)
        )
        return result

if __name__ == "__main__":
    standoffs = PcbStandoffs(
        positions=[(0, 0), (50, 0), (50, 30), (0, 30)],
        height=8.0,
        outer_diameter=6.0,
        hole_diameter=2.5,
        hole_depth=6.0
    )
    from ocp_vscode import show
    show(standoffs.solid)
