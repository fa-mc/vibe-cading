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

"""28T gear lego compatible with 1 stud width."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

import cadquery as cq
from models.mechanical.gears import SpurGear
from models.lego.cutters.technic_axle_hole import TechnicAxleHole

class LegoGear28T:
    def __init__(self):
        # Lego gears: Module = 1.0. Outer Diameter = module * (teeth + 2)
        # So 28T has outer diameter = 1.0 * 30 = 30mm.
        # Lego gear width for 1 stud is almost the full 8.0mm, perhaps 7.8mm. But the "face_width" for 1 stud of gear is usually a bit less to avoid rubbing. Let's start with 7.8mm.

        self.module = 1.0
        self.teeth = 28
        # Standard technic beam thickness is 7.2. So maybe 7.2 or 7.8 for gears.
        # A 1-stud width in Lego is technically 8.0 center-to-center. But beams are 7.2mm thick. Gears are sometimes 7.2mm as well, or 8.0 if they are full plates + studs. Let's use 7.8mm for standard 1-stud wide gears, or 7.2 to match beams. I will use 7.8mm.
        self.face_width = 7.8

        self._solid = self._build()

    def _build(self) -> cq.Workplane:
        gear = SpurGear(
            module=self.module,
            teeth=self.teeth,
            face_width=self.face_width,
            bore=None # We will cut a specific axle hole
        )

        # Center the gear at Z = 0 over its thickness for symmetry or keep its base at Z=0.
        # SpurGear extrudes from Z=0 to Z=face_width.
        res = gear.solid

        # Add TechnicAxleHole cutter
        # We need the cutter hole to go all the way through, meaning its depth needs to be face_width + some margin.
        axle_cutter = TechnicAxleHole(depth=self.face_width + 1.0).solid.translate((0, 0, -0.5))

        res = res.cut(axle_cutter)

        # We can also add some standard lightening holes if 28T is too solid (it has a diameter of 30mm).
        # Typically 4 or 6 round holes. Lego 24T usually has none or has round holes.
        # Let's add 4 round holes of 4.8mm to match technic pins, at radius 8mm (1 stud).
        # Actually 28T is 14mm radius.

        pin_hole_dia = 4.8

        # Cut 4 pin holes at X/Y grid positions to be compatible with other lego.
        # If it's a 28T gear, pitch radius is 14mm. So grid points at ±8,0 and 0,±8 work nicely.
        for dx, dy in [(8, 0), (-8, 0), (0, 8), (0, -8)]:
            cutter = cq.Workplane("XY").center(dx, dy).circle(pin_hole_dia / 2).extrude(self.face_width + 1.0).translate((0, 0, -0.5))
            res = res.cut(cutter)

        return res

    @property
    def solid(self) -> cq.Workplane:
        return self._solid

if __name__ == "__main__":
    from ocp_vscode import show
    g = LegoGear28T()
    show(g.solid, names=["LegoGear28T"])
