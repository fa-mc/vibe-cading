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

"""``python -m vibe_cading.mcp`` entry point (R1/R6).

Owns the two responsibilities the design assigns this file:

1. **Missing-extra UX (R6).**  The ``mcp`` SDK is an *optional* extra.  This
   module attempts the SDK import inside a ``try/except ImportError`` and, if it
   is missing, prints **one** actionable line naming
   ``pip install -e ".[mcp]"`` and exits non-zero — never a raw traceback.

2. **stdio-transport bootstrap (R1).**  On a successful import it runs the
   ``server.build_server()`` ``Server`` over MCP stdio (JSON-RPC on
   stdin/stdout) — no network listener, no port, no API key.

This is one of exactly two files (with ``server.py``) permitted to import the
``mcp`` SDK.  It carries no ``__name__``-comparison guard (a ``__main__`` module
body runs directly under ``python -m``), so it does not trip
``check_no_main_blocks.py`` — and this docstring deliberately avoids spelling
out the literal guarded form, which the grep belt-and-braces twin would match.

> **AGPL §13 posture.**  The stdio transport is intentionally **not** an AGPL
> §13 network-interaction surface — stdin/stdout is not "interacting through a
> computer network", there is no network listener, and the server is
> single-tenant local-trust, so §13's remote-source-offer obligation is not
> engaged.  Any *future* HTTP/SSE/WebSocket transport (which the ``uvicorn`` /
> ``starlette`` already in the ``mcp`` dependency tree make trivially reachable)
> WOULD engage §13 and require a Corresponding-Source offer to remote users —
> do not add one without that licensing call.

> **SDK surface** — verified live against ``mcp 1.28.0`` (``mcp>=1,<2``):
> ``mcp.server.stdio.stdio_server()`` is an async context manager yielding
> ``(read_stream, write_stream)``; ``Server.run(read, write,
> initialization_options)`` drives the loop; ``Server.create_initialization_options()``
> builds the options.
"""

from __future__ import annotations

import sys

_MISSING_EXTRA_HINT = (
    "The MCP interface requires the optional 'mcp' extra.\n"
    'Install it with:  pip install -e ".[mcp]"\n'
)

try:
    # The single SDK-import gate.  asyncio is stdlib but only needed on the
    # success path, so it is imported here alongside the SDK.
    import asyncio

    from mcp.server.stdio import stdio_server

    from vibe_cading.mcp.server import build_server
except ImportError:
    # Missing extra (or a broken SDK install) — one actionable line, no
    # traceback, non-zero exit.
    sys.stderr.write(_MISSING_EXTRA_HINT)
    sys.exit(1)


async def _run() -> None:
    """Serve the engine tools over MCP stdio until the client disconnects."""
    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """Entry point for ``python -m vibe_cading.mcp``."""
    asyncio.run(_run())


main()
