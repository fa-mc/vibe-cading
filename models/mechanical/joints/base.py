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
