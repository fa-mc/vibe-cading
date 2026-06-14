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
"""Slice a STEP file at one or more planes, export cross-section profiles as SVG.

Usage
-----
    python3 tools/section_slicer.py <path.step> --axis Z --at 10 17 23
    python3 tools/section_slicer.py <path.step> --axis Y --at 0 --out tmp/sections/
    python3 tools/section_slicer.py <path.step> --axis Z --sweep 5     # every 5 mm
    python3 tools/section_slicer.py <path.step> --axis Z --at 10 --report  # + geometry table

Output
------
One SVG per slice written to the output directory.  The SVG shows the 2D
cross-section profile projected onto the slice plane, with coordinates in mm.

Each SVG is a clean line drawing that agents can read back to understand
internal geometry (pockets, ribs, wall thicknesses).
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GeomAbs import (
    GeomAbs_Line,
    GeomAbs_Circle,
    GeomAbs_Ellipse,
    GeomAbs_BSplineCurve,
    GeomAbs_BezierCurve,
)

# Ensure the repo root is on sys.path so the absolute import below resolves
# when this script is run directly (python vibe_cading/tools/<name>.py) without
# an installed package / PYTHONPATH.  Mirrors boolean_diff.py.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from vibe_cading.tools.step_primitives import StepLoadError, load_step  # noqa: E402


# Axis label → (normal direction, projection axes for 2D SVG)
_AXIS_CONFIG = {
    "X": (gp_Dir(1, 0, 0), ("Y", "Z"), lambda p: (p.Y(), p.Z())),
    "Y": (gp_Dir(0, 1, 0), ("X", "Z"), lambda p: (p.X(), p.Z())),
    "Z": (gp_Dir(0, 0, 1), ("X", "Y"), lambda p: (p.X(), p.Y())),
}


def _sample_edge_points(edge, n_samples: int = 40) -> list[tuple[float, float, float]]:
    """Sample *n_samples* points along an edge using BRepAdaptor_Curve."""
    adaptor = BRepAdaptor_Curve(edge)
    t0 = adaptor.FirstParameter()
    t1 = adaptor.LastParameter()
    pts = []
    for i in range(n_samples + 1):
        t = t0 + (t1 - t0) * i / n_samples
        p = adaptor.Value(t)
        pts.append((p.X(), p.Y(), p.Z()))
    return pts


def _build_section_shape(occ_solid, axis: str, position: float):
    """Build a cross-section of *occ_solid* at *position* along *axis*.

    Returns the raw OCC result shape, or ``None`` if the section failed.
    """
    normal, _, _ = _AXIS_CONFIG[axis]
    origin = gp_Pnt(
        position if axis == "X" else 0.0,
        position if axis == "Y" else 0.0,
        position if axis == "Z" else 0.0,
    )
    sec = BRepAlgoAPI_Section(occ_solid, gp_Pln(origin, normal))
    sec.Build()
    return sec.Shape() if sec.IsDone() else None


def _polylines_from_shape(
    result_shape, axis: str
) -> list[list[tuple[float, float]]]:
    """Convert a section result shape to a list of 2D polylines."""
    explorer = TopExp_Explorer(result_shape, TopAbs_EDGE)
    polylines: list[list[tuple[float, float]]] = []
    while explorer.More():
        edge = TopoDS.Edge_s(explorer.Current())
        pts_3d = _sample_edge_points(edge)
        if axis == "Z":
            pts_2d = [(p[0], p[1]) for p in pts_3d]
        elif axis == "Y":
            pts_2d = [(p[0], p[2]) for p in pts_3d]
        else:  # X
            pts_2d = [(p[1], p[2]) for p in pts_3d]
        polylines.append(pts_2d)
        explorer.Next()
    return polylines


def _section_at(occ_solid, axis: str, position: float) -> list[list[tuple[float, float]]]:
    """Cut the solid at a plane and return 2D polyline profiles.

    Returns a list of polylines, each a list of (u, v) tuples in the
    cross-section's 2D coordinate system.
    """
    result_shape = _build_section_shape(occ_solid, axis, position)
    if result_shape is None:
        return []
    return _polylines_from_shape(result_shape, axis)


def _analyse_section_edges(result_shape, axis: str) -> list[dict]:
    """Return geometric info for each edge in a section result shape.

    Each dict has at minimum a ``type`` key.  Additional keys per type:

    * ``circle``  → ``radius``, ``diameter``, ``centre`` (2D tuple)
    * ``line``    → ``length``, ``start``, ``end`` (2D tuples)
    * ``ellipse`` → ``major_r``, ``minor_r``, ``centre`` (2D tuple)
    * other types → ``type`` string only
    """
    _to_2d = {
        "Z": lambda p: (round(p.X(), 3), round(p.Y(), 3)),
        "Y": lambda p: (round(p.X(), 3), round(p.Z(), 3)),
        "X": lambda p: (round(p.Y(), 3), round(p.Z(), 3)),
    }[axis]

    explorer = TopExp_Explorer(result_shape, TopAbs_EDGE)
    edges_info: list[dict] = []
    while explorer.More():
        edge = TopoDS.Edge_s(explorer.Current())
        adaptor = BRepAdaptor_Curve(edge)
        ctype = adaptor.GetType()

        if ctype == GeomAbs_Circle:
            circle = adaptor.Circle()
            r = circle.Radius()
            info: dict = {
                "type": "circle",
                "radius": round(r, 3),
                "diameter": round(r * 2, 3),
                "centre": _to_2d(circle.Location()),
            }
        elif ctype == GeomAbs_Line:
            p0 = adaptor.Value(adaptor.FirstParameter())
            p1 = adaptor.Value(adaptor.LastParameter())
            length = math.sqrt(
                (p1.X() - p0.X()) ** 2
                + (p1.Y() - p0.Y()) ** 2
                + (p1.Z() - p0.Z()) ** 2
            )
            info = {
                "type": "line",
                "length": round(length, 3),
                "start": _to_2d(p0),
                "end": _to_2d(p1),
            }
        elif ctype == GeomAbs_Ellipse:
            ell = adaptor.Ellipse()
            info = {
                "type": "ellipse",
                "major_r": round(ell.MajorRadius(), 3),
                "minor_r": round(ell.MinorRadius(), 3),
                "centre": _to_2d(ell.Location()),
            }
        else:
            type_names = {
                GeomAbs_BSplineCurve: "bspline",
                GeomAbs_BezierCurve: "bezier",
            }
            info = {"type": type_names.get(ctype, f"curve({int(ctype)})")}

        edges_info.append(info)
        explorer.Next()
    return edges_info


def _polylines_to_svg(
    polylines: list[list[tuple[float, float]]],
    u_label: str,
    v_label: str,
    title: str = "",
    stroke_width: float = 0.15,
) -> str:
    """Render polylines as an SVG string.

    The SVG uses mm-scale coordinates with a viewBox fitted to the content.
    """
    if not polylines:
        return '<svg xmlns="http://www.w3.org/2000/svg"><text x="10" y="20">No section geometry</text></svg>'

    # Compute bounding box
    all_u = [p[0] for poly in polylines for p in poly]
    all_v = [p[1] for poly in polylines for p in poly]
    u_min, u_max = min(all_u), max(all_u)
    v_min, v_max = min(all_v), max(all_v)

    pad = max((u_max - u_min), (v_max - v_min)) * 0.08 + 1.0
    vb_x = u_min - pad
    vb_y = -(v_max + pad)  # SVG Y is flipped
    vb_w = (u_max - u_min) + 2 * pad
    vb_h = (v_max - v_min) + 2 * pad

    # SVG header
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{max(400, vb_w * 8):.0f}" height="{max(400, vb_h * 8):.0f}" '
        f'viewBox="{vb_x:.4f} {vb_y:.4f} {vb_w:.4f} {vb_h:.4f}">',
        f'<title>{title}</title>',
        '<style>path {{ fill: none; stroke: #000; stroke-width: {sw}; stroke-linecap: round; }}</style>'.format(sw=stroke_width),
    ]

    # Draw origin crosshair
    ch = pad * 0.3
    svg_lines.append(
        f'<line x1="{-ch:.3f}" y1="0" x2="{ch:.3f}" y2="0" '
        f'stroke="#ccc" stroke-width="{stroke_width * 0.5:.3f}"/>'
    )
    svg_lines.append(
        f'<line x1="0" y1="{-ch:.3f}" x2="0" y2="{ch:.3f}" '
        f'stroke="#ccc" stroke-width="{stroke_width * 0.5:.3f}"/>'
    )

    # Draw polylines
    for poly in polylines:
        if len(poly) < 2:
            continue
        d_parts = [f"M {poly[0][0]:.4f},{-poly[0][1]:.4f}"]
        for p in poly[1:]:
            d_parts.append(f"L {p[0]:.4f},{-p[1]:.4f}")
        svg_lines.append(f'<path d="{" ".join(d_parts)}"/>')

    # Axis labels
    font_size = min(vb_w, vb_h) * 0.06
    svg_lines.append(
        f'<text x="{u_max + pad * 0.3:.3f}" y="{-((v_min + v_max) / 2):.3f}" '
        f'font-size="{font_size:.2f}" fill="#888">{u_label}</text>'
    )
    svg_lines.append(
        f'<text x="{(u_min + u_max) / 2:.3f}" y="{-(v_max + pad * 0.3):.3f}" '
        f'font-size="{font_size:.2f}" fill="#888">{v_label}</text>'
    )

    svg_lines.append("</svg>")
    return "\n".join(svg_lines)


def slice_step(
    path: str | Path,
    axis: str = "Z",
    positions: list[float] | None = None,
    sweep: float | None = None,
    out_dir: str | Path = "tmp/sections",
    report: bool = False,
) -> list[Path]:
    """Slice a STEP file and write SVG cross-sections.

    Parameters
    ----------
    path : str or Path
        STEP file to slice.
    axis : str
        Axis perpendicular to the slice plane: 'X', 'Y', or 'Z'.
    positions : list[float] or None
        Explicit slice positions along *axis*.  Mutually exclusive with *sweep*.
    sweep : float or None
        If set, slice every *sweep* mm through the bounding box extent.
    out_dir : str or Path
        Output directory for SVG files.
    report : bool
        If ``True``, print a table of edge geometry (circle radii and centres,
        line lengths) for each slice immediately after the WROTE line.

    Returns
    -------
    list[Path]
        Paths of written SVG files.
    """
    path = Path(path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    loaded = load_step(path)
    solid = loaded.occ_compound
    bb = loaded.shape.BoundingBox()

    # Determine slice positions
    axis = axis.upper()
    if axis == "X":
        lo, hi = bb.xmin, bb.xmax
    elif axis == "Y":
        lo, hi = bb.ymin, bb.ymax
    else:
        lo, hi = bb.zmin, bb.zmax

    if positions is not None:
        pos_list = positions
    elif sweep is not None:
        # Generate positions from lo to hi at sweep intervals
        pos_list = []
        p = lo + sweep / 2
        while p < hi:
            pos_list.append(round(p, 4))
            p += sweep
    else:
        # Default: three slices at 25%, 50%, 75%
        span = hi - lo
        pos_list = [
            round(lo + span * 0.25, 4),
            round(lo + span * 0.50, 4),
            round(lo + span * 0.75, 4),
        ]

    _, (u_label, v_label), _ = _AXIS_CONFIG[axis]
    _ax_labels = {"Z": ("X", "Y"), "Y": ("X", "Z"), "X": ("Y", "Z")}
    u_ax, v_ax = _ax_labels[axis]
    stem = path.stem
    written: list[Path] = []

    for pos in pos_list:
        result_shape = _build_section_shape(solid, axis, pos)
        polylines = _polylines_from_shape(result_shape, axis) if result_shape is not None else []
        title = f"{stem} section {axis}={pos:.2f}"
        svg = _polylines_to_svg(polylines, u_label, v_label, title=title)

        fname = f"{stem}_section_{axis}_{pos:.2f}.svg"
        svg_path = out_dir / fname
        svg_path.write_text(svg, encoding="utf-8")
        written.append(svg_path)
        print(f"WROTE {svg_path}  ({len(polylines)} edges)")

        if report and result_shape is not None:
            edge_data = _analyse_section_edges(result_shape, axis)
            print(f"  {axis} = {pos:+.3f}  ({len(edge_data)} edges)")
            for e in edge_data:
                if e["type"] == "circle":
                    cx, cy = e["centre"]
                    print(
                        f"    circle   \u00d8 {e['diameter']:.3f}  R={e['radius']:.3f}  "
                        f"centre=({u_ax}={cx:.3f}, {v_ax}={cy:.3f})"
                    )
                elif e["type"] == "line":
                    sx, sy = e["start"]
                    ex2, ey2 = e["end"]
                    print(
                        f"    line     len={e['length']:.3f}  "
                        f"({sx:.3f},{sy:.3f})\u2192({ex2:.3f},{ey2:.3f})"
                    )
                elif e["type"] == "ellipse":
                    cx, cy = e["centre"]
                    print(
                        f"    ellipse  a={e['major_r']:.3f} b={e['minor_r']:.3f}  "
                        f"centre=({u_ax}={cx:.3f}, {v_ax}={cy:.3f})"
                    )
                else:
                    print(f"    {e['type']}")

    return written


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Slice a STEP file and export cross-section SVGs.",
    )
    parser.add_argument("step_file", help="Path to the .step / .stp file")
    parser.add_argument("--axis", default="Z", choices=["X", "Y", "Z"], help="Slice axis (default: Z)")
    parser.add_argument("--at", nargs="+", type=float, default=None, metavar="POS", help="Explicit slice positions along the axis")
    parser.add_argument("--sweep", type=float, default=None, help="Slice every N mm through the bounding box")
    parser.add_argument("--out", default="tmp/sections", help="Output directory (default: tmp/sections/)")
    parser.add_argument("--report", action="store_true", help="Print a table of edge geometry (radii, centres) for each slice")
    args = parser.parse_args()

    if args.at and args.sweep:
        parser.error("--at and --sweep are mutually exclusive")

    try:
        slice_step(
            args.step_file,
            axis=args.axis,
            positions=args.at,
            sweep=args.sweep,
            out_dir=args.out,
            report=args.report,
        )
    except StepLoadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
