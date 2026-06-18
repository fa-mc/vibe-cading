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
"""Two-layer guard keeping the ``mcp`` SDK out of the library import graph.

Per ``vibe/INSTRUCTIONS.md`` (and the design at
``docs/design_plans/2026-06-18-mcp-subpackage_design.md`` R7), the optional
``vibe_cading.mcp`` subpackage and its ``mcp`` SDK dependency MUST NOT leak onto
library-only consumers.  Concretely:

* No class module under ``vibe_cading/**`` or ``parts/**`` may import ``mcp`` or
  any ``vibe_cading.mcp`` module — except the ``vibe_cading/mcp/`` subtree
  itself (which legitimately uses the SDK in ``__main__.py`` / ``server.py``)
  and ``vibe_cading/tools/`` (CLI entry points, not library surface — same
  carve-out the no-main-block and ocp_vscode guards already use).
* After a plain ``import vibe_cading``, neither ``mcp`` nor any
  ``vibe_cading.mcp.*`` may appear in ``sys.modules``.

Two layers, mirroring the ``check_no_main_blocks.py`` shape:

**Layer A — static AST guard (primary, stdlib-only, pre-build).**  Walk every
``*.py`` under the scanned roots (excluding the carve-outs), parse with ``ast``,
and fail on any ``import mcp`` / ``from mcp …`` / ``import vibe_cading.mcp`` /
``from vibe_cading.mcp …``.  AST (not regex) so the literal string
``"vibe_cading.mcp"`` inside a docstring or comment does not false-positive —
the same rationale ``check_no_main_blocks.py`` cites.

**Layer B — live-import assertion (defense-in-depth).**  In a clean subprocess
(pristine ``sys.modules``), ``import vibe_cading`` and assert neither ``mcp``
nor any ``vibe_cading.mcp.*`` ended up imported.  This catches *transitive* /
*dynamic* pollution that a source-level AST scan cannot see, and asserts the
actual runtime-graph property the invariant promises.  It is host-independent
(pure import-graph; no fonts / OCCT / glyph dependence), satisfying the
reproducibility constraint — and it requires ``mcp`` to be **absent** to be a
meaningful "no leak" assertion (run it in the lint stage where the SDK is not
installed).

Stdlib-only so it runs in the lint stage before any heavy dependency
(CadQuery, the ``mcp`` SDK) is installed.
"""

from __future__ import annotations

import ast
import pathlib
import subprocess
import sys

# The package that must never appear in the library import graph, plus the
# in-repo subpackage that wraps it.  A leak of *either* token is a violation.
_FORBIDDEN_ROOTS = ("mcp", "vibe_cading.mcp")


def _is_forbidden_module(name: str | None) -> bool:
    """True if dotted module *name* is ``mcp`` / ``vibe_cading.mcp`` or below.

    Matches the exact token or a dotted child (``mcp.server``,
    ``vibe_cading.mcp.tools``) but NOT an unrelated module that merely shares a
    prefix substring (e.g. a hypothetical ``mcphelper`` is not ``mcp``).
    """
    if not name:
        return False
    for root in _FORBIDDEN_ROOTS:
        if name == root or name.startswith(root + "."):
            return True
    return False


def _module_imports_forbidden(tree: ast.AST) -> bool:
    """True if the parsed *tree* contains a forbidden import statement."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # `import mcp`, `import mcp.server as s`, `import vibe_cading.mcp...`
            for alias in node.names:
                if _is_forbidden_module(alias.name):
                    return True
        elif isinstance(node, ast.ImportFrom):
            # `from mcp.server import Server`, `from vibe_cading.mcp import x`.
            # node.module is None for a bare relative import (`from . import x`);
            # such an import cannot name an absolute forbidden root, so skip it.
            if node.level == 0 and _is_forbidden_module(node.module):
                return True
    return False


def find_violations(
    roots: list[pathlib.Path],
    exclude: list[pathlib.Path] | None = None,
) -> list[pathlib.Path]:
    """Return the list of files that import ``mcp`` / ``vibe_cading.mcp``.

    Paths under any directory in *exclude* are skipped — see :func:`main` for
    the ``vibe_cading/mcp/`` and ``vibe_cading/tools/`` carve-outs.
    """
    exclude = exclude or []
    bad: list[pathlib.Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if any(path.is_relative_to(ex) for ex in exclude):
                continue
            try:
                tree = ast.parse(
                    path.read_text(encoding="utf-8"), filename=str(path)
                )
            except SyntaxError as exc:                       # pragma: no cover
                print(f"SYNTAX  {path}: {exc}", file=sys.stderr)
                bad.append(path)
                continue
            if _module_imports_forbidden(tree):
                bad.append(path)
    return bad


# Layer B is run as a child process with a pristine interpreter so the parent's
# already-imported modules (pytest will have imported plenty) cannot mask a
# leak.  Kept as a module constant so the test suite can import and run the
# exact same probe the CLI runs.
_LAYER_B_PROBE = (
    "import sys; import vibe_cading; "
    "leaked = sorted(m for m in sys.modules "
    "if m == 'mcp' or m.startswith('mcp.') or m.startswith('vibe_cading.mcp')); "
    "print('LEAKED:' + ','.join(leaked)); "
    "sys.exit(1 if leaked else 0)"
)


def run_layer_b() -> tuple[int, str]:
    """Run the Layer-B assertion in a clean subprocess.

    Returns ``(returncode, combined_output)``.  ``returncode == 0`` means
    ``import vibe_cading`` left ``sys.modules`` free of ``mcp`` /
    ``vibe_cading.mcp.*``.
    """
    proc = subprocess.run(
        [sys.executable, "-c", _LAYER_B_PROBE],
        capture_output=True,
        text=True,
    )
    return proc.returncode, (proc.stdout + proc.stderr)


def main() -> int:
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    roots = [repo_root / "vibe_cading", repo_root / "parts"]
    # Carve out the mcp subpackage itself (it MAY use the SDK in
    # __main__.py / server.py) and vibe_cading/tools/ (CLI entry points, not
    # library surface — the same carve-out check_no_main_blocks uses).
    exclude = [
        repo_root / "vibe_cading" / "mcp",
        repo_root / "vibe_cading" / "tools",
    ]

    rc = 0

    # ---- Layer A: static AST scan -------------------------------------------
    violations = find_violations(roots, exclude)
    if violations:
        print(
            "Layer A FAILED — forbidden mcp / vibe_cading.mcp import(s) found "
            "in the library import graph:"
        )
        for v in violations:
            print(f"  - {v.relative_to(repo_root)}")
        print(
            f"\n{len(violations)} file(s) import the mcp SDK or the "
            "vibe_cading.mcp subpackage outside the carve-out "
            "(vibe_cading/mcp/, vibe_cading/tools/)."
        )
        rc = 1
    else:
        print(
            "Layer A OK: no mcp / vibe_cading.mcp imports under vibe_cading/ "
            "or parts/ (excluding vibe_cading/mcp/ and vibe_cading/tools/)."
        )

    # ---- Layer B: live import-graph assertion -------------------------------
    b_rc, b_out = run_layer_b()
    b_out = b_out.strip()
    if b_rc != 0:
        print(
            "Layer B FAILED — `import vibe_cading` pulled mcp / "
            "vibe_cading.mcp into sys.modules:"
        )
        if b_out:
            print(f"  {b_out}")
        rc = 1
    else:
        print(
            "Layer B OK: `import vibe_cading` leaves sys.modules free of "
            "mcp / vibe_cading.mcp.*"
        )

    return rc


if __name__ == "__main__":
    sys.exit(main())
