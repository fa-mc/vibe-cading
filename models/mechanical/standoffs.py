"""
Hexagonal Standoffs / Spacers (standard PCB/electronics mounting hardware).
"""

from __future__ import annotations

import cadquery as cq

class HexStandoff:
    """Standard Hexagonal Standoff (Spacer) used for mounting PCBs.

    Supports modeling actual brass/nylon standoffs and generating clearance
    pockets to embed them into 3D printed parts.
    """

    # Common sizes (Size: Width Across Flats)
    # M3 is typically 5.5mm flat-to-flat. 6-32 (PC hardware) is often 1/4" (6.35mm).
    DIMENSIONS = {
        "M2": {"width_flats": 4.0},
        "M2.5": {"width_flats": 5.0},
        "M3": {"width_flats": 5.5},
        "M4": {"width_flats": 7.0},
        "4-40": {"width_flats": 4.76}, # 3/16 inch
        "6-32": {"width_flats": 6.35}, # 1/4 inch
    }

    def __init__(self, size: str = "M3", length: float = 10.0, type_: str = "F-F", thread_length: float = 6.0):
        """
        :param size: The thread/body profile size ("M3", "6-32").
        :param length: The length of the hexagonal body (mm).
        :param type_: "F-F" (Female-Female), "M-F" (Male-Female), or "M-M" (Male-Male).
        :param thread_length: How far the male threaded stud protrudes (only used for M-F or M-M).
        """
        if size not in self.DIMENSIONS:
            raise ValueError(f"Unknown standoff size {size}. Supported: {list(self.DIMENSIONS.keys())}")

        self.size = size
        self.length = length
        self.type_ = type_.upper()
        self.thread_length = thread_length
        self.width_flats = self.DIMENSIONS[size]["width_flats"]

        # Hexagon flat-to-flat = sqrt(3) * R
        self.radius = self.width_flats / 1.7320508075688772

        # Rough thread diameters for drawing male studs/female bores
        # (visual only, standoffs use standard nominal sizes)
        self.nominal_dia = 3.0 if size == "M3" else 4.0 if size == "M4" else 2.5 if size == "M2.5" else 2.0 if size == "M2" else 3.5

    @property
    def solid(self) -> cq.Workplane:
        """The literal 3D solid of the standoff."""
        # Main hex body
        body = (
            cq.Workplane("XY")
            .polygon(6, self.radius * 2)
            .extrude(self.length)
        )

        # Internal bores
        if self.type_ in ["F-F", "M-F"]:
            depth = self.length if self.type_ == "F-F" else self.length / 2.0
            body = body.faces(">Z").workplane().circle(self.nominal_dia / 2.0).cutBlind(-depth)

        # External male studs
        if self.type_ in ["M-F", "M-M"]:
            stud = cq.Workplane("XY").circle(self.nominal_dia / 2.0).extrude(-self.thread_length)
            body = body.union(stud)

        if self.type_ == "M-M":
            stud2 = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, 0, self.length))
                .circle(self.nominal_dia / 2.0)
                .extrude(self.thread_length)
            )
            body = body.union(stud2)

        return body

    def to_cutter(self, radial_allowance: float = 0.15, depth_allowance: float = 0.2) -> cq.Workplane:
        """Generate a static pocket cutter for press-fitting the hex body."""
        r = self.radius + radial_allowance
        # Cut starting from Z=0 up to the standoff length (incorporating allowance if needed)
        # Note: If it's Male-Female, you usually embed the base up to where the hex starts.
        return (
            cq.Workplane("XY")
            .polygon(6, r * 2)
            .extrude(self.length + depth_allowance)
        )

if __name__ == "__main__":
    from ocp_vscode import show

    ff = HexStandoff("M3", 15, "F-F")
    mf = HexStandoff("M3", 15, "M-F", thread_length=6.0)

    show(
        ff.solid.translate((-10, 0, 0)),
        mf.solid.translate((10, 0, 0)),
        names=["M3 15mm F-F", "M3 15mm M-F"]
    )