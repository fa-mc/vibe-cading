import cadquery as cq
from models.mechanical.screws import MetricMachineScrew
from models.print_settings import get_screw_allowances

class MotorMountPlate:
    def __init__(self, gearbox_screw_size="M2.5", motor_screw_size="M3", motor_hole_dist=17.0, motor_boss_clearance_d=9.0, material="PLA"):
        self.gearbox_screw_size = gearbox_screw_size
        self.motor_screw_size = motor_screw_size
        self.motor_hole_dist = motor_hole_dist
        self.motor_boss_clearance_d = motor_boss_clearance_d

        self.material = material
        allowances = get_screw_allowances(self.material)
        self.radial_allowance = allowances["radial_allowance"]
        self.head_recess = allowances["head_recess_depth"]

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
        gb_screw = MetricMachineScrew(size=self.gearbox_screw_size, length=self.thickness + 2.0, head_type="flat", drive_type="hex")
        gb_cutter = gb_screw.to_cutter(mode="clearance", radial_allowance=self.radial_allowance, head_recess_depth=self.head_recess)

        for pt in self.corner_hole_centers:
            # Shift cutting tool to the top face (Z = thickness)
            cutter_shifted = gb_cutter.translate((pt[0], pt[1], self.thickness))
            plate = plate.cut(cutter_shifted)

        # 3. Motor mounting holes (Mounts motor to the plate)
        # Flathead screws facing UP, flat on the bottom surface
        motor_screw = MetricMachineScrew(size=self.motor_screw_size, length=self.thickness + 2.0, head_type="flat", drive_type="hex")
        motor_cutter = motor_screw.to_cutter(mode="clearance", radial_allowance=self.radial_allowance, head_recess_depth=self.head_recess).rotate((0,0,0), (1,0,0), 180)

        motor_pts = [
            (self.motor_hole_dist/2, 0.0),
            (-self.motor_hole_dist/2, 0.0)
        ]

        for pt in motor_pts:
            # Bottom face is at Z = 0
            cutter_shifted = motor_cutter.translate((pt[0], pt[1], 0))
            plate = plate.cut(cutter_shifted)

        # 4. Central bore hole for the motor front boss
        plate = plate.faces(">Z").workplane().hole(self.motor_boss_clearance_d)

        self.solid = plate

if __name__ == "__main__":
    from ocp_vscode import show

    # Preview configuration
    model = MotorMountPlate()
    show(model.solid, names=["Mount Plate - Default 370"])
