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

"""Printable hex-pocket gauge for calibrating the M3 nut press-fit
width-across-flats on a specific FDM printer / material.

Calibrates the ``press.radial`` knob of the active
:class:`~vibe_cading.print_settings.ToleranceProfile` against a real
M3 hex nut. Layout mirrors
:class:`vibe_cading.lego.axle_hole_gauge.AxleHoleGauge` (flat block
with engraved labels on a label band) — but the swept dimension is the
hexagonal pocket's width-across-flats, not a round-hole diameter.
"""

from __future__ import annotations

import math
from typing import Sequence

import cadquery as cq

from vibe_cading.mechanical.nuts.metric import MetricHexNut


# Default sweep: brackets the 5.5 mm M3 nut nominal asymmetrically with
# wider headroom on the +side to bracket typical FDM over-shrink. 0.10
# mm steps × 0.50 mm range (5.30 → 5.80) gives 6 pockets — wide enough
# to catch typical FDM variation without burning more material than a
# single short gauge needs.
DEFAULT_WIDTHS: tuple[float, ...] = (5.30, 5.40, 5.50, 5.60, 5.70, 5.80)


class MThreeNutPocketGauge:
    """Printable hex-pocket gauge for calibrating M3 nut press-fit
    width-across-flats on a specific FDM printer / material.

    Calibrates the ``press.radial`` knob of the active
    :class:`~vibe_cading.print_settings.ToleranceProfile`. The smallest
    swept pocket that grips an actual M3 hex nut as a press-fit gives
    the effective fitting width-across-flats ``D``; the calibrated
    value is::

        press.radial = (D - MetricHexNut.DIMENSIONS["M3"]["width_flats"]) / 2
                     = (D - 5.5) / 2

    The hex-pocket case is geometrically identical to the round-hole
    case because ``width_flats`` is a diameter-like dimension
    (across-the-flats face-to-face distance), and
    :meth:`MetricHexNut.to_cutter` inflates ``width_flats`` by
    ``2 * grade.radial`` to size the pocket — symmetric to a round
    hole.

    Origin (0, 0, 0): the block is plan-centred — its XY centroid sits
    at the origin — and its bottom face lies on the Z=0 print bed; the
    block extrudes up into +Z. Pocket axes are parallel to Z, flats
    aligned to the +X / -X axis (matching the layout convention of
    :class:`vibe_cading.mechanical.holes.CaptiveNutPocket`).

    Calibration procedure
    ---------------------
    1. Print the gauge flat, pockets vertical (axis parallel to
       build-Z), on the target printer + material, with the same
       slicer settings used for real parts.
    2. Press a real M3 hex nut into each pocket from the labelled
       (top) face. Apply firm finger pressure — do NOT hammer.
    3. The smallest pocket the nut enters as a press-fit (snug enough
       that the nut does not wobble or fall out, tight enough that a
       firm push is required) gives the effective fitting
       width-across-flats ``D``.
    4. Hand ``D`` to ``tools/calibrate.py press --diameter <D>`` to
       write the calibrated ``press.radial`` into your
       ``print_profiles_user.json``.

    Parameters
    ----------
    widths:
        Swept pocket widths-across-flats (mm), one hex pocket per
        entry. Default ``DEFAULT_WIDTHS`` brackets 5.5 mm in 0.10 mm
        steps from 5.30 to 5.80.
    depth:
        Block thickness = pocket depth (mm). Default 8.0 = one stud
        unit — well over the 2.4 mm M3 hex nut thickness so the user
        can press the nut fully home.
    pocket_pitch:
        Cell width per pocket along X (mm) — centre-to-centre spacing.
    engrave_depth:
        Depth of the width label engraving on the top face (mm).
    """

    def __init__(
        self,
        widths: Sequence[float] = DEFAULT_WIDTHS,
        depth: float = 8.0,
        pocket_pitch: float = 10.0,
        engrave_depth: float = 0.6,
    ) -> None:
        if not widths:
            raise ValueError(
                "MThreeNutPocketGauge requires at least one width"
            )
        self.widths: tuple[float, ...] = tuple(float(w) for w in widths)
        self.depth: float = float(depth)
        self.pocket_pitch: float = float(pocket_pitch)
        self.engrave_depth: float = float(engrave_depth)

        # ── Nominal-source guard ──────────────────────────────────────
        # Live read from the source-of-truth constant — the
        # ``MetricHexNut.DIMENSIONS["M3"]["width_flats"]`` table entry.
        # If the swept tuple's centre value diverges from the live
        # nominal the gauge is bracketing the wrong target and the
        # calibration formula would silently mis-apply. Caught at
        # construction.
        nominal = float(MetricHexNut.DIMENSIONS["M3"]["width_flats"])
        if nominal not in self.widths:
            raise ValueError(
                f"MThreeNutPocketGauge sweep tuple {self.widths!r} "
                f"does not include the live M3 nut width-flats nominal "
                f"({nominal} mm). Bracket the nominal so the user can "
                f"select 'exactly the nominal' as their best-fit "
                f"variant."
            )

        # ── Derived layout ────────────────────────────────────────────
        n = len(self.widths)
        self._label_band: float = 6.0
        self._margin: float = 4.0
        self.length: float = n * self.pocket_pitch
        # Hex height (point-to-point along Y when one flat sits on +X /
        # -X) = WAF / cos(30°). Use the largest pocket for sizing.
        max_pt = max(self.widths) / math.cos(math.radians(30))
        self.width: float = max_pt + 2 * self._margin + self._label_band
        # Pocket-row centreline sits +label_band/2 above block centre.
        self._pocket_row_y: float = self._label_band / 2.0
        self._label_y: float = self._pocket_row_y - max_pt / 2.0 - 2.0

        self._solid: cq.Workplane = self._build()

    def _pocket_x(self, index: int) -> float:
        """X centre of the pocket at *index*, plan-centred about X=0."""
        start_x = -((len(self.widths) - 1) / 2.0) * self.pocket_pitch
        return start_x + index * self.pocket_pitch

    def _build(self) -> cq.Workplane:
        """Build the flat block, cut hex through-pockets, then engrave."""
        # Base block: plan-centred in XY, bottom face on Z=0.
        base = (
            cq.Workplane("XY")
            .box(self.length, self.width, self.depth)
            .translate((0, 0, self.depth / 2.0))
        )

        # ── Hex through-pockets ───────────────────────────────────────
        # CadQuery's ``polygon(6, diameter)`` defines a *circumscribed*
        # circle diameter (point-to-point). Width-across-flats (WAF) =
        # inscribed circle diameter → circumscribed = WAF / cos(30°).
        # Pockets extrude through the full block thickness with small
        # entry / terminal overcut to avoid coincident faces in the
        # boolean kernel. NO additional clearance is baked in — the
        # printed pocket's geometry exactly equals the swept WAF value
        # the user reads off the label.
        overcut = 0.1
        pocket_cutters: list[cq.Workplane] = []
        for index, waf in enumerate(self.widths):
            r_circumscribed = (waf / math.cos(math.radians(30))) / 2.0
            cutter = (
                cq.Workplane("XY")
                .polygon(6, r_circumscribed * 2)
                .extrude(self.depth + 2 * overcut)
                .translate(
                    (self._pocket_x(index), self._pocket_row_y, -overcut)
                )
            )
            pocket_cutters.append(cutter)

        pockets = pocket_cutters[0]
        for cutter in pocket_cutters[1:]:
            pockets = pockets.union(cutter)
        base = base.cut(pockets)

        # ── Width labels ──────────────────────────────────────────────
        # All label glyphs unioned into one compound before a single
        # ``.cut()`` — engraving each label separately stalls the OCCT
        # boolean kernel.
        label_solids: list[cq.Workplane] = []
        for index, waf in enumerate(self.widths):
            text = (
                cq.Workplane("XY")
                .text(
                    f"{waf:.2f}",
                    fontsize=3.0,
                    distance=self.engrave_depth,
                    halign="center",
                    valign="center",
                )
                .translate(
                    (
                        self._pocket_x(index),
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
        assert len(result.solids().vals()) == 1, (
            "MThreeNutPocketGauge expected a single solid, got "
            f"{len(result.solids().vals())}"
        )
        return result

    @property
    def solid(self) -> cq.Workplane:
        """The gauge block — a single contiguous solid (read-only)."""
        return self._solid
