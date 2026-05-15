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
from vibe_cading.mechanical.screws import MetricMachineScrew
from vibe_cading.print_settings import get_profile

class MotorMountPlate:
    def __init__(
        self,
        gearbox_screw_size: str = "M2.5",
        motor_screw_size: str = "M3",
        motor_hole_dist: float = 17.0,
        motor_boss_clearance_diameter: float = 9.0,
        material: str = "PLA",
    ) -> None:
        self.gearbox_screw_size = gearbox_screw_size
        self.motor_screw_size = motor_screw_size
        self.motor_hole_dist = motor_hole_dist
        self.motor_boss_clearance_diameter = motor_boss_clearance_diameter

        self.material = material
        self.profile = get_profile(self.material)

        self.width = 24.0
        self.height = 24.0
        self.thickness = 4.12

        # Outer box mounting holes to attach the plate to the gearbox
        self.corner_hole_dist = 9.55 * 2

        self.corner_hole_centers = [
            (self.corner_hole_dist/2, self.corner_hole_dist/2),
            (self.corner_hole_dist/2, -self.corner_hole_dist/2),
            (-self.corner_hole_dist/2, self.corner_hole_dist/2),
            (-self.corner_hole_dist/2, -self.corner_hole_dist/2)
        ]

        self._build()

    def _build(self):
        # 1. Base plate on XY plane extruded along +Z
        plate = cq.Workplane("XY").rect(self.width, self.height).extrude(self.thickness)

        # 2. Corner holes (Mounts plate down to gear box)
        # Flathead screws facing down, flat on the top surface
        gb_screw = MetricMachineScrew.from_size(size=self.gearbox_screw_size, length=self.thickness + 2.0, head_type="flat", drive_type="hex")
        gb_cutter = gb_screw.to_cutter(profile=self.profile, fit="clearance")

        for pt in self.corner_hole_centers:
            # Shift cutting tool to the top face (Z = thickness)
            cutter_shifted = gb_cutter.translate((pt[0], pt[1], self.thickness))
            plate = plate.cut(cutter_shifted)

        # 3. Motor mounting holes (Mounts motor to the plate)
        # Flathead screws facing UP, flat on the bottom surface
        motor_screw = MetricMachineScrew.from_size(size=self.motor_screw_size, length=self.thickness + 2.0, head_type="flat", drive_type="hex")
        motor_cutter = motor_screw.to_cutter(profile=self.profile, fit="clearance").rotate((0,0,0), (1,0,0), 180)

        motor_pts = [
            (self.motor_hole_dist/2, 0.0),
            (-self.motor_hole_dist/2, 0.0)
        ]

        for pt in motor_pts:
            # Bottom face is at Z = 0
            cutter_shifted = motor_cutter.translate((pt[0], pt[1], 0))
            plate = plate.cut(cutter_shifted)

        # 4. Central bore hole for the motor front boss
        from vibe_cading.mechanical.holes import ClearanceHole
        from vibe_cading.print_settings import ToleranceProfile, FitGrade
        # Zero-clearance profile: the legacy STEP reference baked in the bore
        # diameter, so we must avoid the default ``free.radial`` inflation.
        prof = ToleranceProfile(
            name="legacy",
            free=FitGrade(radial=0.0, axial=0.0),
            slip=FitGrade(radial=0.0, axial=0.0),
            press=FitGrade(radial=0.0, axial=0.0),
        )
        boss_hole = ClearanceHole(self.motor_boss_clearance_diameter, self.thickness, prof)
        # Position at top surface Z=thickness, going down
        # ClearanceHole bakes its own through-hole overcut (100 mm) per class.
        cutter = boss_hole.to_cutter().translate((0, 0, self.thickness))
        plate = plate.cut(cutter)

        self.solid = plate
