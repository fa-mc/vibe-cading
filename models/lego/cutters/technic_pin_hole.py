import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cadquery as cq
from lego.constants import PIN_HOLE_DIAMETER
from cq_utils import cylinder


# Standard Technic counterbore spec (measured from STP loose-fit file)
TECHNIC_PIN_CB_DIAMETER: float = 6.2   # outer flange / counterbore diameter
TECHNIC_PIN_CB_DEPTH: float = 1.0      # depth of each counterbore end


class TechnicPinHole:
    """Lego Technic pin hole profile.

    Builds a cylindrical cutter sized to the Technic pin *hole* dimensions,
    with optional counterbores on both ends (matching the flanged recess on
    the real part).

    Use the :pymeth:`solid` property as a boolean cutter::

        from lego.technic_pin_hole import TechnicPinHole

        hole = TechnicPinHole(depth=8.0)
        part = part.cut(hole.solid)

    Parameters
    ----------
    depth:
        Total axial depth of the hole (mm).
    diameter:
        Bore diameter (mm). Defaults to ``PIN_HOLE_DIAMETER`` (4.8 mm).
    counterbore_depth:
        Depth of each counterbore end cap (mm). Pass 0 to omit. Default 1.0.
    counterbore_diameter:
        Diameter of the counterbore flanges (mm). Default 6.2 mm.
    """

    DEFAULT_DIAMETER: float = PIN_HOLE_DIAMETER
    DEFAULT_CB_DEPTH: float = TECHNIC_PIN_CB_DEPTH
    DEFAULT_CB_DIAMETER: float = TECHNIC_PIN_CB_DIAMETER

    @classmethod
    def standard(cls, depth: float) -> "TechnicPinHole":
        """Factory: standard Technic pin hole with default counterbore spec."""
        return cls(
            depth=depth,
            diameter=cls.DEFAULT_DIAMETER,
            counterbore_depth=cls.DEFAULT_CB_DEPTH,
            counterbore_diameter=cls.DEFAULT_CB_DIAMETER,
        )

    def __init__(
        self,
        depth: float,
        diameter: float = DEFAULT_DIAMETER,
        counterbore_depth: float = DEFAULT_CB_DEPTH,
        counterbore_diameter: float = DEFAULT_CB_DIAMETER,
    ):
        self.depth = depth
        self.diameter = diameter
        self.counterbore_depth = counterbore_depth
        self.counterbore_diameter = counterbore_diameter
        self._solid = self._build()

    def _build(self) -> cq.Workplane:
        bore = cylinder(self.diameter / 2, self.depth)

        if self.counterbore_depth > 0:
            cb_bottom = cylinder(self.counterbore_diameter / 2, self.counterbore_depth)
            cb_top = cylinder(
                self.counterbore_diameter / 2,
                self.counterbore_depth,
                center=(0, 0, self.depth - self.counterbore_depth),
            )
            bore = bore.union(cb_bottom).union(cb_top)

        return bore

    @property
    def solid(self) -> cq.Workplane:
        """The cutter solid — subtract from any part to bore a pin hole."""
        return self._solid


if __name__ == "__main__":
    from ocp_vscode import show
    show(TechnicPinHole.standard(depth=8).solid)
