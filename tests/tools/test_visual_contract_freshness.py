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

"""Guards for the visual-contract freshness checker's coverage gate.

Regression guard for a silent gap: ``DEFAULT_PLANS_DIR`` pointed at the
pre-pip-package ``.agents/plans`` directory, which no longer exists, so the
coverage gate globbed an empty set and passed *vacuously* — an unregistered
design SVG could never be caught. These tests fail if the default is ever
repointed away from the real ``visual_contracts/`` tree, or if the gate goes
trivial (zero design SVGs scanned).
"""

from vibe_cading.tools.check_visual_contract_freshness import (
    DEFAULT_MANIFEST,
    DEFAULT_PLANS_DIR,
    DESIGN_SVG_GLOB,
    REPO_ROOT,
    load_manifest,
    run_coverage_gate,
)


def test_default_plans_dir_is_visual_contracts_and_exists() -> None:
    """The default design-SVG dir must be the tracked visual_contracts/ tree."""
    assert DEFAULT_PLANS_DIR == REPO_ROOT / "visual_contracts"
    assert DEFAULT_PLANS_DIR.is_dir(), f"{DEFAULT_PLANS_DIR} does not exist"


def test_coverage_gate_is_non_trivial() -> None:
    """The gate must actually scan tracked design SVGs — a nonexistent/empty
    default dir would pass vacuously (the original bug)."""
    svgs = list(DEFAULT_PLANS_DIR.glob(DESIGN_SVG_GLOB))
    assert len(svgs) >= 1, (
        f"coverage gate would no-op: no {DESIGN_SVG_GLOB} under {DEFAULT_PLANS_DIR}"
    )


def test_default_coverage_gate_passes() -> None:
    """Every tracked design SVG under the default dir is registered, and every
    manifest target exists (bidirectional manifest-rot check)."""
    contracts = load_manifest(DEFAULT_MANIFEST, REPO_ROOT)
    problems = run_coverage_gate(contracts, DEFAULT_PLANS_DIR)
    assert problems == [], problems
