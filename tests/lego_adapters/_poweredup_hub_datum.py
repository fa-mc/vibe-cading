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

"""The Powered Up hub's half-finished re-datum, in one place.

Rounds 60-61 re-dimensioned :class:`PoweredUpHubCover` from calipers on the
owner's real LEGO parts, because the LDraw reference was found to be wrong
about the hardware -- it draws the lid 54.400 mm wide where the part measures
52.330, and the housing cavity 54.400 where it measures 52.960. The reference
figures were verified three independent ways (raw ``.dat`` in LDU, converted
mesh, STEP); they agree with each other and disagree with the hardware, so the
conversion pipeline was never the problem. See
``docs/design_plans/2026-08-28-poweredup-hub_physical-measurements.md``, which
is authoritative wherever it and LDraw overlap.

The Housing and Tray have NOT been re-datumed yet -- deliberately, at the
owner's direction to get the Cover printed and fit-tested first. So the Cover
is dimensioned to the REAL housing while ours is still dimensioned from LDraw,
and every test that measures one against the other is comparing parts from two
different reference frames. Those tests are not wrong and their tolerances have
NOT been loosened; they are temporarily meaningless, which is a different thing
and is why this is an xfail rather than a widened bound.

**strict=True on purpose.** When the Housing is re-datumed these will start
passing, and a strict xfail turns that into a LOUD failure ("XPASS") demanding
the marker be removed. A non-strict xfail would let them quietly pass forever
while still reporting as expected-failures -- which is how a suite ends up with
a dozen permanently disabled cross-part checks that nobody notices are green.
"""

import pytest

CROSS_DATUM_REASON = (
    "Cover is datumed to the REAL housing (rounds 60-61, measured); Housing "
    "and Tray are still on the LDraw datum, so this cross-part measurement "
    "compares two reference frames. Remove this marker in the same change "
    "that re-datums the Housing -- see "
    "docs/design_plans/2026-08-28-poweredup-hub_physical-measurements.md"
)

#: Apply to any test that measures the Cover against the Housing or Tray.
xfail_cross_datum = pytest.mark.xfail(reason=CROSS_DATUM_REASON, strict=True)
