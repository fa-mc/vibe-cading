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

"""vibe-cading library package — parametric CadQuery primitives.

Top-level marker so ``vibe_cading.*`` resolves as a regular package
(not a namespace package).  Per the design Round 5.5 "two-level
__init__.py discipline", this file intentionally does NOT re-export
anything from sub-packages — contributors import the symbols they need
from the leaf package that owns them (e.g.
``from vibe_cading.mechanical.screws import MetricMachineScrew``).
"""

try:
    from .__commit__ import __commit__
except ImportError:
    __commit__ = "unknown"

# ``__version__`` is sourced from installed package metadata so
# ``pyproject.toml`` ``[project].version`` stays the single source of truth
# (see docs/releasing.md). A source checkout that was never ``pip install``-ed
# has no metadata, so fall back to a clearly-marked sentinel instead of raising.
from importlib.metadata import version as _pkg_version, PackageNotFoundError

try:
    __version__ = _pkg_version("vibe_cading")
except PackageNotFoundError:  # running from a source checkout, not installed
    __version__ = "0.0.0+unknown"
