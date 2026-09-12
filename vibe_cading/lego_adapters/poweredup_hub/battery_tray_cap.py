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

    #: NOMINAL plate thickness -- the rebate's own depth. The plate as BUILT
    #: is thinner by the profile's axial allowance; see ``self._thickness``
    #: and :attr:`GLUE_GAP_Z`. Kept as the nominal because it is the pocket
    #: this plate is sized against, not an independent number.
    THICKNESS = PoweredUpHubBatteryTray.STRAP_CAP_THICKNESS

    #: ROUND 88 -- the plate's Z clearance, which did not exist before.
    #:
    #: Owner, on a printed part: *"the plate does not sit flush in the
    #: tray"*. It sat PROUD, and the cause was that this class gave the
    #: plate a running clearance on its four EDGES (``free.radial`` per
    #: flank, in ``__init__`` below) but NONE on its thickness: ``THICKNESS``
    #: was exactly the rebate depth, 1.200 against 1.200. This is a GLUED
    #: joint -- the class docstring says so, and says "glue needs somewhere
    #: to go" -- but the only place it had to go was under the plate, which
    #: is precisely what lifts it proud of the floor.
    #:
    #: An exactly-filling plate cannot finish flush in practice; it can only
    #: finish flush or proud, and every real-world departure (glue film,
    #: elephant's foot on the rebate floor, a first-layer squish on the
    #: plate) pushes it the proud way. Recessed by a few tenths is harmless
    #: -- the pack bears on the floor around it -- while proud is exactly
    #: the failure the owner hit.
    #:
    #: Routed through the profile rather than a literal, so it tracks the
    #: same knob every other clearance on this assembly uses and a user can
    #: tune it in one place. Note ``cnc`` has ``free.axial == 0.000``: on a
    #: machined part an exact fit is correct and this correctly yields no
    #: gap. The value is computed per-instance in ``__init__`` (it depends
    #: on the profile), and exposed as ``self.thickness``.

    #: Height of this plate's bottom face above the Tray's own ``Z = 0``
    #: bottom rim once seated -- i.e. the clear height of the strap
    #: channel beneath it. Re-exported from the Tray so a caller placing
    #: this part does not have to know which class owns the number.
    SEAT_Z = PoweredUpHubBatteryTray.STRAP_CAP_Z

    #: Y of this plate's own centre once seated, in the Tray's frame.
    #: Round 72 centre-aligned the whole strap assembly with the side tabs
    #: (Y = 2.000) instead of leaving it on Y = 0, so a caller that places
    #: this part at Y = 0 now misses its rebate by that much. Re-exported
    #: for the same reason as SEAT_Z: the placer should not have to know
    #: which class owns the number.
    SEAT_Y = PoweredUpHubBatteryTray.STRAP_Y_CENTER

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

        # ROUND 88 -- the edges have always taken a clearance here; the
        # thickness now does too. See GLUE_GAP_Z for why, and for the printed
        # part that showed it.
        self._thickness = self.THICKNESS - prof.free.axial
        assert self._thickness > 0.0, (
            f"the profile's axial allowance ({prof.free.axial:.3f}) is at or "
            f"beyond the rebate depth ({self.THICKNESS:.3f}) -- the plate "
            f"would have no thickness left"
        )
        # The plate must still be thick enough to be a plate. Two perimeters
        # at a 0.400 nozzle is the same floor the housing's latch skin uses.
        assert self._thickness >= 0.800, (
            f"the plate would be {self._thickness:.3f} mm thick, below the "
            f"0.800 mm printable floor. The rebate depth "
            f"({self.THICKNESS:.3f}) cannot absorb this profile's axial "
            f"allowance ({prof.free.axial:.3f}) -- deepen the rebate rather "
            f"than shipping an unprintable plate."
        )

        self._solid = self._build()

    @property
    def thickness(self) -> float:
        """As-built plate thickness, i.e. the rebate depth less the glue gap.

        Public because the seated height of anything stacked on this plate
        depends on it, and a caller re-deriving it from ``THICKNESS`` would
        silently miss the gap.
        """
        return self._thickness

    def _build(self) -> cq.Workplane:
        part = rounded_box(
            width=2 * self._x_half,
            depth=2 * self._y_half,
            height=self._thickness,
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
