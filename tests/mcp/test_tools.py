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

"""Handler unit tests for ``vibe_cading.mcp.tools`` (R2/R4/R10).

These call each tool handler **directly** — no MCP SDK, no subprocess.  They run
in the ``mcp``-absent lint stage, which is what *enforces* the SDK-free
discipline of ``tools.py`` (a stray top-level ``import mcp`` would fail
collection here).  The ``compile_model`` rows need CadQuery and are gated with
``pytest.importorskip("cadquery")``.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from vibe_cading.mcp import tools as T
from vibe_cading.mcp.contract import TOOL_CONTRACT_VERSION

# A real, cheap class present in the committed engine_api.json.
_REAL_FQN = "vibe_cading.lego.technic_beam.LegoTechnicBeam"
_REAL_NAME = "LegoTechnicBeam"
_REAL_PARAMS = {"length_in_studs": 3}


# --------------------------------------------------------------------------
# Test #2 — list_engine_classes: reads committed JSON, deterministic, filters
# --------------------------------------------------------------------------

def test_list_engine_classes_reads_committed_json():
    r = T.list_engine_classes({})
    assert r["tool_contract_version"] == TOOL_CONTRACT_VERSION
    # engine_api_schema_version comes verbatim from the committed JSON.
    assert r["engine_api_schema_version"]
    # count == len(classes) invariant.
    assert r["count"] == len(r["classes"])
    assert r["count"] > 0
    # summary fields only (not the full record).
    sample = r["classes"][0]
    assert set(sample.keys()) == {"fqn", "name", "module", "doc_summary"}


def test_list_engine_classes_deterministic():
    # Same JSON ⇒ byte-identical introspection output (R2 / NFC determinism).
    a = json.dumps(T.list_engine_classes({}), sort_keys=True)
    b = json.dumps(T.list_engine_classes({}), sort_keys=True)
    assert a == b


def test_list_engine_classes_module_prefix_filter():
    full = T.list_engine_classes({})["count"]
    filtered = T.list_engine_classes({"module_prefix": "vibe_cading.mechanical"})
    assert 0 < filtered["count"] < full
    assert all(
        c["fqn"].startswith("vibe_cading.mechanical")
        or c["module"].startswith("vibe_cading.mechanical")
        for c in filtered["classes"]
    )


def test_list_engine_classes_name_contains_filter():
    filtered = T.list_engine_classes({"name_contains": "beam"})
    assert filtered["count"] >= 1
    # case-insensitive substring on the short name.
    assert all("beam" in c["name"].lower() for c in filtered["classes"])


# --------------------------------------------------------------------------
# Test #3 — query_engine_class: fqn hit, short fallback, ambiguous, miss
# --------------------------------------------------------------------------

def test_query_engine_class_exact_fqn():
    r = T.query_engine_class({"class_key": _REAL_FQN})
    assert r["class"]["fqn"] == _REAL_FQN
    assert r["class"]["name"] == _REAL_NAME
    # full record carries constructors/result_accessor verbatim.
    assert "constructors" in r["class"]
    assert "result_accessor" in r["class"]
    assert r["tool_contract_version"] == TOOL_CONTRACT_VERSION


def test_query_engine_class_short_name_fallback():
    r = T.query_engine_class({"class_key": _REAL_NAME})
    assert r["class"]["fqn"] == _REAL_FQN


def test_query_engine_class_miss_raises_class_not_found():
    with pytest.raises(T._ToolError) as exc:
        T.query_engine_class({"class_key": "no.such.Class"})
    assert exc.value.error_code == "class_not_found"


def test_query_engine_class_ambiguous_short_name(monkeypatch):
    # The real catalog has no duplicate short names, so synthesize one to prove
    # ambiguity is reported (never silently resolved).
    fake_api = {
        "schema_version": "1.1",
        "classes": [
            {"fqn": "a.b.Dup", "name": "Dup", "module": "a.b"},
            {"fqn": "c.d.Dup", "name": "Dup", "module": "c.d"},
        ],
    }
    monkeypatch.setattr(T, "_load_engine_api", lambda: fake_api)
    with pytest.raises(T._ToolError) as exc:
        T.query_engine_class({"class_key": "Dup"})
    assert exc.value.error_code == "ambiguous_class"
    # both candidate fqns are surfaced in the detail.
    assert "a.b.Dup" in exc.value.detail and "c.d.Dup" in exc.value.detail


def test_query_engine_class_match_short_forces_short_path(monkeypatch):
    # match='short' must NOT match on fqn even if the key looks like an fqn.
    fake_api = {
        "schema_version": "1.1",
        "classes": [{"fqn": "a.b.Widget", "name": "Widget", "module": "a.b"}],
    }
    monkeypatch.setattr(T, "_load_engine_api", lambda: fake_api)
    # key == the fqn but match='short' -> short-name lookup fails -> miss.
    with pytest.raises(T._ToolError) as exc:
        T.query_engine_class({"class_key": "a.b.Widget", "match": "short"})
    assert exc.value.error_code == "class_not_found"


# --------------------------------------------------------------------------
# Test #6 [CQ] — compile_model step output under a namespaced OS-temp dir
# --------------------------------------------------------------------------

def test_compile_model_step_output_under_temp():
    pytest.importorskip("cadquery")
    r = T.compile_model({"class_path": _REAL_FQN, "params": _REAL_PARAMS})
    assert r["tool_contract_version"] == TOOL_CONTRACT_VERSION
    assert len(r["artifacts"]) == 1
    art = r["artifacts"][0]
    assert art["format"] == "step"
    p = Path(art["path"])
    assert p.exists()
    # under the OS temp root, namespaced, NOT in the repo tree.
    assert str(p).startswith(tempfile.gettempdir())
    assert "vibe_cading_mcp_" in str(p)
    repo_root = Path(__file__).resolve().parent.parent.parent
    assert not str(p).startswith(str(repo_root))


def test_compile_model_stl_output():
    pytest.importorskip("cadquery")
    r = T.compile_model(
        {"class_path": _REAL_FQN, "params": _REAL_PARAMS, "outputs": ["stl"]}
    )
    art = r["artifacts"][0]
    assert art["format"] == "stl"
    assert Path(art["path"]).exists()


# --------------------------------------------------------------------------
# Test #7 [CQ] — compile_model svg via export_previews; inline cap behaviour
# --------------------------------------------------------------------------

def test_compile_model_svg_inline_under_cap():
    pytest.importorskip("cadquery")
    r = T.compile_model(
        {
            "class_path": _REAL_FQN,
            "params": _REAL_PARAMS,
            "outputs": ["svg"],
            "return_inline": True,
        }
    )
    art = r["artifacts"][0]
    assert art["format"] == "svg"
    assert art["view"] == "iso_ne"
    assert Path(art["path"]).exists()
    # a small beam SVG is well under 256 KiB -> inline present, no note.
    assert "inline" in art
    assert art["inline"].lstrip().startswith("<")
    assert "note" not in art


def test_compile_model_svg_no_inline_by_default():
    pytest.importorskip("cadquery")
    r = T.compile_model(
        {"class_path": _REAL_FQN, "params": _REAL_PARAMS, "outputs": ["svg"]}
    )
    art = r["artifacts"][0]
    assert "inline" not in art  # default return_inline=false -> path only
    assert "path" in art


def test_compile_model_svg_over_cap_omits_inline(monkeypatch):
    pytest.importorskip("cadquery")
    # Force the cap to 1 byte so any real SVG exceeds it.
    monkeypatch.setattr(T, "MAX_INLINE_SVG_BYTES", 1)
    r = T.compile_model(
        {
            "class_path": _REAL_FQN,
            "params": _REAL_PARAMS,
            "outputs": ["svg"],
            "return_inline": True,
        }
    )
    art = r["artifacts"][0]
    assert "inline" not in art
    assert art["note"] == "svg exceeded inline cap; path-only"
    assert Path(art["path"]).exists()  # path still returned


# --------------------------------------------------------------------------
# Test #14 — AGPL header presence on every non-empty new .py
# --------------------------------------------------------------------------

def test_new_mcp_files_carry_agpl_header():
    repo_root = Path(__file__).resolve().parent.parent.parent
    snippet = "vibe-cading is free software: you can redistribute it and/or modify"
    new_files = [
        repo_root / "vibe_cading" / "mcp" / "__init__.py",
        repo_root / "vibe_cading" / "mcp" / "__main__.py",
        repo_root / "vibe_cading" / "mcp" / "server.py",
        repo_root / "vibe_cading" / "mcp" / "tools.py",
        repo_root / "vibe_cading" / "mcp" / "context.py",
        repo_root / "vibe_cading" / "mcp" / "contract.py",
        repo_root / "vibe_cading" / "tools" / "check_mcp_import_isolation.py",
    ]
    for f in new_files:
        assert f.exists(), f"{f} missing"
        assert snippet in f.read_text(encoding="utf-8"), f"{f} missing AGPL header"
