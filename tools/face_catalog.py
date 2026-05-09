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
"""Classify every face in a STEP file by surface type and extract geometry.

Usage
-----
    python3 tools/face_catalog.py <path.step>
    python3 tools/face_catalog.py <path.step> --type Cylinder
    python3 tools/face_catalog.py <path.step> --json

Output
------
A table (or JSON array) of every face with:
  - index, surface type, area
  - type-specific geometry (axis, radius, normal, origin, …)
  - bounding box

Filtering
---------
``--type`` filters to a single surface type (case-insensitive).
``--min-area`` hides tiny fillet/chamfer faces (e.g. ``--min-area 1.0``).
``--sort`` orders by ``area`` (default), ``radius``, or ``index``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import OCP.BRepAdaptor as ba
import OCP.GeomAbs as ga

from tools.step_primitives import StepLoadError, face_area, load_step, vec3

# ── Surface-type names ────────────────────────────────────────────────────────

_SURFACE_TYPE_MAP = {
    ga.GeomAbs_SurfaceType.GeomAbs_Plane: "Plane",
    ga.GeomAbs_SurfaceType.GeomAbs_Cylinder: "Cylinder",
    ga.GeomAbs_SurfaceType.GeomAbs_Cone: "Cone",
    ga.GeomAbs_SurfaceType.GeomAbs_Sphere: "Sphere",
    ga.GeomAbs_SurfaceType.GeomAbs_Torus: "Torus",
    ga.GeomAbs_SurfaceType.GeomAbs_BezierSurface: "Bezier",
    ga.GeomAbs_SurfaceType.GeomAbs_BSplineSurface: "BSpline",
    ga.GeomAbs_SurfaceType.GeomAbs_SurfaceOfRevolution: "Revolution",
    ga.GeomAbs_SurfaceType.GeomAbs_SurfaceOfExtrusion: "Extrusion",
    ga.GeomAbs_SurfaceType.GeomAbs_OffsetSurface: "Offset",
    ga.GeomAbs_SurfaceType.GeomAbs_OtherSurface: "Other",
}


def _face_bbox(cq_face) -> dict:
    bb = cq_face.BoundingBox()
    return {
        "xmin": round(bb.xmin, 4), "xmax": round(bb.xmax, 4),
        "ymin": round(bb.ymin, 4), "ymax": round(bb.ymax, 4),
        "zmin": round(bb.zmin, 4), "zmax": round(bb.zmax, 4),
    }


def catalog_faces(path: str | Path) -> list[dict]:
    """Return a list of face descriptors for every face in the STEP file.

    Each descriptor contains at minimum:
    ``{index, type, area, bbox}``

    Type-specific keys are added:
    - **Plane**: ``normal``, ``origin``
    - **Cylinder**: ``radius``, ``axis``, ``location``
    - **Cone**: ``radius``, ``semi_angle``, ``axis``, ``location``
    - **Sphere**: ``radius``, ``center``
    - **Torus**: ``major_radius``, ``minor_radius``, ``axis``, ``location``
    """
    faces = load_step(path).wp.faces().vals()

    result: list[dict] = []
    for i, f in enumerate(faces):
        adaptor = ba.BRepAdaptor_Surface(f.wrapped)
        st = adaptor.GetType()
        type_name = _SURFACE_TYPE_MAP.get(st, str(st))
        area = round(face_area(f.wrapped), 4)

        entry: dict = {
            "index": i,
            "type": type_name,
            "area": area,
            "bbox": _face_bbox(f),
        }

        if st == ga.GeomAbs_SurfaceType.GeomAbs_Plane:
            pln = adaptor.Plane()
            entry["normal"] = vec3(pln.Axis().Direction())
            entry["origin"] = vec3(pln.Location())

        elif st == ga.GeomAbs_SurfaceType.GeomAbs_Cylinder:
            cyl = adaptor.Cylinder()
            entry["radius"] = round(cyl.Radius(), 4)
            entry["axis"] = vec3(cyl.Axis().Direction())
            entry["location"] = vec3(cyl.Location())

        elif st == ga.GeomAbs_SurfaceType.GeomAbs_Cone:
            cone = adaptor.Cone()
            entry["radius"] = round(cone.RefRadius(), 4)
            entry["semi_angle"] = round(cone.SemiAngle(), 6)
            entry["axis"] = vec3(cone.Axis().Direction())
            entry["location"] = vec3(cone.Location())

        elif st == ga.GeomAbs_SurfaceType.GeomAbs_Sphere:
            sph = adaptor.Sphere()
            entry["radius"] = round(sph.Radius(), 4)
            entry["center"] = vec3(sph.Location())

        elif st == ga.GeomAbs_SurfaceType.GeomAbs_Torus:
            tor = adaptor.Torus()
            entry["major_radius"] = round(tor.MajorRadius(), 4)
            entry["minor_radius"] = round(tor.MinorRadius(), 4)
            entry["axis"] = vec3(tor.Axis().Direction())
            entry["location"] = vec3(tor.Location())

        result.append(entry)

    return result


def _format_table(faces: list[dict]) -> str:
    """Pretty-print face catalog as a text table."""
    lines: list[str] = []
    lines.append(f"{'Idx':>4}  {'Type':12s}  {'Area':>10}  Details")
    lines.append("-" * 80)

    for f in faces:
        details_parts: list[str] = []

        if "radius" in f:
            details_parts.append(f"R={f['radius']:.3f}")
        if "major_radius" in f:
            details_parts.append(f"R_maj={f['major_radius']:.3f}")
        if "minor_radius" in f:
            details_parts.append(f"R_min={f['minor_radius']:.3f}")
        if "semi_angle" in f:
            import math
            details_parts.append(f"half_angle={math.degrees(f['semi_angle']):.1f}°")
        if "axis" in f:
            a = f["axis"]
            details_parts.append(f"axis=({a['x']:+.2f},{a['y']:+.2f},{a['z']:+.2f})")
        if "normal" in f:
            n = f["normal"]
            details_parts.append(f"normal=({n['x']:+.2f},{n['y']:+.2f},{n['z']:+.2f})")
        if "location" in f:
            p = f["location"]
            details_parts.append(f"loc=({p['x']:.2f},{p['y']:.2f},{p['z']:.2f})")
        if "origin" in f:
            p = f["origin"]
            details_parts.append(f"origin=({p['x']:.2f},{p['y']:.2f},{p['z']:.2f})")
        if "center" in f:
            p = f["center"]
            details_parts.append(f"center=({p['x']:.2f},{p['y']:.2f},{p['z']:.2f})")

        details = "  ".join(details_parts)
        lines.append(f"{f['index']:4d}  {f['type']:12s}  {f['area']:10.3f}  {details}")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classify faces in a STEP file by surface type.",
    )
    parser.add_argument("step_file", help="Path to the .step / .stp file")
    parser.add_argument("--type", default=None, help="Filter to a single surface type (case-insensitive)")
    parser.add_argument("--min-area", type=float, default=0.0, help="Hide faces with area < this (mm²)")
    parser.add_argument("--sort", default="area", choices=["area", "radius", "index"], help="Sort order (default: area)")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of a table")
    parser.add_argument("--summary", action="store_true", help="Print only a type-count summary")
    args = parser.parse_args()

    try:
        faces = catalog_faces(args.step_file)
    except StepLoadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    # Filter by type
    if args.type:
        t = args.type.lower()
        faces = [f for f in faces if f["type"].lower() == t]

    # Filter by area
    if args.min_area > 0:
        faces = [f for f in faces if f["area"] >= args.min_area]

    # Sort
    if args.sort == "area":
        faces.sort(key=lambda f: -f["area"])
    elif args.sort == "radius":
        faces.sort(key=lambda f: -f.get("radius", f.get("major_radius", 0)))
    else:
        faces.sort(key=lambda f: f["index"])

    if args.summary:
        counts: dict[str, int] = {}
        for f in faces:
            counts[f["type"]] = counts.get(f["type"], 0) + 1
        if args.json:
            print(json.dumps(counts, indent=2))
        else:
            print("Face type summary:")
            for name, count in sorted(counts.items(), key=lambda x: -x[1]):
                print(f"  {name:12s}: {count}")
            print(f"  {'TOTAL':12s}: {sum(counts.values())}")
        return

    if args.json:
        print(json.dumps(faces, indent=2))
    else:
        print(f"Face catalog for: {args.step_file}")
        print(f"Showing {len(faces)} face(s)")
        if args.type:
            print(f"Filtered to type: {args.type}")
        print()
        print(_format_table(faces))


if __name__ == "__main__":
    main()
