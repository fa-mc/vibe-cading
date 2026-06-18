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

"""Tests for ``vibe_cading/tools/check_mcp_import_isolation.py`` (R7).

* **#10 — Layer A** flags a planted ``from vibe_cading.mcp import x`` (and a bare
  ``import mcp``) in a temp fixture, while the real tree is clean; a docstring
  mention of the forbidden name does NOT false-positive (AST, not grep).
* **#11 — Layer B** asserts, in a clean subprocess, that ``import vibe_cading``
  leaves ``sys.modules`` free of ``mcp`` / ``vibe_cading.mcp.*`` — host-
  independent (pure import-graph).
"""

from __future__ import annotations

import pathlib

from vibe_cading.tools import check_mcp_import_isolation as guard


# --------------------------------------------------------------------------
# Test #10 — Layer A (static AST scan)
# --------------------------------------------------------------------------

def test_layer_a_flags_planted_violation(tmp_path):
    pkg = tmp_path / "fakepkg"
    pkg.mkdir()
    clean = pkg / "clean.py"
    clean.write_text("import os\nx = 1\n", encoding="utf-8")
    violating_from = pkg / "bad_from.py"
    violating_from.write_text("from vibe_cading.mcp import tools\n", encoding="utf-8")
    violating_import = pkg / "bad_import.py"
    violating_import.write_text("import mcp.server\n", encoding="utf-8")

    found = guard.find_violations([pkg])
    found_set = {p.name for p in found}
    assert "bad_from.py" in found_set
    assert "bad_import.py" in found_set
    assert "clean.py" not in found_set


def test_layer_a_docstring_mention_does_not_false_positive(tmp_path):
    pkg = tmp_path / "fakepkg2"
    pkg.mkdir()
    f = pkg / "mentions.py"
    # The forbidden tokens appear only in a docstring / comment / string literal.
    f.write_text(
        '"""This file talks about import mcp and vibe_cading.mcp but does not."""\n'
        "# import mcp  -- a comment, not a real import\n"
        's = "from vibe_cading.mcp import x"\n',
        encoding="utf-8",
    )
    found = guard.find_violations([pkg])
    assert f not in found
    assert found == []


def test_layer_a_excludes_carve_out_dirs(tmp_path):
    # A file under an excluded dir must be skipped even if it imports mcp.
    root = tmp_path / "root"
    sub = root / "carved"
    sub.mkdir(parents=True)
    bad = sub / "uses_sdk.py"
    bad.write_text("import mcp\n", encoding="utf-8")
    # Without exclude -> flagged; with exclude -> skipped.
    assert bad in guard.find_violations([root])
    assert guard.find_violations([root], exclude=[sub]) == []


def test_layer_a_clean_on_real_tree():
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    roots = [repo_root / "vibe_cading", repo_root / "parts"]
    exclude = [
        repo_root / "vibe_cading" / "mcp",
        repo_root / "vibe_cading" / "tools",
    ]
    assert guard.find_violations(roots, exclude) == []


# --------------------------------------------------------------------------
# Test #11 — Layer B (live import-graph assertion in a clean subprocess)
# --------------------------------------------------------------------------

def test_layer_b_no_leak_on_real_tree():
    rc, out = guard.run_layer_b()
    assert rc == 0, f"Layer B reported a leak: {out}"
    # the probe prints the (empty) leaked list.
    assert "LEAKED:" in out
    leaked_line = [ln for ln in out.splitlines() if ln.startswith("LEAKED:")][0]
    assert leaked_line == "LEAKED:"  # nothing after the colon
