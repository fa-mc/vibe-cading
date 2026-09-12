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

from typing import Literal

import cadquery as cq

from vibe_cading.lego.constants import BEAM_THICKNESS, BEAM_WIDTH


class _HoleMouthSelector(cq.Selector):
    """Pick the counterbore-rim circle edges at hole entries for chamfer operations.

    Supports two axis discriminators via the ``axis`` keyword:

    ``axis="z"`` (default — existing behavior, unchanged)
        Selects edges on the **top/bottom (Z) faces** of the beam — i.e. main-axis
        holes bored along +Z.  Predicate: (a) ``geomType() == 'CIRCLE'``, (b) radius
        approximately equal to the counterbore radius, (c) ``|Center().z -
        BEAM_THICKNESS/2|`` approximately equal to ``target_z_abs_from_mid`` (folds
        Z=0 and Z=BEAM_THICKNESS to the same threshold).  This is **byte-identical to
        the pre-generalization predicate** — no Y-centreline guard is added.  Safe for
        both :class:`~vibe_cading.lego.technic_beam.LegoTechnicBeam` (rims at Y≈0) and
        :class:`~vibe_cading.lego.technic_l_liftarm.LegoTechnicLLiftarm` (rims at
        non-zero Y, e.g. −4, −12, −20, −28, −36 mm) — a Y-guard would break the
        latter.  Perp rims (``center.z ≈ BEAM_THICKNESS/2``) are **already excluded**
        by the Z-fold clause: the fold evaluates to ``abs(0 − 3.9) = 3.9 ≫ tol``, so
        no compensating guard is required.

    ``axis="y"`` (new — perpendicular holes only)
        Selects edges on the **side (±Y) faces** of the beam — i.e. perp-axis holes
        bored along ±Y.  Predicate: (a) ``geomType() == 'CIRCLE'``, (b) radius
        approximately equal to the counterbore radius, (c) ``|Center().y| ≈
        BEAM_WIDTH/2`` (on a side face).  The Z-centre constraint is **omitted**
        for two reasons:

        (a) **Redundancy for num_holes ≥ 2** — when two or more holes are present,
            every perp counterbore rim circle sits at exactly ``Z = BEAM_THICKNESS/2
            ≈ 3.9 mm`` (mid-height), precisely as the design reasoned.  The
            ``|Center().y| ≈ BEAM_WIDTH/2`` Y-face constraint (3.9 mm) already
            cleanly separates face-entry rims from interior counterbore-floor circles
            (whose ``|center.y| ≈ 2.9 mm``), so an additional Z-centre clause would
            be a no-op for this common path.

        (b) **Degenerate num_holes=1 exception** — when the beam holds a single
            perpendicular hole, the Ø6.2 counterbore is wide enough to clip the
            rounded end-caps of the 8 mm-pitch beam body.  This splits each rim into
            arcs whose Z-centres land at ``Z ≈ 0.8 mm`` and ``Z ≈ 7.0 mm`` (not
            at mid-height).  A strict ``|Center().z - BEAM_THICKNESS/2| < tol``
            clause would incorrectly reject these legitimate face-entry rims.  The
            Y-face predicate alone handles both the n=1 and n≥2 cases correctly
            because the face-entry rims always have ``|center.y| = BEAM_WIDTH/2``
            regardless of how the Z-position is affected by end-cap clipping.

        ``target_z_abs_from_mid`` is accepted but **ignored** for this branch.

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

    def __init__(
        self,
        target_radius: float,
        target_z_abs_from_mid: float = BEAM_THICKNESS / 2,
        tol: float = 0.05,
        *,
        axis: Literal["z", "y"] = "z",
    ):
        self.target_radius = target_radius
        self.target_z_abs_from_mid = target_z_abs_from_mid
        self.tol = tol
        self.axis = axis

    def filter(self, edges):
        kept = []
        for e in edges:
            try:
                if e.geomType() != "CIRCLE":
                    continue
                if abs(e.radius() - self.target_radius) >= self.tol:
                    continue
                if self.axis == "z":
                    # ── Z-axis holes (main): top/bottom flat faces ───────────
                    # Fold through the mid-plane Z=BEAM_THICKNESS/2 so the top face
                    # (Z=BEAM_THICKNESS) and bottom face (Z=0) collapse to the same
                    # |center.z - BEAM_THICKNESS/2| ≈ BEAM_THICKNESS/2 threshold.
                    # NO Y-centreline guard — LegoTechnicLLiftarm's rims sit at
                    # non-zero Y (≈ -4…-36 mm) and must not be rejected.
                    if abs(abs(e.Center().z - BEAM_THICKNESS / 2) - self.target_z_abs_from_mid) >= self.tol:
                        continue
                else:
                    # ── Y-axis holes (perp): narrow ±Y side faces ────────────
                    # Face-entry rim circles always satisfy |center.y| = BEAM_WIDTH/2
                    # (exactly on the ±Y side face).  For num_holes ≥ 2 they also
                    # sit at Z = BEAM_THICKNESS/2 (mid-height); for num_holes = 1 the
                    # single Ø6.2 counterbore clips the rounded end-caps and the rims
                    # land at Z ≈ 0.8 mm and Z ≈ 7.0 mm instead.  A Z-centre clause
                    # is therefore OMITTED: it is redundant for n≥2 (the Y-face
                    # predicate alone separates face-entry rims from interior
                    # counterbore-floor circles at |center.y| ≈ 2.9 mm), and it would
                    # INCORRECTLY REJECT the legitimate n=1 end-cap-clipped rims.
                    if abs(abs(e.Center().y) - BEAM_WIDTH / 2) >= self.tol:
                        continue
                kept.append(e)
            except Exception:
                # geomType()/radius()/Center() may raise on non-circular edge types;
                # treat any failure as "not a hole-mouth edge" and skip.
                continue
        return kept
