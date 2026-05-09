# vibe-cading is free software: you can redistribute it and/or modify
import cadquery as cq

class TrailerHitchCover:
    """
    Cover for a standard North American 2-inch receiver hitch.
    The primary physical interface (mating face to the receiver) is at Z=0.
    The insert extends into -Z, and the rounded head extends into +Z.
    """
    def __init__(self, size=2, head_diameter=90.0, head_thickness=12.0):
        # 2-inch standard receiver is 50.8 mm. We use 49.5 mm for clearance.
        self.tube_outer = 49.5
        self.tube_inner = 41.5
        self.tube_length = 80.0
        
        self.head_diameter = head_diameter
        self.head_thickness = head_thickness
        
        # Standard 5/8" hitch pin hole (15.875 mm -> 16.5 mm for clearance)
        self.pin_hole_diameter = 16.5
        # Standard distance from receiver face to pin hole is typically 2.5" (63.5mm)
        self.pin_hole_z = -63.5
        
    @property
    def solid(self) -> cq.Workplane:
        # 1. Round head extending into +Z
        head = (
            cq.Workplane("XY")
            .circle(self.head_diameter / 2)
            .extrude(self.head_thickness)
            .edges(">Z").fillet(3.0)
        )
        
        # 2. Square tube insert extending into -Z
        insert = (
            cq.Workplane("XY")
            .rect(self.tube_outer, self.tube_outer)
            .extrude(-self.tube_length)
        )
        
        # Option to hollow out the tube to save material
        hollow = (
            cq.Workplane("XY")
            .workplane(offset=-self.tube_length - 0.1)
            .rect(self.tube_inner, self.tube_inner)
            .extrude(self.tube_length)
        )
        insert = insert.cut(hollow)
        
        # Fillet the insert edges slightly for easier insertion
        insert = insert.edges("|Z").fillet(2.0)
        
        # 3. Combine head and insert
        body = head.union(insert)
        
        # 4. Cut the pin hole through the X axis
        pin_hole_cutter = (
            cq.Workplane("YZ")
            .workplane(offset=-self.tube_outer / 2 - 5.0)
            .center(self.pin_hole_z, 0) # (Z, Y) due to YZ plane mapping
            .circle(self.pin_hole_diameter / 2)
            .extrude(self.tube_outer + 10.0)
        )
        
        body = body.cut(pin_hole_cutter)
        
        return body
