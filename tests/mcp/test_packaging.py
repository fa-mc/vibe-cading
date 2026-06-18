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

"""Packaging tests for the optional ``[mcp]`` extra (R5, test #8).

Asserts ``pyproject.toml`` declares ``mcp`` under
``[project.optional-dependencies]`` pinned ``mcp>=1,<2`` and that the mandatory
``dependencies`` were NOT touched (``mcp`` must never resolve for a plain
``pip install vibe_cading``).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

_PYPROJECT = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"


def _load() -> dict:
    with _PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)


def test_mcp_extra_declared_and_pinned():
    cfg = _load()
    extras = cfg["project"]["optional-dependencies"]
    assert "mcp" in extras
    assert extras["mcp"] == ["mcp>=1,<2"]


def test_mcp_not_in_mandatory_dependencies():
    cfg = _load()
    deps = cfg["project"]["dependencies"]
    # mandatory deps are untouched — exactly cadquery, no mcp / ASGI stack.
    assert deps == ["cadquery"]
    joined = " ".join(deps).lower()
    assert "mcp" not in joined
    for leaked in ("starlette", "uvicorn", "sse-starlette", "pydantic"):
        assert leaked not in joined
