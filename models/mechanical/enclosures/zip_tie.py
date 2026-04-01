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

@dataclass
class ZipTieAnchor:
    """
    Parametric Zip-tie Anchor.
    A simple bridge structure meant to be unioned onto a surface.
    Centered at the Z=0 plane. Length goes along X, width along Y.
    """
    width: float = 8.0     # The length along the zip tie path (Y)
    length: float = 12.0   # The perpendicular length (X)
    height: float = 6.0    # Total height of the anchor
    slot_width: float = 5.0 # Width of the zip tie (Y)
    slot_height: float = 2.0 # Thickness of the zip tie (Z)
    bridge_thickness: float = 2.0 # Material above the slot (Z)
    
    @property
    def solid(self) -> cq.Workplane:
        """
        Returns the additive geometry for the zip-tie anchor.
        """
        # Create a 2D profile on the XZ plane and extrude along Y (width)
        # We start at the bottom-left, go up to slot_height, right by (length-slot_width)/2, etc.
        # Actually easier to extrude the solid shape and apply a cut, or sketch a wire.
        
        # Let's sketch it directly.
        # The bridge profile has two legs and a top bridge. 
        # But wait, it's an anchor so the slot goes completely through the width.
        # This means the profile on XZ plane is an inverted 'U' if the slot is flush with the ground.
        # Let's create an outer rectangle and subtract an inner rectangle, then extrude.
        
        leg_length = (self.length - self.slot_width) / 2
        
        result = (
            cq.Workplane("XZ")
            # Outer boundary
            .rect(self.length, self.height, centered=(True, False))
            # Inner slot boundary
            .rect(self.length + 0.1, self.slot_height, centered=(True, False))
            .extrude(self.width, both=True)
            .intersect(cq.Workplane("XY").box(self.length, self.width, self.height, centered=(True,True,False)))
        )
        
        # Simpler 2D pure sketch:
        w = self.length / 2
        sw = self.slot_width / 2
        h = self.height
        sh = self.slot_height
        
        pts = [
            (w, 0),        # Bottom right
            (w, h),        # Top right
            (-w, h),       # Top left
            (-w, 0),       # Bottom left
            (-sw, 0),      # Inner bottom left
            (-sw, sh),     # Inner top left
            (sw, sh),      # Inner top right
            (sw, 0),       # Inner bottom right
        ]
        
        anchor = (
            cq.Workplane("XZ")
            .polyline(pts)
            .close()
            .extrude(self.width / 2, both=True)
        )
        
        # Bevel the outer top edges 
        try:
            # We want to fillet only the top edges
            anchor = anchor.edges(">Z").fillet(self.bridge_thickness * 0.45)
        except Exception:
            pass # Failsafe
            
        return anchor

if __name__ == "__main__":
    anchor = ZipTieAnchor()
    from ocp_vscode import show
    show(anchor.solid)
