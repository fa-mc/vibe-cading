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

    def to_cutter(self, mode: str = "tap", radial_allowance: float = 0.0, head_recess_depth: float = 0.0) -> cq.Workplane:
        if mode == "tap":
            shaft_radius = (self.tap_diameter / 2.0) + radial_allowance
        elif mode == "clearance":
            shaft_radius = (self.clearance_diameter / 2.0) + radial_allowance
        else:
            raise ValueError("SetScrew to_cutter mode must be 'tap' or 'clearance'")

        overcut = 100.0
        # For a grub screw, the 'head' is flush with the top, so we push the cutter all the way through the recess.
        z_start = -head_recess_depth + overcut
        return cq.Workplane("XY", origin=(0, 0, z_start)).circle(shaft_radius).extrude(-(self.length + overcut*2))

if __name__ == "__main__":
    from ocp_vscode import show
    grub = SetScrew.from_size("M3", 4)
    show(
        grub.solid.translate((-5, 0, 0)),
        grub.to_cutter(mode="tap").translate((5, 0, 0)),
        names=["M3 Grub", "Tap Cutter"]
    )
