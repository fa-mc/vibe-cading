import math
import cadquery as cq
from .base import Screw

# Standard dimensions for thread-forming screws for plastics (e.g., PT screws, K-Jet).
# These need specific pilot hole diameters to avoid splitting plastic bosses.
# Based on ISO 14581 / common PT standards.
PLASTIC_SCREW_SIZES = {
    "M2": {"major_dia": 2.0, "core_dia": 1.2, "pilot_dia": 1.6, "pan_head_dia": 4.0, "pan_head_h": 1.6, "flat_head_dia": 3.8, "flat_head_h": 1.2},
    "M2.5": {"major_dia": 2.5, "core_dia": 1.5, "pilot_dia": 2.0, "pan_head_dia": 5.0, "pan_head_h": 2.1, "flat_head_dia": 4.7, "flat_head_h": 1.5},
    "M3": {"major_dia": 3.0, "core_dia": 1.8, "pilot_dia": 2.4, "pan_head_dia": 6.0, "pan_head_h": 2.4, "flat_head_dia": 5.5, "flat_head_h": 1.65},
    "M4": {"major_dia": 4.0, "core_dia": 2.3, "pilot_dia": 3.2, "pan_head_dia": 8.0, "pan_head_h": 3.1, "flat_head_dia": 8.4, "flat_head_h": 2.7},
    "M5": {"major_dia": 5.0, "core_dia": 2.8, "pilot_dia": 4.0, "pan_head_dia": 10.0, "pan_head_h": 3.8, "flat_head_dia": 9.3, "flat_head_h": 2.7},
}

class PlasticsScrew(Screw):
    """
    Self-tapping / thread-forming screws designed for plastics (e.g. PT screws).
    
    The crucial difference from machine screws is the `to_cutter` method, which generates
    the correct tighter pilot bore so the aggressive threads can bite into the plastic without
    splitting the boss.
    """
    def __init__(self, size: str, length: float, head_type: str = "pan", drive_type: str = "phillips"):
        size = size.upper()
        if size not in PLASTIC_SCREW_SIZES:
            raise ValueError(f"Unsupported plastic screw size: {size}. Available: {list(PLASTIC_SCREW_SIZES.keys())}")
            
        data = PLASTIC_SCREW_SIZES[size]
        self.head_type = head_type.lower()
        
        if self.head_type == "flat":
            self.head_diameter = data["flat_head_dia"]
            self.head_height = data["flat_head_h"]
            self.head_angle = 90.0
        elif self.head_type == "pan":
            self.head_diameter = data["pan_head_dia"]
            self.head_height = data["pan_head_h"]
        else:
            raise ValueError(f"Unsupported head type: {head_type}. Choose 'flat' or 'pan'.")

        self.size = size
        self.length = length
        self.major_diameter = data["major_dia"]
        self.core_diameter = data["core_dia"]
        self.pilot_diameter = data["pilot_dia"]
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
        else: # pan
            head_cyl = cq.Workplane("XY").circle(self.head_diameter / 2.0).extrude(self.head_height - 0.5)
            # Add a slight dome to the pan head
            dome = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, 0, self.head_height - 0.5))
                .circle(self.head_diameter / 2.0)
                .workplane(offset=0.5)
                .circle(self.head_diameter / 3.0)
                .loft()
            )
            head = head_cyl.union(dome)
            
        # Build shaft
        shaft_z = -self.head_height if self.head_type == "flat" else 0.0
        shaft_len = self.length - self.head_height if self.head_type == "flat" else self.length
        
        # Base shaft
        shaft = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, shaft_z))
            .circle(self.major_diameter / 2.0)
            .extrude(-shaft_len + 1.0) # leave 1mm for point
        )
        
        # Self-tapping sharp point
        point = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, shaft_z - shaft_len + 1.0))
            .circle(self.major_diameter / 2.0)
            .workplane(offset=-1.0)
            .circle(0.1)
            .loft()
        )
        
        return head.union(shaft).union(point)

    def to_cutter(self, mode: str = "tap", radial_allowance: float = 0.0, head_recess_depth: float = 0.0) -> cq.Workplane:
        """
        Generates the subtraction cutter for the plastics screw.
        
        mode="tap" (default): Generates a tightly sized pilot hole so threads format plastic.
        mode="clearance": Generates a loose hole so the screw passes freely through the part.
        """
        if mode == "tap":
            shaft_radius = (self.pilot_diameter / 2.0) + radial_allowance
        elif mode == "clearance":
            shaft_radius = (self.major_diameter / 2.0) + radial_allowance + 0.2
        else:
            raise ValueError("PlasticsScrew to_cutter mode must be 'tap' or 'clearance'")

        head_radius = (self.head_diameter / 2.0) + radial_allowance
        z_offset = -head_recess_depth
        
        if self.head_type == "flat":
            angle_rad = math.radians(self.head_angle / 2.0)
            cone_height = (head_radius - shaft_radius) / math.tan(angle_rad)
            
            # Recessed straight bore above the countersink (if recessing deep into part)
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
                .extrude(-shaft_len - 5.0) # overcut
            )
            
            cutter = countersink.union(shaft)
            if upper_recess:
                cutter = upper_recess.union(cutter)
                
        else: # pan
            head = (
                cq.Workplane("XY")
                .circle(head_radius)
                .extrude(self.head_height + 5.0) # Extend upwards to clear any material above
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
                .extrude(-self.length - 5.0) # overcut
            )
            cutter = head.union(shaft)

        return cutter

if __name__ == "__main__":
    from ocp_vscode import show
    
    screw1 = PlasticsScrew("M3", 10, head_type="pan")
    screw2 = PlasticsScrew("M3", 10, head_type="flat")
    
    show(
        screw1.solid.translate((-10, 0, 0)),
        screw1.to_cutter(mode="tap").translate((-5, 0, 0)),
        screw2.solid.translate((5, 0, 0)),
        screw2.to_cutter(mode="clearance").translate((10, 0, 0)),
        names=["M3 Pan Solid", "M3 Pan Pilot Tap", "M3 Flat Solid", "M3 Flat Clearance"]
    )