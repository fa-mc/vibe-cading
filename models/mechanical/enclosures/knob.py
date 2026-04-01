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
from dataclasses import dataclass
import math

@dataclass
class RibbedKnob:
    """
    Parametric Ribbed Knob / Grip Surface.
    Generates a knob with ribbed/knurled exterior for 3D printing,
    using pure 2D sketches to avoid costly 3D booleans.
    Centered at the origin at Z=0.
    """
    diameter: float = 20.0
    height: float = 12.0
    rib_count: int = 30
    rib_depth: float = 1.0  # How deep the indentations go
    shaft_diameter: float = 6.0
    shaft_depth: float = 8.0
    
    # Optional flat for a D-shaft
    d_shaft_flat_depth: float = 1.0 
    
    @property
    def solid(self) -> cq.Workplane:
        """
        Returns the solid knob geometry.
        """
        outer_radius = self.diameter / 2
        inner_radius = outer_radius - self.rib_depth
        
        # Generate a continuous 2D wavy profile for the ribbed perimeter
        pts = []
        # We'll use a high resolution for a smooth 3D printed print
        segments_per_rib = 6
        total_segments = self.rib_count * segments_per_rib
        
        for i in range(total_segments):
            angle = (i / total_segments) * 2 * math.pi
            # create a sine wave offset
            # cos(rib_count * angle) goes from 1 to -1.
            # Scale it to go from 0 to 1, then multiply by rib_depth.
            wave = (math.cos(self.rib_count * angle) + 1) / 2
            r = inner_radius + wave * self.rib_depth
            
            x = r * math.cos(angle)
            y = r * math.sin(angle)
            pts.append((x, y))
            
        knob = (
            cq.Workplane("XY")
            .polyline(pts)
            .close()
            .extrude(self.height)
        )
        
        # Add a slight chamfer or fillet? Filleting a ribbed profile in 3D might fail,
        # so we'll just leave it flat or add a top dome using a revolve, but simple is better here.
        # Let's add a chamfer to the top and bottom edges using a simple sub-cutter.
        chamfer_cutter = (
            cq.Workplane("XZ")
            .polyline([
                (outer_radius + 5, self.height + 5), 
                (outer_radius - 1.5, self.height + 5), 
                (outer_radius + 5, self.height - 1.5)
            ]).close().revolve(360, (0,0,-1), (0,0,1))
        )
        knob = knob - chamfer_cutter
        
        # Bottom chamfer
        chamfer_cutter_bott = (
            cq.Workplane("XZ")
            .polyline([
                (outer_radius + 5, -5), 
                (outer_radius - 1.5, -5), 
                (outer_radius + 5, 1.5)
            ]).close().revolve(360, (0,0,-1), (0,0,1))
        )
        knob = knob - chamfer_cutter_bott
        
        # Cut the shaft hole
        shaft_cutter = cq.Workplane("XY").workplane(offset=0).circle(self.shaft_diameter / 2).extrude(self.shaft_depth)
        
        # Apply the flat for a D-shaft if specified
        if self.d_shaft_flat_depth > 0:
            flat_offset = (self.shaft_diameter / 2) - self.d_shaft_flat_depth
            d_flat_cutter = (
                cq.Workplane("XY")
                .workplane(offset=0)
                .center(flat_offset, 0)
                .rect(self.shaft_diameter, self.shaft_diameter, centered=(False, True))
                .extrude(self.shaft_depth)
            )
            shaft_cutter = shaft_cutter - d_flat_cutter
            
        return knob - shaft_cutter

if __name__ == "__main__":
    knob = RibbedKnob()
    from ocp_vscode import show
    show(knob.solid)