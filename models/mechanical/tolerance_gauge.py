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
Physical test blocks for tuning generic FDM printer tolerances.
"""

from typing import Sequence
import cadquery as cq

from models.mechanical.screws.metric import MetricMachineScrew
from models.mechanical.bearings import Bearing
from models.lego.cutters.technic_pin_hole import TechnicPinHole
from models.lego.constants import PIN_HOLE_DIAMETER
from models.cq_utils import cylinder

class ToleranceGauge:
    """Parametric block to test clearance tuning for FDM printers."""

    def __init__(self, offsets: Sequence[float] = (0.0, 0.05, 0.10, 0.15, 0.20)):
        self.offsets = tuple(offsets)
        self.base_thickness = 8.0
        self.x_spacing = 14.0
        self.y_spacing = 12.0
        self._solid = self._build()

    def _build(self) -> cq.Workplane:
        num_cols = len(self.offsets)
        width = num_cols * self.x_spacing
        length = 4 * self.y_spacing + 12.0  # 4 rows, + extra padding

        # Base block centered at (0, 0, Z). Bottom at Z=0.
        base = (
            cq.Workplane("XY")
            .box(width, length, self.base_thickness)
            .translate((0, 0, self.base_thickness / 2.0))
        )

        cutters = []
        pegs = []
        labels = []

        # Y coordinates for the 4 rows (centered around 0)
        y_coords = [
            1.5 * self.y_spacing,
            0.5 * self.y_spacing,
            -0.5 * self.y_spacing,
            -1.5 * self.y_spacing,
        ]

        # Start X coordinates
        start_x = -((num_cols - 1) / 2.0) * self.x_spacing

        for i, offset in enumerate(self.offsets):
            x = start_x + (i * self.x_spacing)

            # 1. Row 1 (y_coords[0]): M3 Clearance
            m3 = MetricMachineScrew.from_size("M3", length=12.0, head_type="socket")
            m3_cutter = m3.to_cutter(mode="clearance", radial_allowance=offset, head_recess_depth=1.0)
            m3_cutter = m3_cutter.translate((x, y_coords[0], self.base_thickness))
            cutters.append(m3_cutter)

            # 2. Row 2 (y_coords[1]): MR85 Bearing outer pocket (8mm OD, 2.5mm thick)
            brg = Bearing(inner_dia=5.0, outer_dia=8.0, thickness=2.5)
            brg_pocket = brg.outer_pocket(radial_clearance=offset)
            # Pocket goes from Z=0 to 2.5. Translate to top surface.
            pocket_z = self.base_thickness - 2.5
            brg_pocket = brg_pocket.translate((x, y_coords[1], pocket_z))
            
            # Add a 4mm through-hole underneath the pocket to push the bearing out
            push_hole = cylinder(radius=2.0, height=pocket_z + 0.1, center=(0, 0, 0)).translate((x, y_coords[1], 0))
            cutters.append(brg_pocket)
            cutters.append(push_hole)

            # 3. Row 3 (y_coords[2]): MR85 Bearing inner OD PEG (5mm shaft)
            # Offset is subtracted here intentionally, as outer pegs shrink when allowance is applied.
            # Tested diameter = 5.0 - 2 * offset
            peg_radius = (5.0 - 2 * offset) / 2.0
            peg = cylinder(radius=peg_radius, height=4.0, center=(0, 0, 0)).translate((x, y_coords[2], self.base_thickness))
            
            # Sub-cut a tiny chamfer on the peg so bearings slide on easily
            peg_chamfer = (
                cq.Workplane("XY", origin=(x, y_coords[2], self.base_thickness + 4.0))
                .circle(peg_radius).circle(peg_radius - 0.5)
                .extrude(-0.5)
            )
            # Actually, standard cadquery chamfer is better:
            # We'll just keep it simple as a cylinder for now to test raw diameter tolerance.
            pegs.append(peg)

            # 4. Row 4 (y_coords[3]): Lego Technic pins (4.8mm hole)
            pin_dia = PIN_HOLE_DIAMETER + 2 * offset
            pin_cutter = TechnicPinHole(depth=self.base_thickness, diameter=pin_dia).solid
            pin_cutter = pin_cutter.translate((x, y_coords[3], 0))
            cutters.append(pin_cutter)

            # Label (Debossed on Top surface)
            text_str = f"+{offset:.2f}"
            t = (
                cq.Workplane("XY")
                .text(text_str, fontsize=4.0, distance=1.0, halign="center", valign="center")
            )
            # Place label below each column exactly centered or above it?
            # Let's put a label between row 1 and 2, and row 3 and 4.
            t1 = t.translate((x, y_coords[0] - self.y_spacing/2.0, self.base_thickness - 0.5))
            labels.append(t1)
            t2 = t.translate((x, y_coords[3] + self.y_spacing/2.0, self.base_thickness - 0.5))
            labels.append(t2)

        # Union all additions
        for peg in pegs:
            base = base.union(peg)


        # Cut holes first
        if cutters:
            cutter_tool = cutters[0]
            for ct in cutters[1:]:
                cutter_tool = cutter_tool.union(ct)
            base = base.cut(cutter_tool)



        # Cut labels using the fast block-level combine method
        if labels:
            # Empty workplane to gather all text solids
            all_labels = cq.Workplane("XY")
            for l in labels:
                all_labels.add(l.vals())
            
            # Combine all text solids into one Compound before cutting
            base = base.cut(all_labels.combine())

        return base

    @property
    def solid(self) -> cq.Workplane:
        return self._solid
