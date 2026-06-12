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
"""Compute distances between parallel planar faces in a STEP file.

Detects wall thicknesses, slot widths, tab heights, and other parametric
dimensions by finding all pairs of parallel planar faces and reporting
the perpendicular distance between them.

Usage
-----
    python3 tools/face_distances.py <path.step>
    python3 tools/face_distances.py <path.step> --max-dist 10
    python3 tools/face_distances.py <path.step> --axis Z          # only Z-normal faces
    python3 tools/face_distances.py <path.step> --unique           # deduplicated dims

Output
------
Table or JSON listing each pair of parallel planar faces with:
  - face indices, normals, origin Z (or projected position)
  - perpendicular distance between the planes
  - classification hint (wall, slot, step, …)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import OCP.BRepAdaptor as ba
import OCP.GeomAbs as ga

from vibe_cading.tools.step_primitives import StepLoadError, face_area, load_step, vec3


def _dot(a: dict, b: dict) -> float:
    return a["x"] * b["x"] + a["y"] * b["y"] + a["z"] * b["z"]


def _dominant_axis(normal: dict) -> str:
    """Return 'X', 'Y', or 'Z' for the dominant component of a normal."""
    ax = abs(normal["x"])
    ay = abs(normal["y"])
    az = abs(normal["z"])
    if az >= ax and az >= ay:
        return "Z"
    if ay >= ax:
        return "Y"
    return "X"


def find_face_distances(
    path: str | Path,
    max_dist: float | None = None,
    axis_filter: str | None = None,
    angle_tol: float = 0.01,
) -> list[dict]:
    """Find perpendicular distances between parallel planar faces.

    Parameters
    ----------
    path : str or Path
        STEP file to analyse.
    max_dist : float or None
        If set, only return pairs closer than this distance.
    axis_filter : str or None
        If set to 'X', 'Y', or 'Z', only consider faces whose normal
        is aligned with that axis.
    angle_tol : float
        Tolerance for considering two normals as parallel (dot product ≥ 1 - tol).

    Returns
    -------
    list[dict]
        Each dict: ``{face_a, face_b, normal, distance, area_a, area_b, axis}``.
    """
    all_faces = load_step(path).wp.faces().vals()

    # Collect planar faces
    planes: list[dict] = []
    for i, f in enumerate(all_faces):
        adaptor = ba.BRepAdaptor_Surface(f.wrapped)
        if adaptor.GetType() != ga.GeomAbs_SurfaceType.GeomAbs_Plane:
            continue
        pln = adaptor.Plane()
        normal = vec3(pln.Axis().Direction())
        origin = vec3(pln.Location())
        area = face_area(f.wrapped)

        # Skip tiny faces (fillets etc.)
        if area < 0.1:
            continue

        # Axis filter
        if axis_filter:
            dom = _dominant_axis(normal)
            if dom != axis_filter.upper():
                continue

        # Signed distance from world origin to the plane
        # d = normal · origin
        d = _dot(normal, origin)

        planes.append({
            "index": i,
            "normal": normal,
            "origin": origin,
            "signed_d": d,
            "area": area,
        })

    # Find all parallel pairs
    pairs: list[dict] = []
    seen = set()
    for i, pa in enumerate(planes):
        for j, pb in enumerate(planes):
            if j <= i:
                continue
            pair_key = (pa["index"], pb["index"])
            if pair_key in seen:
                continue

            # Check parallel: normals parallel or anti-parallel
            dot = _dot(pa["normal"], pb["normal"])
            if abs(abs(dot) - 1.0) > angle_tol:
                continue

            # Perpendicular distance between the two planes
            # For parallel planes, distance = |d_a - d_b| when normals
            # point the same way, or |d_a + d_b| when anti-parallel.
            if dot > 0:
                dist = abs(pa["signed_d"] - pb["signed_d"])
            else:
                dist = abs(pa["signed_d"] + pb["signed_d"])

            if dist < 0.001:
                continue  # Same plane (coplanar faces)

            if max_dist is not None and dist > max_dist:
                continue

            seen.add(pair_key)
            axis = _dominant_axis(pa["normal"])
            pairs.append({
                "face_a": pa["index"],
                "face_b": pb["index"],
                "distance": round(dist, 4),
                "normal": pa["normal"],
                "axis": axis,
                "area_a": round(pa["area"], 4),
                "area_b": round(pb["area"], 4),
                "origin_a": pa["origin"],
                "origin_b": pb["origin"],
            })

    pairs.sort(key=lambda p: p["distance"])
    return pairs


def unique_distances(pairs: list[dict], tolerance: float = 0.05) -> list[dict]:
    """Deduplicate distances, keeping one representative per unique value.

    Returns a list of ``{distance, count, axis, example_faces}`` sorted
    by distance.
    """
    buckets: list[dict] = []
    for p in sorted(pairs, key=lambda p: p["distance"]):
        d = p["distance"]
        merged = False
        for b in buckets:
            if abs(b["distance"] - d) < tolerance:
                b["count"] += 1
                b["examples"].append((p["face_a"], p["face_b"]))
                merged = True
                break
        if not merged:
            buckets.append({
                "distance": d,
                "count": 1,
                "axis": p["axis"],
                "examples": [(p["face_a"], p["face_b"])],
            })

    result = []
    for b in buckets:
        result.append({
            "distance": round(b["distance"], 4),
            "count": b["count"],
            "axis": b["axis"],
            "example_faces": b["examples"][:3],  # keep up to 3 examples
        })
    return result


def _format_table(pairs: list[dict]) -> str:
    lines: list[str] = []
    lines.append(f"{'#':>3}  {'Face A':>6}  {'Face B':>6}  {'Dist':>8}  {'Axis':>4}  {'Area A':>8}  {'Area B':>8}")
    lines.append("-" * 60)
    for i, p in enumerate(pairs):
        lines.append(
            f"{i:3d}  {p['face_a']:6d}  {p['face_b']:6d}  "
            f"{p['distance']:8.3f}  {p['axis']:>4}  "
            f"{p['area_a']:8.2f}  {p['area_b']:8.2f}"
        )
    return "\n".join(lines)


def _format_unique(uniq: list[dict]) -> str:
    lines: list[str] = []
    lines.append(f"{'Dist':>8}  {'Count':>5}  {'Axis':>4}  Example face pairs")
    lines.append("-" * 50)
    for u in uniq:
        examples = ", ".join(f"({a},{b})" for a, b in u["example_faces"])
        lines.append(f"{u['distance']:8.3f}  {u['count']:5d}  {u['axis']:>4}  {examples}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find distances between parallel planar faces in a STEP file.",
    )
    parser.add_argument("step_file", help="Path to the .step / .stp file")
    parser.add_argument("--max-dist", type=float, default=None, help="Max distance to report (mm)")
    parser.add_argument("--axis", choices=["X", "Y", "Z"], default=None, help="Filter by dominant normal axis")
    parser.add_argument("--unique", action="store_true", help="Show deduplicated distances only")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    try:
        pairs = find_face_distances(args.step_file, max_dist=args.max_dist, axis_filter=args.axis)
    except StepLoadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.unique:
        uniq = unique_distances(pairs)
        if args.json:
            print(json.dumps(uniq, indent=2))
        else:
            print(f"Unique parallel-face distances in: {args.step_file}")
            print(f"Found {len(uniq)} unique distance(s) from {len(pairs)} pair(s)")
            print()
            print(_format_unique(uniq))
    else:
        if args.json:
            print(json.dumps(pairs, indent=2))
        else:
            print(f"Parallel-face distances in: {args.step_file}")
            print(f"Found {len(pairs)} pair(s)")
            print()
            print(_format_table(pairs))


if __name__ == "__main__":
    main()
