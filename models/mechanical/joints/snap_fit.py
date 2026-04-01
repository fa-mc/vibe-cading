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
import math

try:
    from .base import BaseJoint
except ImportError:
    from base import BaseJoint

class CantileverSnapFit(BaseJoint):
    """Parametric Cantilever Snap-Fit joint.

    The base of the hook is at (X=0, Y=0, Z=0), extending fully in +Z.

    The hook head faces the +X direction. The flexible beam bends in the -X
    direction upon insertion, then snaps back into the catch lip, which also
    faces +X.
    """

    def __init__(
        self,
        length: float = 10.0,
        width: float = 5.0,
        thickness: float = 2.0,
        hook_depth: float = 1.5,
        insertion_angle: float = 30.0,
        retention_angle: float = 90.0,
        clearance: float = 0.2
    ):
        """
        Args:
            length: Z-height of the flexible beam up to the hook's ledge.
            width: Y-width of the cantilever hook.
            thickness: X-thickness of the main beam shaft.
            hook_depth: How far the hook protrudes beyond the beam in +X.
            insertion_angle: The ramp angle (from vertical Z) for easy sliding.
            retention_angle: The return angle (90 for permanent locking, <90 for release).
            clearance: Extra dimensional space around the female catch for printing tolerances.
        """
        self.length = length
        self.width = width
        self.thickness = thickness
        self.hook_depth = hook_depth
        self.insertion_angle = insertion_angle
        self.retention_angle = retention_angle
        self.clearance = clearance

    def male(self, overlap: float = 1.0) -> cq.Workplane:
        """Returns the cantilever hook body intended to be unioned onto a base."""
        h_insertion = self.hook_depth / math.tan(math.radians(self.insertion_angle))

        if self.retention_angle == 90.0:
            h_retention = 0.0
        else:
            h_retention = self.hook_depth / math.tan(math.radians(self.retention_angle))

        pts = [
            (0, -overlap),                                  # Back heel
            (self.thickness, -overlap),                     # Front heel
            (self.thickness, self.length - h_retention),    # Beam inner edge (starts ledge drop if any)
            (self.thickness + self.hook_depth, self.length),# Hook ledge tip
            (self.thickness, self.length + h_insertion),    # Hook top tip
            (0, self.length + h_insertion),                 # Back top (straight column)
        ]

        hook = (
            cq.Workplane("XZ")
            .polyline(pts)
            .close()
            .extrude(self.width / 2.0, both=True)
        )
        return hook

    def female(self, overlap: float = 1.0) -> cq.Workplane:
        """Returns the cutting cavity to receive the cantilever hook.

        This cavity includes the insertion void, the deflection space behind the beam,
        and the engage lip.
        """
        h_insertion = self.hook_depth / math.tan(math.radians(self.insertion_angle))
        top_z = self.length + h_insertion + overlap

        # Deflection space: the beam bends backward by `hook_depth`
        back_x = -(self.hook_depth + self.clearance)

        # The main shaft where beam sits
        front_shaft_x = self.thickness + self.clearance

        # The catch recess where the hook expands into
        front_catch_x = self.thickness + self.hook_depth + self.clearance

        if self.retention_angle == 90.0:
            h_retention = 0.0
        else:
            h_retention = self.hook_depth / math.tan(math.radians(self.retention_angle))

        # Add Z-clearance to the catch altitude so the ledge has room to click
        catch_z = self.length + self.clearance

        pts = [
            (back_x, -overlap),
            (front_shaft_x, -overlap),
            (front_shaft_x, catch_z - h_retention),
            (front_catch_x, catch_z),
            (front_catch_x, top_z),
            (back_x, top_z),
        ]

        cavity = (
            cq.Workplane("XZ")
            .polyline(pts)
            .close()
            .extrude((self.width / 2.0) + self.clearance, both=True)
        )
        return cavity

if __name__ == "__main__":
    from ocp_vscode import show

    joint = CantileverSnapFit(length=12, hook_depth=1.5)

    # Show the hook
    male_hook = joint.male()

    # Create a base block and cut the female cavity into it
    female_base = cq.Workplane("XY").box(10, 10, 20, centered=(False, True, False)).translate((-4, 0, 0))
    female_cut = female_base.cut(joint.female(overlap=2.0))

    show(
        male_hook,
        female_cut.translate((15, 0, 0)),
        names=["Male Hook", "Female Cavity"],
        colors=["lightblue", "lightgreen"]
    )
