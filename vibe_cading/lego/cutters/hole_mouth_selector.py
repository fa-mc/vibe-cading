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

"""Shared selector that picks hole-mouth faces for counterbore/chamfer rim operations."""

import cadquery as cq

from vibe_cading.lego.constants import BEAM_THICKNESS


class _HoleMouthSelector(cq.Selector):
    """Pick the counterbore-rim circle edges at each hole entry on the top/bottom (Z) faces.

    Filters edges to: (a) ``geomType() == 'CIRCLE'``, (b) radius approximately equal
    to the counterbore radius (``TechnicPinHole.DEFAULT_CB_DIAMETER / 2 = 3.1 mm``),
    and (c) ``|Center().z - BEAM_THICKNESS/2|`` approximately equal to
    ``BEAM_THICKNESS / 2 = 3.9 mm`` (i.e. on the top face Z=BEAM_THICKNESS or bottom
    face Z=0, not interior to the counterbore well).  The body sits at
    Z ∈ [0, BEAM_THICKNESS], so the Z-face entries land at Z=0 and Z=BEAM_THICKNESS;
    folding through the mid-plane Z=BEAM_THICKNESS/2 normalizes both faces to the
    same ``|...| ≈ 3.9 mm`` threshold.

    Why a custom Selector and not a CadQuery string selector?  The string-selector
    DSL does not support compound predicates with radius / centre filters; lambda
    selectors are not supported by CadQuery 2.7.0 either.  A ``cq.Selector``
    subclass with a ``filter()`` method is the canonical extension point.

    Why filter on the counterbore rim and not the inner bore mouth?  When the
    pin-hole cutter carries counterbores (the default), the inner bore-mouth circle
    is *absorbed* by the counterbore at the Z-face and is not present as a
    standalone face-incident edge.  Interior counterbore-floor / bore-cylinder
    intersection circles live at ``|Center().z - BEAM_THICKNESS/2| ≈ 2.91 mm`` and
    would cause ``BRep_API: command not done`` failures if fed to ``.chamfer()``;
    the ``|Center().z - BEAM_THICKNESS/2|`` predicate excludes them.
    """

    def __init__(self, target_radius: float, target_z_abs_from_mid: float, tol: float = 0.05):
        self.target_radius = target_radius
        self.target_z_abs_from_mid = target_z_abs_from_mid
        self.tol = tol

    def filter(self, edges):
        kept = []
        for e in edges:
            try:
                if e.geomType() != "CIRCLE":
                    continue
                if abs(e.radius() - self.target_radius) >= self.tol:
                    continue
                # Fold through the mid-plane Z=BEAM_THICKNESS/2 so the top face
                # (Z=BEAM_THICKNESS) and bottom face (Z=0) collapse to the same
                # |center.z - BEAM_THICKNESS/2| ≈ BEAM_THICKNESS/2 threshold.
                if abs(abs(e.Center().z - BEAM_THICKNESS / 2) - self.target_z_abs_from_mid) >= self.tol:
                    continue
                kept.append(e)
            except Exception:
                # geomType()/radius()/Center() may raise on non-circular edge types;
                # treat any failure as "not a hole-mouth edge" and skip.
                continue
        return kept
