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

"""stdio smoke test for ``python -m vibe_cading.mcp`` (R1, test #1).

Spawns the server as a real subprocess and drives it with the ``mcp`` SDK's own
stdio client: a full ``initialize`` handshake plus one ``tools/call``
(``list_engine_classes``).  Asserts a well-formed response — proving the stdio
transport (no port, no listener, no API key) works end-to-end.

Gated with ``pytest.importorskip("mcp")`` so the no-``mcp`` lint stage skips it
rather than failing collection.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from mcp import ClientSession, StdioServerParameters       # noqa: E402
from mcp.client.stdio import stdio_client                   # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


async def _round_trip() -> dict:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "vibe_cading.mcp"],
        cwd=str(_REPO_ROOT),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool("list_engine_classes", {})
            return {
                "server_name": init.serverInfo.name,
                "tool_names": [t.name for t in tools.tools],
                "is_error": result.isError,
                "text": result.content[0].text if result.content else "",
            }


def test_stdio_initialize_and_tools_call():
    out = asyncio.run(asyncio.wait_for(_round_trip(), timeout=60))

    assert out["server_name"] == "vibe-cading-engine"
    # all four tools advertised over the wire.
    assert set(out["tool_names"]) == {
        "list_engine_classes",
        "query_engine_class",
        "get_design_context",
        "compile_model",
    }
    # the tools/call returned a well-formed, non-error payload.
    assert out["is_error"] is False
    payload = json.loads(out["text"])
    assert payload["count"] == len(payload["classes"])
    assert payload["count"] > 0
    assert payload["tool_contract_version"]


def test_stdio_tools_call_error_is_structured():
    async def _err_round_trip() -> dict:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "vibe_cading.mcp"],
            cwd=str(_REPO_ROOT),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "query_engine_class", {"class_key": "no.such.Class"}
                )
                return {
                    "is_error": result.isError,
                    "text": result.content[0].text if result.content else "",
                }

    out = asyncio.run(asyncio.wait_for(_err_round_trip(), timeout=60))
    assert out["is_error"] is True
    payload = json.loads(out["text"])
    assert payload["error_code"] == "class_not_found"
