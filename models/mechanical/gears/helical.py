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

"""HelicalGear — parametric involute helical gear."""

from __future__ import annotations
import math
import cadquery as cq
from .spur import SpurGear

class HelicalGear(SpurGear):
    """Parametric involute helical gear.

    Parameters
    ----------
    module : float
        Normal module (mm). Standard values: 0.5, 1, 1.5, 2...
    teeth : int
        Number of teeth.
    face_width : float
        Axial thickness (mm).
    helix_angle : float
        Helix angle in degrees. Positive for right-hand, negative for left-hand.
    bore : float | None
        Diameter of central through-bore (mm).
    pressure_angle : float
        Normal pressure angle in degrees. Default 20°.
    n_flank : int
        Number of points per flank.
    """
    def __init__(
        self,
        module: float,
        teeth: int,
        face_width: float,
        helix_angle: float,
        bore: float | None = None,
        pressure_angle: float = 20.0,
        n_flank: int = 32,
    ) -> None:
        self.normal_module = float(module)
        self.helix_angle = float(helix_angle)
        self.normal_pressure_angle = float(pressure_angle)
        
        # Calculate transverse properties
        beta_rad = math.radians(self.helix_angle)
        transverse_module = self.normal_module / math.cos(beta_rad)
        
        # Transverse pressure angle
        # tan(alpha_t) = tan(alpha_n) / cos(beta)
        tan_alpha_t = math.tan(math.radians(self.normal_pressure_angle)) / math.cos(beta_rad)
        transverse_pressure_angle = math.degrees(math.atan(tan_alpha_t))

        # We initialize SpurGear with the TRANSVERSE properties to build the 2-D profile
        super().__init__(
            module=transverse_module,
            teeth=teeth,
            face_width=face_width,
            bore=bore,
            pressure_angle=transverse_pressure_angle,
            n_flank=n_flank
        )

    def _build(self) -> cq.Workplane:
        pts = self._gear_profile_points(
            n_flank=self._n_flank,
            n_tip=max(2, self._n_flank // 8),
            n_root=max(3, self._n_flank // 8),
        )

        # Twist angle in degrees over face_width
        # Twist = 360 * width * tan(beta) / (pi * d)  where d = m_t * z
        d = self.pitch_radius * 2.0
        twist_degrees = 360.0 * self.face_width * math.tan(math.radians(self.helix_angle)) / (math.pi * d)

        gear = (
            cq.Workplane("XY")
            .polyline(pts)
            .close()
            .twistExtrude(self.face_width, twist_degrees)
        )

        if self.bore is not None:
            bore_cyl = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, 0, -0.1))
                .circle(self.bore / 2.0)
                .extrude(self.face_width + 0.2)
            )
            gear = gear.cut(bore_cyl)

        return gear

if __name__ == "__main__":
    from ocp_vscode import show
    g = HelicalGear(module=2, teeth=20, face_width=15, helix_angle=30, bore=5)
    show(g.solid, names=["HelicalGear"], colors=["gold"])
