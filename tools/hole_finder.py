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
"""Detect cylindrical holes and bosses in a STEP file.

Usage
-----
    python3 tools/hole_finder.py <path.step>
    python3 tools/hole_finder.py <path.step> --grid 8.0       # check Lego grid alignment
    python3 tools/hole_finder.py <path.step> --type holes      # only holes (concave)
    python3 tools/hole_finder.py <path.step> --type bosses     # only bosses (convex)

Algorithm
---------
1. Find all cylindrical faces.
2. Group coaxial cylinders (same axis + location within tolerance).
3. For each group determine if the feature is a **hole** (concave → material
   removed) or a **boss** (convex → material added) by checking the face
   orientation relative to the surface normal.
4. Compute depth from the axial extent of the group.
5. Optionally report distance to the nearest grid point.

Output
------
Table or JSON with: diameter, depth, axis, center, type (hole/boss),
and optional grid-alignment info.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cadquery as cq
import OCP.BRepAdaptor as ba
import OCP.BRepGProp as bgp
import OCP.GeomAbs as ga
import OCP.GProp as gprop
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_FORWARD, TopAbs_REVERSED


def _vec3(gp_obj) -> dict:
    return {"x": round(gp_obj.X(), 4), "y": round(gp_obj.Y(), 4), "z": round(gp_obj.Z(), 4)}


def _face_area(occ_face) -> float:
    props = gprop.GProp_GProps()
    bgp.BRepGProp.SurfaceProperties_s(occ_face, props)
    return props.Mass()


def _coaxial(a_loc, a_dir, b_loc, b_dir, tol: float = 0.1, ang_tol: float = 0.01) -> bool:
    """Return True if two axes are coaxial (same line in space) within tolerance."""
    # Check parallel (or anti-parallel)
    dot = abs(a_dir.X() * b_dir.X() + a_dir.Y() * b_dir.Y() + a_dir.Z() * b_dir.Z())
    if dot < 1.0 - ang_tol:
        return False
    # Check distance between axis lines
    dx = b_loc.X() - a_loc.X()
    dy = b_loc.Y() - a_loc.Y()
    dz = b_loc.Z() - a_loc.Z()
    # Cross product of (b_loc - a_loc) with a_dir
    cx = dy * a_dir.Z() - dz * a_dir.Y()
    cy = dz * a_dir.X() - dx * a_dir.Z()
    cz = dx * a_dir.Y() - dy * a_dir.X()
    dist = math.sqrt(cx * cx + cy * cy + cz * cz)
    return dist < tol


def find_cylindrical_features(path: str | Path, grid: float | None = None) -> list[dict]:
    """Detect holes and bosses in a STEP file.

    Parameters
    ----------
    path : str or Path
        STEP file to analyse.
    grid : float or None
        If set, report distance to the nearest grid point for each feature
        centre (projected onto the plane perpendicular to the feature axis).

    Returns
    -------
    list[dict]
        Each dict has keys: ``diameter``, ``radius``, ``depth``, ``axis``,
        ``center``, ``feature_type`` ("hole" or "boss"), ``face_indices``,
        ``area``.  If *grid* is set, adds ``grid_offset``.
    """
    wp = cq.importers.importStep(str(path))
    all_faces = wp.faces().vals()

    # Collect cylindrical faces with geometry
    cyl_faces: list[dict] = []
    for i, f in enumerate(all_faces):
        adaptor = ba.BRepAdaptor_Surface(f.wrapped)
        if adaptor.GetType() != ga.GeomAbs_SurfaceType.GeomAbs_Cylinder:
            continue
        cyl = adaptor.Cylinder()
        orientation = f.wrapped.Orientation()
        area = _face_area(f.wrapped)
        # Skip tiny fillet cylinders
        if area < 0.5:
            continue
        cyl_faces.append({
            "index": i,
            "radius": cyl.Radius(),
            "axis_dir": cyl.Axis().Direction(),
            "axis_loc": cyl.Location(),
            "orientation": orientation,
            "area": area,
            "cq_face": f,
        })

    # Group coaxial cylinders with the same radius
    groups: list[list[dict]] = []
    used = set()
    for i, cf in enumerate(cyl_faces):
        if i in used:
            continue
        group = [cf]
        used.add(i)
        for j, cf2 in enumerate(cyl_faces):
            if j in used:
                continue
            if abs(cf["radius"] - cf2["radius"]) < 0.05 and _coaxial(
                cf["axis_loc"], cf["axis_dir"],
                cf2["axis_loc"], cf2["axis_dir"],
            ):
                group.append(cf2)
                used.add(j)
        groups.append(group)

    # Also include ungrouped single-face cylinders (already in groups of 1)

    features: list[dict] = []
    for group in groups:
        radius = group[0]["radius"]
        axis_dir = group[0]["axis_dir"]
        axis_loc = group[0]["axis_loc"]

        # Determine axial extent from bounding boxes projected onto axis
        z_vals: list[float] = []
        total_area = 0.0
        for cf in group:
            bb = cf["cq_face"].BoundingBox()
            # Project bbox corners onto axis direction
            for pt in [
                (bb.xmin, bb.ymin, bb.zmin), (bb.xmax, bb.ymax, bb.zmax),
                (bb.xmin, bb.ymin, bb.zmax), (bb.xmax, bb.ymax, bb.zmin),
            ]:
                proj = (
                    (pt[0] - axis_loc.X()) * axis_dir.X()
                    + (pt[1] - axis_loc.Y()) * axis_dir.Y()
                    + (pt[2] - axis_loc.Z()) * axis_dir.Z()
                )
                z_vals.append(proj)
            total_area += cf["area"]

        depth = max(z_vals) - min(z_vals) if z_vals else 0.0
        mid_z = (max(z_vals) + min(z_vals)) / 2 if z_vals else 0.0

        # Centre point along axis at midpoint
        cx = axis_loc.X() + axis_dir.X() * mid_z
        cy = axis_loc.Y() + axis_dir.Y() * mid_z
        cz = axis_loc.Z() + axis_dir.Z() * mid_z

        # Determine hole vs boss from face orientation:
        # FORWARD orientation with outward normal → boss (convex)
        # REVERSED orientation → hole (concave)
        # Heuristic: majority vote across faces in group
        hole_votes = sum(
            1 for cf in group
            if cf["orientation"] == TopAbs_REVERSED
        )
        boss_votes = len(group) - hole_votes
        feature_type = "hole" if hole_votes >= boss_votes else "boss"

        entry: dict = {
            "diameter": round(2 * radius, 4),
            "radius": round(radius, 4),
            "depth": round(depth, 4),
            "axis": _vec3(axis_dir),
            "center": {"x": round(cx, 4), "y": round(cy, 4), "z": round(cz, 4)},
            "feature_type": feature_type,
            "face_count": len(group),
            "face_indices": [cf["index"] for cf in group],
            "area": round(total_area, 4),
        }

        if grid is not None and grid > 0:
            # Project centre onto the plane perpendicular to axis and
            # compute distance to nearest grid point.
            # Use the two axes perpendicular to the cylinder axis.
            # For simplicity, project onto XY / XZ / YZ based on dominant axis.
            ad = axis_dir
            ax_abs = (abs(ad.X()), abs(ad.Y()), abs(ad.Z()))
            # Choose the two coordinates perpendicular to the dominant axis direction
            if ax_abs[2] >= ax_abs[0] and ax_abs[2] >= ax_abs[1]:
                # Axis ~Z → grid in XY
                gx = round(cx / grid) * grid
                gy = round(cy / grid) * grid
                offset = math.sqrt((cx - gx) ** 2 + (cy - gy) ** 2)
                entry["grid_nearest"] = {"x": round(gx, 4), "y": round(gy, 4)}
            elif ax_abs[1] >= ax_abs[0]:
                # Axis ~Y → grid in XZ
                gx = round(cx / grid) * grid
                gz = round(cz / grid) * grid
                offset = math.sqrt((cx - gx) ** 2 + (cz - gz) ** 2)
                entry["grid_nearest"] = {"x": round(gx, 4), "z": round(gz, 4)}
            else:
                # Axis ~X → grid in YZ
                gy = round(cy / grid) * grid
                gz = round(cz / grid) * grid
                offset = math.sqrt((cy - gy) ** 2 + (cz - gz) ** 2)
                entry["grid_nearest"] = {"y": round(gy, 4), "z": round(gz, 4)}
            entry["grid_offset"] = round(offset, 4)

        features.append(entry)

    # Sort by diameter descending, then depth descending
    features.sort(key=lambda f: (-f["diameter"], -f["depth"]))
    return features


def _format_table(features: list[dict]) -> str:
    lines: list[str] = []
    lines.append(
        f"{'#':>3}  {'Type':5s}  {'Dia':>8}  {'Depth':>8}  "
        f"{'Axis':>20}  {'Centre':>28}  {'Faces':>5}  {'Grid':>8}"
    )
    lines.append("-" * 100)

    for i, f in enumerate(features):
        a = f["axis"]
        c = f["center"]
        axis_s = f"({a['x']:+.2f},{a['y']:+.2f},{a['z']:+.2f})"
        ctr_s = f"({c['x']:7.2f},{c['y']:7.2f},{c['z']:7.2f})"
        grid_s = f"{f['grid_offset']:.3f}" if "grid_offset" in f else ""
        lines.append(
            f"{i:3d}  {f['feature_type']:5s}  {f['diameter']:8.3f}  {f['depth']:8.3f}  "
            f"{axis_s:>20}  {ctr_s:>28}  {f['face_count']:5d}  {grid_s:>8}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect holes and bosses in a STEP file.",
    )
    parser.add_argument("step_file", help="Path to the .step / .stp file")
    parser.add_argument("--grid", type=float, default=None, help="Grid spacing for alignment check (e.g. 8.0 for Lego)")
    parser.add_argument("--type", choices=["holes", "bosses", "all"], default="all", help="Filter feature type")
    parser.add_argument("--min-dia", type=float, default=0.0, help="Minimum diameter to report (mm)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    features = find_cylindrical_features(args.step_file, grid=args.grid)

    if args.type == "holes":
        features = [f for f in features if f["feature_type"] == "hole"]
    elif args.type == "bosses":
        features = [f for f in features if f["feature_type"] == "boss"]

    if args.min_dia > 0:
        features = [f for f in features if f["diameter"] >= args.min_dia]

    if args.json:
        print(json.dumps(features, indent=2))
    else:
        print(f"Cylindrical features in: {args.step_file}")
        print(f"Found {len(features)} feature(s)")
        if args.grid:
            print(f"Grid alignment check: {args.grid} mm")
        print()
        print(_format_table(features))


if __name__ == "__main__":
    main()
