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

"""Private side-wall cutter orientation helpers (lego_adapters package only).

Previously lived in ``vibe_cading.cq_utils`` as ``orient_to_neg_x`` /
``orient_to_pos_x``.  Both helpers exist solely to orient a +Z-extruded cutter
so it enters a part through a vertical X wall — a use case unique to the
SG90-servo mount and clamp under ``lego_adapters/servos/sg90/``.  Moved here
to keep ``cq_utils`` focused on generic library primitives.

The leading underscore on the module name signals "package-private": this
module is intentionally NOT re-exported from
``vibe_cading.lego_adapters.__init__``.  Promote a helper back to ``cq_utils``
if a second, non-SG90 caller materialises.
"""

from __future__ import annotations

import cadquery as cq


def orient_to_neg_x(
    solid: cq.Workplane,
    wall_x: float,
    at_y: float,
    at_z: float,
) -> cq.Workplane:
    """Orient a +Z-extruded cutter so it enters the part through the −X wall.

    The solid's Z = 0 face is placed flush with the outer wall at *wall_x*
    (negative) and the bore axis points inward (+X direction).

    Parameters
    ----------
    solid:
        A cutter solid whose axis runs along +Z, centred at XY origin.
    wall_x:
        X coordinate of the outer face (negative value, e.g. −12.0).
    at_y, at_z:
        Y and Z position of the hole centre.
    """
    return solid.rotate((0, 0, 0), (0, 1, 0), 90).translate((wall_x, at_y, at_z))


def orient_to_pos_x(
    solid: cq.Workplane,
    wall_x: float,
    at_y: float,
    at_z: float,
) -> cq.Workplane:
    """Orient a +Z-extruded cutter so it enters the part through the +X wall.

    Parameters
    ----------
    solid:
        A cutter solid whose axis runs along +Z, centred at XY origin.
    wall_x:
        X coordinate of the outer face (positive value, e.g. +12.0).
    at_y, at_z:
        Y and Z position of the hole centre.
    """
    return solid.rotate((0, 0, 0), (0, 1, 0), -90).translate((wall_x, at_y, at_z))
