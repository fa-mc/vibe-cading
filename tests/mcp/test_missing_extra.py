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

"""Missing-extra UX test for ``python -m vibe_cading.mcp`` (R6, test #9).

Runs the module in a subprocess with the ``mcp`` SDK *forced absent* (a
meta-path finder that raises ``ImportError`` on ``import mcp``), so the test is
valid whether or not ``mcp`` happens to be installed in the host env.  Asserts:
the one-line ``pip install -e ".[mcp]"`` hint is printed, the process exits
non-zero, and **no Python traceback escapes**.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# A bootstrap that installs a meta-path finder making `import mcp` raise, then
# runs the package as __main__ — exactly what `python -m vibe_cading.mcp` does.
_BOOTSTRAP = (
    "import sys, importlib.abc\n"
    "class _Block(importlib.abc.MetaPathFinder):\n"
    "    def find_spec(self, name, path, target=None):\n"
    "        if name == 'mcp' or name.startswith('mcp.'):\n"
    "            raise ImportError('simulated missing extra: ' + name)\n"
    "        return None\n"
    "sys.meta_path.insert(0, _Block())\n"
    "import runpy\n"
    "runpy.run_module('vibe_cading.mcp', run_name='__main__', alter_sys=True)\n"
)


def test_missing_extra_prints_hint_and_exits_nonzero():
    proc = subprocess.run(
        [sys.executable, "-c", _BOOTSTRAP],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
    )
    combined = proc.stdout + proc.stderr
    # one actionable line naming the exact install command.
    assert 'pip install -e ".[mcp]"' in combined
    assert "optional 'mcp' extra" in combined
    # non-zero exit.
    assert proc.returncode != 0
    # never a raw traceback.
    assert "Traceback" not in combined
