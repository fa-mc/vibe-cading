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

from vibe_cading.print_settings import ToleranceProfile


class DovetailJoint:
    """Parametric dovetail joint generator for 3D printing.

    Generates male (pin) and female (socket) 3D geometries that can be
    unioned or subtracted from other bodies.

    The base of the joint is centered at (X=0, Y=0), with the dovetail
    protruding into the +Y direction.

    Through-vs-blind: the dovetail cutter is fundamentally **blind**
    along the joint axis (the socket pocket has a defined floor), but
    extends in -Y past the entry face via the caller-supplied
    ``overlap`` on ``male``.  The ``to_cutter`` method bakes a built-in
    1 mm entry overlap on the cutting side; consumers needing more can
    apply additional translation themselves.
    """

    # Class-level entry overcut baked into ``to_cutter``.  Joint cutter
    # axis is +Y; entry face sits at Y = 0 and the cutter extends in -Y
    # past the entry by this amount.  1 mm matches the historical
    # ``female(overlap=1.0)`` default, preserving byte-perfect parity
    # with any caller that previously relied on the default.
    _CUTTER_ENTRY_OVERLAP: float = 1.0

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
            .lineTo(nh, -overlap)
            .lineTo(nh, 0.0)
            .lineTo(th, self.depth)
            .lineTo(-th, self.depth)
            .lineTo(-nh, 0.0)
            .close()
        )
        return profile.extrude(self.length)

    def to_cutter(self, profile: ToleranceProfile | None = None) -> cq.Workplane:
        """Generates the female dovetail socket as a cutting tool.

        The entry overlap is baked at ``_CUTTER_ENTRY_OVERLAP`` (1 mm),
        matching the historical ``female(overlap=1.0)`` default.

        :param profile: Currently unused — dovetail clearance is owned
            by the ``clearance`` constructor argument since the joint
            tolerance is a geometric (not manufacturing) concern.  The
            argument is accepted to satisfy ``CutterProtocol``.
        """
        overlap = self._CUTTER_ENTRY_OVERLAP
        # Add clearance directly to the profile bounds
        nh = (self.neck_width / 2.0) + self.clearance
        th = (self.tail_width / 2.0) + self.clearance
        d = self.depth + self.clearance

        socket = (
            cq.Workplane("XY")
            .moveTo(-nh, -overlap)
            .lineTo(nh, -overlap)
            .lineTo(nh, 0.0)
            .lineTo(th, d)
            .lineTo(-th, d)
            .lineTo(-nh, 0.0)
            .close()
        )
        return socket.extrude(self.length)

    @property
    def solid(self) -> cq.Workplane:
        """Single-instance solid view — returns the male pin with the
        joint's default attachment overlap (1 mm).

        Provides a ``tools/view.py vibe_cading.mechanical.joints.dovetail.DovetailJoint``
        rendering.  The 1 mm default preserves the historical
        ``male(overlap=1.0)`` signature so the visualised pin matches the
        shape a caller would union into a host body.
        """
        return self.male()

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Show a male pin (block + male overlap) and female socket (block - female cavity)."""
        joint = cls(
            neck_width=4.0, tail_width=6.0, depth=4.0,
            length=10.0, clearance=0.1,
        )

        base = cq.Workplane("XY").rect(20, 10).extrude(10).translate((0, -5, 0))
        pin = joint.male(overlap=2.0)
        male_part = base.union(pin)

        receiver = cq.Workplane("XY").rect(20, 10).extrude(10).translate((0, 5, 0))
        socket = joint.to_cutter()
        female_part = receiver.cut(socket)

        return [
            (male_part, "Male Pin", "lightblue"),
            (female_part.translate((0, 2, 0)), "Female Socket (Offset)", "lightgreen"),
        ]
