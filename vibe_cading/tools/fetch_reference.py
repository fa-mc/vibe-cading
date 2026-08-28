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
"""Acquire third-party reference geometry that must not be committed.

Some reference meshes this project compares against are derived from the
LDraw parts library.  Their *dimensions* are facts and are quoted freely in
the design record, but no converted geometry is committed here -- see
``docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md``
(section "Licensing").  The consequence is that any check pointing at such
a reference can only be run by a contributor who has already obtained it by
hand -- so it is enforced nowhere, and the acquisition steps live in
throwaway scratch scripts that nobody else can reproduce.

This tool closes that gap without committing a byte of it: the source
archive is fetched on demand, pinned by SHA-256, and converted locally into
the meshes the conformance manifest expects.

Why the hash pin is the load-bearing part
-----------------------------------------
LDraw ships periodic part updates to the *same* URL.  Any tolerance a
comparison is judged against -- a ``surface_diff.py`` agreement percentage,
a ``boolean_diff.py`` volume delta -- is calibrated against one specific
revision of the reference.  An unpinned fetch would let an upstream part
revision silently move the thing those numbers are measured against, and
the drift would read as a model regression, or worse, as an improvement.
So a hash mismatch is a hard failure demanding human review, never an
auto-accept.

Exit codes
----------
``0``  every requested reference is present and verified.
``1``  INTEGRITY failure -- the archive hash does not match the manifest.
       The upstream source changed; every calibrated tolerance measured
       against it must be re-reviewed before the pin is bumped.
``2``  USAGE error -- bad manifest, unknown part, malformed arguments.
``3``  INFRA error -- the archive could not be downloaded.  Deliberately
       distinct from 0 and 1 so a caller can red a CI job as infrastructure
       rather than silently treating an unreachable network as a pass.

Attribution
-----------
LDraw parts are (c) their authors -- for the PoweredUp hub, Philippe
Hurbain [Philo] -- and licensed CC BY 4.0
(https://creativecommons.org/licenses/by/4.0/).  This tool downloads them
to a git-ignored cache; it redistributes nothing.

Usage
-----
    python3 vibe_cading/tools/fetch_reference.py            # fetch + convert all
    python3 vibe_cading/tools/fetch_reference.py --list     # show manifest, no network
    python3 vibe_cading/tools/fetch_reference.py --verify   # check cache, never download
    python3 vibe_cading/tools/fetch_reference.py --part 24853.dat
"""
import argparse
import hashlib
import struct
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib

# Exit codes -- see the module docstring.  Named rather than literal because
# the whole point of code 3 is that a caller can distinguish it from 1.
EXIT_OK = 0
EXIT_INTEGRITY = 1
EXIT_USAGE = 2
EXIT_INFRA = 3

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "reference_sources.toml"

# 1 LDraw Unit = 0.4 mm.  Fixed by the LDraw standard, not a tunable.
LDU_MM = 0.4

# Search order for resolving a subpart reference inside the archive.  LDraw
# files reference each other by bare name and rely on the loader knowing
# which directory each kind lives in.
SEARCH_DIRS = ("parts", "p", "parts/s", "p/48", "p/8", "models")

# An LDraw part that recurses deeper than this is malformed or cyclic.
MAX_DEPTH = 25

IDENTITY = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)


class IntegrityError(Exception):
    """The fetched archive does not match its pinned hash."""


class InfraError(Exception):
    """The archive could not be retrieved."""


class ManifestError(Exception):
    """The manifest is missing, malformed, or names an unknown part."""


def _sha256(path: Path, chunk: int = 1 << 20) -> str:
    """Stream the file so a 145 MB archive never lands in memory."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def load_manifest(path: Path) -> dict:
    """Parse and structurally validate the manifest."""
    if not path.exists():
        raise ManifestError(f"manifest not found: {path}")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ManifestError(f"{path}: malformed TOML -- {exc}") from exc

    archive = data.get("archive")
    if not isinstance(archive, dict):
        raise ManifestError(f"{path}: missing [archive] table")
    for key in ("url", "sha256", "cache"):
        if not archive.get(key):
            raise ManifestError(f"{path}: [archive] is missing '{key}'")

    parts = data.get("part") or []
    if not parts:
        raise ManifestError(f"{path}: no [[part]] entries")
    for entry in parts:
        for key in ("name", "output"):
            if not entry.get(key):
                raise ManifestError(f"{path}: a [[part]] entry is missing '{key}'")
    return data


def ensure_archive(archive: dict, *, allow_download: bool = True,
                   progress=print) -> Path:
    """Return the verified archive path, downloading it only if needed.

    A cached file whose hash already matches is never re-downloaded, so the
    common case costs one hash of a local file and no network at all.
    """
    cache = REPO_ROOT / archive["cache"]
    expected = archive["sha256"].strip().lower()

    if cache.exists():
        actual = _sha256(cache)
        if actual == expected:
            progress(f"cache HIT   {cache.relative_to(REPO_ROOT)} (sha256 verified)")
            return cache
        # A stale cache is not automatically an integrity failure -- a
        # truncated earlier download looks identical here.  Re-fetch once and
        # let the post-download check make the call.
        progress(f"cache STALE {cache.relative_to(REPO_ROOT)} -- hash differs, re-fetching")
        if not allow_download:
            raise IntegrityError(
                f"cached archive {cache} has sha256 {actual}, manifest pins {expected}"
            )
    elif not allow_download:
        raise InfraError(f"archive not cached at {cache} and downloading is disabled")

    cache.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_suffix(cache.suffix + ".part")
    progress(f"fetching    {archive['url']}")
    try:
        req = urllib.request.Request(
            archive["url"], headers={"User-Agent": "vibe-cading reference fetch"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp, tmp.open("wb") as fh:
            while True:
                block = resp.read(1 << 20)
                if not block:
                    break
                fh.write(block)
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        tmp.unlink(missing_ok=True)
        raise InfraError(f"could not download {archive['url']}: {exc}") from exc

    actual = _sha256(tmp)
    if actual != expected:
        # Keep the evidence: a human has to decide whether upstream moved
        # legitimately, and deleting the file would destroy what they need.
        bad = cache.with_suffix(cache.suffix + ".unverified")
        tmp.replace(bad)
        raise IntegrityError(
            f"archive hash mismatch\n"
            f"  url      {archive['url']}\n"
            f"  expected {expected}\n"
            f"  actual   {actual}\n"
            f"  saved to {bad}\n"
            f"LDraw ships periodic part updates to this same URL, so this is "
            f"most likely an upstream revision rather than corruption. Do NOT "
            f"just bump the pin: any tolerance calibrated against the old "
            f"revision must be re-reviewed first."
        )
    tmp.replace(cache)
    progress(f"verified    {cache.relative_to(REPO_ROOT)} (sha256 {actual[:16]}...)")
    return cache


class _LDrawArchive:
    """Read-only view of an LDraw distribution zip.

    Private by name deliberately: this is an implementation detail of the
    fetch step, not a geometry-producing model class, and the engine_api
    extractor catalogs every public class under ``vibe_cading/`` -- a public
    name here would publish a zip reader into the wire contract with a
    nonsense ``.solid`` accessor.

    Resolves subpart references without extracting the archive: at ~37k
    members and ~145 MB, an on-disk extraction costs far more than an index
    built once from the member list.
    """

    def __init__(self, zip_path: Path):
        self._zip = zipfile.ZipFile(zip_path)
        # LDraw references are case-insensitive and use backslash separators;
        # normalise once so lookup is a dict hit rather than a scan.
        self._index: dict[str, str] = {}
        for member in self._zip.namelist():
            if member.endswith("/"):
                continue
            self._index.setdefault(member.lower(), member)
        self._cache: dict[str, str | None] = {}

    def close(self) -> None:
        self._zip.close()

    def __enter__(self) -> "_LDrawArchive":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def read(self, name: str) -> str | None:
        """Resolve an LDraw part name to its text, or None if absent."""
        key = name.replace("\\", "/").lower()
        if key in self._cache:
            body = self._cache[key]
            return body
        member = None
        base = key.rsplit("/", 1)[-1]
        for root in ("ldraw",):
            candidates = [f"{root}/{key}"]
            candidates += [f"{root}/{d}/{key}" for d in SEARCH_DIRS]
            candidates += [f"{root}/{d}/{base}" for d in SEARCH_DIRS]
            for cand in candidates:
                if cand in self._index:
                    member = self._index[cand]
                    break
            if member:
                break
        if member is None:
            self._cache[key] = None
            return None
        body = self._zip.read(member).decode("utf-8", errors="replace")
        self._cache[key] = body
        return body


def _transform(matrix, translation, vertex):
    x, y, z = vertex
    return (
        matrix[0] * x + matrix[1] * y + matrix[2] * z + translation[0],
        matrix[3] * x + matrix[4] * y + matrix[5] * z + translation[1],
        matrix[6] * x + matrix[7] * y + matrix[8] * z + translation[2],
    )


def _compose(outer, inner):
    """Row-major 3x3 matrix product, outer * inner."""
    return [
        sum(outer[r * 3 + k] * inner[k * 3 + c] for k in range(3))
        for r in range(3)
        for c in range(3)
    ]


def collect_triangles(archive: _LDrawArchive, name: str) -> tuple[list, set]:
    """Flatten an LDraw part into a triangle soup, in raw LDU coordinates.

    Returns ``(triangles, missing)``.  ``missing`` names every subpart that
    could not be resolved -- reported rather than swallowed, because a
    silently-dropped subpart yields a mesh that looks plausible and is
    quietly incomplete.
    """
    triangles: list[tuple] = []
    missing: set[str] = set()

    def walk(part: str, matrix=IDENTITY, translation=(0.0, 0.0, 0.0), depth=0):
        if depth > MAX_DEPTH:
            return
        body = archive.read(part)
        if body is None:
            missing.add(part)
            return
        for line in body.splitlines():
            field = line.split()
            if not field:
                continue
            try:
                if field[0] == "1" and len(field) >= 15:
                    sub_t = tuple(map(float, field[2:5]))
                    sub_m = list(map(float, field[5:14]))
                    walk(
                        field[14],
                        _compose(matrix, sub_m),
                        _transform(matrix, translation, sub_t),
                        depth + 1,
                    )
                elif field[0] in ("3", "4"):
                    n = 3 if field[0] == "3" else 4
                    verts = [
                        _transform(matrix, translation,
                                   tuple(map(float, field[2 + 3 * i:5 + 3 * i])))
                        for i in range(n)
                    ]
                    triangles.append((verts[0], verts[1], verts[2]))
                    if n == 4:
                        # LDraw quads are planar and convex by spec, so a
                        # single fan split is safe.
                        triangles.append((verts[0], verts[2], verts[3]))
            except ValueError:
                # A malformed numeric field in one line must not abort the
                # whole part; LDraw files in the wild carry stray metadata.
                continue

    walk(name)
    return triangles, missing


def to_model_frame(triangles, zref_ldu: float):
    """Map LDraw axes onto this project's Z-up model frame.

    LDraw is X / Y(vertical, -Y is up) / Z at 0.4 mm per LDU.  The mapping
    is fixed by the library and proven in the design record:

        cq_x =  ldraw_X            * 0.4
        cq_y =  ldraw_Z            * 0.4
        cq_z = (zref_ldu - ldraw_Y) * 0.4

    ``zref_ldu`` is the part's own vertical datum in its LDraw parent frame
    (0 for the lid and tray, 50 for the housing shell).  It is per-part
    manifest data rather than a constant because companion parts share one
    parent frame -- re-centring each part independently would silently break
    that shared frame and make the parts no longer assemble.
    """
    out = []
    for tri in triangles:
        out.append(tuple(
            (v[0] * LDU_MM, v[2] * LDU_MM, (zref_ldu - v[1]) * LDU_MM)
            for v in tri
        ))
    return out


def write_binary_stl(triangles, path: Path) -> None:
    """Write a binary STL.

    Facet normals are written as zero: this mesh exists to be sampled by
    ``surface_diff.py``, which derives its own normals, and a zero normal is
    the conventional "consumer should compute it" marker.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        fh.write(b"\0" * 80)
        fh.write(struct.pack("<I", len(triangles)))
        for tri in triangles:
            fh.write(struct.pack("<3f", 0.0, 0.0, 0.0))
            for vertex in tri:
                fh.write(struct.pack("<3f", *(float(c) for c in vertex)))
            fh.write(b"\0\0")


def bbox(triangles):
    """Axis-aligned bounds as (lo, hi), or None for an empty soup."""
    if not triangles:
        return None
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for tri in triangles:
        for vertex in tri:
            for i in range(3):
                lo[i] = min(lo[i], vertex[i])
                hi[i] = max(hi[i], vertex[i])
    return tuple(lo), tuple(hi)


def convert_part(archive: _LDrawArchive, entry: dict, progress=print) -> dict:
    """Resolve one manifest part to an STL and report what was written."""
    name = entry["name"]
    out = REPO_ROOT / entry["output"]
    triangles, missing = collect_triangles(archive, name)
    if not triangles:
        raise ManifestError(
            f"{name}: resolved to zero triangles -- the part is absent from the "
            f"archive or its name is wrong"
        )
    model = to_model_frame(triangles, float(entry.get("zref_ldu", 0.0)))
    write_binary_stl(model, out)

    lo, hi = bbox(model)
    progress(
        f"wrote       {out.relative_to(REPO_ROOT)}  "
        f"{len(model)} tris  "
        f"X[{lo[0]:.3f},{hi[0]:.3f}] Y[{lo[1]:.3f},{hi[1]:.3f}] Z[{lo[2]:.3f},{hi[2]:.3f}]"
    )
    if missing:
        # Loud, because an unresolved subpart produces a mesh that is
        # geometrically plausible and quietly missing a feature.
        progress(f"  WARNING   {len(missing)} unresolved subpart(s): "
                 f"{', '.join(sorted(missing)[:5])}")
    return {"name": name, "output": out, "triangles": len(model), "missing": missing}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch and convert third-party reference geometry (never committed).",
        epilog="Exit codes: 0 ok, 1 hash mismatch, 2 usage, 3 network/infra.",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST,
                        help=f"manifest path (default: {DEFAULT_MANIFEST.name})")
    parser.add_argument("--part", action="append", metavar="NAME",
                        help="convert only this part (repeatable)")
    parser.add_argument("--list", action="store_true",
                        help="print the manifest and exit; no network, no writes")
    parser.add_argument("--verify", action="store_true",
                        help="verify the cached archive only; never download")
    args = parser.parse_args(argv)

    try:
        manifest = load_manifest(args.manifest)
    except ManifestError as exc:
        print(f"ERROR (usage): {exc}", file=sys.stderr)
        return EXIT_USAGE

    archive_spec = manifest["archive"]
    entries = manifest["part"]

    if args.part:
        wanted = set(args.part)
        known = {e["name"] for e in entries}
        unknown = wanted - known
        if unknown:
            print(f"ERROR (usage): unknown part(s): {', '.join(sorted(unknown))}\n"
                  f"  known: {', '.join(sorted(known))}", file=sys.stderr)
            return EXIT_USAGE
        entries = [e for e in entries if e["name"] in wanted]

    if args.list:
        print(f"archive  {archive_spec['url']}")
        print(f"sha256   {archive_spec['sha256']}")
        print(f"cache    {archive_spec['cache']}")
        if archive_spec.get("license"):
            print(f"license  {archive_spec['license']}")
        print()
        for entry in entries:
            print(f"  {entry['name']:<16} -> {entry['output']}"
                  f"   zref={entry.get('zref_ldu', 0.0)} LDU")
            if entry.get("description"):
                print(f"    {entry['description']}")
        return EXIT_OK

    try:
        archive_path = ensure_archive(archive_spec, allow_download=not args.verify)
    except IntegrityError as exc:
        print(f"ERROR (integrity): {exc}", file=sys.stderr)
        return EXIT_INTEGRITY
    except InfraError as exc:
        print(f"ERROR (infra): {exc}\n"
              f"  The reference could not be retrieved. This is an "
              f"infrastructure failure, NOT a conformance pass.", file=sys.stderr)
        return EXIT_INFRA

    if args.verify:
        print("OK: cached archive matches the manifest pin.")
        return EXIT_OK

    try:
        with _LDrawArchive(archive_path) as archive:
            for entry in entries:
                convert_part(archive, entry)
    except zipfile.BadZipFile as exc:
        print(f"ERROR (integrity): {archive_path} is not a readable zip: {exc}",
              file=sys.stderr)
        return EXIT_INTEGRITY
    except ManifestError as exc:
        print(f"ERROR (usage): {exc}", file=sys.stderr)
        return EXIT_USAGE

    print(f"\n{len(entries)} reference(s) written. These files are git-ignored "
          f"and must stay that way.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
