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

"""Parametric ball bearings with press-fit clearances."""

from __future__ import annotations
import cadquery as cq

class Bearing:
    """Parametric radial ball bearing.

    Generates representations of standard bearings and provides
    subtractive cutter tools to create housing pockets with
    appropriate clearances for 3D printed press-fits.

    Parameters
    ----------
    inner_diameter : float
        Inside diameter (shaft hole size).
    outer_diameter : float
        Outside diameter.
    thickness : float
        Axial width of the bearing.
    flange_diameter : float | None
        Outside diameter of the flange (if it is a flanged bearing).
    flange_thickness : float | None
        Thickness of the flange.
    """
    def __init__(
        self,
        inner_diameter: float,
        outer_diameter: float,
        thickness: float,
        flange_diameter: float | None = None,
        flange_thickness: float | None = None,
    ) -> None:
        self.inner_diameter = float(inner_diameter)
        self.outer_diameter = float(outer_diameter)
        self.thickness = float(thickness)
        self.flange_diameter = float(flange_diameter) if flange_diameter else None
        self.flange_thickness = float(flange_thickness) if flange_thickness else None
        self._solid = self._build()

    def _build(self) -> cq.Workplane:
        b = (
            cq.Workplane("XY")
            .circle(self.outer_diameter / 2.0)
            .circle(self.inner_diameter / 2.0)
            .extrude(self.thickness)
        )
        if self.flange_diameter and self.flange_thickness:
            flange = (
                cq.Workplane("XY")
                .circle(self.flange_diameter / 2.0)
                .circle(self.inner_diameter / 2.0)
                .extrude(self.flange_thickness)
            )
            b = b.union(flange)
        return b

    @property
    def solid(self) -> cq.Workplane:
        """The CadQuery solid representing the exact bearing geometry."""
        return self._solid

    def outer_pocket(self, profile=None) -> cq.Workplane:
        from vibe_cading.print_settings import get_profile
        prof = profile or get_profile()
        radial_clearance = prof.press.radial
        depth_clearance = prof.press.axial
        """Generates a cutter for burying the outer race into a printed housing.

        Use `radial_clearance` ~0.05mm for a tight press fit, or ~0.1mm for a looser
        slip fit on FDM printers.
        """
        p = (
            cq.Workplane("XY")
            .circle((self.outer_diameter / 2.0) + radial_clearance)
            .extrude(self.thickness + depth_clearance)
        )
        if self.flange_diameter and self.flange_thickness:
            flange = (
                cq.Workplane("XY")
                .circle((self.flange_diameter / 2.0) + radial_clearance)
                .extrude(self.flange_thickness + depth_clearance)
            )
            p = p.union(flange)
        return p

    def shaft_cutter(self, profile=None) -> cq.Workplane:
        from vibe_cading.print_settings import get_profile
        prof = profile or get_profile()
        radial_clearance = prof.slip.radial
        """Generates a basic inner cylinder to cut an axis hole through the housing
        so a shaft can freely pass through the bearing without binding.
        """
        return (
            cq.Workplane("XY")
            .circle((self.inner_diameter / 2.0) + radial_clearance)
            .extrude(self.thickness * 2.0)  # Make it comfortably longer for generic through-cuts
            .translate((0, 0, -self.thickness / 2.0))
        )

    # --- Common Standards Presets ---

    @classmethod
    def b608(cls) -> "Bearing":
        """Skate bearing: 8x22x7mm"""
        return cls(8.0, 22.0, 7.0)

    @classmethod
    def b623(cls) -> "Bearing":
        """Common 3D printer bearing: 3x10x4mm"""
        return cls(3.0, 10.0, 4.0)

    @classmethod
    def f623(cls) -> "Bearing":
        """Flanged printer bearing: 3x10x4mm with 11.5x1mm flange"""
        return cls(3.0, 10.0, 4.0, flange_diameter=11.5, flange_thickness=1.0)

    @classmethod
    def b624(cls) -> "Bearing":
        """4x13x5mm"""
        return cls(4.0, 13.0, 5.0)

    @classmethod
    def b6702(cls) -> "Bearing":
        """Thin-section 15x21x4mm"""
        return cls(15.0, 21.0, 4.0)

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Show an F623 bearing above a square housing with the pocket cut."""
        brg = cls.f623()
        pocket = brg.outer_pocket()

        # Example housing demonstrating the cut
        housing = cq.Workplane("XY").rect(20, 20).extrude(10)
        housing = housing.cut(pocket)

        return [
            (brg.solid.translate((0, 0, 10)), "F623 Bearing", "silver"),
            (housing,                          "Housing",      "gray"),
        ]
