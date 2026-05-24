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
"""Example: cut an M3 counterbore into a host block via tolerance profile.

Primitive demonstrated: ``MetricMachineScrew.to_cutter(profile=..., fit=...)``
from ``vibe_cading.mechanical.screws.metric`` combined with
``get_profile("fdm_standard")`` from ``vibe_cading.print_settings``.  A
plain CadQuery host block becomes a fastener mount when the screw's
boolean cutter is subtracted from it — this is the canonical
"compose a part with library hardware" pattern.

Run:
    python3 examples/screw_cutter.py

Outputs (under ``examples/build/screw_cutter/``):
    - screw_cutter.step
    - screw_cutter.svg
"""
from pathlib import Path

import cadquery as cq

from vibe_cading.mechanical.screws.metric import MetricMachineScrew
from vibe_cading.print_settings import get_profile


if __name__ == "__main__":
    # Host block: 15 x 15 x 6 mm, top face at Z=6, bottom at Z=0.
    # Walls ~ (15 - 5.5) / 2 ~= 4.75 mm around the M3 counterbore — see
    # design's Known Risks for the wall-thickness reasoning.
    host = cq.Workplane("XY").box(15, 15, 6, centered=(True, True, False))

    # Build the screw and request its boolean cutter.  Hard-coded
    # "fdm_standard" for reproducibility across contributors; in production
    # code, call get_profile() with no arg to read VIBE_PRINT_PROFILE
    # from .env.  fit="clearance" gives the through-hole the shaft inflates
    # into per the project's free-fit tolerance.
    screw = MetricMachineScrew.from_size("M3", length=10, head_type="socket")
    cutter = screw.to_cutter(profile=get_profile("fdm_standard"), fit="clearance")

    # Cutter native origin: counterbore mouth at Z=0, shaft descending into -Z.
    # Translate so the mouth lands at the host's top face (Z=6); shaft punches
    # through and exits the bottom (length=10 > host depth=6, intentional
    # demonstration of the project's Infinite Cutter Overcuts rule).
    result = host.cut(cutter.translate((0, 0, 6)))

    # Output goes under examples/build/<name>/ (gitignored — see .gitignore).
    out_dir = Path(__file__).parent / "build" / "screw_cutter"
    out_dir.mkdir(parents=True, exist_ok=True)
    step_path = out_dir / "screw_cutter.step"
    svg_path = out_dir / "screw_cutter.svg"

    # Single-call exports — extension drives the format.
    # Export + path-print logic is duplicated by design — examples are teaching
    # artefacts; see .agents/plans/2026-05-15-examples-directory_design.md Round 1.
    cq.exporters.export(result, str(step_path))
    cq.exporters.export(result, str(svg_path))

    # str() = native separators; switch to .as_posix() if cross-platform paste-fidelity matters.
    print(f"STEP: {str(step_path.resolve())}")
    print(f"SVG: {str(svg_path.resolve())}")
