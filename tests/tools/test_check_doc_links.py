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

"""Tests for ``vibe_cading/tools/check_doc_links.py``.

Hermetic — they build a throwaway Markdown tree under ``tmp_path`` and point the
checker at it via its positional-arg path (the same arg the CLI exposes so a
test never depends on the real repo docs for pass/fail).  Coverage:

* **valid relative link** → reports clean, ``main`` returns 0;
* **dead relative link** → reports the break, ``main`` returns non-zero;
* the false-positive classes the checker deliberately tolerates — external
  URLs, in-page anchors, ``"title"`` suffixes, ``<placeholder>`` template
  tokens, links inside code spans / fences / HTML comments, and a directory
  target — must NOT be flagged.

A final non-hermetic smoke asserts the *real* tracked docs are clean, so this
test fails the moment a live doc grows a broken link.
"""

from __future__ import annotations

import pathlib

from vibe_cading.tools import check_doc_links as checker


# --------------------------------------------------------------------------
# (a) valid relative link -> clean / exit 0
# --------------------------------------------------------------------------

def test_valid_relative_link_is_clean(tmp_path, capsys):
    (tmp_path / "target.md").write_text("# Target\n", encoding="utf-8")
    (tmp_path / "doc.md").write_text(
        "See [the target](target.md) for details.\n", encoding="utf-8"
    )

    rc = checker.main([str(tmp_path)])
    out = capsys.readouterr().out

    assert rc == 0
    assert "OK" in out
    # No failure markers (the clean message itself contains the word "broken").
    assert "FAIL" not in out
    assert "->" not in out


def test_find_broken_links_empty_when_all_resolve(tmp_path):
    (tmp_path / "a.md").write_text("[self](a.md)\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.md").write_text(
        "[up to a](../a.md)\n", encoding="utf-8"
    )
    assert checker.find_broken_links(
        checker.collect_markdown_files([str(tmp_path)])
    ) == []


# --------------------------------------------------------------------------
# (b) dead relative link -> reported / non-zero exit
# --------------------------------------------------------------------------

def test_dead_link_is_reported(tmp_path, capsys):
    (tmp_path / "doc.md").write_text(
        "Broken: [missing](does_not_exist.md)\n", encoding="utf-8"
    )

    rc = checker.main([str(tmp_path)])
    out = capsys.readouterr().out

    assert rc != 0
    assert "does_not_exist.md" in out
    # Reported as ``file:line -> target``.
    assert "doc.md:1 -> does_not_exist.md" in out
    assert "FAIL" in out


def test_dead_link_relative_to_containing_dir(tmp_path):
    # ``sub/doc.md`` links to ``sibling.md`` which exists at the ROOT, not in
    # ``sub/`` — so it must resolve relative to ``sub/`` and be reported broken.
    (tmp_path / "sibling.md").write_text("x\n", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "doc.md").write_text("[sib](sibling.md)\n", encoding="utf-8")

    broken = checker.find_broken_links(
        checker.collect_markdown_files([str(tmp_path)])
    )
    targets = [t for _, _, t in broken]
    assert "sibling.md" in targets


# --------------------------------------------------------------------------
# False-positive classes the checker must tolerate (no flags)
# --------------------------------------------------------------------------

def test_external_anchor_and_title_are_skipped(tmp_path, capsys):
    (tmp_path / "exists.md").write_text("x\n", encoding="utf-8")
    (tmp_path / "doc.md").write_text(
        "\n".join(
            [
                "[web](https://example.com/page)",
                "[mail](mailto:a@b.com)",
                "[proto](//cdn.example.com/x.js)",
                "[anchor](#a-heading)",
                "[titled](exists.md \"hover text\")",  # title stripped, file OK
                "[frag](exists.md#section)",            # fragment stripped
                "[empty]()",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rc = checker.main([str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0, out


def test_placeholder_token_targets_are_skipped(tmp_path, capsys):
    # The project template convention: ``<task-slug>`` etc. are fill-ins, never
    # real paths.  Must not be flagged even though no such file exists.
    (tmp_path / "doc.md").write_text(
        "![iso](../../visual_contracts/<YYYY-MM-DD>-<task-slug>_iso.svg)\n"
        "[wrapped](<filename>)\n",
        encoding="utf-8",
    )
    rc = checker.main([str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0, out


def test_links_in_code_and_comments_are_skipped(tmp_path, capsys):
    doc = "\n".join(
        [
            "Inline `[x](nope_inline.md)` code span.",
            "",
            "```markdown",
            "[x](nope_fenced.md)",
            "```",
            "",
            "<!-- [x](nope_comment.md) -->",
            "",
            "<!--",
            "multi-line [x](nope_multiline.md) comment",
            "-->",
        ]
    )
    (tmp_path / "doc.md").write_text(doc + "\n", encoding="utf-8")

    rc = checker.main([str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0, out
    for token in ("nope_inline", "nope_fenced", "nope_comment", "nope_multiline"):
        assert token not in out


def test_directory_target_is_accepted(tmp_path, capsys):
    (tmp_path / "subdir").mkdir()
    (tmp_path / "doc.md").write_text("[dir](subdir/)\n", encoding="utf-8")
    rc = checker.main([str(tmp_path)])
    assert rc == 0, capsys.readouterr().out


def test_url_escaped_space_is_unescaped(tmp_path, capsys):
    (tmp_path / "a b.md").write_text("x\n", encoding="utf-8")
    (tmp_path / "doc.md").write_text("[spaced](a%20b.md)\n", encoding="utf-8")
    rc = checker.main([str(tmp_path)])
    assert rc == 0, capsys.readouterr().out


# --------------------------------------------------------------------------
# Real-tree smoke: the live (non-design_plans) docs must be link-clean.
# --------------------------------------------------------------------------

def test_real_tracked_docs_are_clean():
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    md_files = checker.list_tracked_markdown(repo_root)
    # Design-plans are excluded by list_tracked_markdown; sanity-check that.
    assert all(
        checker.DESIGN_PLANS_EXCLUDE_PREFIX not in str(p.relative_to(repo_root))
        for p in md_files
    )
    broken = checker.find_broken_links(md_files)
    assert broken == [], (
        "broken relative links in tracked live docs:\n"
        + "\n".join(f"  {p}:{ln} -> {t}" for p, ln, t in broken)
    )
