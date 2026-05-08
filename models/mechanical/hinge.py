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
from models.print_settings import ToleranceProfile

class PrintInPlaceHinge:
    """
    Parametric Print-in-Place Hinge.
    
    The origin (0,0,0) is located precisely at the center of the hinge axis.
    The hinge is split along the X-axis:
      - Leaf A extends towards +X.
      - Leaf B extends towards -X.
    
    The hinge pivots on the Y-axis. The mating mechanism relies on 
    45-degree conical pins and sockets to allow FDM printing.
    """

    def __init__(
        self,
        width: float = 30.0,
        leaf_a_length: float = 20.0,
        leaf_b_length: float = 20.0,
        leaf_a_width: float = None,
        leaf_b_width: float = None,
        thickness: float = 4.0,
        knuckle_diameter: float = 10.0,
        knuckle_count: int = 3,
        angle: float = 0.0,
        profile: ToleranceProfile = None
    ):
        if profile is None:
            from models.print_settings import get_profile
            profile = get_profile("fdm_standard")
            
        self.width = width
        self.leaf_a_length = leaf_a_length
        self.leaf_b_length = leaf_b_length
        self.leaf_a_width = leaf_a_width if leaf_a_width is not None else width
        self.leaf_b_width = leaf_b_width if leaf_b_width is not None else width
        self.thickness = thickness
        self.knuckle_diameter = knuckle_diameter
        self.knuckle_count = max(2, knuckle_count)
        self.angle = angle
        self.clearance = profile.free_fit
        self.face_gap = profile.free_fit
        
        # Calculate knuckle segments
        self.total_gaps = (self.knuckle_count - 1) * self.face_gap
        self.knuckle_width = (self.width - self.total_gaps) / self.knuckle_count
        
        # Conical pin parameters
        self.cone_height = min((self.knuckle_width / 2.0) - 0.5, (self.knuckle_diameter / 2.0) - 1.0)
        self.cone_height = max(1.0, self.cone_height)
        self.cone_base_radius = self.cone_height
        
        # Pre-compute alternating knuckle gap positions
        self._gaps_list = []
        start_y = -self.width / 2.0
        for i in range(self.knuckle_count):
            end_y = start_y + self.knuckle_width
            if i < self.knuckle_count - 1:
                y_gap = end_y + self.face_gap / 2.0
                self._gaps_list.append((i, i+1, y_gap))
            start_y = end_y + self.face_gap

        # Build the two leaves
        self.leaf_a = self._build_leaf_a()
        self.leaf_b = self._build_leaf_b()
        
        # Apply user rotation to Leaf B relative to Leaf A
        if self.angle != 0.0:
            self.leaf_b = self.leaf_b.rotate((0, 0, 0), (0, 1, 0), self.angle)

    def _get_knuckle_ranges(self, target_parity: int):
        ranges = []
        start_y = -self.width / 2.0
        for i in range(self.knuckle_count):
            end_y = start_y + self.knuckle_width
            if i % 2 == target_parity:
                ranges.append((start_y, end_y, i))
            start_y = end_y + self.face_gap
        return ranges

    def _build_pin(self, y_gap: float, dir_y: int) -> cq.Workplane:
        """ dir_y is 1 for +Y, -1 for -Y. """
        pin_h = self.cone_height - self.clearance
        pin_r = self.cone_base_radius - self.clearance
        
        pin = (
            cq.Workplane("XZ")
            .circle(pin_r)
            .workplane(offset=pin_h)
            .circle(0.01)
            .loft(combine=True)
            # Extrude backwards to join with main body
            .union(cq.Workplane("XZ").circle(pin_r).extrude(-self.face_gap))
        )
        if dir_y == -1:
            pin = pin.rotate((0,0,0), (1,0,0), 180)
            
        return pin.translate((0, y_gap, 0))

    def _build_socket(self, y_gap: float, dir_y: int) -> cq.Workplane:
        """ dir_y is 1 for +Y, -1 for -Y. """
        soc_h = self.cone_height
        soc_r = self.cone_base_radius
        
        soc = (
            cq.Workplane("XZ")
            .circle(soc_r)
            .workplane(offset=soc_h + 0.1) # tiny overcut at tip
            .circle(0.01)
            .loft(combine=True)
            # Extrude backwards past face level to ensure breaking the outer face
            .union(cq.Workplane("XZ").circle(soc_r).extrude(-self.face_gap))
        )
        if dir_y == -1:
            soc = soc.rotate((0,0,0), (1,0,0), 180)
            
        return soc.translate((0, y_gap, 0))

    def _build_leaf_a(self) -> cq.Workplane:
        """Leaf A (+X). Knuckles with even indices (0, 2, 4...)"""
        plate = (
            cq.Workplane("XY")
            .center(self.leaf_a_length / 2, 0)
            .box(self.leaf_a_length, self.leaf_a_width, self.thickness)
        )
        plate = plate.translate((0, 0, (self.thickness - self.knuckle_diameter) / 2))
        
        # Carve rectangular spaces where B's knuckles rotate
        b_ranges = self._get_knuckle_ranges(1)
        clearance_x = self.knuckle_diameter + self.face_gap * 4
        
        for (y_min, y_max, idx) in b_ranges:
            kw = y_max - y_min
            y_mid = (y_min + y_max) / 2
            clearance_box = (
                cq.Workplane("XY")
                .box(clearance_x, kw + self.face_gap * 2, self.knuckle_diameter * 2)
                .translate((0, y_mid, 0))
            )
            plate = plate.cut(clearance_box)

        # Build knuckles
        knuckles_solid = cq.Workplane("XZ")
        a_ranges = self._get_knuckle_ranges(0)
        for (y_min, y_max, idx) in a_ranges:
            y_mid = (y_min + y_max) / 2
            kw = y_max - y_min
            knuckle = cq.Workplane("XZ").cylinder(kw, self.knuckle_diameter / 2).translate((0, y_mid, 0))
            knuckles_solid = knuckles_solid.union(knuckle)
            
        # Attach male pins (which only ever exist on A leaf knuckles)
        for (left_idx, right_idx, y_gap) in self._gaps_list:
            if left_idx % 2 == 0:
                knuckles_solid = knuckles_solid.union(self._build_pin(y_gap, 1))
            elif right_idx % 2 == 0:
                knuckles_solid = knuckles_solid.union(self._build_pin(y_gap, -1))
                
        return plate.union(knuckles_solid)

    def _build_leaf_b(self) -> cq.Workplane:
        """Leaf B (-X). Knuckles with odd indices (1, 3, 5...)"""
        plate = (
            cq.Workplane("XY")
            .center(-self.leaf_b_length / 2, 0)
            .box(self.leaf_b_length, self.leaf_b_width, self.thickness)
        )
        plate = plate.translate((0, 0, (self.thickness - self.knuckle_diameter) / 2))
        
        # Carve rectangular spaces where A's knuckles rotate
        a_ranges = self._get_knuckle_ranges(0)
        clearance_x = self.knuckle_diameter + self.face_gap * 4
        
        for (y_min, y_max, idx) in a_ranges:
            kw = y_max - y_min
            y_mid = (y_min + y_max) / 2
            clearance_box = (
                cq.Workplane("XY")
                .box(clearance_x, kw + self.face_gap * 2, self.knuckle_diameter * 2)
                .translate((0, y_mid, 0))
            )
            plate = plate.cut(clearance_box)

        # Build knuckles
        knuckles_solid = cq.Workplane("XZ")
        b_ranges = self._get_knuckle_ranges(1)
        for (y_min, y_max, idx) in b_ranges:
            y_mid = (y_min + y_max) / 2
            kw = y_max - y_min
            knuckle = cq.Workplane("XZ").cylinder(kw, self.knuckle_diameter / 2).translate((0, y_mid, 0))
            knuckles_solid = knuckles_solid.union(knuckle)
            
        # Cut female cavities (which only ever exist on B leaf knuckles)
        for (left_idx, right_idx, y_gap) in self._gaps_list:
            if left_idx % 2 == 0:
                knuckles_solid = knuckles_solid.cut(self._build_socket(y_gap, 1))
            elif right_idx % 2 == 0:
                knuckles_solid = knuckles_solid.cut(self._build_socket(y_gap, -1))
                
        return plate.union(knuckles_solid)

    @property
    def solid(self) -> cq.Workplane:
        """Returns the fully assembled static geometry of the hinge."""
        comp = cq.Assembly()
        comp.add(self.leaf_a, name="leaf_a")
        comp.add(self.leaf_b, name="leaf_b")
        return comp.toCompound()
    
# Boilerplate for preview and build pipeline
if __name__ == "__main__":
    hinge = PrintInPlaceHinge(
        width=40,
        knuckle_count=5,
        leaf_a_width=20,
        leaf_b_width=60,
        leaf_a_length=25,
        leaf_b_length=25,
        angle=30
    )
    
    try:
        from ocp_vscode import show
        show(hinge.solid)
    except ImportError:
        pass
