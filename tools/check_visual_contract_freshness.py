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

#!/usr/bin/env python3
"""
Visual-contract SVG freshness check.

Enforces the ``committed == regenerable`` invariant for the project's visual
contracts: every tracked ``.agents/plans/*_design_*.svg`` registered in
``visual_contracts.toml`` is re-rendered from its source class and byte-compared
against the committed file.  A drifted contract (the model class was refactored
but the committed SVG was never refreshed) fails the check.

The render path is **not** re-implemented here — the tool imports and calls
``tools.preview.export_previews`` (which transitively uses
``tools.model_loader``), so the regeneration pipeline is provably identical to
the one that produced the committed contracts.  In particular this tool never
calls the low-level SVG exporter and never rounds coordinates itself; doing so
would create a second source of truth that could drift from ``preview.py``.

Two gates run:

1. **Coverage gate** — every tracked ``*_design_*.svg`` under the plans dir must
   be registered in the manifest, and every manifest ``svg`` target must exist.
   Either direction failing is a "manifest rot" signal.
2. **Freshness gate** — each manifest entry is regenerated into a temporary
   directory and byte-compared against its committed ``svg`` file.

Usage
-----
    python3 tools/check_visual_contract_freshness.py [--update]
                  [--manifest PATH] [--plans-dir PATH]

    --update      Regenerate every manifest entry and overwrite the committed
                  SVG in place (refresh mode).  Reports which files changed and
                  exits 0; does NOT fail on diff.
    --manifest    Override the manifest path (default: <repo>/visual_contracts.toml).
    --plans-dir   Override the design-SVG directory the coverage gate globs
                  (default: <repo>/.agents/plans).

The ``--manifest`` / ``--plans-dir`` overrides exist so negative-path tests can
exercise the gates against a ``tmp/`` scratch manifest + dir without perturbing
the tracked ``.agents/plans/`` tree.

Interpreter note
----------------
CadQuery lives on the ``python3.11`` interpreter in this container (the default
``python3`` is 3.13 without cadquery).  Run this tool — and the ``--update``
refresh it suggests — under ``python3.11`` locally.  In CI, ``python3`` already
resolves to the 3.11 interpreter ``actions/setup-python`` pins, so the CI step
invokes it as plain ``python3``.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import tomllib
from pathlib import Path

# ── Canonical-profile pin (load-bearing — see design Phase-B finding) ─────────
# Visual contracts are canonical *shipped-default-profile* (``fdm_standard``)
# renderings: a contract must be a pure function of *tracked* repo state so it
# regenerates byte-identically in CI and in any fresh clone.  The profile-
# dependent contracts (the beam + axle-cross gauges) resolve their tolerance
# profile internally via ``get_profile()``, which reads ``PRINT_PROFILE`` at
# model-instantiation time.  A contributor's local ``.env`` (e.g.
# PRINT_PROFILE="bambu_p1s") would otherwise leak a non-shipped profile into the
# render and report *false drift* against the canonical committed bytes.
#
# We force ``fdm_standard`` here, BEFORE importing ``tools.preview`` (which
# transitively imports the model modules → ``vibe_cading.print_settings``, whose
# import-time ``load_env_file()`` seeds the ``.env``).  That seeder uses
# ``os.environ.setdefault`` (``vibe_cading/_env.py``), so a value already present
# in ``os.environ`` *wins* over the file — setting it first makes the forced
# profile authoritative regardless of any local ``.env``.  ``--update`` shares
# this module path, so refreshes are pinned to the same canonical profile.
#
# Residual assumption (cheap-fix boundary): a contributor who *also* maintains a
# local ``print_profiles_user.json`` that redefines ``fdm_standard``'s own leaves
# would still shadow the shipped values, because ``_load_json_profiles()`` deep-
# merges the user file over the shipped defaults at the leaf level.  Suppressing
# that merge would require a new hook in the shared ``print_settings`` loader
# (out-of-scope shared-surface change), so it is documented rather than coded:
# the check is reproducible iff no local user-file override of ``fdm_standard``
# exists.  CI and fresh clones carry no user file at all, so the canonical path
# is unaffected; only a self-inflicted local override of fdm_standard would drift.
os.environ["PRINT_PROFILE"] = "fdm_standard"

# tools/model_loader.py owns sys.path management.  Add REPO_ROOT here so the
# ``from tools.preview import export_previews`` line below resolves; the loader
# then inserts REPO_ROOT idempotently for the model imports it performs.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from tools.preview import export_previews  # noqa: E402

# Defaults are anchored to REPO_ROOT (derived from __file__), never to the
# process cwd, so the tool and its coverage glob behave identically whether
# invoked from the repo root (CI) or any subdirectory (a contributor's editor
# terminal).  --manifest / --plans-dir override these for scratch-dir testing.
DEFAULT_MANIFEST = REPO_ROOT / "visual_contracts.toml"
DEFAULT_PLANS_DIR = REPO_ROOT / ".agents" / "plans"

# Coverage-gate glob: every tracked design SVG follows the *_design_*.svg
# naming the Visual Contract rule mandates, so this glob tracks the rule.
DESIGN_SVG_GLOB = "*_design_*.svg"

# How a contributor refreshes contracts locally (see the interpreter note in
# the module docstring for why this names python3.11 rather than python3).
REFRESH_INTERPRETER = "python3.11"
REFRESH_CMD = f"{REFRESH_INTERPRETER} tools/check_visual_contract_freshness.py --update"


class Contract:
    """One manifest row: which committed SVG, which class+view+params produce it.

    ``svg`` is stored both as the manifest-relative string (for human-readable
    output that matches what a contributor typed) and as an absolute path
    resolved against the repo root (the source of truth for byte comparison).
    """

    def __init__(self, svg: str, model: str, view: str,
                 params: dict | None, repo_root: Path) -> None:
        self.svg_rel = svg
        self.model = model
        self.view = view
        self.params = params or {}
        self.svg_path = (repo_root / svg).resolve()

    def regenerate_bytes(self, tmp_dir: Path) -> bytes:
        """Render this contract into *tmp_dir* and return the produced bytes.

        Delegates entirely to ``export_previews`` (which applies the viewport
        fix + coordinate rounding internally) and reads back the *single
        returned Path* — never relying on the ``<ClassName>_<view>.svg`` name
        ``export_previews`` chooses, which differs from the committed
        design-slug filename (the FR4 indirection).
        """
        written = export_previews(
            self.model, tmp_dir, self.params, views=[self.view]
        )
        return written[0].read_bytes()


def load_manifest(manifest_path: Path, repo_root: Path) -> list[Contract]:
    """Parse the visual-contract manifest into a list of ``Contract`` objects."""
    with open(manifest_path, "rb") as f:
        data = tomllib.load(f)
    contracts: list[Contract] = []
    for row in data.get("contract", []):
        contracts.append(
            Contract(
                svg=row["svg"],
                model=row["model"],
                view=row["view"],
                params=row.get("params"),
                repo_root=repo_root,
            )
        )
    return contracts


def run_coverage_gate(contracts: list[Contract], plans_dir: Path) -> list[str]:
    """Bidirectional coverage gate.  Returns a list of human-readable problems.

    * A tracked design SVG that is NOT registered in the manifest → problem
      (the manifest is rotting as new design SVGs land).
    * A manifest row whose ``svg`` target does not exist on disk → problem
      (a registered contract has gone missing).
    """
    problems: list[str] = []

    registered = {c.svg_path for c in contracts}
    tracked = {p.resolve() for p in plans_dir.glob(DESIGN_SVG_GLOB)}

    unregistered = sorted(tracked - registered)
    for svg in unregistered:
        rel = _display_path(svg)
        problems.append(
            f"UNREGISTERED: tracked design SVG not in the manifest: {rel}\n"
            f"    Add a [[contract]] entry for it in visual_contracts.toml."
        )

    for contract in contracts:
        if not contract.svg_path.exists():
            problems.append(
                f"MISSING TARGET: manifest row points at a non-existent file: "
                f"{contract.svg_rel}\n"
                f"    Either restore the file or remove the [[contract]] row."
            )

    return problems


def run_freshness_check(contracts: list[Contract]) -> list[Contract]:
    """Regenerate every contract and return the list of drifted ones."""
    drifted: list[Contract] = []
    for contract in contracts:
        if not contract.svg_path.exists():
            # Missing-target case is reported by the coverage gate; skip the
            # byte-compare so we do not crash reading a non-existent file.
            continue
        committed = contract.svg_path.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            regenerated = contract.regenerate_bytes(Path(tmp))
        if regenerated != committed:
            drifted.append(contract)
    return drifted


def run_update(contracts: list[Contract]) -> list[Contract]:
    """Regenerate every contract and overwrite the committed file in place.

    Returns the list of contracts whose committed bytes actually changed.
    """
    changed: list[Contract] = []
    for contract in contracts:
        existed = contract.svg_path.exists()
        before = contract.svg_path.read_bytes() if existed else None
        with tempfile.TemporaryDirectory() as tmp:
            regenerated = contract.regenerate_bytes(Path(tmp))
        if regenerated != before:
            contract.svg_path.parent.mkdir(parents=True, exist_ok=True)
            contract.svg_path.write_bytes(regenerated)
            changed.append(contract)
    return changed


def _display_path(path: Path) -> str:
    """Return *path* relative to REPO_ROOT when possible, else as-is."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check that every committed visual-contract SVG regenerates "
            "byte-for-byte from its source class."
        ),
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help=(
            "Regenerate every manifest entry and overwrite the committed SVG "
            "in place (refresh mode); reports changed files and exits 0."
        ),
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="Manifest path (default: <repo>/visual_contracts.toml).",
    )
    parser.add_argument(
        "--plans-dir",
        default=str(DEFAULT_PLANS_DIR),
        help="Directory the coverage gate globs (default: <repo>/.agents/plans).",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    plans_dir = Path(args.plans_dir).resolve()
    # Manifest-relative svg fields resolve against the manifest's own directory
    # so a scratch manifest in tmp/ can reference scratch SVGs sitting beside it.
    manifest_root = manifest_path.parent

    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    contracts = load_manifest(manifest_path, manifest_root)
    total = len(contracts)

    # ── --update refresh mode ──────────────────────────────────────────────
    if args.update:
        changed = run_update(contracts)
        if changed:
            print(f"Refreshed {len(changed)} / {total} contract(s):")
            for c in changed:
                print(f"  UPDATED {c.svg_rel}")
        else:
            print(f"All {total} contract(s) already fresh — nothing to update.")
        return 0

    # ── read-only check mode (CI default) ──────────────────────────────────
    coverage_problems = run_coverage_gate(contracts, plans_dir)
    drifted = run_freshness_check(contracts)

    fresh = total - len(drifted)
    print(f"{fresh} / {total} contracts fresh, {len(drifted)} drifted")

    if not coverage_problems and not drifted:
        print("Coverage gate: PASS — every tracked design SVG is registered "
              "and every manifest target exists.")
        return 0

    if coverage_problems:
        print("\nCoverage gate: FAIL")
        for problem in coverage_problems:
            print(f"  {problem}")

    if drifted:
        print("\nVisual contracts DRIFTED from their source class:")
        for c in drifted:
            print(f"  DRIFT {c.svg_rel}")
            print(f"        source: {c.model}  view={c.view}"
                  + (f"  params={c.params}" if c.params else ""))
        print(
            "\nTo refresh all contracts (run under the cadquery interpreter — "
            f"{REFRESH_INTERPRETER} here; default python3 is 3.13 without "
            "cadquery):\n"
            f"    {REFRESH_CMD}\n"
            "If you just bumped cadquery / OCCT, a drift across all contracts "
            "is expected — run --update in the same PR that bumps the dep."
        )

    return 1


if __name__ == "__main__":
    sys.exit(main())
