import math
import cadquery as cq
from abc import ABC, abstractmethod

class Gear(ABC):
    """Abstract base class for parametric involute gears."""
    
    def __init__(self, module: float, teeth: int, face_width: float, bore: float | None = None, pressure_angle: float = 20.0):
        self.module = float(module)
        self.teeth = int(teeth)
        self.face_width = float(face_width)
        self.bore = bore
        self.pressure_angle = float(pressure_angle)
        
        if self.module <= 0:
            raise ValueError(f"module must be positive, got {self.module}")
        if self.face_width <= 0:
            raise ValueError(f"face_width must be positive, got {self.face_width}")

        phi = math.radians(self.pressure_angle)
        z_min = int(2.0 / math.sin(phi) ** 2)
        if self.teeth < z_min:
            raise ValueError(
                f"teeth={self.teeth} would cause undercut; minimum for "
                f"pressure_angle={self.pressure_angle}° is {z_min}. "
                "Increase tooth count or use profile shift."
            )

        # Derived radii for standard involute gears
        m, z = self.module, self.teeth
        self.pitch_radius = m * z / 2.0
        self.base_radius = self.pitch_radius * math.cos(phi)
        self.tip_radius = self.pitch_radius + m          # addendum = m
        self.root_radius = self.pitch_radius - 1.25 * m  # dedendum = 1.25 m

    @property
    @abstractmethod
    def solid(self) -> cq.Workplane:
        """The CadQuery solid representing the generated gear."""
        pass

    def center_distance_to(self, other: "Gear") -> float:
        """Calculate the standard center-to-center operating distance to another gear."""
        if self.module != other.module:
            raise ValueError("Gears must have the same module to mesh properly.")
        if self.pressure_angle != other.pressure_angle:
            raise ValueError("Gears must have the same pressure angle to mesh properly.")
        return self.pitch_radius + other.pitch_radius
