import math
import cadquery as cq
from .base import Screw

# Standard Imperial UTS (Unified Thread Standard) dimensions converted to mm.
# Common sizes for electronics, rack mounts, and basic hardware.
IMPERIAL_SIZES = {
    "4-40": {"major_dia": 2.845, "socket_head_dia": 5.2, "socket_head_h": 2.8, "flat_head_dia": 5.7, "flat_head_h": 1.7, "pan_head_dia": 5.5, "pan_head_h": 2.0},
    "6-32": {"major_dia": 3.505, "socket_head_dia": 5.7, "socket_head_h": 3.5, "flat_head_dia": 7.1, "flat_head_h": 2.1, "pan_head_dia": 7.0, "pan_head_h": 2.5},
    "8-32": {"major_dia": 4.166, "socket_head_dia": 6.8, "socket_head_h": 4.1, "flat_head_dia": 8.5, "flat_head_h": 2.5, "pan_head_dia": 8.0, "pan_head_h": 3.0},
    "10-24": {"major_dia": 4.826, "socket_head_dia": 7.9, "socket_head_h": 4.8, "flat_head_dia": 9.8, "flat_head_h": 2.9, "pan_head_dia": 9.5, "pan_head_h": 3.4},
    "1/4-20": {"major_dia": 6.350, "socket_head_dia": 9.5, "socket_head_h": 6.3, "flat_head_dia": 13.0, "flat_head_h": 3.9, "pan_head_dia": 12.5, "pan_head_h": 4.4},
}

class ImperialMachineScrew(Screw):
    """Standard Unified Thread Standard (UTS) Imperial machine screws 
    (e.g., 6-32, 4-40) converted to native mm coordinates for CadQuery use.
    """
    def __init__(self, size: str, length: float, head_type: str = "socket", drive_type: str = "hex"):
        size = size.lower()
        if size not in IMPERIAL_SIZES:
            raise ValueError(f"Unsupported imperial size: {size}. Available: {list(IMPERIAL_SIZES.keys())}")
            
        data = IMPERIAL_SIZES[size]
        self.head_type = head_type.lower()
        
        if self.head_type == "flat":
            self.head_diameter = data["flat_head_dia"]
            self.head_height = data["flat_head_h"]
            self.head_angle = 82.0 # Imperial flat heads use 82-degree countersink (unlike Metric 90-degree)
        elif self.head_type == "socket":
            self.head_diameter = data["socket_head_dia"]
            self.head_height = data["socket_head_h"]
        elif self.head_type in ["pan", "button"]:
            self.head_diameter = data["pan_head_dia"]
            self.head_height = data["pan_head_h"]
        else:
            raise ValueError(f"Unsupported head type: {head_type}. Choose 'socket', 'flat', or 'pan'.")

        self.size = size
        self.length = length
        self.major_diameter = data["major_dia"]
        self.drive_type = drive_type

    @property
    def solid(self) -> cq.Workplane:
        # Build head
        if self.head_type == "flat":
            r1 = self.head_diameter / 2.0
            r2 = self.major_diameter / 2.0
            head = (
                cq.Workplane("XY")
                .circle(r1)
                .workplane(offset=-self.head_height)
                .circle(r2)
                .loft()
            )
        else:
            if self.head_type == "socket":
                head = cq.Workplane("XY").circle(self.head_diameter / 2.0).extrude(self.head_height)
            elif self.head_type in ["pan", "button"]:
                head_cyl = cq.Workplane("XY").circle(self.head_diameter / 2.0).extrude(self.head_height - 0.5)
                comp = (
                    cq.Workplane("XY")
                    .transformed(offset=cq.Vector(0, 0, self.head_height - 0.5))
                    .circle(self.head_diameter / 2.0)
                    .workplane(offset=0.5)
                    .circle(self.head_diameter / 3.0)
                    .loft()
                )
                head = head_cyl.union(comp)
            
        # Build shaft
        shaft_z = -self.head_height if self.head_type == "flat" else 0.0
        shaft_len = self.length - self.head_height if self.head_type == "flat" else self.length
        
        shaft = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, shaft_z))
            .circle(self.major_diameter / 2.0)
            .extrude(-shaft_len)
        )
        
        return head.union(shaft)

    def to_cutter(self, mode: str = "clearance", radial_allowance: float = 0.0, head_recess_depth: float = 0.0) -> cq.Workplane:
        if mode == "clearance":
            shaft_radius = (self.major_diameter / 2.0) + radial_allowance + 0.15
        elif mode == "tap":
            shaft_radius = (self.major_diameter / 2.0) - 0.15 + radial_allowance
        elif mode == "interference":
            shaft_radius = (self.major_diameter / 2.0) - 0.3 + radial_allowance
        else:
            raise ValueError("Unsupported cutter mode")

        head_radius = (self.head_diameter / 2.0) + radial_allowance
        z_offset = -head_recess_depth
        
        if self.head_type == "flat":
            angle_rad = math.radians(self.head_angle / 2.0)
            cone_height = (head_radius - shaft_radius) / math.tan(angle_rad)
            
            upper_recess = None
            if head_recess_depth > 0:
                upper_recess = cq.Workplane("XY").circle(head_radius).extrude(-head_recess_depth)
                
            countersink = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, 0, z_offset))
                .circle(head_radius)
                .workplane(offset=-cone_height)
                .circle(shaft_radius)
                .loft()
            )
            
            shaft_z = z_offset - cone_height
            shaft_len = self.length - self.head_height + head_recess_depth + cone_height
            
            shaft = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, 0, shaft_z))
                .circle(shaft_radius)
                .extrude(-shaft_len - 5.0) 
            )
            
            cutter = countersink.union(shaft)
            if upper_recess:
                cutter = upper_recess.union(cutter)
                
        else:
            head = (
                cq.Workplane("XY")
                .circle(head_radius)
                .extrude(self.head_height + 5.0) 
            )
            
            if head_recess_depth > 0:
                recess = (
                    cq.Workplane("XY")
                    .circle(head_radius)
                    .extrude(-head_recess_depth)
                )
                head = head.union(recess)
                
            shaft = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, 0, z_offset))
                .circle(shaft_radius)
                .extrude(-self.length - 5.0) 
            )
            cutter = head.union(shaft)

        return cutter

if __name__ == "__main__":
    from ocp_vscode import show
    
    # Showcase standard 6-32 flathead PC/server screw and cutter
    unc = ImperialMachineScrew("6-32", 10, head_type="flat")
    
    show(
        unc.solid.translate((-5, 0, 0)),
        unc.to_cutter(mode="clearance").translate((5, 0, 0)),
        names=["6-32 Flat Solid", "6-32 Flat Cutter"]
    )