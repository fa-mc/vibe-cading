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
"""Validate relative file links in the project's tracked Markdown docs.

The instruction graph (``vibe/INSTRUCTIONS.md``, the role / command / template
files, ``README.md``, ``CONTRIBUTING.md``, the ``docs/`` tree, …) is dense with
relative cross-references — ``[docs/lego-technic.md](../docs/lego-technic.md)``,
``[the TL persona](vibe/agents/tl.md)``.  When a file is renamed or moved these
silently rot; a reader following the link hits a 404.  This check regenerates no
artifacts — it simply asserts that the *file* every relative inline link points
at still exists on disk, and fails CI if any does not.

**Scope (what is scanned).**  By default the tracked ``*.md`` files reported by
``git ls-files '*.md'`` — EXCLUDING anything under ``docs/design_plans/``.
Design-plan artifacts are *historical*: a brief written months ago intentionally
cites files that were later removed, or ``tmp/`` probes that never get committed,
or paths that only existed on a since-merged feature branch.  Link-checking them
would flag deliberate, frozen history as broken, so the whole prefix is skipped
(see ``DESIGN_PLANS_EXCLUDE_PREFIX``).  Optional positional arguments override
the git-tracked set with explicit files / directories — used by the test suite
to point the checker at a hermetic fixture tree instead of the real repo.

**What is validated (and what is not).**  For each Markdown inline link
``[text](target)`` (and the image form ``![alt](target)``) the *file* part of
``target`` is resolved relative to the containing ``.md`` file's directory; if it
does not exist on disk, the link is reported broken.  Deliberately NOT validated
in v1: the ``#anchor`` fragment itself.  Verifying that a heading-anchor resolves
requires a Markdown-aware slugifier (GitHub's algorithm differs subtly from
CommonMark's), and an anchor drift is far lower-stakes than a missing file — so
v1 strips the fragment and checks only the file's existence.  An existing
*directory* target (e.g. ``[the agents dir](vibe/agents/)``) is accepted.

**Why links inside code are skipped.**  Fenced code blocks (``` ``` ``` /
``~~~``) and inline code spans (`` `…` ``) are stripped before link extraction,
because a Markdown renderer treats their contents as literal text, not links.
This is not a convenience hack: ``vibe/INSTRUCTIONS.md`` documents the
visual-contract embed syntax inside a ```` ```markdown ```` fence
(``![…](../../visual_contracts/2026-MM-DD-task-slug…svg)`` — a placeholder, not
a real file), and ``vibe/agents/designer.md`` shows ``` `![…](<filename>)` ```
as an inline-code example.  Both are syntax *documentation*, not navigation, and
a correct Markdown link parser must not treat them as links.

Stdlib-only (no CadQuery, no third-party deps) so ``--help`` is instant and the
check runs in the lint stage before any heavy dependency is installed.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
from urllib.parse import unquote

# Tracked Markdown under this prefix is skipped: design-plan briefs are frozen
# historical artifacts that intentionally cite removed / tmp/ / feature-branch-
# only files (see the module docstring).  Kept as a clear module-level constant
# so the exclusion is greppable and easy to adjust.
DESIGN_PLANS_EXCLUDE_PREFIX = "docs/design_plans/"

# URL schemes / forms that are not local files and must be skipped.  An empty
# target, a pure in-page anchor (``#section``), and a protocol-relative URL
# (``//host/path``) are handled separately in ``_link_is_external`` /
# ``_extract_file_part``.
_EXTERNAL_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")

# Inline link / image: an optional leading ``!`` (image), ``[label](target)``.
# The label is non-greedy and may contain anything except an unescaped ``]``;
# the target runs to the matching ``)``.  Reference-style links (``[a][b]``),
# autolinks (``<https://…>``) and bare URLs are intentionally out of scope —
# this check is about relative *file* links, which are always inline.
_INLINE_LINK_RE = re.compile(r"!?\[(?:[^\]]*)\]\(([^)]*)\)")

# Strip a trailing ``"title"`` / ``'title'`` from a link target:
# ``[x](path "tooltip")`` → the path is ``path``.  Requires whitespace before
# the quote so a quote that is part of a (rare) filename is not mis-stripped.
_TITLE_SUFFIX_RE = re.compile(r"""\s+["'].*$""")

# An angle-bracketed *fill-in token* — ``<task-slug>``, ``<YYYY-MM-DD>``,
# ``<slug>``, ``<filename>``.  This is the project-wide template-placeholder
# convention (used throughout vibe/templates/ and docs/templates/): a target
# such as ``../../visual_contracts/<YYYY-MM-DD>-<task-slug>_design_iso_ne.svg``
# is a scaffold to be filled in, NOT a real on-disk path.  The token's inner
# text is a bare identifier — letters / digits / ``-`` / ``_`` only — which is
# what distinguishes a placeholder from a genuine CommonMark angle-bracket link
# whose inner text is a real path (``<my file.md>`` contains ``.`` and a space,
# ``<dir/sub>`` contains ``/``).  A grep confirmed every ``<…>``-bearing link
# target in the live docs is such a placeholder.
_PLACEHOLDER_TOKEN_RE = re.compile(r"<[A-Za-z0-9][A-Za-z0-9_-]*>")

# HTML comments are not rendered, so any ``[x](y)`` inside ``<!-- … -->`` is not
# a live link.  Matched non-greedily across lines (``re.DOTALL``) and blanked
# before link extraction — e.g. the optional-extra-views example in
# vibe/templates/_template_design.md lives inside such a comment.
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def list_tracked_markdown(repo_root: pathlib.Path) -> list[pathlib.Path]:
    """Return tracked ``*.md`` paths (absolute), minus the design-plans prefix.

    Uses ``git ls-files`` so only *tracked* files are scanned — untracked
    scratch Markdown under ``tmp/`` never reaches the check.
    """
    out = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    paths: list[pathlib.Path] = []
    for line in out.splitlines():
        rel = line.strip()
        if not rel:
            continue
        # Compare on the POSIX-style path git emits, regardless of host sep.
        if rel.startswith(DESIGN_PLANS_EXCLUDE_PREFIX):
            continue
        paths.append(repo_root / rel)
    return paths


def collect_markdown_files(args: list[str]) -> list[pathlib.Path]:
    """Resolve the scan set from optional positional file/dir *args*.

    Empty *args* → the git-tracked set (design-plans excluded).  Otherwise each
    arg is either a Markdown file (added as-is) or a directory (all ``*.md``
    beneath it, recursively).  The design-plans exclusion applies ONLY to the
    git-tracked default; explicit args are taken verbatim so a test fixture can
    place files wherever it likes.
    """
    if not args:
        repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
        return list_tracked_markdown(repo_root)

    files: list[pathlib.Path] = []
    for arg in args:
        p = pathlib.Path(arg)
        if p.is_dir():
            files.extend(sorted(p.rglob("*.md")))
        elif p.is_file():
            files.append(p)
        else:
            print(f"warning: not a file or directory, skipping: {arg}",
                  file=sys.stderr)
    return files


def _blank_html_comments(text: str) -> str:
    """Replace ``<!-- … -->`` regions with blanks, preserving line count.

    A Markdown renderer does not render links inside HTML comments, so they must
    not be checked.  Newlines inside a (possibly multi-line) comment are kept so
    reported line numbers stay accurate; all other comment characters become
    spaces.
    """
    def _blank(match: re.Match[str]) -> str:
        return "".join("\n" if ch == "\n" else " " for ch in match.group(0))

    return _HTML_COMMENT_RE.sub(_blank, text)


def _strip_code(text: str) -> str:
    """Blank out HTML comments, fenced code blocks, and inline code spans.

    A Markdown renderer treats the contents of fenced blocks (``` ``` ``` /
    ``~~~``), inline code spans (`` `…` ``) and HTML comments (``<!-- … -->``)
    as non-link text, so any ``[x](y)`` inside them is NOT a link.  We replace
    those regions with blank lines / spaces (preserving line numbering for
    accurate reporting) before extracting links.  This is what prevents the
    documented embed-syntax examples in ``vibe/INSTRUCTIONS.md`` /
    ``vibe/agents/designer.md`` and the commented optional-view example in
    ``vibe/templates/_template_design.md`` from being mis-read as broken links
    (see the module docstring).
    """
    text = _blank_html_comments(text)
    lines = text.splitlines()
    out: list[str] = []
    in_fence = False
    fence_marker = ""  # the exact opening run (``` or ~~~), to match the close
    for line in lines:
        stripped = line.lstrip()
        if in_fence:
            # Inside a fence: a line whose first non-space token is a run of the
            # same fence char (>= the opener's length) closes it.  Blank the
            # line either way — its contents are literal.
            if stripped.startswith(fence_marker):
                in_fence = False
                fence_marker = ""
            out.append("")
            continue
        # Not in a fence: does this line open one?  An opening fence is >= 3
        # backticks or >= 3 tildes as the first non-space token.
        m = re.match(r"(`{3,}|~{3,})", stripped)
        if m:
            in_fence = True
            fence_marker = m.group(1)[:3]  # closing needs only the 3-char run
            out.append("")
            continue
        # Inline code spans: blank everything between matched backtick runs on
        # this line.  Replace with same-width spaces so column-ish context (and
        # any links OUTSIDE the spans) are preserved.
        out.append(_blank_inline_code(line))
    return "\n".join(out)


def _blank_inline_code(line: str) -> str:
    """Replace inline-code-span contents on a single *line* with spaces.

    Handles multi-backtick delimiters (`` ``code`` ``): an opening run of N
    backticks is closed by the next run of exactly N backticks.  An unmatched
    opener (no closer on the line) is left as-is — it is not a code span.
    """
    result: list[str] = []
    i = 0
    n = len(line)
    while i < n:
        if line[i] == "`":
            # Measure the opening backtick run length.
            j = i
            while j < n and line[j] == "`":
                j += 1
            run = j - i
            tick = "`" * run
            # Find a closing run of exactly the same length.
            close = line.find(tick, j)
            # Reject a "closer" that is itself part of a longer backtick run.
            while close != -1:
                after = close + run
                if after < n and line[after] == "`":
                    close = line.find(tick, after)
                    continue
                break
            if close == -1:
                # No matching closer: not a code span, emit the run literally.
                result.append(line[i:j])
                i = j
            else:
                # Blank the whole span (delimiters + body) with spaces.
                result.append(" " * (close + run - i))
                i = close + run
        else:
            result.append(line[i])
            i += 1
    return "".join(result)


def _link_is_external(target: str) -> bool:
    """True if *target* is not a local relative file reference.

    Skips: empty, pure in-page anchor (``#…``), protocol-relative (``//host``),
    and any explicit scheme (``http:``, ``https:``, ``mailto:``, ``ftp:`` …).
    """
    if not target:
        return True
    if target.startswith("#"):
        return True
    if target.startswith("//"):
        return True
    if _EXTERNAL_SCHEME_RE.match(target):
        return True
    return False


def _extract_file_part(target: str) -> str | None:
    """Reduce a raw link *target* to the on-disk path part, or ``None``.

    ``None`` means "nothing to check" (external / anchor-only / empty).  Steps:
    unwrap ``<…>``; drop a trailing ``"title"``; split off ``#anchor`` and
    ``?query``; URL-unescape (``%20`` → space).  An anchor-only target reduces
    to ``""`` and yields ``None``.
    """
    t = target.strip()
    # Un-filled template placeholder (``<task-slug>``, ``<filename>``)?  Checked
    # on the RAW target, before the angle-bracket unwrap below — otherwise a
    # whole-target placeholder like ``<filename>`` would be unwrapped to the bare
    # word ``filename`` and lose its placeholder signal.  The regex deliberately
    # does NOT match a genuine wrapped path (``<my file.md>`` / ``<dir/sub>``).
    if _PLACEHOLDER_TOKEN_RE.search(t):
        return None
    # Unwrap a CommonMark angle-bracket-delimited target: ``[x](<my file.md>)``.
    if t.startswith("<") and t.endswith(">"):
        t = t[1:-1].strip()
    # Drop a trailing quoted title (must be preceded by whitespace).
    t = _TITLE_SUFFIX_RE.sub("", t).strip()
    if _link_is_external(t):
        return None
    # Strip the fragment / query — we validate only the file's existence (v1).
    t = t.split("#", 1)[0]
    t = t.split("?", 1)[0]
    if not t:
        return None  # was a pure ``#anchor`` (or ``?query``) with no file part.
    return unquote(t)


def find_broken_links(
    md_files: list[pathlib.Path],
) -> list[tuple[pathlib.Path, int, str]]:
    """Return ``(file, line_number, raw_target)`` for every broken link.

    A link is broken when its resolved file part does not exist on disk.  The
    target is resolved relative to the containing ``.md`` file's directory.
    """
    broken: list[tuple[pathlib.Path, int, str]] = []
    for md in md_files:
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:        # pragma: no cover
            print(f"warning: cannot read {md}: {exc}", file=sys.stderr)
            continue
        base = md.parent
        scrubbed = _strip_code(text)
        for lineno, line in enumerate(scrubbed.splitlines(), start=1):
            for m in _INLINE_LINK_RE.finditer(line):
                raw_target = m.group(1)
                file_part = _extract_file_part(raw_target)
                if file_part is None:
                    continue
                resolved = (base / file_part)
                if not resolved.exists():
                    broken.append((md, lineno, raw_target))
    return broken


def _format_report(
    broken: list[tuple[pathlib.Path, int, str]],
    cwd: pathlib.Path,
) -> str:
    """Format broken links grouped by file, paths relative to *cwd* if possible."""
    def rel(p: pathlib.Path) -> str:
        try:
            return str(p.relative_to(cwd))
        except ValueError:
            return str(p)

    lines: list[str] = []
    current: pathlib.Path | None = None
    for md, lineno, target in broken:
        if md != current:
            lines.append(f"{rel(md)}:")
            current = md
        lines.append(f"  {rel(md)}:{lineno} -> {target}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate that relative file links in tracked Markdown docs point "
            "at files that exist on disk."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help=(
            "Optional Markdown files or directories to scan.  When omitted, "
            "scans the git-tracked *.md set excluding "
            f"{DESIGN_PLANS_EXCLUDE_PREFIX} (frozen historical briefs)."
        ),
    )
    args = parser.parse_args(argv)

    md_files = collect_markdown_files(args.paths)
    broken = find_broken_links(md_files)

    cwd = pathlib.Path.cwd()
    if broken:
        print(_format_report(broken, cwd))
        n_files = len({md for md, _, _ in broken})
        print(
            f"\nFAIL: {len(broken)} broken link(s) across {n_files} file(s) "
            f"in {len(md_files)} scanned Markdown file(s)."
        )
        return 1

    print(
        f"OK: no broken relative links in {len(md_files)} scanned "
        "Markdown file(s)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
