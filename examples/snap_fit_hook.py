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
"""Example: build a cantilever snap-fit hook + matching host-block cavity.

Primitive demonstrated: ``CantileverSnapFit`` from
``vibe_cading.mechanical.joints.snap_fit`` — both ``.male()`` (the
hook to print) and ``.to_cutter()`` (the matching cavity, subtracted
from a host block).  Two distinct physical parts → two STEP files
per the design's FR14.

Run:
    python3 examples/snap_fit_hook.py

Outputs (under ``examples/build/snap_fit_hook/``):
    - hook.step  / hook.svg   (the printable male hook)
    - host.step  / host.svg   (the host block with cavity cut)
"""
from pathlib import Path

import cadquery as cq

from vibe_cading.mechanical.joints.snap_fit import CantileverSnapFit


if __name__ == "__main__":
    # length=10 (Z-height of beam), hook_depth=1.5 (X-protrusion of catch).
    joint = CantileverSnapFit(length=10, hook_depth=1.5)

    # Male hook — print this, snap it into the host.
    hook = joint.male()

    # Host block: 10 x 10 x 16 mm; cut the cavity directly at the
    # joint's native (0,0,0) origin.  The cutter's entry overcut
    # (_CUTTER_ENTRY_OVERLAP = 1.0) automatically punches through
    # the host's bottom face (Z=0) so the cavity opens cleanly.
    host = (
        cq.Workplane("XY")
        .box(10, 10, 16, centered=(True, True, False))
        .cut(joint.to_cutter())
    )

    # Output goes under examples/build/<name>/ (gitignored — see .gitignore).
    out_dir = Path(__file__).parent / "build" / "snap_fit_hook"
    out_dir.mkdir(parents=True, exist_ok=True)
    hook_step = out_dir / "hook.step"
    hook_svg = out_dir / "hook.svg"
    host_step = out_dir / "host.step"
    host_svg = out_dir / "host.svg"

    # Single-call exports per artefact — extension drives the format.
    # Export + path-print logic is duplicated by design — examples are teaching
    # artefacts; see .agents/plans/2026-05-15-examples-directory_design.md Round 1.
    cq.exporters.export(hook, str(hook_step))
    cq.exporters.export(hook, str(hook_svg))
    cq.exporters.export(host, str(host_step))
    cq.exporters.export(host, str(host_svg))

    # str() = native separators; switch to .as_posix() if cross-platform paste-fidelity matters.
    print(f"STEP: {str(hook_step.resolve())}")
    print(f"SVG: {str(hook_svg.resolve())}")
    print(f"STEP: {str(host_step.resolve())}")
    print(f"SVG: {str(host_svg.resolve())}")
