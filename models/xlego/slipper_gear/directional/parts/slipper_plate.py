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

"""SlipperPlate — base disc + central hub + independent spiral leaf springs."""

from __future__ import annotations
import cadquery as cq

from models.lego.cutters.technic_axle_hole import TechnicAxleHole

class SlipperPlate:
    """A Slipper Plate assembly consisting of a base disk, a central cross-axle hub,
    and a spiral leaf spring hovering above the base disk.

    Parameters
    ----------
    plate_r : float
        Radius of the outer base disk (mm).
    plate_thickness : float
        Axial thickness of the base disk (mm).
    hub_r : float
        Radius of the solid central core (mm).
    hub_length : float
        Total length of the central hub (mm).
    """

    def __init__(
        self,
        plate_r: float = 10.3,
        plate_thickness: float = 1.2,
        hub_r: float = 6.0,
        hub_length: float = 1.2,
        hole_d: float | None = None,
        bushing_r: float | None = None,
        bushing_clearance: float = 0.1,
    ) -> None:
        self.plate_r = plate_r
        self.plate_thickness = plate_thickness
        self.hub_r = hub_r
        self.hub_length = hub_length
        self.hole_d = hole_d
        self.bushing_r = bushing_r
        self.bushing_clearance = bushing_clearance

        self._solid = self._build()

    @property
    def solid(self) -> cq.Workplane:
        return self._solid

    def _build(self) -> cq.Workplane:
        # If hub is taller than base, union them. Otherwise base covers it.
        overall_length = max(self.plate_thickness, self.hub_length)
        axle_fw = overall_length + 2.0

        if self.bushing_r is not None:
            # 1. Outer plate (washer)
            outer_hole_r = self.bushing_r + self.bushing_clearance
            outer = cq.Workplane("XY").circle(self.plate_r).circle(outer_hole_r).extrude(overall_length)

            # 2. Inner bushing
            inner = cq.Workplane("XY").circle(self.bushing_r).extrude(overall_length)
            axle_tool = TechnicAxleHole(depth=axle_fw).solid.translate((0, 0, -1.0))
            inner = inner.cut(axle_tool)

            parts = [outer.val(), inner.val()]
            return cq.Workplane(obj=cq.Compound.makeCompound(parts))

        # 1. Base Disk
        core = cq.Workplane("XY").circle(self.plate_r).extrude(overall_length)

        # 3. Add axle hole or round clearance hole

        if self.hole_d is not None:
            axle_tool = cq.Workplane("XY").circle(self.hole_d / 2.0).extrude(axle_fw).translate((0, 0, -1.0))
        else:
            axle_tool = TechnicAxleHole(depth=axle_fw).solid.translate((0, 0, -1.0))

        core = core.cut(axle_tool)

        return core
