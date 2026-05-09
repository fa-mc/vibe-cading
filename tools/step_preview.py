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

#!/usr/bin/env python3
"""Generate orthographic SVG previews directly from a STEP file.

Mirrors the interface of ``preview.py`` but takes a ``.step`` file as input
instead of a Python model class.  This lets agents visually compare a
reference STEP file against a generated model using identical projections.

Usage
-----
    python3 tools/step_preview.py <path.step>
    python3 tools/step_preview.py <path.step> --views top front left right
    python3 tools/step_preview.py <path.step> --views all --out tmp/ref_preview/

Output
------
One SVG per view written to the output directory, named
``<StemName>_<view>.svg``.  Format is identical to ``preview.py`` output.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cadquery as cq

# Re-use the named-view registry and SVG fixer from preview.py
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from preview import NAMED_VIEWS, DEFAULT_VIEWS, _fix_svg_viewport
from tools.step_primitives import StepLoadError, load_step


def export_step_previews(
    step_path: str | Path,
    out_dir: Path | None = None,
    views: list[str] | None = None,
    stroke_width: float = 0.25,
) -> list[Path]:
    """Export orthographic SVG previews of a STEP file.

    Parameters
    ----------
    step_path : str or Path
        Path to the .step / .stp file.
    out_dir : Path or None
        Output directory.  Defaults to ``tmp/preview/`` in repo root.
    views : list[str] or None
        View names to export.  Defaults to ``DEFAULT_VIEWS``.
        Pass ``["all"]`` for every named view.
    stroke_width : float
        SVG stroke width in mm-space.

    Returns
    -------
    list[Path]
        Paths of written SVG files.
    """
    step_path = Path(step_path)
    if out_dir is None:
        out_dir = REPO_ROOT / "tmp" / "preview"

    requested = views or DEFAULT_VIEWS
    if requested == ["all"]:
        requested = list(NAMED_VIEWS.keys())

    unknown = [v for v in requested if v not in NAMED_VIEWS]
    if unknown:
        raise ValueError(
            f"Unknown view(s): {unknown}.  Available: {list(NAMED_VIEWS.keys())}"
        )

    shape: cq.Shape = load_step(step_path).shape

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = step_path.stem
    written: list[Path] = []

    for view_name in requested:
        proj_dir = NAMED_VIEWS[view_name]
        svg_path = out_dir / f"{stem}_{view_name}.svg"
        cq.exporters.export(
            shape,
            str(svg_path),
            cq.exporters.ExportTypes.SVG,
            opt={
                "projectionDir": proj_dir,
                "showAxes": False,
                "strokeWidth": stroke_width,
                "width": 400,
                "height": 400,
            },
        )
        _fix_svg_viewport(svg_path)
        written.append(svg_path)
        print(f"WROTE {svg_path}")

    return written


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export orthographic SVG previews of a STEP file.",
    )
    parser.add_argument("step_file", help="Path to the .step / .stp file")
    parser.add_argument(
        "--out",
        default=None,
        help="Output directory for SVGs (default: tmp/preview/)",
    )
    parser.add_argument(
        "--views",
        nargs="+",
        default=None,
        metavar="VIEW",
        help=(
            "Views to export (default: top front left).  "
            "Use 'all' for every named view."
        ),
    )
    parser.add_argument(
        "--stroke-width",
        type=float,
        default=0.25,
        help="SVG stroke width (default: 0.25)",
    )
    parser.add_argument(
        "--list-views",
        action="store_true",
        help="Print all available view names and exit.",
    )
    args = parser.parse_args()

    if args.list_views:
        print("Available views:")
        for name, (dx, dy, dz) in NAMED_VIEWS.items():
            print(f"  {name:<14}  dir=({dx:+.0f}, {dy:+.0f}, {dz:+.0f})")
        print(f"\nDefault views: {' '.join(DEFAULT_VIEWS)}")
        return

    out_dir = Path(args.out) if args.out else None
    try:
        export_step_previews(
            args.step_file,
            out_dir=out_dir,
            views=args.views,
            stroke_width=args.stroke_width,
        )
    except StepLoadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
