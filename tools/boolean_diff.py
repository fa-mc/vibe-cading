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
"""Compare two STEP files (or a STEP file and a CadQuery model) via boolean difference.

Computes ``A − B`` and ``B − A`` to quantify and visualise mismatches
between a reference and a generated model.

Usage
-----
    python3 tools/boolean_diff.py <reference.step> <candidate.step>
    python3 tools/boolean_diff.py <reference.step> <module.Class> --model
    python3 tools/boolean_diff.py <ref.step> <cand.step> --export --out tmp/diff/

Output
------
Text report with:
  - Volume of reference, candidate, intersection
  - Volume of ``ref − cand`` (missing material) and ``cand − ref`` (extra material)
  - Jaccard similarity (intersection / union)

With ``--export``, writes STEP files of the residuals for visual inspection.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

import cadquery as cq
import OCP.BRepGProp as bgp
import OCP.GProp as gprop
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy, BRepBuilderAPI_Transform
from OCP.gp import gp_Trsf, gp_Vec
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models"
sys.path.insert(0, str(MODELS_DIR))


def _volume(occ_shape) -> float:
    """Compute volume of an OCC shape."""
    props = gprop.GProp_GProps()
    bgp.BRepGProp.VolumeProperties_s(occ_shape, props)
    return abs(props.Mass())


def _has_solid(occ_shape) -> bool:
    """Check if a shape contains at least one solid."""
    explorer = TopExp_Explorer(occ_shape, TopAbs_SOLID)
    return explorer.More()


def _load_step(path: str | Path) -> cq.Shape:
    wp = cq.importers.importStep(str(path))
    return wp.val()


def _load_model(model_path: str, params: dict[str, float] | None = None) -> cq.Shape:
    module_str, class_name = model_path.rsplit(".", 1)
    module = importlib.import_module(module_str)
    cls = getattr(module, class_name)
    instance = cls(**(params or {}))
    return instance.solid.val()


def _bbox_center(shape: cq.Shape) -> tuple[float, float, float]:
    bb = shape.BoundingBox()
    return (bb.center.x, bb.center.y, bb.center.z)


def _translate_shape(occ_shape, dx: float, dy: float, dz: float):
    """Return a translated copy of an OCC shape."""
    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Vec(dx, dy, dz))
    builder = BRepBuilderAPI_Transform(occ_shape, trsf, True)
    return builder.Shape()


def boolean_diff(
    ref_shape: cq.Shape,
    cand_shape: cq.Shape,
    align_bbox: bool = False,
) -> dict:
    """Compute boolean difference metrics between two shapes.

    Returns
    -------
    dict with keys:
        ref_volume, cand_volume, intersection_volume,
        missing_volume (ref - cand), extra_volume (cand - ref),
        union_volume, jaccard_similarity
    """
    ref_occ = ref_shape.wrapped
    # Deep-copy the candidate so OCCT booleans work even when both inputs
    # originate from the same STEP file (identical TopoDS_Shape).
    cand_occ = BRepBuilderAPI_Copy(cand_shape.wrapped).Shape()

    if align_bbox:
        rc = _bbox_center(ref_shape)
        cc = _bbox_center(cq.Shape(cand_occ))
        dx, dy, dz = rc[0] - cc[0], rc[1] - cc[1], rc[2] - cc[2]
        cand_occ = _translate_shape(cand_occ, dx, dy, dz)

    ref_vol = _volume(ref_occ)
    cand_vol = _volume(cand_occ)

    # Intersection: A ∩ B
    common_op = BRepAlgoAPI_Common(ref_occ, cand_occ)
    common_op.Build()
    inter_vol = 0.0
    if common_op.IsDone() and _has_solid(common_op.Shape()):
        inter_vol = _volume(common_op.Shape())

    # Missing material: A − B (in ref but not in candidate)
    cut_ref_op = BRepAlgoAPI_Cut(ref_occ, cand_occ)
    cut_ref_op.Build()
    missing_vol = 0.0
    if cut_ref_op.IsDone() and _has_solid(cut_ref_op.Shape()):
        missing_vol = _volume(cut_ref_op.Shape())

    # Extra material: B − A (in candidate but not in ref)
    cut_cand_op = BRepAlgoAPI_Cut(cand_occ, ref_occ)
    cut_cand_op.Build()
    extra_vol = 0.0
    if cut_cand_op.IsDone() and _has_solid(cut_cand_op.Shape()):
        extra_vol = _volume(cut_cand_op.Shape())

    union_vol = ref_vol + cand_vol - inter_vol
    jaccard = inter_vol / union_vol if union_vol > 0 else 0.0

    return {
        "ref_volume": round(ref_vol, 4),
        "cand_volume": round(cand_vol, 4),
        "intersection_volume": round(inter_vol, 4),
        "missing_volume": round(missing_vol, 4),
        "extra_volume": round(extra_vol, 4),
        "union_volume": round(union_vol, 4),
        "jaccard_similarity": round(jaccard, 6),
        # Convenience
        "volume_diff_pct": round((cand_vol - ref_vol) / ref_vol * 100, 2) if ref_vol > 0 else 0.0,
        "_missing_shape": cut_ref_op.Shape() if cut_ref_op.IsDone() else None,
        "_extra_shape": cut_cand_op.Shape() if cut_cand_op.IsDone() else None,
    }


def _format_report(info: dict) -> str:
    lines = [
        "Boolean difference report",
        "=" * 40,
        f"Reference volume:     {info['ref_volume']:10.2f} mm³",
        f"Candidate volume:     {info['cand_volume']:10.2f} mm³",
        f"Volume difference:    {info['volume_diff_pct']:+.2f}%",
        "",
        f"Intersection (A∩B):   {info['intersection_volume']:10.2f} mm³",
        f"Missing (ref−cand):   {info['missing_volume']:10.2f} mm³",
        f"Extra (cand−ref):     {info['extra_volume']:10.2f} mm³",
        "",
        f"Jaccard similarity:   {info['jaccard_similarity']:.4f}  (1.0 = perfect match)",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare two shapes via boolean difference.",
    )
    parser.add_argument("reference", help="Path to reference .step file")
    parser.add_argument("candidate", help="Path to candidate .step file, or module.Class if --model is set")
    parser.add_argument("--model", action="store_true", help="Treat candidate as a CadQuery model class path")
    parser.add_argument("--params", nargs="*", default=[], metavar="key=value", help="Constructor params for --model")
    parser.add_argument("--align-bbox", action="store_true", help="Translate candidate to align bounding-box centres before comparing")
    parser.add_argument("--export", action="store_true", help="Export residual shapes as STEP files")
    parser.add_argument("--out", default="tmp/diff", help="Output directory for exported residuals")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    ref_shape = _load_step(args.reference)

    if args.model:
        params = {}
        for item in args.params:
            k, v = item.split("=", 1)
            params[k.strip()] = float(v.strip())
        cand_shape = _load_model(args.candidate, params)
    else:
        cand_shape = _load_step(args.candidate)

    info = boolean_diff(ref_shape, cand_shape, align_bbox=args.align_bbox)

    if args.export:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        if info["_missing_shape"] is not None and _has_solid(info["_missing_shape"]):
            missing_path = out_dir / "missing_ref_minus_cand.step"
            cq.exporters.export(
                cq.Shape(info["_missing_shape"]),
                str(missing_path),
            )
            print(f"WROTE {missing_path}")
        if info["_extra_shape"] is not None and _has_solid(info["_extra_shape"]):
            extra_path = out_dir / "extra_cand_minus_ref.step"
            cq.exporters.export(
                cq.Shape(info["_extra_shape"]),
                str(extra_path),
            )
            print(f"WROTE {extra_path}")

    # Remove internal shapes before printing
    printable = {k: v for k, v in info.items() if not k.startswith("_")}

    if args.json:
        print(json.dumps(printable, indent=2))
    else:
        print(_format_report(printable))


if __name__ == "__main__":
    main()
