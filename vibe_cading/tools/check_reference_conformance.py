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

"""Check registered components against their reference geometry.

Sibling of ``check_visual_contract_freshness.py``: that one enforces
``committed == regenerable``; this one enforces ``model == reference, except
where declared``.

The point is *per-component* conformance with **intent attached**. A whole-part
similarity figure conflates unintended drift, deliberate deviation and
reference artifacts, so it can be neither trusted nor enforced -- see
``reference_contracts.toml``'s own header for the incident behind that.

Usage
-----
    python3 vibe_cading/tools/check_reference_conformance.py
    python3 vibe_cading/tools/check_reference_conformance.py --update
    python3 vibe_cading/tools/check_reference_conformance.py --verbose

Exit codes: ``0`` pass (or skipped), ``1`` a component regressed below its
floor, ``2`` the manifest itself is invalid.

``--update`` may only RAISE a floor
-----------------------------------
It refuses to lower one. Ratcheting a threshold DOWN to accommodate a
regression is how this project shipped a non-functional latch: an accepted
interference bound was widened 45.0 -> 25.0 mm^3 across rounds with ever more
elaborate justification, when the premise itself was wrong. A floor that only
goes up cannot be used to absorb drift; lowering one is a deliberate act that
belongs in a reviewed diff with a written reason.
"""
from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from vibe_cading.tools.surface_diff import (  # noqa: E402
    InconclusiveRegion,
    compare,
    load_triangles,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "reference_contracts.toml"

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


class ManifestError(RuntimeError):
    """The manifest is malformed -- distinct from a component failing."""


def _require(entry: dict, key: str, name: str):
    if key not in entry:
        raise ManifestError(f"component {name!r} is missing required key {key!r}")
    return entry[key]


def load_manifest(path: Path = MANIFEST) -> list[dict]:
    if not path.exists():
        raise ManifestError(f"no manifest at {path}")
    data = tomllib.loads(path.read_text())
    comps = data.get("component", [])
    if not comps:
        raise ManifestError(f"{path} registers no components")
    for c in comps:
        name = c.get("name", "<unnamed>")
        for key in ("name", "model", "reference", "region", "min_agreement"):
            _require(c, key, name)
        if len(c["region"]) != 6:
            raise ManifestError(f"component {name!r}: region needs 6 numbers")
        for dev in c.get("accepted_deviation", []):
            # A deviation without a stated reason is indistinguishable from
            # drift someone got tired of fixing.
            for key in ("what", "why"):
                if not str(dev.get(key, "")).strip():
                    raise ManifestError(
                        f"component {name!r}: an accepted_deviation is missing "
                        f"{key!r}. Every declared deviation must say what it is "
                        "and why it is intended.")
    return comps


def check_component(comp: dict, *, verbose: bool = False) -> tuple[str, str, float | None]:
    """Return ``(status, message, measured_agreement)``."""
    ref_path = REPO_ROOT / comp["reference"]
    if not ref_path.exists():
        return (SKIP,
                f"reference {comp['reference']} not present locally -- this "
                "component is a contributor-local check, not a CI gate",
                None)

    excludes = [d["region"] for d in comp.get("accepted_deviation", []) if "region" in d]
    a = load_triangles(str(ref_path))
    b = load_triangles(comp["model"])
    c = compare(a, b,
                a_name=comp["reference"], b_name=comp["model"],
                region=tuple(float(v) for v in comp["region"]),
                tol=float(comp.get("tolerance", 0.2)),
                exclude=excludes)
    try:
        got = c.agreement
    except InconclusiveRegion as exc:
        # Not a pass. An empty region is the classic false-clean result.
        return (FAIL, f"INCONCLUSIVE -- {exc}", None)

    floor = float(comp["min_agreement"])
    detail = ""
    if verbose:
        detail = (f"\n      missing: max {c.a_to_b.max:.3f} mean {c.a_to_b.mean:.3f}"
                  f" (n={c.a_to_b.n})"
                  f"\n      extra:   max {c.b_to_a.max:.3f} mean {c.b_to_a.mean:.3f}"
                  f" (n={c.b_to_a.n})")
    if got + 1e-9 < floor:
        return (FAIL,
                f"agreement {got:.1f}% is below the {floor:.1f}% floor{detail}",
                got)
    return (PASS, f"agreement {got:.1f}%  (floor {floor:.1f}%){detail}", got)


def raise_floor(text: str, name: str, new: float) -> str:
    """Rewrite one component's ``min_agreement`` in the manifest text.

    Anchored to the component's own ``name`` and matching the WHOLE numeric
    literal. A naive ``text.replace(f"min_agreement = {old:g}", ...)`` is
    wrong: ``{73.0:g}`` renders ``"73"``, which matches the ``73`` inside
    ``73.0`` and leaves the trailing ``.0`` behind -- this produced
    ``min_agreement = 84.1.0`` and corrupted the manifest. Factored out of
    ``main`` so it is directly testable.
    """
    pat = re.compile(
        r'(name\s*=\s*"' + re.escape(name) + r'".*?^min_agreement\s*=\s*)'
        r'[0-9]+(?:\.[0-9]+)?',
        re.S | re.M)
    new_text, n = pat.subn(lambda mo: f"{mo.group(1)}{new:.1f}", text, count=1)
    if n != 1:
        raise ManifestError(
            f"could not locate min_agreement for component {name!r}")
    return new_text


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--update", action="store_true",
                    help="raise floors to the measured values (never lowers)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    try:
        comps = load_manifest()
    except ManifestError as exc:
        print(f"manifest error: {exc}")
        sys.exit(2)

    failed = skipped = 0
    raises: list[tuple[str, float, float]] = []
    for comp in comps:
        status, msg, got = check_component(comp, verbose=args.verbose)
        print(f"  {status}  {comp['name']}: {msg}")
        for dev in comp.get("accepted_deviation", []):
            scored = "excluded from scoring" if "region" in dev else "documented only"
            print(f"          accepted deviation ({scored}): {dev['what']}")
        if status == FAIL:
            failed += 1
        elif status == SKIP:
            skipped += 1
        if args.update and got is not None:
            floor = float(comp["min_agreement"])
            if got > floor + 1e-9:
                raises.append((comp["name"], floor, got))

    if args.update:
        if raises:
            text = MANIFEST.read_text()
            for name, old, new in raises:
                text = raise_floor(text, name, new)
                print(f"  RAISED {name}: {old:.1f}% -> {new:.1f}%")
            # Never leave a manifest we cannot read back. --update corrupting
            # the file it maintains is worse than not updating it.
            try:
                tomllib.loads(text)
            except tomllib.TOMLDecodeError as exc:
                raise ManifestError(
                    f"--update would produce an unparseable manifest: {exc}") from exc
            MANIFEST.write_text(text)
        else:
            print("  nothing to raise (--update never lowers a floor; "
                  "lowering one is a reviewed, reasoned edit)")

    total = len(comps)
    print(f"\n{total - failed - skipped}/{total} passed, {failed} failed, "
          f"{skipped} skipped")
    if skipped:
        print("NOTE: skipped components have references that are not committed "
              "(third-party geometry). They do NOT run in CI.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
