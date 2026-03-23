"""
Hexagonal Standoffs / Spacers (standard PCB/electronics mounting hardware).
"""
from __future__ import annotations
import cadquery as cq

class HexStandoff:
    """Standard Hexagonal Standoff (Spacer) used for mounting PCBs."""
    DIMENSIONS = {
        "M2": {"width_flats": 4.0, "nominal_dia": 2.0},
        "M2.5": {"width_flats": 5.0, "nominal_dia": 2.5},
        "M3": {"width_flats": 5.5, "nominal_dia": 3.0},
        "M4": {"width_flats": 7.0, "nominal_dia": 4.0},
        "4-40": {"width_flats": 4.76, "nominal_dia": 2.8},
        "6-32": {"width_flats": 6.35, "nominal_dia": 3.5},
    }

    def __init__(self, width_flats: float, length: float, nominal_dia: float, type_: str = "F-F", thread_length: float = 6.0):
        self.width_flats = float(width_flats)
        self.length = float(length)
        self.nominal_dia = float(nominal_dia)
        self.type_ = type_.upper()
        self.thread_length = float(thread_length)
        self.radius = self.width_flats / 1.7320508075688772

    @classmethod
    def from_size(cls, size: str, length: float = 10.0, type_: str = "F-F", thread_length: float = 6.0) -> "HexStandoff":
        if size not in cls.DIMENSIONS:
            raise ValueError(f"Unknown standoff size {size}. Supported: {list(cls.DIMENSIONS.keys())}")
        dims = cls.DIMENSIONS[size]
        return cls(
            width_flats=dims["width_flats"],
            length=length,
            nominal_dia=dims["nominal_dia"],
            type_=type_,
            thread_length=thread_length
        )

    @property
    def solid(self) -> cq.Workplane:
        body = cq.Workplane("XY").polygon(6, self.radius * 2).extrude(self.length)
        if self.type_ in ["F-F", "M-F"]:
            depth = self.length if self.type_ == "F-F" else self.length / 2.0
            body = body.faces(">Z").workplane().circle(self.nominal_dia / 2.0).cutBlind(-depth)
            
        if self.type_ in ["M-F", "M-M"]:
            stud = cq.Workplane("XY").circle(self.nominal_dia / 2.0).extrude(-self.thread_length)
            body = body.union(stud)

        if self.type_ == "M-M":
            stud2 = (cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, self.length))
                     .circle(self.nominal_dia / 2.0).extrude(self.thread_length))
            body = body.union(stud2)

        return body

    def to_cutter(self, radial_allowance: float = 0.15, depth_allowance: float = 0.2) -> cq.Workplane:
        r = self.radius + radial_allowance
        return cq.Workplane("XY").polygon(6, r * 2).extrude(self.length + depth_allowance)

if __name__ == "__main__":
    from ocp_vscode import show
    ff = HexStandoff.from_size("M3", 15, "F-F")
    mf = HexStandoff.from_size("M3", 15, "M-F", thread_length=6.0)
    show(ff.solid.translate((-10, 0, 0)), mf.solid.translate((10, 0, 0)), names=["M3 15mm F-F", "M3 15mm M-F"])
