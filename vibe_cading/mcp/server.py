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

"""MCP ``Server`` construction + the SDK-facing adapter (R1/R8/R9).

This module is one of exactly **two** files (with ``__main__.py``) that may
import the ``mcp`` SDK — the isolation-guard carve-out keeps the SDK out of the
library import graph everywhere else.

It concentrates *all* SDK ceremony so ``tools.py`` / ``context.py`` /
``contract.py`` stay SDK-free and unit-testable:

* It builds the low-level ``mcp.server.Server``.
* It registers the four tools from ``tools.TOOLS`` via the SDK's
  ``@server.list_tools()`` / ``@server.call_tool()`` decorators.
* It owns the **one** ``try/except`` that converts a handler's plain-dict
  return or raised exception into the MCP wire envelope — a
  ``CallToolResult`` whose ``content`` is a single ``TextContent`` wrapping
  ``json.dumps(payload)``, with ``isError=True`` on the error path.  A Python
  traceback never escapes as a transport-level crash (R9).

> **SDK surface** — verified live against ``mcp 1.28.0`` (``mcp>=1,<2``):
> ``from mcp.server import Server`` (the low-level server); decorator-based
> registration (``@server.list_tools()`` returning ``list[types.Tool]``,
> ``@server.call_tool()`` taking ``(name, arguments)`` and returning a
> ``types.CallToolResult``); ``types.Tool`` / ``types.TextContent`` /
> ``types.CallToolResult`` constructors.  See ``__main__.py`` for the stdio
> bootstrap (``mcp.server.stdio.stdio_server`` + ``Server.run``).
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server import Server
from mcp import types

from vibe_cading.mcp.contract import TOOL_CONTRACT_VERSION
from vibe_cading.mcp.tools import TOOLS, _ToolError

SERVER_NAME = "vibe-cading-engine"


def _success_result(payload: dict[str, Any]) -> types.CallToolResult:
    """Wrap a handler's plain-dict payload in the success MCP envelope.

    The dict shapes documented throughout the design are the JSON *inside* this
    one text block — a single serialization owned here, used for both success
    and error.
    """
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(payload))],
        isError=False,
    )


def _error_result(payload: dict[str, Any]) -> types.CallToolResult:
    """Wrap a structured error object in the error MCP envelope (``isError``)."""
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(payload))],
        isError=True,
    )


def _dispatch(handler: Any, args: dict[str, Any]) -> types.CallToolResult:
    """Run one handler under the single error-envelope ``try/except`` (R9).

    A handled :class:`_ToolError` becomes its structured payload; any other
    exception becomes the broad ``compile_failed`` catch-all so a novel
    OCCT/library failure still returns a clean tool error rather than crashing
    the stdio loop.
    """
    try:
        payload = handler(args or {})
        return _success_result(payload)
    except _ToolError as exc:
        return _error_result(exc.to_payload())
    except Exception as exc:  # noqa: BLE001 — last-resort catch-all is the point
        return _error_result(
            {
                "error_code": "compile_failed",
                "message": "Tool failed during execution",
                "detail": f"{type(exc).__name__}: {exc}",
            }
        )


def build_server() -> Server:
    """Construct the MCP ``Server`` with the four engine tools registered.

    Returns the configured low-level ``Server``; ``__main__.py`` drives it over
    stdio.  Factored out so the smoke / contract-snapshot tests can introspect
    the registered tool definitions without standing up a transport.
    """
    server: Server = Server(SERVER_NAME, version=TOOL_CONTRACT_VERSION)

    # Build the SDK Tool definitions once from the SDK-free registry.
    tool_defs = [
        types.Tool(name=name, description=description, inputSchema=schema)
        for (name, _handler, schema, description) in TOOLS
    ]
    handlers = {name: handler for (name, handler, _schema, _desc) in TOOLS}

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return tool_defs

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        handler = handlers.get(name)
        if handler is None:
            # Unknown tool name — structured error, never a crash.
            return _error_result(
                {
                    "error_code": "unknown_tool",
                    "message": f"No such tool: {name!r}",
                    "detail": None,
                }
            )
        return _dispatch(handler, arguments)

    return server
