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

try:
    from .base import BaseJoint
except ImportError:
    from base import BaseJoint

class DovetailJoint(BaseJoint):
    """Parametil jont generator for 3D printing.

    Generates male (pin) and female (socket) 3D geometries that can be unioned
    or subtracted from other bodies.

    The base of the joint is centered at (X=0, Y=0), with the dovetail
    protruding into the +Y direction.
    """

    def __init__(
        self,
        neck_width: float,
        tail_width: float,
        depth: float,
        length: float,
        clearance: float = 0.05
    ):
        self.neck_width = neck_width
        self.tail_width = tail_width
        self.depth = depth
        self.length = length
        self.clearance = clearance

    def male(self, overlap: float = 1.0) -> cq.Workplane:
        """Generates the male dovetail pin."""
        nh = self.neck_width / 2.0
        th = self.tail_width / 2.0

        profile = (
            cq.Workplane("XY")
            .moveTo(-nh, -overlap)
            .lineTo( nh, -overlap)
            .lineTo( nh, 0.0)
            .lineTo( th, self.depth)
            .lineTo(-th, self.depth)
            .lineTo(-nh, 0.0)
            .close()
        )
        return profile.extrude(self.length)

    def female(self, overlap: float = 1.0) -> cq.Workplane:
        """Generates the female dovetail socket as a cutting tool."""
        # Add clearance directly to the profile bounds
        nh = (self.neck_width / 2.0) + self.clearance
        th = (self.tail_width / 2.0) + self.clearance
        d  = self.depth + self.clearance

        profile = (
            cq.Workplane("XY")
            .moveTo(-nh, -overlap)
            .lineTo( nh, -overlap)
            .lineTo( nh, 0.0)
            .lineTo( th, d)
            .lineTo(-th, d)
            .lineTo(-nh, 0.0)
            .close()
        )
        return profile.extrude(self.length)

if __name__ == "__main__":
    from ocp_vscode import show

    joint = DovetailJoint(neck_width=4.0, tail_width=6.0, depth=4.0, length=10.0, clearance=0.1)

    base = cq.Workplane("XY").rect(20, 10).extrude(10).translate((0, -5, 0))
    pin = joint.male(overlap=2.0)
    male_part = base.union(pin)

    receiver = cq.Workplane("XY").rect(20, 10).extrude(10).translate((0, 5, 0))
    socket = joint.female(overlap=2.0)
    female_part = receiver.cut(socket)

    show(male_part, female_part.translate((0, 2, 0)), names=["Male Pin", "Female Socket (Offset)"], colors=["lightblue", "lightgreen"])
