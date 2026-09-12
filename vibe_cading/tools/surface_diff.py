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

"""Surface-level comparison of two shapes, including non-watertight meshes.

Complements :mod:`boolean_diff`, it does not replace it:

===================  ===================================  ==========================
                     ``boolean_diff.py``                  ``surface_diff.py``
===================  ===================================  ==========================
needs watertight     yes -- silently returns all-zero /   no -- works on triangles,
solids?              Jaccard 0 on an open mesh            so STL / scan / mesh refs
what it reports      one signed volume delta              two DIRECTED deviations
scoping              whole shape                          ``--region`` sub-volume
finds *where*        residual STEP to eyeball             ranked stations, clusters
===================  ===================================  ==========================

**Why the two directions matter.** ``reference -> ours`` finds what we are
MISSING; ``ours -> reference`` finds what we INVENTED. A symmetric mean hides
both, and they call for opposite fixes.

**Why scoping matters.** Whole-part statistics wash out small features. A
0.220 mm retention bead is a rounding error against a 57 mm lid, yet it is the
entire mechanism. ``--region`` restricts sampling to a sub-volume so a delicate
component is scored on its own terms.

Positive control
----------------
Every result carries the sample counts that produced it, and
:attr:`Comparison.agreement` **raises** :class:`InconclusiveRegion` when either
side contributed no samples. This is deliberate and structural: the most
dangerous failure in this kind of tooling is a probe that reports a clean
"no difference" because it was looking at the wrong place, at which point an
absence of evidence reads as evidence of absence. You cannot obtain an
agreement figure from an empty region -- you get an exception naming the side
that was empty.

Usage
-----
    # whole-shape, both directions
    python3 vibe_cading/tools/surface_diff.py ref.stl module.path.Class

    # scope to one component (the delicate-detail case)
    python3 vibe_cading/tools/surface_diff.py ref.stl mod.Class \\
        --region 5.6,19.2,-36,-30,0,13

    # let the data pick the worst cross-sections in that component
    python3 vibe_cading/tools/surface_diff.py ref.stl mod.Class \\
        --region 5.6,19.2,-36,-30,0,13 --sweep x

    # exact surface positions along one ray (what a section cannot show)
    python3 vibe_cading/tools/surface_diff.py ref.stl mod.Class --ray x=12.4,z=5.0

Each source is a ``module.path.ClassName``, a ``.step``/``.stp`` file, or a
``.stl`` file.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from vibe_cading.tools.model_loader import load_solid, parse_params  # noqa: E402

TESSELLATION_TOL = 0.03


class InconclusiveRegion(RuntimeError):
    """Raised when a comparison is read from a region one side does not occupy.

    Carries which side was empty so the caller can fix the region rather than
    mistake emptiness for agreement.
    """


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------
def _tris_from_shape(shape, tol: float = TESSELLATION_TOL) -> np.ndarray:
    verts, faces = shape.tessellate(tol)
    v = np.array([[p.x, p.y, p.z] for p in verts])
    return v[np.array(faces)]


def _tris_from_stl(path: Path) -> np.ndarray:
    raw = path.read_bytes()
    is_ascii = raw[:5].lower() == b"solid" and b"facet" in raw[:1024].lower()
    if is_ascii:
        pts = [
            tuple(float(x) for x in line.split()[1:4])
            for line in raw.decode("utf-8", "replace").splitlines()
            if line.strip().startswith("vertex")
        ]
        return np.array(pts).reshape(-1, 3, 3)
    n = int.from_bytes(raw[80:84], "little")
    out = np.empty((n, 3, 3))
    for i in range(n):
        off = 84 + i * 50 + 12
        out[i] = np.frombuffer(raw, "<f4", count=9, offset=off).reshape(3, 3)
    return out


def load_triangles(source: str, params: dict | None = None) -> np.ndarray:
    """Triangles for a model class, a STEP file, or an STL file."""
    low = source.lower()
    if low.endswith(".stl"):
        return _tris_from_stl(Path(source))
    if low.endswith((".step", ".stp")):
        import cadquery as cq  # noqa: PLC0415

        return _tris_from_shape(cq.importers.importStep(source).val())
    _, solid = load_solid(source, params or {})
    return _tris_from_shape(solid.val() if hasattr(solid, "val") else solid)


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------
def sample_points(tris: np.ndarray, per_tri: int = 4) -> np.ndarray:
    """Barycentric samples over every triangle, plus its vertices.

    Vertices are always included so a sparse, large-facet model (a CAD solid)
    is not under-represented against a finely tessellated mesh.
    """
    pts = [tris.reshape(-1, 3)]
    if per_tri:
        rng = np.linspace(0.2, 0.8, max(1, int(math.sqrt(per_tri))))
        for u in rng:
            for v in rng:
                if u + v < 1.0:
                    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
                    pts.append(a + (b - a) * u + (c - a) * v)
    return np.vstack(pts)


def point_triangle_distance(pts: np.ndarray, tris: np.ndarray,
                            chunk: int = 512) -> np.ndarray:
    """Distance from each point to the nearest triangle (chunked, numpy-only)."""
    if len(pts) == 0 or len(tris) == 0:
        return np.zeros(len(pts))
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    ab, ac = b - a, c - a
    nrm = np.cross(ab, ac)
    area2 = np.einsum("ij,ij->i", nrm, nrm)
    area2[area2 == 0] = 1e-20
    out = np.empty(len(pts))
    for i in range(0, len(pts), chunk):
        p = pts[i:i + chunk][:, None, :]
        ap = p - a[None]
        t = np.einsum("ijk,jk->ij", ap, nrm) / area2[None]
        proj = p - t[..., None] * nrm[None]
        # barycentric coordinates of the projection
        v0, v1, v2 = ab[None], ac[None], proj - a[None]
        d00 = np.einsum("ijk,ijk->ij", v0, v0)
        d01 = np.einsum("ijk,ijk->ij", v0, v1)
        d11 = np.einsum("ijk,ijk->ij", v1, v1)
        d20 = np.einsum("ijk,ijk->ij", v2, v0)
        d21 = np.einsum("ijk,ijk->ij", v2, v1)
        den = d00 * d11 - d01 * d01
        den[den == 0] = 1e-20
        u = (d11 * d20 - d01 * d21) / den
        w = (d00 * d21 - d01 * d20) / den
        inside = (u >= 0) & (w >= 0) & (u + w <= 1)
        d_plane = np.abs(np.einsum("ijk,jk->ij", ap, nrm)) / np.sqrt(area2)[None]

        # Outside the face, the nearest point lies on an EDGE, not necessarily
        # at a vertex. Falling back to the nearest vertex (as this did until
        # round 38) overestimates badly on coarse meshes with large triangles:
        # against an 882-triangle reference it reported 5.456 mm where the true
        # surface distance was ~0.49 mm, and inflated a whole component's
        # disagreement. Vertex fallback is only correct when triangles are
        # small relative to the distances being measured -- which is exactly
        # when it does not matter.
        def _edge_dist(p0, p1):
            e = (p1 - p0)[None]                      # (1, T, 3)
            v = p - p0[None]                         # (P, T, 3)
            ee = np.einsum("ijk,ijk->ij", e, e)
            ee = np.where(ee == 0, 1e-20, ee)
            t = np.clip(np.einsum("ijk,ijk->ij", v, e) / ee, 0.0, 1.0)
            return np.linalg.norm(v - t[..., None] * e, axis=2)

        dv = np.minimum.reduce([_edge_dist(a, b), _edge_dist(b, c), _edge_dist(c, a)])
        out[i:i + chunk] = np.where(inside, d_plane, dv).min(axis=1)
    return out


def clip_region(arr: np.ndarray, region: tuple | None) -> np.ndarray:
    """Keep points (N,3) or triangles (N,3,3) intersecting an AABB."""
    if region is None:
        return arr
    lo = np.array(region[0::2], float)
    hi = np.array(region[1::2], float)
    if arr.ndim == 3:
        return arr[np.all(arr.max(axis=1) >= lo, axis=1)
                   & np.all(arr.min(axis=1) <= hi, axis=1)]
    return arr[np.all(arr >= lo, axis=1) & np.all(arr <= hi, axis=1)]


# --------------------------------------------------------------------------
# results
# --------------------------------------------------------------------------
@dataclass
class Direction:
    """One directed half of the comparison."""

    label: str
    n: int
    dist: np.ndarray = field(repr=False)
    tol: float
    pts: np.ndarray = field(repr=False, default=None)

    @property
    def within(self) -> float:
        return 100.0 * float((self.dist <= self.tol).mean()) if self.n else float("nan")

    @property
    def mean(self) -> float:
        return float(self.dist.mean()) if self.n else float("nan")

    @property
    def max(self) -> float:
        return float(self.dist.max()) if self.n else float("nan")


@dataclass
class Comparison:
    a_name: str
    b_name: str
    a_to_b: Direction
    b_to_a: Direction
    region: tuple | None

    @property
    def conclusive(self) -> bool:
        """Both shapes contributed samples -- the positive control."""
        return self.a_to_b.n > 0 and self.b_to_a.n > 0

    def _check(self) -> None:
        if self.conclusive:
            return
        empty = []
        if self.a_to_b.n == 0:
            empty.append(f"{self.a_name} (A)")
        if self.b_to_a.n == 0:
            empty.append(f"{self.b_name} (B)")
        raise InconclusiveRegion(
            f"no samples from {' and '.join(empty)} in region {self.region}. "
            "An empty region is not agreement -- widen the region or check the "
            "coordinate frame before reading any figure from this comparison."
        )

    @property
    def agreement(self) -> float:
        """Worst of the two directed within-tolerance percentages.

        Raises :class:`InconclusiveRegion` rather than returning a flattering
        number when one side occupies nothing in the region.
        """
        self._check()
        return min(self.a_to_b.within, self.b_to_a.within)


def drop_regions(pts: np.ndarray, excludes) -> np.ndarray:
    """Remove sample points falling inside any excluded AABB.

    This is how a DECLARED, intentional difference stops being scored as a
    defect. Excluding points (not triangles) is deliberate: the excluded
    geometry must still exist as a comparison target for everything around it,
    it simply must not contribute samples of its own.
    """
    if not excludes or len(pts) == 0:
        return pts
    keep = np.ones(len(pts), bool)
    for r in excludes:
        lo = np.array(r[0::2], float)
        hi = np.array(r[1::2], float)
        keep &= ~(np.all(pts >= lo, axis=1) & np.all(pts <= hi, axis=1))
    return pts[keep]


def compare(a_tris, b_tris, *, a_name="A", b_name="B", region=None,
            tol=0.2, density=4, exclude=None) -> Comparison:
    """Two-sided surface deviation, optionally scoped to *region*.

    *exclude* is an iterable of AABBs whose samples are dropped -- the
    mechanism by which an intentional difference (a feature removed by design)
    is declared rather than repeatedly rediscovered as a defect.
    """
    a_r, b_r = clip_region(a_tris, region), clip_region(b_tris, region)
    pa = drop_regions(clip_region(sample_points(a_r, density), region), exclude)
    pb = drop_regions(clip_region(sample_points(b_r, density), region), exclude)
    return Comparison(
        a_name=a_name, b_name=b_name, region=region,
        a_to_b=Direction(f"{a_name} -> {b_name}  (missing from {b_name})",
                         len(pa), point_triangle_distance(pa, b_r), tol, pa),
        b_to_a=Direction(f"{b_name} -> {a_name}  (extra in {b_name})",
                         len(pb), point_triangle_distance(pb, a_r), tol, pb),
    )


def sweep_stations(a_tris, b_tris, axis, region, *, step=0.25, tol=0.2, density=1):
    """Score every station along *axis*, worst first, so the DATA picks the slice.

    A hand-picked station is biased toward the flattering one; a feature's own
    centreline is typically its most self-similar plane and blind to whatever
    varies along that axis.
    """
    idx = "xyz".index(axis)
    lo, hi = region[idx * 2], region[idx * 2 + 1]
    rows = []
    at = lo
    while at <= hi + 1e-9:
        sub = list(region)
        sub[idx * 2], sub[idx * 2 + 1] = at - step / 2.0, at + step / 2.0
        c = compare(a_tris, b_tris, region=tuple(sub), tol=tol, density=density)
        rows.append((at, c))
        at += step
    # Rank by the WORSE of the two directions. Ranking on one direction only
    # makes the sweep structurally blind to the other -- sorting by
    # `a_to_b` alone cannot see material we INVENTED, which is exactly the
    # asymmetry this tool exists to expose.
    def _worst(row):
        c = row[1]
        if not c.conclusive:
            return -1.0
        return max(c.a_to_b.max, c.b_to_a.max)

    return sorted(rows, key=lambda r: -_worst(r))


def ray_surfaces(tris, axis, fixed: dict) -> list[float]:
    """Where a shape's surfaces sit along *axis*, at the given other coords.

    Reports raw crossing positions and makes no inside/outside (parity)
    assumption, so it is valid on open meshes where booleans are not.
    """
    ai = "xyz".index(axis)
    o1, o2 = [i for i in range(3) if i != ai]
    k1, k2 = fixed["xyz"[o1]], fixed["xyz"[o2]]
    hits = []
    for t in tris:
        p = np.asarray(t, float)
        a, d1, d2 = p[0], p[1] - p[0], p[2] - p[0]
        m = np.array([[d1[o1], d2[o1]], [d1[o2], d2[o2]]])
        det = np.linalg.det(m)
        if abs(det) < 1e-12:
            continue
        u, v = np.linalg.solve(m, np.array([k1 - a[o1], k2 - a[o2]]))
        if u < -1e-9 or v < -1e-9 or u + v > 1 + 1e-9:
            continue
        hits.append(float(a[ai] + u * d1[ai] + v * d2[ai]))
    return sorted(hits)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _fmt(d: Direction) -> str:
    return (f"  {d.label:<44} n={d.n:<7d} within {d.within:5.1f}%   "
            f"mean {d.mean:6.3f}  max {d.max:6.3f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--region", help="xmin,xmax,ymin,ymax,zmin,zmax")
    ap.add_argument("--tol", type=float, default=0.2)
    ap.add_argument("--density", type=int, default=4)
    ap.add_argument("--sweep", choices=list("xyz"))
    ap.add_argument("--sweep-step", type=float, default=0.25)
    ap.add_argument("--ray", help="e.g. 'x=12.4,z=5.0' -- casts along the third axis")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--worst", type=int, default=0,
                    help="list the N worst-deviating sample coordinates, so "
                         "'where exactly' is answered without a second probe")
    ap.add_argument("--params-a", nargs="*", default=[])
    ap.add_argument("--params-b", nargs="*", default=[])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    region = tuple(float(v) for v in args.region.split(",")) if args.region else None
    if region is not None and len(region) != 6:
        ap.error("--region needs exactly 6 comma-separated numbers")

    a = load_triangles(args.a, parse_params(args.params_a))
    b = load_triangles(args.b, parse_params(args.params_b))

    if args.ray:
        fixed = {k: float(v) for k, v in
                 (p.split("=") for p in args.ray.split(","))}
        axis = next(x for x in "xyz" if x not in fixed)
        sa, sb = ray_surfaces(a, axis, fixed), ray_surfaces(b, axis, fixed)
        if not sa and not sb:
            raise InconclusiveRegion(
                f"neither shape has any surface on the ray {args.ray}; "
                "an empty ray is not agreement")
        print(f"surfaces along {axis} at {args.ray}")
        print(f"  {args.a}: {[round(v, 3) for v in sa]}")
        print(f"  {args.b}: {[round(v, 3) for v in sb]}")
        return

    if args.sweep:
        if region is None:
            ap.error("--sweep needs --region to bound the scan")
        rows = sweep_stations(a, b, args.sweep, region,
                              step=args.sweep_step, tol=args.tol)
        print(f"stations along {args.sweep}, worst first "
              f"(ranked by the data, not hand-picked):")
        print(f"  {'at':>8} {'missing_max':>12} {'extra_max':>11}  note")
        for at, c in rows[:args.top]:
            if not c.conclusive:
                print(f"  {at:8.2f} {'-':>12} {'-':>11}  INCONCLUSIVE (empty)")
            else:
                print(f"  {at:8.2f} {c.a_to_b.max:12.3f} {c.b_to_a.max:11.3f}")
        return

    c = compare(a, b, a_name=args.a, b_name=args.b, region=region,
                tol=args.tol, density=args.density)
    if args.json:
        try:
            agree = c.agreement
        except InconclusiveRegion as exc:
            print(json.dumps({"conclusive": False, "reason": str(exc)}, indent=2))
            sys.exit(2)
        print(json.dumps({
            "conclusive": True, "agreement": agree, "tol": args.tol,
            "a_to_b": {"n": c.a_to_b.n, "within": c.a_to_b.within,
                       "mean": c.a_to_b.mean, "max": c.a_to_b.max},
            "b_to_a": {"n": c.b_to_a.n, "within": c.b_to_a.within,
                       "mean": c.b_to_a.mean, "max": c.b_to_a.max},
        }, indent=2))
        return

    print(f"region: {region if region else 'whole shape'}   tolerance: {args.tol} mm")
    print(_fmt(c.a_to_b))
    print(_fmt(c.b_to_a))
    if args.worst:
        for d, pts in ((c.a_to_b, c.a_to_b.pts), (c.b_to_a, c.b_to_a.pts)):
            if d.n == 0:
                continue
            order = np.argsort(-d.dist)[:args.worst]
            print(f"\n  worst samples, {d.label}:")
            for i in order:
                x, y, z = pts[i]
                print(f"     dev {d.dist[i]:6.3f} at x={x:8.3f} y={y:8.3f} z={z:7.3f}")
    try:
        print(f"\n  agreement (worst direction): {c.agreement:.1f}%")
    except InconclusiveRegion as exc:
        print(f"\n  INCONCLUSIVE: {exc}")
        sys.exit(2)


if __name__ == "__main__":
    main()
