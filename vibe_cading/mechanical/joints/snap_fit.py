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

from vibe_cading.print_settings import ToleranceProfile


class CantileverSnapFit:
    """Parametric Cantilever Snap-Fit joint.

    The base of the hook is at (X=0, Y=0, Z=0), extending fully in +Z.

    The hook head faces the +X direction. The flexible beam bends in the
    -X direction upon insertion, then snaps back into the catch lip,
    which also faces +X.

    Through-vs-blind: the snap-fit cutter is fundamentally **blind**
    along the insertion axis (the catch cavity has a defined ceiling),
    but the entry face below Z=0 is overcut via the baked
    ``_CUTTER_ENTRY_OVERLAP`` so the cavity opens cleanly into the host
    body's external face.  1 mm matches the historical
    ``female(overlap=1.0)`` default.
    """

    # Class-level entry overcut baked into ``to_cutter``.  Matches the
    # historical ``female(overlap=1.0)`` default to preserve byte-perfect
    # parity with callers that previously relied on the default.
    _CUTTER_ENTRY_OVERLAP: float = 1.0

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
            (0, -overlap),                                   # Back heel
            (self.thickness, -overlap),                      # Front heel
            (self.thickness, self.length - h_retention),     # Beam inner edge (starts ledge drop if any)
            (self.thickness + self.hook_depth, self.length), # Hook ledge tip
            (self.thickness, self.length + h_insertion),     # Hook top tip
            (0, self.length + h_insertion),                  # Back top (straight column)
        ]

        hook = (
            cq.Workplane("XZ")
            .polyline(pts)
            .close()
            .extrude(self.width / 2.0, both=True)
        )
        return hook

    def to_cutter(self, profile: ToleranceProfile | None = None) -> cq.Workplane:
        """Returns the cutting cavity to receive the cantilever hook.

        The cavity includes the insertion void, the deflection space
        behind the beam, and the engage lip.  Entry overlap baked at
        ``_CUTTER_ENTRY_OVERLAP`` (1 mm).

        :param profile: Currently unused — snap-fit clearance is owned
            by the ``clearance`` constructor argument since the joint
            tolerance is a geometric (not manufacturing) concern.  The
            argument is accepted to satisfy ``CutterProtocol``.
        """
        overlap = self._CUTTER_ENTRY_OVERLAP
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

    @property
    def solid(self) -> cq.Workplane:
        """Single-instance solid view — returns the male hook with the joint's
        default attachment overlap (1 mm).
        """
        return self.male()

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Show a male hook beside a block with the female cavity cut into it."""
        joint = cls(length=12, hook_depth=1.5)

        # Show the hook
        male_hook = joint.male()

        # Create a base block and cut the female cavity into it
        female_base = cq.Workplane("XY").box(
            10, 10, 20, centered=(False, True, False)
        ).translate((-4, 0, 0))
        female_cut = female_base.cut(joint.to_cutter())

        return [
            (male_hook, "Male Hook", "lightblue"),
            (female_cut.translate((15, 0, 0)), "Female Cavity", "lightgreen"),
        ]
