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

"""vibe_cading.mechanical — mid-level package.

Per the design Round 5.5 "two-level __init__.py discipline", this
mid-level package intentionally re-exports nothing.  Contributors import
the symbols they need directly from the leaf modules / subpackages that
own them, e.g.::

    from vibe_cading.mechanical.holes import ClearanceHole
    from vibe_cading.mechanical.screws import MetricMachineScrew
"""
