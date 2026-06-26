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

"""Gears package.

Contains parametric gear generators and the composable bore primitives that
gear hubs consume.
"""

from .base import Gear, ISO_STANDARD_MODULES
from .bevel import BevelGear
from .bore import Bore, DBore, HexBore, KeyedBore, RoundBore
from .helical import HelicalGear
from .rack import RackGear
from .spur import SpurGear

__all__ = [
    "Gear",
    "ISO_STANDARD_MODULES",
    "Bore",
    "RoundBore",
    "HexBore",
    "DBore",
    "KeyedBore",
    "SpurGear",
    "HelicalGear",
    "RackGear",
    "BevelGear",
]
