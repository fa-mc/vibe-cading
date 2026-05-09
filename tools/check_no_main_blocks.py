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
"""AST-based check forbidding ``if __name__ == "__main__":`` blocks in models/.

Per ``vibe/INSTRUCTIONS.md`` § "OCP Viewer — Dedicated Entry Point", model
class files MUST NOT contain ``if __name__ == "__main__":`` viewer blocks;
``tools/view.py`` is the only sanctioned entry point.  This script walks
every ``models/**/*.py`` file's top-level ``If`` nodes and fails non-zero on
the literal AST shape ``Compare(Name('__name__'), [Eq()], [Constant('__main__')])``.

Stdlib-only.  AST (not regex) so string literals inside docstrings or
example blocks do not false-positive.
"""

from __future__ import annotations

import ast
import pathlib
import sys


def _is_main_guard(node: ast.AST) -> bool:
    """True if *node* is an ``if __name__ == "__main__":`` top-level guard."""
    if not isinstance(node, ast.If):
        return False
    test = node.test
    if not isinstance(test, ast.Compare):
        return False
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    if len(test.comparators) != 1:
        return False
    left, right = test.left, test.comparators[0]
    left_is_name = isinstance(left, ast.Name) and left.id == "__name__"
    right_is_main = isinstance(right, ast.Constant) and right.value == "__main__"
    return left_is_name and right_is_main


def find_violations(root: pathlib.Path) -> list[pathlib.Path]:
    """Return the list of model files containing a top-level main guard."""
    bad: list[pathlib.Path] = []
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:                      # pragma: no cover
            print(f"SYNTAX  {path}: {exc}", file=sys.stderr)
            bad.append(path)
            continue
        if any(_is_main_guard(n) for n in tree.body):
            bad.append(path)
    return bad


def main() -> int:
    repo_root  = pathlib.Path(__file__).resolve().parent.parent
    models_dir = repo_root / "models"
    violations = find_violations(models_dir)
    if violations:
        print("Forbidden `if __name__ == \"__main__\":` blocks found in:")
        for v in violations:
            print(f"  - {v.relative_to(repo_root)}")
        print(f"\n{len(violations)} file(s) violate the policy.")
        print("Use `tools/view.py <module.path.ClassName>` (optionally with "
              "--demo) instead.")
        return 1
    print("OK: no `if __name__ == \"__main__\":` blocks under models/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
