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
    inner_dia : float
        Inside diameter (shaft hole size).
    outer_dia : float
        Outside diameter.
    thickness : float
        Axial width of the bearing.
    flange_dia : float | None
        Outside diameter of the flange (if it is a flanged bearing).
    flange_thickness : float | None
        Thickness of the flange.
    """
    def __init__(
        self,
        inner_dia: float,
        outer_dia: float,
        thickness: float,
        flange_dia: float | None = None,
        flange_thickness: float | None = None,
    ) -> None:
        self.inner_dia = float(inner_dia)
        self.outer_dia = float(outer_dia)
        self.thickness = float(thickness)
        self.flange_dia = float(flange_dia) if flange_dia else None
        self.flange_thickness = float(flange_thickness) if flange_thickness else None
        self._solid = self._build()
        
    def _build(self) -> cq.Workplane:
        b = (
            cq.Workplane("XY")
            .circle(self.outer_dia / 2.0)
            .circle(self.inner_dia / 2.0)
            .extrude(self.thickness)
        )
        if self.flange_dia and self.flange_thickness:
            flange = (
                cq.Workplane("XY")
                .circle(self.flange_dia / 2.0)
                .circle(self.inner_dia / 2.0)
                .extrude(self.flange_thickness)
            )
            b = b.union(flange)
        return b

    @property
    def solid(self) -> cq.Workplane:
        """The CadQuery solid representing the exact bearing geometry."""
        return self._solid

    def outer_pocket(self, radial_clearance: float = 0.05, depth_clearance: float = 0.0) -> cq.Workplane:
        """Generates a cutter for burying the outer race into a printed housing.
        
        Use `radial_clearance` ~0.05mm for a tight press fit, or ~0.1mm for a looser
        slip fit on FDM printers.
        """
        p = (
            cq.Workplane("XY")
            .circle((self.outer_dia / 2.0) + radial_clearance)
            .extrude(self.thickness + depth_clearance)
        )
        if self.flange_dia and self.flange_thickness:
            flange = (
                cq.Workplane("XY")
                .circle((self.flange_dia / 2.0) + radial_clearance)
                .extrude(self.flange_thickness + depth_clearance)
            )
            p = p.union(flange)
        return p

    def shaft_cutter(self, radial_clearance: float = 0.1) -> cq.Workplane:
        """Generates a basic inner cylinder to cut an axis hole through the housing
        so a shaft can freely pass through the bearing without binding.
        """
        return (
            cq.Workplane("XY")
            .circle((self.inner_dia / 2.0) + radial_clearance)
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
        return cls(3.0, 10.0, 4.0, flange_dia=11.5, flange_thickness=1.0)
        
    @classmethod
    def b624(cls) -> "Bearing":
        """4x13x5mm"""
        return cls(4.0, 13.0, 5.0)

    @classmethod
    def b6702(cls) -> "Bearing":
        """Thin-section 15x21x4mm"""
        return cls(15.0, 21.0, 4.0)


if __name__ == "__main__":
    from ocp_vscode import show
    brg = Bearing.f623()
    pocket = brg.outer_pocket(radial_clearance=0.1)
    
    # Example housing demonstrating the cut
    housing = cq.Workplane("XY").rect(20, 20).extrude(10)
    housing = housing.cut(pocket)
    
    show(brg.solid.translate((0, 0, 10)), housing, names=["F623 Bearing", "Housing"], colors=["silver", "gray"])
