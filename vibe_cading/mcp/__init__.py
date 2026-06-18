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

"""``vibe_cading.mcp`` — the engine's optional MCP (stdio) interface.

This subpackage exposes four deterministic engine tools
(``list_engine_classes``, ``query_engine_class``, ``get_design_context``,
``compile_model``) over the Model Context Protocol on **stdio**, runnable as::

    python -m vibe_cading.mcp

It is a *thin adapter* over already-validated, already-CI-fresh seams
(``vibe_cading.tools.model_loader``, ``vibe_cading.tools.preview``, the
committed ``engine_api.json``, and ``vibe_cading.print_settings``); it adds no
domain logic and no re-derivation of param-parsing, ``sys.path`` handling, or
solid resolution.

Isolation invariant (enforced by
``vibe_cading/tools/check_mcp_import_isolation.py``)
---------------------------------------------------------------------------
This module is a **package marker only**.  It MUST NOT import ``server``,
``tools``, ``context``, or the ``mcp`` SDK.  Importing the package name
therefore stays both ``mcp``-SDK-free and CadQuery-free, preserving the property
that a plain ``import vibe_cading`` never drags the optional ``mcp`` dependency
or its ASGI stack onto a library-only consumer.  Only ``__main__.py`` and
``server.py`` may import the ``mcp`` SDK; ``tools.py`` / ``context.py`` /
``contract.py`` stay SDK-free (their unit tests import them with ``mcp`` absent,
which is what enforces that discipline).
"""
