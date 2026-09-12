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
import io
import pathlib
import sys
import tokenize

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


def _assignment_lines(tree: ast.AST) -> set[int]:
    """Line numbers on which an assignment (or annotated one) begins."""
    lines = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            lines.add(node.lineno)
    return lines


def _orphaned_doc_comments(source: str, path: str, tree: ast.AST) -> list[str]:
    """Find ``#:`` doc-comment blocks that document no assignment.

    Sphinx's ``#:`` prefix means "this comment documents the attribute
    assigned on the next line". A block not followed by an assignment
    documents nothing -- and reads, convincingly, as though the attribute
    exists. Other code then references it by name and every reference dangles.

    Round 88 shipped exactly that: a 24-line ``#:`` block describing
    ``GLUE_GAP_Z`` on ``PoweredUpHubBatteryTrayCap`` with no such constant
    anywhere, plus references to it -- one in live ``__init__`` code.

    ROUND 88, SECOND PASS -- this was first written as a raw line scan, and
    it did not do what this docstring said. It never checked for an
    assignment at all: it fired iff the next line was blank, a comment, or
    EOF. So it was silent when a block was followed by ``def``, a decorator,
    a dedent (which the docstring explicitly claimed to handle) or any other
    non-assignment statement -- had ``GLUE_GAP_Z`` sat directly above
    ``def __init__`` the guard would have said nothing. It also fired on any
    ``#:``-leading line inside a string or docstring, so documenting this
    very convention with an example reddened CI on itself.

    ``tokenize`` fixes both directions and dissolves the "must be textual"
    premise the first version argued from: comments are not AST nodes, but
    they ARE tokens, and the assignment lines come from the AST. Neither half
    has to guess.
    """
    out: list[str] = []
    assigns = _assignment_lines(tree)
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError):
        # Unparseable as tokens; the AST parse above already reported it.
        return out

    # Only real COMMENT tokens -- a "#:" inside a string is a STRING token and
    # never reaches here.
    #
    # Sphinx has TWO forms, and only the leading one can dangle. `X = 1  #: doc`
    # is the trailing form: it documents the assignment on its own line and is
    # by construction attached to it. Its comment token starts at a column past
    # the start of the line, which is how it is told apart. Without this the
    # scanner flags the standard trailing form and points at the very line that
    # assigns -- a false positive on correct code.
    comments = [t for t in toks
                if t.type == tokenize.COMMENT
                and t.string.startswith("#:")
                and not source.splitlines()[t.start[0] - 1][:t.start[1]].strip()]

    # Group consecutive "#:" comment lines into blocks.
    blocks: list[list[int]] = []
    for t in comments:
        line = t.start[0]
        if blocks and line == blocks[-1][-1] + 1:
            blocks[-1].append(line)
        else:
            blocks.append([line])

    # A "#:" block documents the assignment DIRECTLY below it -- adjacency is
    # the whole convention, so anything between the two breaks the association
    # and the block documents nothing. (That is the exact shape the GLUE_GAP_Z
    # block had: prose, blank line, then an unrelated attribute. A rule that
    # merely looked for "an assignment eventually" would call it fine -- the
    # self-test catches that, having caught it on the first attempt at this
    # rewrite.)
    #
    # ROUND 88, THIRD PASS -- an earlier version of this loop skipped over any
    # number of intervening plain "#" comment lines before looking for the
    # assignment. That carve-out contradicted the adjacency rationale directly
    # above it, disagreed with Sphinx, and was unbounded: replacing the blank
    # line in the GLUE_GAP_Z shape with a single "# TODO: ..." made the
    # flagship defect pass the guard written to catch it. Adjacency now means
    # adjacency.
    lines = source.splitlines()

    def _text(lineno: int) -> str:
        return lines[lineno - 1].strip() if lineno - 1 < len(lines) else ""

    for block in blocks:
        probe = block[-1] + 1
        if probe <= len(lines) and probe in assigns:
            continue
        if probe > len(lines):
            where = "end of file"
        elif _text(probe) == "":
            where = f"blank line {probe}"
        else:
            where = f"line {probe}"
        out.append(
            f"{path}:{block[0]}: '#:' doc-comment block documents no "
            f"assignment ({where} follows it)"
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
    # The orphaned-doc-comment check.
    #
    # These cases were once described as "four it missed, three it wrongly
    # flagged". That was wrong, and the correction matters more than the
    # tally: re-running the original line scan over all of them shows it got
    # 4 of 12 wrong (3 missed, 1 wrongly flagged). Several cases here are NOT
    # regressions of the old version -- the string-literal one cannot fail
    # under any implementation, and the dedent case the old docstring claimed
    # to mishandle was in fact caught. They are kept anyway as forward
    # guards; what is not kept is the claim that each one documents a past
    # failure.
    def _orphans(src: str) -> list[str]:
        return _orphaned_doc_comments(src, "<probe>", ast.parse(src))

    must_flag = {
        "blank line after": (
            "class C:\n    #: documents nothing\n\n    OTHER = 1\n"),
        "followed by def": (
            "class C:\n    #: documents nothing\n    def m(self):\n"
            "        return 1\n"),
        "followed by decorator": (
            "class C:\n    #: documents nothing\n    @property\n"
            "    def m(self):\n        return 1\n"),
        "followed by non-assignment stmt": (
            "class C:\n    #: documents nothing\n    print(1)\n"),
        "followed by dedent": (
            "class C:\n    def m(self):\n        pass\n"
            "    #: documents nothing\n\nX = 1\n"),
        "at end of file": (
            "class C:\n    X = 1\n    #: documents nothing\n"),
        # The GLUE_GAP_Z shape with its blank line replaced by an aside.
        # Tolerating intervening comments made this pass the guard built to
        # catch it -- see the adjacency note in _orphaned_doc_comments.
        "separated by a plain '#' aside": (
            "class C:\n    #: documents nothing\n    # TODO: revisit\n"
            "    OTHER = 1\n"),
        "module top before any code": (
            "#: documents nothing\n\nimport os\n"),
    }
    for label, src in must_flag.items():
        assert _orphans(src), (
            f"self-test failed: orphaned '#:' block not detected ({label})"
        )

    must_not_flag = {
        "plain assignment": "class C:\n    #: a real doc\n    REAL = 1\n",
        "annotated assignment": (
            "class C:\n    #: a real doc\n    REAL: int = 1\n"),
        # A bare annotation IS a documentable attribute in Sphinx -- `#:` above
        # `X: int` documents a declared-but-unassigned attribute, so this is
        # correct code, not an orphan.
        "bare annotation, no value": (
            "class C:\n    #: a real doc\n    X: int\n"),
        "trailing '#:' form": "class C:\n    REAL = 1  #: a real doc\n",
        "trailing form, module level": "REAL = 1  #: a real doc\n",
        "annotated, nested class": (
            "class C:\n    class D:\n        #: a real doc\n"
            "        REAL: int = 1\n"),
        "inside a function body": (
            "def f():\n    #: a real doc\n    real = 1\n    return real\n"),
        "async def body": (
            "async def f():\n    #: a real doc\n    real = 1\n"
            "    return real\n"),
        "walrus is not an assignment stmt, but the block sits on one": (
            "class C:\n    #: a real doc\n    REAL = (x := 1)\n"),
        "'#:' inside a docstring": (
            'def f():\n    """Example:\n\n    #: a doc comment\n    X = 1\n'
            '    """\n    return 1\n'),
        "'#:' inside a string literal": (
            'S = "#: not a comment at all"\n'),
        "multi-line assignment": (
            "class C:\n    #: a real doc\n    REAL = (\n        1,\n"
            "        2,\n    )\n"),
    }
    for label, src in must_not_flag.items():
        assert not _orphans(src), (
            f"self-test failed: '#:' wrongly flagged ({label})"
        )


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
        findings += _orphaned_doc_comments(source, str(f), tree)

    if findings:
        print(f"check_dead_code: {len(findings)} problem(s) in {scanned} file(s)")
        for line in findings:
            print("  " + line)
        return 1
    print(f"check_dead_code: clean ({scanned} files scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
