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

"""Error-envelope mapping tests for ``vibe_cading.mcp`` (R9, test #13).

Two layers:

* **Handler layer (SDK-free).**  Each documented exception class maps to the
  right ``error_code`` on the raised :class:`tools._ToolError`.  ``compile_*``
  geometry rows are gated ``pytest.importorskip("cadquery")``.
* **Adapter layer (SDK-gated).**  ``server._dispatch`` converts a ``_ToolError``
  (and any unexpected exception) into a ``CallToolResult`` with ``isError=True``
  and a structured-JSON text block — **no traceback escapes**.
"""

from __future__ import annotations

import json

import pytest

from vibe_cading.mcp import tools as T

_REAL_FQN = "vibe_cading.lego.technic_beam.LegoTechnicBeam"
_REAL_PARAMS = {"length_in_studs": 3}


# --------------------------------------------------------------------------
# Handler-layer mapping (SDK-free)
# --------------------------------------------------------------------------

def test_bad_class_path_no_dot():
    pytest.importorskip("cadquery")
    with pytest.raises(T._ToolError) as exc:
        T.compile_model({"class_path": "NoDotHere"})
    assert exc.value.error_code == "bad_class_path"
    assert exc.value.detail == "NoDotHere"


def test_module_not_found():
    pytest.importorskip("cadquery")
    with pytest.raises(T._ToolError) as exc:
        T.compile_model({"class_path": "nonexistent_pkg.mod.Klass"})
    assert exc.value.error_code == "module_not_found"


def test_class_not_found_on_compile():
    pytest.importorskip("cadquery")
    # module imports fine, class missing.
    with pytest.raises(T._ToolError) as exc:
        T.compile_model(
            {"class_path": "vibe_cading.lego.technic_beam.NoSuchClass"}
        )
    assert exc.value.error_code == "class_not_found"


def test_bad_params_constructor_rejects():
    pytest.importorskip("cadquery")
    with pytest.raises(T._ToolError) as exc:
        T.compile_model({"class_path": _REAL_FQN, "params": {"bogus": 1}})
    assert exc.value.error_code == "bad_params"


def test_bad_params_non_object():
    # params not a dict -> bad_params, no CadQuery needed (caught before import).
    with pytest.raises(T._ToolError) as exc:
        T.compile_model({"class_path": _REAL_FQN, "params": "not-a-dict"})
    assert exc.value.error_code == "bad_params"


def test_bad_view():
    pytest.importorskip("cadquery")
    with pytest.raises(T._ToolError) as exc:
        T.compile_model(
            {
                "class_path": _REAL_FQN,
                "params": _REAL_PARAMS,
                "outputs": ["svg"],
                "views": ["not_a_real_view"],
            }
        )
    assert exc.value.error_code == "bad_view"


def test_bad_output_format():
    # unknown output format is caught before any CadQuery import.
    with pytest.raises(T._ToolError) as exc:
        T.compile_model({"class_path": _REAL_FQN, "outputs": ["dwg"]})
    assert exc.value.error_code == "bad_params"


def test_query_miss_and_empty_key():
    with pytest.raises(T._ToolError) as exc:
        T.query_engine_class({"class_key": "no.such.Class"})
    assert exc.value.error_code == "class_not_found"
    with pytest.raises(T._ToolError) as exc2:
        T.query_engine_class({"class_key": ""})
    assert exc2.value.error_code == "bad_params"


# --------------------------------------------------------------------------
# Adapter-layer: _ToolError / unexpected exception -> isError, no crash
# --------------------------------------------------------------------------

def test_dispatch_wraps_toolerror_as_iserror():
    pytest.importorskip("mcp")
    from vibe_cading.mcp import server

    def boom(_args):
        raise T._ToolError("bad_params", "nope", "detail-x")

    result = server._dispatch(boom, {})
    assert result.isError is True
    payload = json.loads(result.content[0].text)
    assert payload["error_code"] == "bad_params"
    assert payload["message"] == "nope"
    assert payload["detail"] == "detail-x"


def test_dispatch_wraps_unexpected_exception_as_compile_failed():
    pytest.importorskip("mcp")
    from vibe_cading.mcp import server

    def boom(_args):
        raise RuntimeError("kernel exploded")

    result = server._dispatch(boom, {})
    assert result.isError is True
    payload = json.loads(result.content[0].text)
    # broad catch-all -> compile_failed, never a transport crash / escaping trace.
    assert payload["error_code"] == "compile_failed"
    assert "RuntimeError" in payload["detail"]


def test_dispatch_success_is_not_error():
    pytest.importorskip("mcp")
    from vibe_cading.mcp import server

    result = server._dispatch(lambda _a: {"ok": True}, {})
    assert result.isError is False
    assert json.loads(result.content[0].text) == {"ok": True}
