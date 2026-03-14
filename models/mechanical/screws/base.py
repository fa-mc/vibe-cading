import cadquery as cq
from abc import ABC, abstractmethod

class Screw(ABC):
    """
    Abstract base class for parametric screws. 
    Concrete sub-classes must implement detailed solid generation 
    and cutter tool generation suitable for their thread / head geometries.
    """
    
    @property
    @abstractmethod
    def solid(self) -> cq.Workplane:
        """Generates the positive physical model of the screw."""
        pass

    @abstractmethod
    def to_cutter(self, mode: str = "clearance", radial_allowance: float = 0.0, head_recess_depth: float = 0.0) -> cq.Workplane:
        """
        Generates a boolean subtraction tool (cutter) for this screw.
        
        :param mode: 'clearance' (loose fit), 'tap' (tight fit), or 'interference'.
        :param radial_allowance: Extra radial clearance to add to the hole (often needed for 3D printing tolerances).
        :param head_recess_depth: Sink the head this much deeper into the part (positive value means recess into -Z).
        """
        pass