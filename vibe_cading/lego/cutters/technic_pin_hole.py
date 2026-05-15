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
from vibe_cading.lego.constants import PIN_HOLE_DIAMETER
from vibe_cading.cq_utils import cylinder
from vibe_cading.print_settings import ToleranceProfile


# Standard Technic counterbore spec (measured from STP loose-fit file)
TECHNIC_PIN_CB_DIAMETER: float = 6.2   # outer flange / counterbore diameter
TECHNIC_PIN_CB_DEPTH: float = 1.0      # depth of each counterbore end


class TechnicPinHole:
    """Lego Technic pin hole profile.

    Builds a cylindrical cutter sized to the Technic pin *hole* dimensions,
    with optional counterbores on both ends (matching the flanged recess on
    the real part).

    Use the :pymeth:`to_cutter` method as a boolean cutter::

        from vibe_cading.lego.cutters.technic_pin_hole import TechnicPinHole

        hole = TechnicPinHole(depth=8.0)
        part = part.cut(hole.to_cutter())

    The legacy ``.solid`` accessor remains as an alias for backwards
    compatibility and is read-only.

    Through-vs-blind: this cutter is **blind** by design — the bore
    terminates exactly at the requested ``depth`` so the upper
    counterbore forms a defined-floor cavity.  A 0.01 mm entry overcut
    is baked at Z=0 so the cutter clears the host face cleanly.

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

    # Blind cutter — terminal face exactly at ``depth``; small entry overcut.
    _THROUGH: bool = False
    _ENTRY_OVERCUT: float = 0.01

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
        # Standard bore strictly bounded to the requested depth.
        # We use a small overcut at the bottom (Z=0) so it cuts cleanly
        # when placed flush against a face, but it ends exactly at self.depth.
        overcut = self._ENTRY_OVERCUT
        bore = cylinder(self.diameter / 2, self.depth + overcut, center=(0, 0, -overcut))

        if self.counterbore_depth > 0:
            cb_bottom = cylinder(
                self.counterbore_diameter / 2,
                self.counterbore_depth + overcut,
                center=(0, 0, -overcut)
            )
            # Top counterbore stops exactly at self.depth, forming the blind cavity
            cb_top = cylinder(
                self.counterbore_diameter / 2,
                self.counterbore_depth,
                center=(0, 0, self.depth - self.counterbore_depth),
            )
            bore = bore.union(cb_bottom).union(cb_top)

        return bore

    def to_cutter(self, profile: ToleranceProfile | None = None) -> cq.Workplane:
        """Return the cutter solid for boolean subtraction.

        The Technic pin hole's geometry is fully defined by its
        constructor parameters; the ``profile`` argument is accepted to
        satisfy :class:`vibe_cading.mechanical.protocols.CutterProtocol`
        but currently does not affect output.  (Tolerance bake-in would
        be a future deepening — apply ``profile.free.radial`` to the
        bore diameter for an explicit slip/press fit.)
        """
        return self._solid

    @property
    def solid(self) -> cq.Workplane:
        """Legacy alias for :pymeth:`to_cutter` — returns the cutter solid."""
        return self._solid

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Show a depth-8 standard pin hole cut into a small Ø8 cylinder."""
        depth = 8.0
        hole_cutter = cls.standard(depth=depth).to_cutter()
        main_body = cq.Workplane("XY").circle(8.0 / 2).extrude(depth)
        part = main_body.cut(hole_cutter)
        return [(part, "TechnicPinHole demo", "tan")]
