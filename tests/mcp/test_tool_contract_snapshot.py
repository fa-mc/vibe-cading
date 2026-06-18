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

"""Tool-contract snapshot test (R8, test #12).

Serializes the registered MCP tool definitions (name + arg JSON-schema +
result-shape marker) to a stable byte sequence and compares against the
committed fixture ``tests/mcp/tool_contract_snapshot.json`` — mirroring the
``gen_engine_api.py --check`` idiom (``json.dumps(..., indent=2,
sort_keys=False) + "\\n"``).  Any drift in a tool name, arg schema, or the
``TOOL_CONTRACT_VERSION`` fails CI unless the fixture and the version are
updated in the **same PR**.

Regenerate the fixture (when a tool surface change is intentional) with::

    UPDATE_MCP_CONTRACT_SNAPSHOT=1 python -m pytest \\
        tests/mcp/test_tool_contract_snapshot.py

Gated with ``pytest.importorskip("mcp")``: it introspects the SDK-registered
tool defs via ``server.build_server()``, so it needs the SDK installed.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from vibe_cading.mcp.contract import TOOL_CONTRACT_VERSION   # noqa: E402

_SNAPSHOT_PATH = Path(__file__).resolve().parent / "tool_contract_snapshot.json"


def _registered_tool_defs() -> list:
    """Introspect the SDK-registered tool definitions from ``build_server``."""
    import mcp.types as types

    from vibe_cading.mcp.server import build_server

    server = build_server()
    handler = server.request_handlers[types.ListToolsRequest]

    async def _list():
        req = types.ListToolsRequest(method="tools/list")
        result = await handler(req)
        return result.root.tools

    return asyncio.run(_list())


def _serialize_contract() -> str:
    """Produce the canonical byte sequence for the tool contract."""
    tools = _registered_tool_defs()
    payload = {
        "tool_contract_version": TOOL_CONTRACT_VERSION,
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.inputSchema,
            }
            # sort by name for a stable, registration-order-independent sequence.
            for t in sorted(tools, key=lambda t: t.name)
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def test_tool_contract_matches_snapshot():
    current = _serialize_contract()

    if os.environ.get("UPDATE_MCP_CONTRACT_SNAPSHOT") == "1":
        _SNAPSHOT_PATH.write_text(current, encoding="utf-8")
        pytest.skip("snapshot regenerated (UPDATE_MCP_CONTRACT_SNAPSHOT=1)")

    assert _SNAPSHOT_PATH.exists(), (
        "tool_contract_snapshot.json missing — regenerate with "
        "UPDATE_MCP_CONTRACT_SNAPSHOT=1 python -m pytest "
        "tests/mcp/test_tool_contract_snapshot.py"
    )
    committed = _SNAPSHOT_PATH.read_text(encoding="utf-8")
    assert current == committed, (
        "MCP tool contract drifted from the committed snapshot.  If the change "
        "is intentional, bump TOOL_CONTRACT_VERSION (per contract.py policy) and "
        "regenerate the fixture with UPDATE_MCP_CONTRACT_SNAPSHOT=1."
    )


def test_tool_contract_version_echoed_on_results():
    # The version field must actually appear on every tool result (not just in
    # the snapshot) — handler-level check, SDK-free dicts.
    from vibe_cading.mcp import tools as T

    assert T.list_engine_classes({})["tool_contract_version"] == TOOL_CONTRACT_VERSION
    q = T.query_engine_class(
        {"class_key": "vibe_cading.lego.technic_beam.LegoTechnicBeam"}
    )
    assert q["tool_contract_version"] == TOOL_CONTRACT_VERSION
