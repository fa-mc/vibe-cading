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
        
    def pocket(self, radial_clearance: float = 0.05, depth_clearance: float = 0.1) -> cq.Workplane:
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
        
    def pocket(self, clearance: float = 0.1) -> cq.Workplane:
        """Cutter for a glue-in pocket.
        
        Applies a uniform clearance around the X, Y profiles, and adds Z-depth.
        """
        return (
            cq.Workplane("XY")
            .rect(self.length + clearance * 2.0, self.width + clearance * 2.0)
            .extrude(self.thickness + clearance)
        )
        
    @classmethod
    def b10x5x2(cls) -> "BarMagnet":
        return cls(10.0, 5.0, 2.0)


if __name__ == "__main__":
    from ocp_vscode import show
    mag = DiscMagnet.d6x3()
    b_mag = BarMagnet.b10x5x2()
    
    show(
        mag.solid.translate((-10, 0, 0)), 
        mag.pocket(radial_clearance=0.1).translate((-10, 10, 0)),
        b_mag.solid.translate((10, 0, 0)),
        b_mag.pocket(clearance=0.1).translate((10, 10, 0)),
        names=["D6x3", "D6x3 Pocket", "B10x5x2", "B10x5 Pocket"]
    )
