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

"""Engine-API import-path regression test.

Design reference: §Tests T6 in
``.agents/plans/2026-05-13-pre-oss-models-structure_design.md``.

Every public class registered in ``engine_api.json`` must be importable
from its declared ``module`` path under its declared ``name``.  The test
is **driven from the JSON itself** so it never goes out of sync with the
generated artifact — if ``tools/gen_engine_api.py`` adds a new class
under a different namespace, the test follows automatically.

This catches three concrete classes of regression:

1. A class moves between subpackages but ``engine_api.json`` is
   regenerated without the test catching the rename (e.g. the
   ``AxleSleeve`` → ``TechnicAxleToBearingSleeve`` rename in Phase 1).
2. An ``__init__.py`` re-export is forgotten after a file split.
3. A new dependency at import time crashes one specific module
   (``ImportError`` / ``AttributeError`` at the call site).
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ENGINE_API_JSON = _REPO_ROOT / "engine_api.json"


def _load_engine_api_classes() -> list[tuple[str, str, str]]:
    """Return ``[(module, name, fqn), ...]`` for every class in the JSON."""
    if not _ENGINE_API_JSON.exists():
        # Surface this as a single skipped test case rather than crashing
        # collection — the engine_api gate has its own CI workflow that
        # ensures the file is regenerated when it drifts.
        return []
    with open(_ENGINE_API_JSON, "r") as f:
        data = json.load(f)
    cases = []
    for entry in data.get("classes", []):
        module = entry["module"]
        name = entry["name"]
        fqn = entry.get("fqn", f"{module}.{name}")
        cases.append((module, name, fqn))
    return cases


_CASES = _load_engine_api_classes()


def _case_id(case):
    return case[2]  # fqn


def test_engine_api_json_present():
    """``engine_api.json`` exists at the repo root.

    Driven separately so the parametrised import test surfaces a single
    helpful failure rather than a confusing zero-collection situation.
    """
    assert _ENGINE_API_JSON.exists(), (
        f"engine_api.json missing at {_ENGINE_API_JSON} — run "
        "``python3 tools/gen_engine_api.py`` to regenerate."
    )


def test_engine_api_json_non_empty():
    """The JSON declares at least one class (sanity bound)."""
    assert len(_CASES) > 0, "engine_api.json contains zero classes"


@pytest.mark.parametrize("case", _CASES, ids=_case_id)
def test_class_importable_from_declared_module(case):
    """Every ``engine_api.json`` entry resolves to a real class object."""
    module_path, class_name, fqn = case
    module = importlib.import_module(module_path)
    assert hasattr(module, class_name), (
        f"{fqn} declared in engine_api.json but {class_name} is "
        f"not exported from {module_path}"
    )
    cls = getattr(module, class_name)
    assert isinstance(cls, type), (
        f"{fqn} resolves to {type(cls).__name__}, expected a class"
    )
