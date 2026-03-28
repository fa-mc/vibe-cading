from abc import ABC, abstractmethod
import cadquery as cq

class BaseJoint(ABC):
    """Abstract base class for all 3D-printable modular joints.

    All joints should implement standard male (positive) and female (cutting)
    methods that return a standard CadQuery solid. By convention, joints
    should be modeled at the origin (0,0,0) protruding in the +Y or +Z axis,
    with an `overlap` parameter allowing them to cleanly union/cut into base bodies.
    """

    @abstractmethod
    def male(self, overlap: float = 1.0) -> cq.Workplane:
        """Returns the positive geometry (e.g. the dovetail pin or snap hook).

        Args:
            overlap: Extra length extending negatively into the parent body to ensure a clean boolean union.
        """
        pass

    @abstractmethod
    def female(self, overlap: float = 1.0) -> cq.Workplane:
        """Returns the negative cutting geometry (e.g. the dovetail socket or snap catch cavity).

        Args:
            overlap: Extra length extending outside the parent body to ensure a clean boolean cut.
        """
        pass
