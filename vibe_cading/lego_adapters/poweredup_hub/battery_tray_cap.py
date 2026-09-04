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

"""PoweredUpHubBatteryTrayCap -- the glued-in plate that roofs the battery
tray's strap channel.

Round 55, from the user's marked-up sketch. Not a reference feature: LDraw
``24849`` has no strap channel at all, so nothing here is measured off it.

This is the *second* time the tray's floor has involved a separate part,
and the two are not the same design -- worth stating plainly, because the
first one was reverted:

* **Round 54 (reverted)** split the WHOLE floor off as
  ``PoweredUpHubBatteryTrayFloor``, leaving the tray as two unconnected
  side walls. The user rejected it and merged the tray back together.
* **Round 55 (this class)** leaves the floor integral and splits off only
  a small plate that roofs the strap channel. The tray is one piece; this
  plate is the channel's roof, which is exactly the feature that cannot be
  printed in place (it would bridge the corridor). Nothing structural
  depends on the glue joint -- the plate carries the pack's weight into a
  ledge it sits flat on, in compression, not on the adhesive.
"""

from __future__ import annotations

import cadquery as cq

from vibe_cading.cq_utils import rounded_box
from vibe_cading.lego_adapters.poweredup_hub.battery_tray import (
    PoweredUpHubBatteryTray,
)
from vibe_cading.print_settings import ToleranceProfile, get_profile


class PoweredUpHubBatteryTrayCap:
    """A flat rectangular plate, :attr:`PoweredUpHubBatteryTray.STRAP_CAP_THICKNESS`
    thick, dropped from above into the rebate in the TOP face of
    :class:`~vibe_cading.lego_adapters.poweredup_hub.battery_tray.PoweredUpHubBatteryTray`'s
    floor and glued down flush with it. It roofs the strap corridor,
    turning it into a channel that runs UNDER the plate -- floored by
    :class:`~vibe_cading.lego_adapters.poweredup_hub.cover.PoweredUpHubCover`'s
    own face, roofed by this one.

    Prints flat on the bed with no supports and no overhangs -- which is
    the entire reason it is a separate part: printed in place it would be
    a bridge over the corridor.

    Origin / datum
    ---------------
    ``(0, 0, 0)`` is the plate's own **bottom face** and its print-bed
    face, per this project's zero-datum convention -- NOT the height it
    seats at. Seated, its bottom face sits
    :attr:`PoweredUpHubBatteryTray.STRAP_CAP_Z` above the Tray's own
    bottom rim, so
    :func:`~vibe_cading.lego_adapters.poweredup_hub.assembly.assemble`
    applies that offset on top of the Tray's seat translate. X and Y are
    centred on the channel, matching the Tray's own frame.

    Parameters
    ----------
    profile:
        Manufacturing tolerance profile. Sets the running clearance
        between this plate's edges and the rebate walls -- a glued joint,
        so a small positive gap is intended (glue needs somewhere to go),
        not a fit worth chasing to zero. Accepts a
        :class:`~vibe_cading.print_settings.ToleranceProfile` instance, a
        profile name string, or ``None`` for the process-global default.
    """

    #: Plate thickness -- deliberately not an independent number. It IS
    #: the rebate depth, so the plate finishes flush with the Tray floor's
    #: top face and adds nothing to the stack under the battery.
    THICKNESS = PoweredUpHubBatteryTray.STRAP_CAP_THICKNESS

    #: Height of this plate's bottom face above the Tray's own ``Z = 0``
    #: bottom rim once seated -- i.e. the clear height of the strap
    #: channel beneath it. Re-exported from the Tray so a caller placing
    #: this part does not have to know which class owns the number.
    SEAT_Z = PoweredUpHubBatteryTray.STRAP_CAP_Z

    def __init__(self, profile: ToleranceProfile | str | None = None) -> None:
        if profile is None or isinstance(profile, str):
            prof = get_profile(profile) if isinstance(profile, str) else get_profile()
        else:
            prof = profile
        self._profile = prof

        # Sized off the Tray's own pocket rather than a re-derived copy of
        # its formula -- see cap_rebate_half_extents' docstring.
        x_half, y_half = PoweredUpHubBatteryTray.cap_rebate_half_extents(prof)
        self._x_half = x_half - prof.free.radial
        self._y_half = y_half - prof.free.radial

        self._solid = self._build()

    def _build(self) -> cq.Workplane:
        part = rounded_box(
            width=2 * self._x_half,
            depth=2 * self._y_half,
            height=self.THICKNESS,
            corner_r=0.0,
            center=(0.0, 0.0, 0.0),
        )
        assert len(part.solids().vals()) == 1, (
            "Expected single solid, got multiple pieces"
        )
        return part

    @property
    def solid(self) -> cq.Workplane:
        return self._solid
