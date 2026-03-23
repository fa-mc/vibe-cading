import cadquery as cq
from .base import Screw
from .metric import METRIC_SIZES

class SetScrew(Screw):
    """
    Standard Metric Set Screw (grub screw) (e.g. DIN 913 flat point, DIN 916 cup point).
    Used to lock gears, pulleys, and collars onto shafts.

    It has no head, only a threaded cylindrical body.
    """
    def __init__(self, size: str, length: float, drive_type: str = "hex"):
        size = size.upper()
        if size not in METRIC_SIZES:
            raise ValueError(f"Unsupported metric size: {size}. Available: {list(METRIC_SIZES.keys())}")

        data = METRIC_SIZES[size]
        self.size = size
        self.length = length
        self.major_diameter = data["major_dia"]
        self.drive_type = drive_type

        # Hex socket sizes for grub screws are typically smaller than standard machine screws
        self.socket_size = self.major_diameter / 2.0

    @property
    def solid(self) -> cq.Workplane:
        """The literal 3D solid of the grub screw."""
        # Simple threaded cylinder body
        body = (
            cq.Workplane("XY")
            .circle(self.major_diameter / 2.0)
            .extrude(-self.length)
        )

        # Hex drive socket cut into the top
        socket_depth = min(self.length / 2.0, self.major_diameter)
        socket = (
            cq.Workplane("XY")
            .polygon(6, self.socket_size * 2) # circumscribed radius
            .extrude(-socket_depth)
        )

        # Chamfer the bottom slightly (simulating a cup or flat point)
        chamfer_dist = self.major_diameter * 0.1
        body = body.edges(cq.selectors.NearestToPointSelector((0,0,-self.length))).chamfer(chamfer_dist)

        return body.cut(socket)

    def to_cutter(self, mode: str = "tap", radial_allowance: float = 0.0, head_recess_depth: float = 0.0) -> cq.Workplane:
        """
        Generates the subtraction cutter for the set screw.

        mode="tap" (default): Usually grub screws are threaded into a tapped hole.
        mode="clearance": Passes freely through material (rare for grub screws, but supported).
        """

        if mode == "tap":
            shaft_radius = (self.major_diameter / 2.0) - (self.major_diameter * 0.1) + radial_allowance
        elif mode == "clearance":
            shaft_radius = (self.major_diameter / 2.0) + radial_allowance + 0.1
        else:
            raise ValueError("SetScrew to_cutter mode must be 'tap' or 'clearance'")

        # Head recess depth doesn't make geometric sense in the same way for a grub screw,
        # but if provided, we just start the cutter higher up (+Z).
        return (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, head_recess_depth))
            .circle(shaft_radius)
            .extrude(-self.length - head_recess_depth)
        )

if __name__ == "__main__":
    from ocp_vscode import show

    grub = SetScrew("M3", 4)

    show(
        grub.solid.translate((-5, 0, 0)),
        grub.to_cutter(mode="tap").translate((5, 0, 0)),
        names=["M3x4 Grub Screw", "M3 Grub Tap Hole"]
    )