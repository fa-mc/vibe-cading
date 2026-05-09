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

"""RackGear — parametric involute rack gear."""

from __future__ import annotations
import math
import cadquery as cq

class RackGear:
    """Parametric involute rack gear.

    Parameters
    ----------
    module : float
        Normal module (mm). Standard values: 0.5, 1, 1.5, 2.
    length : float
        Total length of the rack (mm).
    face_width : float
        Axial thickness (mm).
    thickness : float
        Thickness of the base of the rack below the root line.
    pressure_angle : float
        Normal pressure angle in degrees. Default 20°.
    """
    def __init__(
        self,
        module: float,
        length: float,
        face_width: float,
        thickness: float,
        pressure_angle: float = 20.0,
    ) -> None:
        self.module = float(module)
        self.length = float(length)
        self.face_width = float(face_width)
        self.thickness = float(thickness)
        self.pressure_angle = float(pressure_angle)
        self._solid = self._build()
        
    @property
    def solid(self) -> cq.Workplane:
        return self._solid
        
    def _build(self) -> cq.Workplane:
        m = self.module
        phi = math.radians(self.pressure_angle)
        
        pitch = math.pi * m
        addendum = m
        dedendum = 1.25 * m
        
        tip_x = pitch / 4.0 - addendum * math.tan(phi)
        root_x = pitch / 4.0 + dedendum * math.tan(phi)
        
        num_teeth = int(math.ceil(self.length / pitch)) + 1
        actual_length = num_teeth * pitch
        start_x = -actual_length / 2.0
        
        profile_pts = []
        profile_pts.append((start_x, -dedendum - self.thickness))
        
        for i in range(num_teeth):
            offset = start_x + i * pitch + pitch / 2.0
            profile_pts.append((offset - root_x, -dedendum))
            profile_pts.append((offset - tip_x, addendum))
            profile_pts.append((offset + tip_x, addendum))
            profile_pts.append((offset + root_x, -dedendum))
            
        profile_pts.append((start_x + actual_length, -dedendum - self.thickness))
        
        rack = (
            cq.Workplane("XY")
            .polyline(profile_pts)
            .close()
            .extrude(self.face_width)
        )
        
        # Trim to exact length requested
        # bounding box to keep the central `length` part
        trim_box = (
            cq.Workplane("XY")
            .rect(self.length, (addendum + dedendum + self.thickness) * 4)
            .extrude(self.face_width * 2)
            .translate((0, 0, -self.face_width / 2.0))
        )
        
        return rack.intersect(trim_box)

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Show a m=2, length=50, fw=10, thickness=5 rack gear."""
        r = cls(module=2, length=50, face_width=10, thickness=5)
        return [(r.solid, "RackGear", "silver")]
