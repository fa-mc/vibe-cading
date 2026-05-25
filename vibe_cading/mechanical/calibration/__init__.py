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

"""Printable calibration gauges for the active print-tolerance profile.

This sub-package collects single-anchor sweep gauges consumed by the
``tools/calibrate.py`` CLI helper. Each gauge exposes a public
``.solid`` and a public swept-dimension tuple (``.diameters`` or
``.widths``) so the helper can read the swept values live (FR11) and
the user can pick the best-fitting variant off a single printed part.

The shape mirrors :class:`vibe_cading.lego.axle_hole_gauge.AxleHoleGauge`
(flat block + label band + engraved labels). New single-anchor sweep
gauges added here should follow the same convention. A shared
``_SweepGaugeBase`` is intentionally deferred until a third exemplar
materialises (see design brief R7).
"""

from vibe_cading.mechanical.calibration.m3_clearance_gauge import (
    MThreeClearanceGauge,
)
from vibe_cading.mechanical.calibration.m3_nut_pocket_gauge import (
    MThreeNutPocketGauge,
)

__all__ = ["MThreeClearanceGauge", "MThreeNutPocketGauge"]
