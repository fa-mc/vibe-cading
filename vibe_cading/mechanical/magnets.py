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

"""Standard Neodymium Magnets and pocket generators."""

from __future__ import annotations
import cadquery as cq

class DiscMagnet:
    """Standard Neodymium Disc Magnet.

    Parameters
    ----------
    diameter : float
        Outer diameter of the magnet.
    thickness : float
        Height/thickness of the disc.
    """
    def __init__(self, diameter: float, thickness: float) -> None:
        self.diameter = float(diameter)
        self.thickness = float(thickness)

    @property
    def solid(self) -> cq.Workplane:
        """The CadQuery solid representing the standard magnet body."""
        return cq.Workplane("XY").circle(self.diameter / 2.0).extrude(self.thickness)

    def pocket(self, profile=None) -> cq.Workplane:
        from vibe_cading.print_settings import get_profile
        prof = profile or get_profile()
        radial_clearance = prof.slip.radial
        depth_clearance = prof.slip.axial
        """Cutter tool for making a press-fit or glue-in pocket.

        Parameters
        ----------
        radial_clearance : float
            Extra radius. Use ~0.05mm for a tight press fit, or ~0.1mm for CA glue.
        depth_clearance : float
            Extra depth to ensure a flush mount.
        """
        return (
            cq.Workplane("XY")
            .circle((self.diameter / 2.0) + radial_clearance)
            .extrude(self.thickness + depth_clearance)
        )

    # --- Common Standards Presets ---

    @classmethod
    def d6x2(cls) -> "DiscMagnet":
        return cls(6.0, 2.0)

    @classmethod
    def d6x3(cls) -> "DiscMagnet":
        return cls(6.0, 3.0)

    @classmethod
    def d10x3(cls) -> "DiscMagnet":
        return cls(10.0, 3.0)

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Show a D6x3 disc and a B10x5x2 bar magnet, each with their pocket."""
        mag = cls.d6x3()
        b_mag = BarMagnet.b10x5x2()

        return [
            (mag.solid.translate((-10, 0, 0)),                   "D6x3",         "silver"),
            (mag.pocket().translate((-10, 10, 0)),               "D6x3 Pocket",  "lightgray"),
            (b_mag.solid.translate((10, 0, 0)),                  "B10x5x2",      "silver"),
            # Note: original block called `pocket(clearance=0.1)` but the
            # method signature is `pocket(profile=None)` — `clearance=` was
            # a bug.  Demo uses the default profile.
            (b_mag.pocket().translate((10, 10, 0)), "B10x5 Pocket", "lightgray"),
        ]


class BarMagnet:
    """Standard Neodymium Bar Magnet.

    Parameters
    ----------
    length : float
        X-axis length.
    width : float
        Y-axis width.
    thickness : float
        Z-axis thickness/height.
    """
    def __init__(self, length: float, width: float, thickness: float) -> None:
        self.length = float(length)
        self.width = float(width)
        self.thickness = float(thickness)

    @property
    def solid(self) -> cq.Workplane:
        return cq.Workplane("XY").rect(self.length, self.width).extrude(self.thickness)

    def pocket(self, profile=None) -> cq.Workplane:
        from vibe_cading.print_settings import get_profile
        prof = profile or get_profile()
        clearance = prof.slip.radial
        z_clearance = prof.slip.axial
        """Cutter for a glue-in pocket.

        Applies a uniform clearance around the X, Y profiles, and adds Z-depth.
        """
        return (
            cq.Workplane("XY")
            .rect(self.length + clearance * 2.0, self.width + clearance * 2.0)
            .extrude(self.thickness + z_clearance)
        )

    @classmethod
    def b10x5x2(cls) -> "BarMagnet":
        return cls(10.0, 5.0, 2.0)
