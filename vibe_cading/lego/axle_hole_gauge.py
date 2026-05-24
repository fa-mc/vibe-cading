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

"""
Printable round-hole gauge for calibrating the Technic axle-hole tip-to-tip
diameter on a specific FDM printer / material.
"""

from typing import Sequence

import cadquery as cq


class AxleHoleGauge:
    """Printable round-hole gauge for calibrating the effective Technic
    axle-hole tip-to-tip diameter on a specific FDM printer / material.

    A Lego Technic cross axle contacts a *round* hole only at its four
    curved arm tips — each tip is an arc of radius ``tip_to_tip / 2``, so
    the axle's outer envelope is a circle of diameter ``tip_to_tip``.  A
    round hole has no concave corners, so FDM "corner blowout" cannot
    confound the measurement: the smallest round hole that accepts the
    axle measures the effective tip-to-tip directly.  This gauge sweeps a
    row of round through-holes so the user can read that diameter off a
    single printed part.

    Origin (0, 0, 0): the block is plan-centred — its XY centroid sits at
    the origin — and its bottom face lies on the Z=0 print bed; the block
    extrudes up into +Z.  Hole axes are parallel to Z.

    Calibration procedure
    ---------------------
    1. Print the gauge flat, holes vertical (axis parallel to build-Z),
       on the target printer + material, with the same slicer settings
       used for real parts.
    2. Insert a real Lego Technic axle into each hole from the labelled
       (top) face.
    3. The smallest hole the axle enters with a firm-but-free slip — no
       slop, no force — gives the effective fitting modelled diameter
       ``D``.  Judge by *axial slide feel*, not rotational wobble: a round
       hole contacts the axle at four tips only, so some rotational wobble
       is inherent and expected, not a defect.
    4. The gauge yields a *profile* clearance, not a constant override.
       The axle-hole nominal (``AXLE_HOLE_TIP_TO_TIP = 4.80``) is fixed
       real-Lego geometry; printer clearance lives in the active
       ``ToleranceProfile``.  Convert the fitting diameter with::

           slip.radial = (D - 4.80) / 2

       and write it into the untracked ``print_profiles_user.json``
       (field-level deep-merges over ``print_profiles.json``), e.g. for
       ``D = 5.00``::

           {"fdm_standard": {"slip": {"radial": 0.10}}}

       See ``docs/lego-technic.md`` > Tuning Tolerances for the full
       procedure.

    Parameters
    ----------
    diameters:
        Swept hole diameters (mm), one straight cylindrical through-hole
        per entry.  The default range 4.70-5.00 in 0.05 mm increments
        brackets the 4.80 mm real-Lego axle-hole nominal with margin for
        FDM hole-shrink.
    depth:
        Block thickness = hole depth (mm).  Default 8.0 = one stud unit.
    hole_pitch:
        Cell width per hole along X (mm) — centre-to-centre hole spacing.
    engrave_depth:
        Depth of the diameter label engraving on the top face (mm).
    """

    def __init__(
        self,
        diameters: Sequence[float] = (4.70, 4.75, 4.80, 4.85, 4.90, 4.95, 5.00),
        depth: float = 8.0,
        hole_pitch: float = 9.0,
        engrave_depth: float = 0.6,
    ) -> None:
        if not diameters:
            raise ValueError("AxleHoleGauge requires at least one diameter")
        self.diameters: tuple[float, ...] = tuple(float(d) for d in diameters)
        self.depth: float = float(depth)
        self.hole_pitch: float = float(hole_pitch)
        self.engrave_depth: float = float(engrave_depth)

        # ── Derived layout ────────────────────────────────────────────────
        # Block length (X) packs one cell per hole; width (Y) leaves a
        # label band on the -Y side of the hole row.  Kept compact to
        # minimise material waste (Parameter Sweeps rule).
        n = len(self.diameters)
        self._label_band: float = 6.0           # -Y strip carrying the labels
        self._margin: float = 4.0               # solid wall around the hole row
        self.length: float = n * self.hole_pitch
        self.width: float = (
            max(self.diameters) + 2 * self._margin + self._label_band
        )
        # Hole-row centreline sits +label_band/2 above block centre so the
        # label band occupies the -Y portion of the top face.
        self._hole_row_y: float = self._label_band / 2.0
        self._label_y: float = self._hole_row_y - max(self.diameters) / 2.0 - 2.0

        self._solid: cq.Workplane = self._build()

    def _hole_x(self, index: int) -> float:
        """X centre of the hole at *index*, plan-centred about X=0."""
        start_x = -((len(self.diameters) - 1) / 2.0) * self.hole_pitch
        return start_x + index * self.hole_pitch

    def _build(self) -> cq.Workplane:
        """Build the flat block, cut the round through-holes, then engrave."""
        # Base block: plan-centred in XY, bottom face on Z=0.
        base = (
            cq.Workplane("XY")
            .box(self.length, self.width, self.depth)
            .translate((0, 0, self.depth / 2.0))
        )

        # ── Round through-holes ───────────────────────────────────────────
        # One straight cylinder per swept diameter, axis parallel to Z, no
        # lead-in chamfer — a chamfer would guide the axle and bias the
        # "smallest hole that fits" judgment; the fit must be read off the
        # full straight bore.  Each cutter is given a small entry/terminal
        # overcut so it cleanly breaks through both faces (coincident
        # cutter/body faces are unreliable in the OCCT boolean kernel).
        overcut = 0.1
        hole_cutters: list[cq.Workplane] = []
        for index, dia in enumerate(self.diameters):
            cutter = (
                cq.Workplane("XY")
                .circle(dia / 2.0)
                .extrude(self.depth + 2 * overcut)
                .translate((self._hole_x(index), self._hole_row_y, -overcut))
            )
            hole_cutters.append(cutter)

        holes = hole_cutters[0]
        for cutter in hole_cutters[1:]:
            holes = holes.union(cutter)
        base = base.cut(holes)

        # ── Diameter labels ───────────────────────────────────────────────
        # Each hole engraved with its diameter on the top face.  All label
        # text solids are unioned into one compound *before* a single
        # ``.cut()`` — engraving each label separately stalls the OCCT
        # boolean kernel (the established ToleranceGauge pattern).
        label_solids: list[cq.Workplane] = []
        for index, dia in enumerate(self.diameters):
            text = (
                cq.Workplane("XY")
                .text(
                    f"{dia:.2f}",
                    fontsize=3.0,
                    distance=self.engrave_depth,
                    halign="center",
                    valign="center",
                )
                # Sit the engraving on the top face: text() extrudes the
                # glyphs symmetrically about its plane, so place the plane
                # engrave_depth/2 below the top so the cut bites downward.
                .translate(
                    (
                        self._hole_x(index),
                        self._label_y,
                        self.depth - self.engrave_depth / 2.0,
                    )
                )
            )
            label_solids.append(text)

        all_labels = cq.Workplane("XY")
        for label in label_solids:
            all_labels.add(label.vals())
        base = base.cut(all_labels.combine())

        result = base
        # Topological guard: the gauge must be a single contiguous solid.
        # A floating sliver here would mean a hole or label cutter severed
        # the block — catch it at the source rather than at print time.
        assert len(result.solids().vals()) == 1, (
            "AxleHoleGauge expected a single solid, got "
            f"{len(result.solids().vals())}"
        )
        return result

    @property
    def solid(self) -> cq.Workplane:
        """The gauge block — a single contiguous solid (read-only)."""
        return self._solid
