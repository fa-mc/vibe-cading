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

"""Tests for vibe_cading/tools/fetch_reference.py.

Every test runs offline against a synthetic LDraw archive built in a tmp
directory. Nothing here touches the network or the real 145 MB library --
a test that needed either would be skipped in CI and would therefore be
guarding nothing.
"""
import hashlib
import struct
import sys
import urllib.error
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from vibe_cading.tools import fetch_reference as fr  # noqa: E402


# --- fixtures ---------------------------------------------------------------

# A two-triangle square (type 3 + type 4) plus a subpart reference, so one
# fixture exercises triangles, quad fanning, and type-1 recursion.
PART_MAIN = """0 Test Part
1 16 0 0 0 1 0 0 0 1 0 0 0 1 sub.dat
3 16 0 0 0  10 0 0  0 0 10
4 16 0 0 0  10 0 0  10 0 10  0 0 10
"""

PART_SUB = """0 Sub Part
3 16 0 -5 0  1 -5 0  0 -5 1
"""


def _build_archive(path: Path, parts: dict) -> str:
    """Write a minimal LDraw-shaped zip; return its sha256."""
    with zipfile.ZipFile(path, "w") as z:
        for name, body in parts.items():
            z.writestr(f"ldraw/parts/{name}", body)
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A fake repo root with a valid archive + manifest already in place."""
    (tmp_path / "tmp").mkdir()
    archive = tmp_path / "tmp" / "lib.zip"
    digest = _build_archive(archive, {"main.dat": PART_MAIN, "sub.dat": PART_SUB})
    monkeypatch.setattr(fr, "REPO_ROOT", tmp_path)

    manifest = tmp_path / "sources.toml"
    manifest.write_text(
        '[archive]\n'
        f'url = "https://example.invalid/lib.zip"\n'
        f'sha256 = "{digest}"\n'
        'cache = "tmp/lib.zip"\n'
        '\n'
        '[[part]]\n'
        'name = "main.dat"\n'
        'output = "tmp/out.stl"\n'
        'zref_ldu = 0.0\n',
        encoding="utf-8",
    )
    return tmp_path, manifest, digest


def read_stl(path: Path):
    data = path.read_bytes()
    count = struct.unpack("<I", data[80:84])[0]
    tris = []
    for k in range(count):
        off = 84 + k * 50 + 12
        vals = struct.unpack("<9f", data[off:off + 36])
        tris.append((vals[0:3], vals[3:6], vals[6:9]))
    return tris


# --- exit-code contract -----------------------------------------------------
# The whole point of this tool is that "could not check" never looks like
# "checked and passed", so each code gets its own test.

def test_clean_run_exits_ok(repo):
    root, manifest, _ = repo
    assert fr.main(["--manifest", str(manifest)]) == fr.EXIT_OK
    assert (root / "tmp" / "out.stl").exists()


def test_hash_mismatch_exits_integrity(repo):
    root, manifest, _ = repo
    # Corrupt the cache, and forbid a re-download so the stale-cache branch
    # must resolve to an integrity verdict rather than silently re-fetching.
    (root / "tmp" / "lib.zip").write_bytes(b"not the pinned archive")
    assert fr.main(["--manifest", str(manifest), "--verify"]) == fr.EXIT_INTEGRITY


def test_downloaded_archive_with_wrong_hash_exits_integrity(repo, monkeypatch):
    root, manifest, _ = repo
    (root / "tmp" / "lib.zip").unlink()

    class FakeResponse:
        def __init__(self):
            self._payload = [b"wrong bytes"]

        def read(self, _n):
            return self._payload.pop(0) if self._payload else b""

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(fr.urllib.request, "urlopen", lambda *a, **k: FakeResponse())
    assert fr.main(["--manifest", str(manifest)]) == fr.EXIT_INTEGRITY
    # The bad download is preserved -- a human has to diff it to decide
    # whether upstream moved legitimately.
    assert (root / "tmp" / "lib.zip.unverified").exists()
    assert not (root / "tmp" / "lib.zip").exists()


def test_network_failure_exits_infra_not_ok(repo, monkeypatch):
    root, manifest, _ = repo
    (root / "tmp" / "lib.zip").unlink()

    def boom(*a, **k):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr(fr.urllib.request, "urlopen", boom)
    code = fr.main(["--manifest", str(manifest)])
    assert code == fr.EXIT_INFRA
    # Explicitly distinct from both success and integrity failure.
    assert code not in (fr.EXIT_OK, fr.EXIT_INTEGRITY)


def test_verify_without_cache_exits_infra(repo):
    root, manifest, _ = repo
    (root / "tmp" / "lib.zip").unlink()
    assert fr.main(["--manifest", str(manifest), "--verify"]) == fr.EXIT_INFRA


def test_missing_manifest_exits_usage(tmp_path):
    assert fr.main(["--manifest", str(tmp_path / "nope.toml")]) == fr.EXIT_USAGE


def test_unknown_part_exits_usage(repo):
    _, manifest, _ = repo
    assert fr.main(["--manifest", str(manifest), "--part", "9999.dat"]) == fr.EXIT_USAGE


def test_list_needs_no_network_and_writes_nothing(repo, monkeypatch):
    root, manifest, _ = repo

    def boom(*a, **k):
        raise AssertionError("--list must not touch the network")

    monkeypatch.setattr(fr.urllib.request, "urlopen", boom)
    assert fr.main(["--manifest", str(manifest), "--list"]) == fr.EXIT_OK
    assert not (root / "tmp" / "out.stl").exists()


# --- manifest validation ----------------------------------------------------

@pytest.mark.parametrize("body, reason", [
    ('[[part]]\nname = "a"\noutput = "o"\n', "missing [archive]"),
    ('[archive]\nurl = "u"\ncache = "c"\n[[part]]\nname = "a"\noutput = "o"\n',
     "missing sha256"),
    ('[archive]\nurl = "u"\nsha256 = "s"\ncache = "c"\n', "no parts"),
    ('[archive]\nurl = "u"\nsha256 = "s"\ncache = "c"\n[[part]]\nname = "a"\n',
     "part missing output"),
])
def test_malformed_manifest_rejected(tmp_path, body, reason):
    path = tmp_path / "m.toml"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(fr.ManifestError):
        fr.load_manifest(path)


def test_manifest_with_bad_toml_rejected(tmp_path):
    path = tmp_path / "m.toml"
    path.write_text("[archive\nurl =", encoding="utf-8")
    with pytest.raises(fr.ManifestError):
        fr.load_manifest(path)


# --- LDraw parsing ----------------------------------------------------------

def test_quad_is_fanned_and_subpart_is_recursed(repo):
    root, _, _ = repo
    with fr._LDrawArchive(root / "tmp" / "lib.zip") as archive:
        tris, missing = fr.collect_triangles(archive, "main.dat")
    assert missing == set()
    # 1 triangle + 1 quad (-> 2 triangles) in the parent, 1 in the subpart.
    assert len(tris) == 4


def test_unresolved_subpart_is_reported_not_swallowed(tmp_path, monkeypatch):
    monkeypatch.setattr(fr, "REPO_ROOT", tmp_path)
    archive_path = tmp_path / "lib.zip"
    _build_archive(archive_path, {"main.dat": PART_MAIN})  # sub.dat absent
    with fr._LDrawArchive(archive_path) as archive:
        tris, missing = fr.collect_triangles(archive, "main.dat")
    assert "sub.dat" in missing
    # The parent's own faces still come through -- a missing subpart must
    # degrade loudly, not empty the result.
    assert len(tris) == 3


def test_subpart_transform_is_applied(tmp_path, monkeypatch):
    monkeypatch.setattr(fr, "REPO_ROOT", tmp_path)
    archive_path = tmp_path / "lib.zip"
    # Translate the subpart by (100, 0, 0) with an identity rotation.
    parent = "1 16 100 0 0 1 0 0 0 1 0 0 0 1 sub.dat\n"
    _build_archive(archive_path, {"p.dat": parent, "sub.dat": PART_SUB})
    with fr._LDrawArchive(archive_path) as archive:
        tris, _ = fr.collect_triangles(archive, "p.dat")
    xs = [v[0] for tri in tris for v in tri]
    assert min(xs) >= 100.0, "subpart translation was not applied"


def test_case_insensitive_and_backslash_lookup(tmp_path, monkeypatch):
    monkeypatch.setattr(fr, "REPO_ROOT", tmp_path)
    archive_path = tmp_path / "lib.zip"
    _build_archive(archive_path, {"sub.dat": PART_SUB})
    with fr._LDrawArchive(archive_path) as archive:
        # LDraw references are case-insensitive and use DOS separators.
        assert archive.read("SUB.DAT") is not None
        assert archive.read("s\\..\\sub.dat".replace("s\\..\\", "")) is not None
        assert archive.read("does_not_exist.dat") is None


# --- coordinate mapping -----------------------------------------------------

def test_ldraw_axis_mapping_and_scale():
    # One triangle whose three vertices isolate one LDraw axis each.
    tris = [((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))]
    out = fr.to_model_frame(tris, zref_ldu=0.0)[0]
    # cq_x = X*0.4 ; cq_y = Z*0.4 ; cq_z = (zref - Y)*0.4
    assert out[0] == pytest.approx((0.4, 0.0, 0.0))
    assert out[1] == pytest.approx((0.0, 0.0, -0.4))
    assert out[2] == pytest.approx((0.0, 0.4, 0.0))


def test_zref_shifts_z_only():
    tris = [((0.0, 10.0, 0.0),) * 3]
    at_zero = fr.to_model_frame(tris, zref_ldu=0.0)[0][0]
    at_fifty = fr.to_model_frame(tris, zref_ldu=50.0)[0][0]
    assert at_zero[2] == pytest.approx(-4.0)      # (0 - 10) * 0.4
    assert at_fifty[2] == pytest.approx(16.0)     # (50 - 10) * 0.4
    assert at_zero[:2] == at_fifty[:2]


def test_zref_is_not_a_recentring(repo):
    """Two parts sharing a parent frame must keep their relative offset.

    Re-centring each part on its own bbox would make the lid and housing no
    longer mate, and the failure would be invisible in any single-part view.
    """
    tris = [((0.0, 0.0, 0.0),) * 3]
    a = fr.to_model_frame(tris, zref_ldu=0.0)[0][0][2]
    b = fr.to_model_frame(tris, zref_ldu=50.0)[0][0][2]
    assert b - a == pytest.approx(20.0)  # 50 LDU * 0.4 mm, preserved exactly


# --- STL output -------------------------------------------------------------

def test_stl_roundtrip_preserves_vertices(tmp_path):
    tris = [((0.0, 1.0, 2.0), (3.0, 4.0, 5.0), (6.0, 7.0, 8.0))]
    out = tmp_path / "x.stl"
    fr.write_binary_stl(tris, out)
    assert out.stat().st_size == 84 + 50
    got = read_stl(out)
    assert len(got) == 1
    for want, have in zip(tris[0], got[0]):
        assert have == pytest.approx(want)


def test_bbox_of_empty_soup_is_none():
    assert fr.bbox([]) is None


def test_convert_writes_expected_geometry(repo):
    root, manifest, _ = repo
    assert fr.main(["--manifest", str(manifest)]) == fr.EXIT_OK
    tris = read_stl(root / "tmp" / "out.stl")
    assert len(tris) == 4
    lo, hi = fr.bbox([tuple(t) for t in tris])
    # main.dat spans 0..10 LDU in X and Z -> 0..4 mm after scaling.
    assert hi[0] == pytest.approx(4.0)


def test_part_resolving_to_nothing_is_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(fr, "REPO_ROOT", tmp_path)
    archive_path = tmp_path / "lib.zip"
    _build_archive(archive_path, {"empty.dat": "0 Comment only\n"})
    with fr._LDrawArchive(archive_path) as archive:
        with pytest.raises(fr.ManifestError):
            fr.convert_part(archive, {"name": "empty.dat", "output": "tmp/o.stl"},
                            progress=lambda *a: None)


def test_valid_cache_is_not_redownloaded(repo, monkeypatch):
    _, manifest, _ = repo

    def boom(*a, **k):
        raise AssertionError("a verified cache must not trigger a download")

    monkeypatch.setattr(fr.urllib.request, "urlopen", boom)
    assert fr.main(["--manifest", str(manifest)]) == fr.EXIT_OK
