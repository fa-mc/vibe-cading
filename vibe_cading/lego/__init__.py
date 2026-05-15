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

"""vibe_cading.lego — mid-level package.

Per the design Round 5.5 "two-level __init__.py discipline", this
mid-level package intentionally re-exports nothing.  Import the cutters,
constants, gears, or axle helpers directly from their leaf modules /
subpackages, e.g.::

    from vibe_cading.lego.cutters import TechnicAxleHole, TechnicPinHole
    from vibe_cading.lego.technic_axle import TechnicAxle
"""
