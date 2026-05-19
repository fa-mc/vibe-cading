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
"""Example: construct a 5-stud Lego Technic beam and export STEP + SVG.

Primitive demonstrated: ``LegoTechnicBeam`` from
``vibe_cading.lego.technic_beam`` — the canonical parametric Technic beam.
Construct one with ``length_in_studs=5``, read its ``.solid`` property,
and write both a STEP file (CAD-tool import) and an SVG snapshot
(visual confirmation) to ``examples/build/lego_technic_beam/``.

Run:
    python3 examples/lego_technic_beam.py

Outputs (under ``examples/build/lego_technic_beam/``):
    - lego_technic_beam.step
    - lego_technic_beam.svg
"""
from pathlib import Path

import cadquery as cq

from vibe_cading.lego.technic_beam import LegoTechnicBeam


if __name__ == "__main__":
    # Build the part — five studs is the most common Technic beam length.
    beam = LegoTechnicBeam(length_in_studs=5)

    # Output goes under examples/build/<name>/ (gitignored — see .gitignore).
    out_dir = Path(__file__).parent / "build" / "lego_technic_beam"
    out_dir.mkdir(parents=True, exist_ok=True)
    step_path = out_dir / "lego_technic_beam.step"
    svg_path = out_dir / "lego_technic_beam.svg"

    # Single-call exports — extension drives the format (no exportType= needed).
    # Export + path-print logic is duplicated by design — examples are teaching
    # artefacts; see .agents/plans/2026-05-15-examples-directory_design.md Round 1.
    cq.exporters.export(beam.solid, str(step_path))
    cq.exporters.export(beam.solid, str(svg_path))

    # str() = native separators; switch to .as_posix() if cross-platform paste-fidelity matters.
    print(f"STEP: {str(step_path.resolve())}")
    print(f"SVG: {str(svg_path.resolve())}")
