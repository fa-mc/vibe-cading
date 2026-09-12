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
"""AST check for unreachable statements and unresolved ``self.<attr>`` reads.

**Why this exists, concretely.** A commit on the PoweredUp hub branch carried
52 lines of unreachable code: the body of a method whose ``def`` line had been
lost in an earlier edit, left sitting after another method's ``return``. It
referenced two attributes that did not exist on the class at all, and one of
those was *also* read from live code inside an assertion's failure message --
so that guard would have raised ``AttributeError`` instead of reporting the
wall thickness the first time it legitimately fired.

``flake8`` was clean on every line of it. Neither unreachable code nor an
unresolved ``self.<attr>`` is within what a style linter checks, which is how
the defect survived a lint-clean commit and an entire test run: the dead branch
is never executed, so tests cannot reach it either.

Two checks, both cheap and purely static:

1. **Unreachable statements** -- any statement following ``return``, ``raise``,
   ``continue`` or ``break`` in the same block.

2. **Unresolved instance attributes** -- a ``self.X`` *read* where ``X`` is
   never bound anywhere in the class: not as a class attribute, not as a
   method, and not assigned via ``self.X = ...`` (including tuple-unpacking,
   augmented, ``for``-target and ``with``-target binds).

Check 2 is deliberately conservative: it only reports attributes with no
binding *anywhere* in the class body, so dynamic patterns like ``setattr`` or
inheritance from a base that defines the attribute are not flagged. It is meant
to catch orphaned or renamed references, not to be a type checker.

Usage::

    python3 vibe_cading/tools/check_dead_code.py [path ...]

With no arguments it walks ``vibe_cading/`` and ``parts/``. Exits 1 on any
finding, printing ``file:line`` for each.
"""
from __future__ import annotations

import ast
import pathlib
import sys

TERMINALS = (ast.Return, ast.Raise, ast.Continue, ast.Break)
DEFAULT_ROOTS = ("vibe_cading", "parts")
# R&D code, outside the OSS surface contract -- same carve-out as
# check_no_main_blocks.py.
SKIP_PARTS = {"experiments", ".git", "__pycache__", "tmp"}


def _bind(target: ast.AST, into: set[str]) -> None:
    """Record every ``self.X`` bound by an assignment target.

    Descends tuple/list unpacking and starred targets. Missing those produced
    three false positives the first time this check was run (an attribute
    bound as ``self.a, _ = f()``), which is why the recursion is here rather
    than a flat isinstance check.
    """
    if isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            _bind(elt, into)
    elif isinstance(target, ast.Starred):
        _bind(target.value, into)
    elif (isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"):
        into.add(target.attr)


def _unreachable(tree: ast.AST, path: str) -> list[str]:
    out = []
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        for i, stmt in enumerate(body[:-1]):
            if isinstance(stmt, TERMINALS):
                nxt = body[i + 1]
                out.append(
                    f"{path}:{nxt.lineno}: unreachable statement "
                    f"(follows {type(stmt).__name__.lower()} at line "
                    f"{stmt.lineno})"
                )
    return out


def _unresolved_attrs(tree: ast.AST, path: str) -> list[str]:
    out = []
    for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
        # SUBCLASSES ARE SKIPPED. An attribute bound in a base class -- very
        # often via `super().__init__(...)` -- is invisible here, and treating
        # that as a finding produced 20 false positives on SpurGear(Gear) and
        # HelicalGear(SpurGear) the first time this ran repo-wide. Resolving
        # bases properly means cross-module import resolution, which is a type
        # checker's job, not this script's.
        #
        # This costs nothing against the defect the check exists for: that was
        # an orphaned method body in a baseless class, referencing attributes
        # that existed nowhere at all. Reporting only what it can prove is the
        # difference between a check people keep and one they learn to ignore.
        if [b for b in cls.bases
                if not (isinstance(b, ast.Name) and b.id == "object")]:
            continue
        defined: set[str] = set()
        for stmt in cls.body:
            if isinstance(stmt, ast.Assign):
                for t in stmt.targets:
                    if isinstance(t, ast.Name):
                        defined.add(t.id)
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                defined.add(stmt.target.id)
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defined.add(stmt.name)
        for node in ast.walk(cls):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    _bind(t, defined)
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                _bind(node.target, defined)
            elif isinstance(node, ast.For):
                _bind(node.target, defined)
            elif isinstance(node, ast.withitem) and node.optional_vars is not None:
                _bind(node.optional_vars, defined)
        for node in ast.walk(cls):
            if (isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "self"
                    and isinstance(node.ctx, ast.Load)
                    and node.attr not in defined):
                out.append(
                    f"{path}:{node.lineno}: self.{node.attr} is never bound "
                    f"on class {cls.name}"
                )
    return out


def _orphaned_doc_comments(source: str, path: str) -> list[str]:
    """Find ``#:`` doc-comment blocks that document no assignment.

    Sphinx's ``#:`` prefix means "this comment documents the attribute
    assigned on the next line". A block not followed by an assignment
    documents nothing -- and reads, convincingly, as though the attribute
    exists. Other code then references it by name and every reference dangles.

    Round 88 shipped exactly that: a 24-line ``#:`` block describing
    ``GLUE_GAP_Z`` on ``PoweredUpHubBatteryTrayCap`` with no such constant
    anywhere, plus three references to it -- one in live ``__init__`` code.
    Nothing caught it. The AST cannot: comments are not nodes, so this check
    is deliberately textual.

    Only blocks that reach a blank line or a dedent without an assignment are
    reported, so the normal ``#:`` + assignment pattern stays silent.
    """
    out: list[str] = []
    lines = source.splitlines()
    i = 0
    while i < len(lines):
        if not lines[i].lstrip().startswith("#:"):
            i += 1
            continue
        start = i
        while i < len(lines) and lines[i].lstrip().startswith("#:"):
            i += 1
        # The block documents whatever the next non-comment line assigns.
        nxt = lines[i].strip() if i < len(lines) else ""
        if not nxt or nxt.startswith("#"):
            out.append(
                f"{path}:{start + 1}: '#:' doc-comment block documents no "
                f"assignment (orphaned at line {i or len(lines)})"
            )
    return out


def _self_test() -> None:
    """Positive control -- the checker must SEE a planted fault.

    Without this, a clean report and a broken checker are indistinguishable,
    and the broken checker is the more likely of the two
    (vibe/INSTRUCTIONS.md, "Positive Control Before Any Absence Claim").
    """
    planted = ast.parse(
        "class C:\n"
        "    def m(self):\n"
        "        return 1\n"
        "        x = 2\n"
        "    def n(self):\n"
        "        return self.never_bound\n"
    )
    assert _unreachable(planted, "<probe>"), (
        "self-test failed: planted unreachable code was not detected"
    )
    assert _unresolved_attrs(planted, "<probe>"), (
        "self-test failed: planted unresolved attribute was not detected"
    )
    # And it must NOT flag a tuple-unpacked bind, the known false positive.
    clean = ast.parse(
        "class C:\n"
        "    def __init__(self):\n"
        "        self.a, _ = (1, 2)\n"
        "    def m(self):\n"
        "        return self.a\n"
    )
    assert not _unresolved_attrs(clean, "<probe>"), (
        "self-test failed: tuple-unpacked self attribute was wrongly flagged"
    )
    # The orphaned-doc-comment check, both directions.
    assert _orphaned_doc_comments(
        "class C:\n"
        "    #: documents nothing at all\n"
        "    #: (no assignment follows this block)\n"
        "\n"
        "    OTHER = 1\n",
        "<probe>",
    ), "self-test failed: planted orphaned '#:' block was not detected"
    assert not _orphaned_doc_comments(
        "class C:\n"
        "    #: a real attribute doc\n"
        "    REAL = 1\n",
        "<probe>",
    ), "self-test failed: a normal '#:' + assignment was wrongly flagged"


def iter_files(roots):
    for root in roots:
        p = pathlib.Path(root)
        if p.is_file() and p.suffix == ".py":
            yield p
            continue
        for f in sorted(p.rglob("*.py")):
            if SKIP_PARTS & set(f.parts):
                continue
            yield f


def main(argv):
    _self_test()
    roots = argv[1:] or list(DEFAULT_ROOTS)
    findings = []
    scanned = 0
    for f in iter_files(roots):
        source = f.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(f))
        except SyntaxError as exc:
            findings.append(f"{f}: could not parse ({exc})")
            continue
        scanned += 1
        findings += _unreachable(tree, str(f))
        findings += _unresolved_attrs(tree, str(f))
        findings += _orphaned_doc_comments(source, str(f))

    if findings:
        print(f"check_dead_code: {len(findings)} problem(s) in {scanned} file(s)")
        for line in findings:
            print("  " + line)
        return 1
    print(f"check_dead_code: clean ({scanned} files scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
