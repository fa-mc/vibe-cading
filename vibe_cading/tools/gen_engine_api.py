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
"""Generate ``engine_api.json`` from ``vibe_cading/**`` and ``parts/**``.

Walks ``vibe_cading/**`` and ``parts/**`` with the AST extractor in
``tools/engine_api/extractor.py`` and writes a deterministic JSON artifact
at the repo root (or the path supplied via ``--out``).

CLI
---
- ``python3 tools/gen_engine_api.py``
    Regenerate ``engine_api.json`` in place.
- ``python3 tools/gen_engine_api.py --out path/to/file.json``
    Write to a custom location (used by tests under ``tmp/``).
- ``python3 tools/gen_engine_api.py --check``
    Regenerate in memory, diff against the on-disk artifact, exit 1 on
    drift. This is what the CI gate runs (see
    ``.github/workflows/engine-api.yml``).

Output ordering is fixed: classes by FQN ascending, constructors in
source order, params in source order. This guarantees a stable byte
sequence so diffs and the ``--check`` gate are reliable.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make ``tools.engine_api`` importable when this script is invoked
# directly (``python3 tools/gen_engine_api.py``). The repo root is the
# parent of ``vibe_cading/tools/``.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from vibe_cading.tools.engine_api.extractor import (  # noqa: E402  (import after sys.path tweak)
    SCHEMA_VERSION,
    extract_classes,
)


def _build_payload(repo_root: Path) -> dict:
    # Walk both the library tree (``vibe_cading/``) and the project-specific
    # end-products tree (``parts/``).  ``experiments/`` is excluded — it is
    # R&D, not a contract-bearing surface.
    roots = [
        d
        for d in (repo_root / "vibe_cading", repo_root / "parts")
        if d.exists()
    ]
    # ``vibe_cading/mcp/`` is the MCP-server runtime entry point — it lives
    # inside the walked ``vibe_cading`` root, so (unlike ``experiments/``)
    # it cannot be kept out of the catalog by omission; exclude its subtree
    # explicitly so a future *public* mcp class never leaks into the JSON.
    records = extract_classes(
        roots, exclude=[repo_root / "vibe_cading" / "mcp"]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "classes": [r.to_dict() for r in records],
    }


def _serialize(payload: dict) -> str:
    """Deterministic JSON encoding.

    ``sort_keys=False`` because the dataclass-driven dict order encodes
    schema intent (e.g. ``name`` before ``type`` in a param). A trailing
    newline keeps POSIX text-file conventions and avoids spurious
    diffs from editors that auto-append one.
    """
    return json.dumps(payload, indent=2, sort_keys=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate engine_api.json from vibe_cading/** and parts/**.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_REPO_ROOT / "vibe_cading" / "engine_api.json",
        help="Output path (default: <repo>/vibe_cading/engine_api.json).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Regenerate in memory and diff against the on-disk file. "
            "Exit 1 on drift; do not write."
        ),
    )
    args = parser.parse_args(argv)

    payload = _build_payload(_REPO_ROOT)
    text = _serialize(payload)

    if args.check:
        if not args.out.exists():
            print(
                f"engine_api.json missing at {args.out}; run "
                "`python3 tools/gen_engine_api.py` to create it.",
                file=sys.stderr,
            )
            return 1
        existing = args.out.read_text(encoding="utf-8")
        if existing != text:
            print(
                f"engine_api.json at {args.out} is out of date. "
                "Run `python3 tools/gen_engine_api.py` to regenerate.",
                file=sys.stderr,
            )
            return 1
        return 0

    args.out.write_text(text, encoding="utf-8")
    print(
        f"Wrote {args.out} ({len(payload['classes'])} classes).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
