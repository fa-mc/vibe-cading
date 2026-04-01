import cadquery as cq
from dataclasses import dataclass
import math

@dataclass
class HexVentilationGrille:
    """
    Parametric Hexagonal Ventilation Grille.
    Generates a matrix of hexagonal holes.
    """
    width: float = 50.0
    length: float = 50.0
    thickness: float = 2.0
    hex_radius: float = 4.0   # Circumradius of the hexagon
    spacing: float = 2.0      # Material width between hexagons
    
    @property
    def solid(self) -> cq.Workplane:
        """
        Returns a solid rectangular plate with hexagonal vent holes cut out of it.
        Centers the plate on the origin at Z=0, extruding upwards.
        """
        base = cq.Workplane("XY").box(self.width, self.length, self.thickness, centered=(True, True, False))
        return base - self.to_cutter(thickness=self.thickness, overcut=1.0)
        
    def to_cutter(self, thickness: float = None, overcut: float = 10.0) -> cq.Workplane:
        """
        Returns the subtractive cutter geometry for the hexagonal holes.
        Extends symmetrically in Z by `overcut` to guarantee clean boolean cuts.
        """
        if thickness is None:
            thickness = self.thickness
            
        # Calculate horizontal and vertical step distances for a hex grid
        # In a pointed-top hex, horizontal distance between centers is 2 * apothem + spacing
        # where apothem = hex_radius * cos(30 deg).
        apothem = self.hex_radius * math.cos(math.radians(30))
        
        # Distance between column centers
        dx = 2 * apothem + self.spacing
        
        # Distance between rows
        dy = 1.5 * self.hex_radius + self.spacing * math.cos(math.radians(30))
        
        cols = int(self.width / dx) + 1
        rows = int(self.length / dy) + 1
        
        # Generate the center points for the hexagons
        pts = []
        for r in range(-rows, rows + 1):
            for c in range(-cols, cols + 1):
                # Offset every other row by half a dx
                x_offset = (dx / 2) if r % 2 != 0 else 0
                x = c * dx + x_offset
                y = r * dy
                
                # Check if the hex (roughly) fits within the requested width/length bounds
                if abs(x) < (self.width / 2) - self.hex_radius and abs(y) < (self.length / 2) - self.hex_radius:
                    pts.append((x, y))
                    
        if not pts:
            return cq.Workplane("XY")
            
        cutter = (
            cq.Workplane("XY")
            .workplane(offset=-overcut)
            .pushPoints(pts)
            .polygon(6, self.hex_radius * 2) # polygon takes circumdiameter
            .extrude(thickness + 2 * overcut)
        )
        return cutter

@dataclass
class SlottedVentilationGrille:
    """
    Parametric Slotted Ventilation Grille.
    Generates a series of elongated slot holes.
    """
    width: float = 50.0
    length: float = 50.0
    thickness: float = 2.0
    slot_width: float = 3.0   # Width of each slot (X)
    slot_length: float = 40.0 # Length of each slot (Y)
    spacing: float = 3.0      # Material width between slots
    
    @property
    def solid(self) -> cq.Workplane:
        """
        Returns a solid rectangular plate with slotted vent holes cut out of it.
        Centers the plate on the origin at Z=0, extruding upwards.
        """
        base = cq.Workplane("XY").box(self.width, self.length, self.thickness, centered=(True, True, False))
        return base - self.to_cutter(thickness=self.thickness, overcut=1.0)
        
    def to_cutter(self, thickness: float = None, overcut: float = 10.0) -> cq.Workplane:
        """
        Returns the subtractive cutter geometry for the slotted holes.
        Extends symmetrically in Z by `overcut`.
        """
        if thickness is None:
            thickness = self.thickness
            
        dx = self.slot_width + self.spacing
        cols = int(self.width / dx)
        
        pts = []
        for c in range(-cols, cols + 1):
            x = c * dx
            if abs(x) < (self.width / 2) - self.slot_width:
                pts.append((x, 0))
                
        if not pts:
            return cq.Workplane("XY")
            
        cutter = (
            cq.Workplane("XY")
            .workplane(offset=-overcut)
            .pushPoints(pts)
            .slot2D(self.slot_length, self.slot_width)
            .extrude(thickness + 2 * overcut)
        )
        return cutter

if __name__ == "__main__":
    hex_grille = HexVentilationGrille(hex_radius=4.0, spacing=2.0)
    slot_grille = SlottedVentilationGrille(width=50, length=50, slot_width=3, slot_length=35, spacing=3)
    
    from ocp_vscode import show
    show(hex_grille.solid, slot_grille.solid.translate((60, 0, 0)))