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
"""
Generic CadQuery model preview exporter.

Exports orthographic SVG previews (top, front, side) of any CadQuery model
class so that agents can read them back and compare against reference drawings
or photos attached to a task.

Usage
-----
    python3 tools/preview.py <module.path.ClassName> [--out DIR] [--params k=v ...]

Arguments
---------
module.path.ClassName
    Dotted import path to the model class, relative to ``models/``.
    E.g.  ``rc.servo.sg90.Sg90Servo``

--out DIR
    Directory to write SVG files into.
    Defaults to ``tmp/preview/`` in the repo root.

--params key=value ...
    Optional constructor keyword arguments (all cast to float).
    E.g.  ``--params body_width=23.0 collar_r=6.5``

Output
------
Prints one ``WROTE <path>`` line per file.  Three SVGs are produced:

    <ClassName>_top.svg    -- plan view (looking down Z)
    <ClassName>_front.svg  -- front elevation (looking along -Y)
    <ClassName>_side.svg   -- side elevation (looking along -X)

Agent usage
-----------
After running this tool, call ``read_file`` on each printed SVG path.
SVG is plain XML: path coordinates are in mm-scale model space.  The
``viewBox`` attribute is set to show the full model without clipping, and
edge ``<path>`` elements let you cross-check geometry against annotated
dimensions in an attached reference image.
"""

from __future__ import annotations

import argparse
import importlib
import re
import sys
from pathlib import Path

import cadquery as cq

REPO_ROOT  = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models"

# Make all model packages importable exactly as build.py does.
sys.path.insert(0, str(MODELS_DIR))

# ── Named view registry ───────────────────────────────────────────────────────
# Each entry is (projection_direction_vector,).  The direction points FROM the
# viewer TOWARD the model (i.e. the camera sits at −dir).
#
# Six orthographic faces
#   top, bottom, front, back, left, right
# Four 45° diagonal elevations (iso = isometric-style, no true isometric projection)
#   iso_ne, iso_nw, iso_se, iso_sw
# Four underside diagonals
#   iso_bot_ne, iso_bot_nw, iso_bot_se, iso_bot_sw
#
NAMED_VIEWS: dict[str, tuple[float, float, float]] = {
    # orthographic faces
    "top":         ( 0,    0,   -1),   # looking down  -Z
    "bottom":      ( 0,    0,    1),   # looking up    +Z
    "front":       ( 0,   -1,    0),   # looking along -Y
    "back":        ( 0,    1,    0),   # looking along +Y
    "left":        (-1,    0,    0),   # looking along -X
    "right":       ( 1,    0,    0),   # looking along +X
    # top 45° diagonals  (from above, four compass quadrants)
    "iso_ne":      ( 1,   -1,   -1),
    "iso_nw":      (-1,   -1,   -1),
    "iso_se":      ( 1,    1,   -1),
    "iso_sw":      (-1,    1,   -1),
    # bottom 45° diagonals (from below, four compass quadrants)
    "iso_bot_ne":  ( 1,   -1,    1),
    "iso_bot_nw":  (-1,   -1,    1),
    "iso_bot_se":  ( 1,    1,    1),
    "iso_bot_sw":  (-1,    1,    1),
}

# Default views used when --views is not specified.
DEFAULT_VIEWS: list[str] = ["top", "front", "left"]


def _fix_svg_viewport(svg_path: Path) -> None:
    """Post-process a CadQuery SVG to add a ``viewBox`` that prevents
    geometry from being clipped by the fixed-size canvas.

    CadQuery's SVG exporter sets ``width``/``height`` but omits ``viewBox``.
    When the affine transform places model geometry outside the pixel canvas
    (common for tall or wide models), those edges are silently clipped.  This
    function computes the actual pixel bounding box of all path data and patches
    the ``<svg>`` element so every edge is visible.
    """
    text = svg_path.read_text(encoding="utf-8")

    # CadQuery writes exactly one <g transform="scale(sx,sy) translate(tx,ty)">
    m = re.search(
        r'transform="scale\(([^,]+),\s*([^)]+)\)\s+translate\(([^,]+),\s*([^)]+)\)"',
        text,
    )
    if not m:
        return

    sx = float(m.group(1))
    sy = float(m.group(2))   # negative → y-axis flip
    tx = float(m.group(3))
    ty = float(m.group(4))

    # Walk all coordinate pairs inside d="..." path attributes.
    path_data = " ".join(re.findall(r'd="([^"]+)"', text))
    pxs: list[float] = []
    pys: list[float] = []
    for xs, ys in re.findall(r"(-?[\d.]+),(-?[\d.]+)", path_data):
        pxs.append(sx * (float(xs) + tx))
        pys.append(sy * (float(ys) + ty))

    if not pxs:
        return

    pad = 10  # pixel padding around content
    vb_x = min(pxs) - pad
    vb_y = min(pys) - pad
    vb_w = max(pxs) - min(pxs) + 2 * pad
    vb_h = max(pys) - min(pys) + 2 * pad

    # Patch width, height, and insert viewBox on the <svg> element.
    text = re.sub(r'width="[^"]+"',  f'width="{vb_w:.0f}"',  text, count=1)
    text = re.sub(r'height="[^"]+"', f'height="{vb_h:.0f}"', text, count=1)
    text = re.sub(
        r"(<svg(?=\s))",
        rf'\1 viewBox="{vb_x:.1f} {vb_y:.1f} {vb_w:.1f} {vb_h:.1f}"',
        text,
        count=1,
    )
    svg_path.write_text(text, encoding="utf-8")


def _parse_params(raw: list[str]) -> dict[str, any]:
    result: dict[str, any] = {}
    for item in raw:
        if "=" not in item:
            raise ValueError(f"--params entries must be key=value, got: {item!r}")
        k, v = item.split("=", 1)
        k = k.strip()
        v = v.strip()
        # Try returning an integer, then a float, otherwise leave as string.
        try:
            val = int(v)
        except ValueError:
            try:
                val = float(v)
            except ValueError:
                val = v
        result[k] = val
    return result


def export_previews(
    model_path: str,
    out_dir: Path,
    params: dict[str, any] | None = None,
    views: list[str] | None = None,
) -> list[Path]:
    """Build *model_path* and write one SVG per view to *out_dir*.

    Parameters
    ----------
    model_path:
        Dotted module + class name, e.g.
        ``"rc.servo.sg90.Sg90Servo"``.
    out_dir:
        Output directory (created if it does not exist).
    params:
        Optional keyword arguments forwarded to the class constructor.
    views:
        List of view names to export.  Each name must be a key in
        ``NAMED_VIEWS``.  Defaults to ``DEFAULT_VIEWS`` when omitted.
        Pass ``["all"]`` as a shortcut to export every named view.

    Returns
    -------
    list[Path]
        Paths of the written SVG files (one per view).
    """
    requested = views or DEFAULT_VIEWS
    if requested == ["all"]:
        requested = list(NAMED_VIEWS.keys())

    unknown = [v for v in requested if v not in NAMED_VIEWS]
    if unknown:
        raise ValueError(
            f"Unknown view(s): {unknown}.  "
            f"Available: {list(NAMED_VIEWS.keys())}"
        )

    module_str, class_name = model_path.rsplit(".", 1)
    module   = importlib.import_module(module_str)
    cls      = getattr(module, class_name)
    instance = cls(**(params or {}))

    shape: cq.Shape = instance.solid.val()

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for view_name in requested:
        proj_dir = NAMED_VIEWS[view_name]
        svg_path = out_dir / f"{class_name}_{view_name}.svg"
        cq.exporters.export(
            shape,
            str(svg_path),
            cq.exporters.ExportTypes.SVG,
            opt={
                "projectionDir": proj_dir,
                "showAxes": False,
                "strokeWidth": 0.25,
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
        description="Export orthographic SVG previews of a CadQuery model class.",
    )
    parser.add_argument(
        "model",
        nargs="?",
        help=(
            "Dotted module.ClassName path relative to models/  "
            "(e.g. rc.servo.sg90.Sg90Servo)"
        ),
    )
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "tmp" / "preview"),
        help="Output directory for SVG files (default: tmp/preview/)",
    )
    parser.add_argument(
        "--params",
        nargs="*",
        default=[],
        metavar="key=value",
        help="Optional constructor keyword arguments (cast to float)",
    )
    parser.add_argument(
        "--views",
        nargs="+",
        default=None,
        metavar="VIEW",
        help=(
            "Views to export (default: top front left).  "
            "Use 'all' to export every named view.  "
            "Run --list-views to see all available names."
        ),
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

    if not args.model:
        parser.error("the following arguments are required: model")

    params = _parse_params(args.params) if args.params else {}
    export_previews(args.model, Path(args.out), params, views=args.views)


if __name__ == "__main__":
    main()
