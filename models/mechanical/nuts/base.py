import cadquery as cq
from abc import ABC, abstractmethod

class Nut(ABC):
    """
    Abstract base class for parametric nuts. 
    Concrete sub-classes must implement detailed solid generation 
    and cutter tool generation suitable for their specific geometries.
    """
    
    @property
    @abstractmethod
    def solid(self) -> cq.Workplane:
        """Generates the positive physical model of the nut."""
        pass

    @abstractmethod
    def to_cutter(self, radial_allowance: float = 0.15, depth_allowance: float = 0.2) -> cq.Workplane:
        """
        Generates a static pocket cutter for press-fitting or embedding the nut.
        
        :param radial_allowance: Extra radial clearance (mm) added to the hole.
        :param depth_allowance: Extra depth clearance (mm) added to the hole.
        """
        pass
        
    @abstractmethod
    def to_captive_slot(self, slot_length: float, radial_allowance: float = 0.15, depth_allowance: float = 0.2) -> cq.Workplane:
        """
        Generates a cutter for a sliding captive nut trap.
        Extrudes the nut profile along the -Y axis by `slot_length` so the nut 
        can be slid into the part from the side.
        
        :param slot_length: Length of the insertion channel (mm).
        :param radial_allowance: Extra radial clearance (mm) added to the slot.
        :param depth_allowance: Extra depth clearance (mm) added to the slot.
        """
        pass