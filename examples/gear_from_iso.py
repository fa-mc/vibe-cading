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
"""Example: construct a spur gear from ISO parameters and export STEP + SVG.

Primitive demonstrated: ``SpurGear.from_iso(module, teeth, face_width)``
from ``vibe_cading.mechanical.gears.spur``.  The ``from_iso`` factory
validates ``module`` against the ISO standard-module table (the
``cls`` must be a concrete subclass — ``Gear.from_iso`` would reject
abstract callers) and returns a fully-formed involute spur gear ready
to export.

Run:
    python3 examples/gear_from_iso.py

Outputs (under ``examples/build/gear_from_iso/``):
    - gear_from_iso.step
    - gear_from_iso.svg
"""
from pathlib import Path

import cadquery as cq

from vibe_cading.mechanical.gears.spur import SpurGear


if __name__ == "__main__":
    # module=1.0 mm is the most common ISO benchmark size; teeth=20 shows
    # the involute profile clearly without ballooning runtime; face_width
    # 5.0 mm matches typical Lego-Technic-scale parts.
    gear = SpurGear.from_iso(module=1.0, teeth=20, face_width=5.0)

    # Output goes under examples/build/<name>/ (gitignored — see .gitignore).
    out_dir = Path(__file__).parent / "build" / "gear_from_iso"
    out_dir.mkdir(parents=True, exist_ok=True)
    step_path = out_dir / "gear_from_iso.step"
    svg_path = out_dir / "gear_from_iso.svg"

    # Single-call exports — extension drives the format.
    # Export + path-print logic is duplicated by design — examples are teaching
    # artefacts; see .agents/plans/2026-05-15-examples-directory_design.md Round 1.
    cq.exporters.export(gear.solid, str(step_path))
    cq.exporters.export(gear.solid, str(svg_path))

    # str() = native separators; switch to .as_posix() if cross-platform paste-fidelity matters.
    print(f"STEP: {str(step_path.resolve())}")
    print(f"SVG: {str(svg_path.resolve())}")
