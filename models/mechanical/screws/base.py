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