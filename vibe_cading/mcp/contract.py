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

"""The MCP tool-contract version and its evolution policy (R8).

Single source of truth for ``TOOL_CONTRACT_VERSION`` — the version of the MCP
*tool surface* (tool names, argument schemas, result shapes).  It is **echoed
on every tool result** (the ``tool_contract_version`` field) and is asserted by
the tool-contract snapshot test, so the version field is *enforced*, not
aspirational.

This is **separate** from ``engine_api.json``'s ``schema_version``, which
versions the *class records* introspection reads — not the *tool signatures*.
Each result that surfaces class data therefore carries two distinct version
fields (``tool_contract_version`` here + ``engine_api_schema_version`` echoed
from the JSON), with independent bump cadences.

SDK-free by construction (it holds only a string + this policy docstring) so the
version and its snapshot test do not need the ``mcp`` SDK installed.

Additive-vs-breaking policy
---------------------------
Mirrors the ``engine_api`` additive discipline.

* **Additive ⇒ bump minor** (e.g. ``1.0`` → ``1.1``): add a new optional arg
  *with a default*; add a new tool; add a new field to a result envelope; add a
  name to the ``get_design_context`` constant allowlist.  Existing clients keep
  working unchanged.

  *Concrete example:* adding ``return_inline: bool = false`` to
  ``compile_model`` — old clients that never send it get the prior
  file-path-only behaviour.

* **Breaking ⇒ bump major** (e.g. ``1.0`` → ``2.0``): rename or remove a tool
  or an arg; change an arg's type or required-ness; change a result field's
  name/type/meaning; change the ``query_engine_class`` lookup-key semantics.

  *Concrete example:* renaming ``query_engine_class``'s ``class_key`` arg to
  ``fqn`` — a client pinned to ``class_key`` silently sends an unknown arg and
  breaks.

When the tool surface changes, update both this constant and the committed
snapshot fixture (``tests/mcp/tool_contract_snapshot.json``) in the **same PR**
(regenerate with ``python -m pytest`` after running the snapshot test's
``--update`` path, per its module docstring).
"""

from __future__ import annotations

TOOL_CONTRACT_VERSION = "1.0"
