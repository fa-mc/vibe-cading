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