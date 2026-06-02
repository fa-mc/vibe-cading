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

"""Printable round-hole gauge for calibrating the M3 clearance hole
diameter on a specific FDM printer / material.

Calibrates the ``free.radial`` knob of the active
:class:`~vibe_cading.print_settings.ToleranceProfile` against a real
M3 machine screw. Layout and procedure mirror
:class:`vibe_cading.lego.axle_hole_gauge.AxleHoleGauge` — a flat block
with a row of round through-holes plus engraved diameter labels on a
label band.
"""

from __future__ import annotations

from typing import Sequence

import cadquery as cq

from vibe_cading.cq_utils import engraved_labels
from vibe_cading.mechanical.screws.metric import METRIC_SIZES


# Default sweep: brackets the 3.2 mm M3 clearance nominal symmetrically
# with ±0.30 mm range in 0.10 mm steps. Coarser than ``AxleHoleGauge``'s
# 0.05 mm step because FDM ``free`` fits tolerate more variation than
# the ``slip`` fits the axle gauge calibrates.
DEFAULT_DIAMETERS: tuple[float, ...] = (
    2.90, 3.00, 3.10, 3.20, 3.30, 3.40, 3.50,
)


class MThreeClearanceGauge:
    """Printable round-hole gauge for calibrating the M3 clearance hole
    diameter on a specific FDM printer / material.

    Calibrates the ``free.radial`` knob of the active
    :class:`~vibe_cading.print_settings.ToleranceProfile`. The smallest
    swept hole that accepts an actual M3 machine screw with a
    firm-but-free clearance fit gives the effective fitting diameter
    ``D``; the calibrated value is::

        free.radial = (D - METRIC_SIZES["M3"]["clearance"]) / 2
                    = (D - 3.2) / 2

    Origin (0, 0, 0): the block is plan-centred — its XY centroid sits
    at the origin — and its bottom face lies on the Z=0 print bed; the
    block extrudes up into +Z. Hole axes are parallel to Z.

    Calibration procedure
    ---------------------
    1. Print the gauge flat, holes vertical (axis parallel to build-Z),
       on the target printer + material, with the same slicer settings
       used for real parts.
    2. Insert a real M3 machine screw shank (NOT a head — just the
       unthreaded shoulder / threaded shank — through each hole from
       the labelled (top) face.
    3. The smallest hole the screw enters with a firm-but-free slip —
       no slop, no force, no thread engagement — gives the effective
       fitting modelled diameter ``D``.
    4. Hand ``D`` to ``tools/calibrate.py free --diameter <D>`` to
       write the calibrated ``free.radial`` into your
       ``print_profiles_user.json``.

    Parameters
    ----------
    diameters:
        Swept hole diameters (mm), one straight cylindrical through-hole
        per entry. Default ``DEFAULT_DIAMETERS`` brackets 3.2 mm ±0.30
        in 0.10 mm steps.
    depth:
        Block thickness = hole depth (mm). Default 8.0 = one stud unit.
    hole_pitch:
        Cell width per hole along X (mm) — centre-to-centre spacing.
    engrave_depth:
        Depth of the diameter label engraving on the top face (mm).
    labels:
        When ``True`` (default) each hole is engraved with its diameter on
        the top face — kept for physical prints, ``build.py`` and
        ``tools/view.py``.  When ``False`` the gauge is geometry-only (no
        engraving); the visual-contract render sets ``labels=False`` because
        ``cq.text()`` glyph tessellation is host-font-dependent and not
        reproducible across CI / clone hosts (see
        :func:`vibe_cading.cq_utils.engraved_labels`).
    """

    def __init__(
        self,
        diameters: Sequence[float] = DEFAULT_DIAMETERS,
        depth: float = 8.0,
        hole_pitch: float = 9.0,
        engrave_depth: float = 0.6,
        labels: bool = True,
    ) -> None:
        if not diameters:
            raise ValueError(
                "MThreeClearanceGauge requires at least one diameter"
            )
        self.diameters: tuple[float, ...] = tuple(float(d) for d in diameters)
        self.depth: float = float(depth)
        self.hole_pitch: float = float(hole_pitch)
        self.engrave_depth: float = float(engrave_depth)
        self.labels: bool = bool(labels)

        # ── Nominal-source guard ──────────────────────────────────────
        # Live read from the source-of-truth constant; if the swept
        # tuple's centre value diverges from the live nominal the gauge
        # is bracketing the wrong target and the calibration formula
        # would silently mis-apply. Caught at construction.
        nominal = float(METRIC_SIZES["M3"]["clearance"])
        if nominal not in self.diameters:
            raise ValueError(
                f"MThreeClearanceGauge sweep tuple {self.diameters!r} "
                f"does not include the live M3 clearance nominal "
                f"({nominal} mm). Bracket the nominal so the user can "
                f"select 'exactly the nominal' as their best-fit "
                f"variant."
            )

        # ── Derived layout ────────────────────────────────────────────
        n = len(self.diameters)
        self._label_band: float = 6.0           # -Y strip carrying labels
        self._margin: float = 4.0               # solid wall around holes
        self.length: float = n * self.hole_pitch
        self.width: float = (
            max(self.diameters) + 2 * self._margin + self._label_band
        )
        # Hole-row centreline sits +label_band/2 above block centre so
        # the label band occupies the -Y portion of the top face.
        self._hole_row_y: float = self._label_band / 2.0
        self._label_y: float = (
            self._hole_row_y - max(self.diameters) / 2.0 - 2.0
        )

        self._solid: cq.Workplane = self._build()

    def _hole_x(self, index: int) -> float:
        """X centre of the hole at *index*, plan-centred about X=0."""
        start_x = -((len(self.diameters) - 1) / 2.0) * self.hole_pitch
        return start_x + index * self.hole_pitch

    def _build(self) -> cq.Workplane:
        """Build the flat block, cut the round through-holes, engrave."""
        # Base block: plan-centred in XY, bottom face on Z=0.
        base = (
            cq.Workplane("XY")
            .box(self.length, self.width, self.depth)
            .translate((0, 0, self.depth / 2.0))
        )

        # ── Round through-holes ───────────────────────────────────────
        # Straight cylinder per swept diameter, axis parallel to Z, no
        # lead-in chamfer — a chamfer would guide the screw and bias
        # the "smallest hole that fits" judgment. Each cutter gets a
        # small entry/terminal overcut so it cleanly breaks through
        # both faces (coincident cutter/body faces are unreliable in
        # the OCCT boolean kernel).
        overcut = 0.1
        hole_cutters: list[cq.Workplane] = []
        for index, dia in enumerate(self.diameters):
            cutter = (
                cq.Workplane("XY")
                .circle(dia / 2.0)
                .extrude(self.depth + 2 * overcut)
                .translate(
                    (self._hole_x(index), self._hole_row_y, -overcut)
                )
            )
            hole_cutters.append(cutter)

        holes = hole_cutters[0]
        for cutter in hole_cutters[1:]:
            holes = holes.union(cutter)
        base = base.cut(holes)

        # ── Diameter labels ───────────────────────────────────────────
        # Each hole engraved with its diameter on the top face via the
        # shared engraved_labels helper (single combined cut — engraving
        # each label separately stalls the OCCT boolean kernel).  text()
        # extrudes glyphs symmetrically about their plane, so the label
        # plane sits engrave_depth/2 below the top face.  labels=False
        # suppresses engraving entirely (geometry-only) — the visual
        # contract renders that way (host-font-dependent glyphs).
        engraving = engraved_labels(
            [
                (
                    f"{dia:.2f}",
                    (
                        self._hole_x(index),
                        self._label_y,
                        self.depth - self.engrave_depth / 2.0,
                    ),
                )
                for index, dia in enumerate(self.diameters)
            ],
            fontsize=3.0,
            depth=self.engrave_depth,
            labels=self.labels,
        )
        if engraving is not None:
            base = base.cut(engraving)

        result = base
        # Topological guard: the gauge must be a single contiguous
        # solid. A floating sliver here would mean a hole or label
        # cutter severed the block — catch at source, not print time.
        assert len(result.solids().vals()) == 1, (
            "MThreeClearanceGauge expected a single solid, got "
            f"{len(result.solids().vals())}"
        )
        return result

    @property
    def solid(self) -> cq.Workplane:
        """The gauge block — a single contiguous solid (read-only)."""
        return self._solid
