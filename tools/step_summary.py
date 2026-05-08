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
"""Summarise a STEP file: bodies, topology counts, bounding box, volume, centre of mass.

Usage
-----
    python3 tools/step_summary.py <path.step>

Output
------
Plain-text report printed to stdout, suitable for agent consumption.

Example output::

    File: models/servo/SG90.step

    Bodies
      Solids: 1
      Shells: 1

    Topology (all solids combined)
      Faces:    89
      Edges:   236
      Vertices: 150

    Bounding box
      X: [-11.00, 21.40]  span 32.40
      Y: [ -6.30,  6.30]  span 12.60
      Z: [-32.40, -2.00]  span 30.40
      Centre: (5.20, 0.00, -17.20)

    Mass properties
      Volume:   5012.34 mm³
      Centre of mass: (4.87, 0.12, -16.55)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cadquery as cq
import OCP.BRepGProp as bgp
import OCP.GProp as gprop
from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX, TopAbs_WIRE
from OCP.TopExp import TopExp_Explorer


def _count_shapes(occ_shape, shape_type) -> int:
    """Count sub-shapes of a given type via TopExp_Explorer."""
    explorer = TopExp_Explorer(occ_shape, shape_type)
    n = 0
    while explorer.More():
        n += 1
        explorer.Next()
    return n


def summarise_step(path: str | Path) -> dict:
    """Load a STEP file and return a summary dict.

    Keys
    ----
    file : str
        Input file path.
    solids : int
        Number of distinct solid bodies.
    shells : int
        Number of shells.
    faces, edges, vertices : int
        Topology counts across all bodies.
    bbox : dict
        ``{xmin, xmax, ymin, ymax, zmin, zmax, xspan, yspan, zspan,
        cx, cy, cz}``
    volume : float
        Total volume in mm³.
    center_of_mass : dict
        ``{x, y, z}``
    bodies : list[dict]
        Per-body info: ``{index, volume, bbox}`` sorted largest-first.
    """
    path = Path(path)
    wp = cq.importers.importStep(str(path))

    solids = wp.solids().vals()
    shells = wp.shells().vals()
    occ_compound = wp.val().wrapped

    n_faces = _count_shapes(occ_compound, TopAbs_FACE)
    n_edges = _count_shapes(occ_compound, TopAbs_EDGE)
    n_vertices = _count_shapes(occ_compound, TopAbs_VERTEX)
    n_wires = _count_shapes(occ_compound, TopAbs_WIRE)

    # Overall bounding box
    bb = wp.val().BoundingBox()

    # Overall volume + centre of mass
    vol_props = gprop.GProp_GProps()
    bgp.BRepGProp.VolumeProperties_s(occ_compound, vol_props)
    total_volume = vol_props.Mass()
    com = vol_props.CentreOfMass()

    # Per-body info (sorted by volume, largest first)
    bodies = []
    for i, s in enumerate(solids):
        bp = gprop.GProp_GProps()
        bgp.BRepGProp.VolumeProperties_s(s.wrapped, bp)
        sv = bp.Mass()
        sc = bp.CentreOfMass()
        sbb = s.BoundingBox()
        bodies.append({
            "index": i,
            "volume": round(sv, 4),
            "center_of_mass": {
                "x": round(sc.X(), 4),
                "y": round(sc.Y(), 4),
                "z": round(sc.Z(), 4),
            },
            "bbox": {
                "xmin": round(sbb.xmin, 4), "xmax": round(sbb.xmax, 4),
                "ymin": round(sbb.ymin, 4), "ymax": round(sbb.ymax, 4),
                "zmin": round(sbb.zmin, 4), "zmax": round(sbb.zmax, 4),
                "xspan": round(sbb.xlen, 4),
                "yspan": round(sbb.ylen, 4),
                "zspan": round(sbb.zlen, 4),
            },
        })
    bodies.sort(key=lambda b: -b["volume"])

    return {
        "file": str(path),
        "solids": len(solids),
        "shells": len(shells),
        "faces": n_faces,
        "edges": n_edges,
        "wires": n_wires,
        "vertices": n_vertices,
        "bbox": {
            "xmin": round(bb.xmin, 4), "xmax": round(bb.xmax, 4),
            "ymin": round(bb.ymin, 4), "ymax": round(bb.ymax, 4),
            "zmin": round(bb.zmin, 4), "zmax": round(bb.zmax, 4),
            "xspan": round(bb.xlen, 4),
            "yspan": round(bb.ylen, 4),
            "zspan": round(bb.zlen, 4),
            "cx": round(bb.center.x, 4),
            "cy": round(bb.center.y, 4),
            "cz": round(bb.center.z, 4),
        },
        "volume": round(total_volume, 4),
        "center_of_mass": {
            "x": round(com.X(), 4),
            "y": round(com.Y(), 4),
            "z": round(com.Z(), 4),
        },
        "bodies": bodies,
    }


def _format_report(info: dict) -> str:
    """Pretty-print a summary dict as a human-readable report."""
    lines = [f"File: {info['file']}", ""]

    lines.append("Bodies")
    lines.append(f"  Solids: {info['solids']}")
    lines.append(f"  Shells: {info['shells']}")
    lines.append("")

    lines.append("Topology")
    lines.append(f"  Faces:    {info['faces']}")
    lines.append(f"  Wires:    {info['wires']}")
    lines.append(f"  Edges:    {info['edges']}")
    lines.append(f"  Vertices: {info['vertices']}")
    lines.append("")

    bb = info["bbox"]
    lines.append("Bounding box")
    lines.append(f"  X: [{bb['xmin']:8.3f}, {bb['xmax']:8.3f}]  span {bb['xspan']:.3f}")
    lines.append(f"  Y: [{bb['ymin']:8.3f}, {bb['ymax']:8.3f}]  span {bb['yspan']:.3f}")
    lines.append(f"  Z: [{bb['zmin']:8.3f}, {bb['zmax']:8.3f}]  span {bb['zspan']:.3f}")
    lines.append(f"  Centre: ({bb['cx']:.3f}, {bb['cy']:.3f}, {bb['cz']:.3f})")
    lines.append("")

    lines.append("Mass properties")
    lines.append(f"  Volume: {info['volume']:.4f} mm³")
    com = info["center_of_mass"]
    lines.append(f"  Centre of mass: ({com['x']:.3f}, {com['y']:.3f}, {com['z']:.3f})")
    lines.append("")

    if len(info["bodies"]) > 1:
        lines.append(f"Per-body breakdown ({len(info['bodies'])} solids, largest first)")
        for b in info["bodies"]:
            bb2 = b["bbox"]
            c2 = b["center_of_mass"]
            lines.append(
                f"  [{b['index']}]  vol={b['volume']:.2f}  "
                f"size=({bb2['xspan']:.2f} × {bb2['yspan']:.2f} × {bb2['zspan']:.2f})  "
                f"com=({c2['x']:.2f}, {c2['y']:.2f}, {c2['z']:.2f})"
            )
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarise a STEP file: topology, bounding box, volume, centre of mass.",
    )
    parser.add_argument("step_file", help="Path to the .step / .stp file")
    parser.add_argument(
        "--json", action="store_true", help="Output machine-readable JSON instead of text",
    )
    args = parser.parse_args()

    info = summarise_step(args.step_file)

    if args.json:
        print(json.dumps(info, indent=2))
    else:
        print(_format_report(info))


if __name__ == "__main__":
    main()
