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

"""Combined Housing + Cover + BatteryTray seated view -- a cross-class
composition.

Per this project's *Assembly modules* convention (see
``vibe/INSTRUCTIONS.md``), a demonstration spanning more than one class belongs in a
module-level ``assemble()`` function, viewable via::

    python3 vibe_cading/tools/view.py --assembly \\
        vibe_cading.lego_adapters.poweredup_hub.assembly

This is **not** a registrable ``visual_contracts.toml`` row -- the freshness
checker's ``VisualContract`` regenerates a single class's ``.solid`` via
:func:`vibe_cading.tools.preview.export_previews`, which has no concept of a
cross-class composition. The combined seated view is still generated (per
the design brief's *Visual contracts* section) via a one-off developer probe
that reuses this module's own placement, then committed as an
**unregistered, illustrative** contract -- exactly as the design-stage probe
it replaces was. Flagged in the design brief's Implementation Status as a
pre-existing tooling gap, not a regression introduced here.

**All three parts now shown (round 18)** -- an earlier version omitted
:class:`~vibe_cading.lego_adapters.poweredup_hub.housing.PoweredUpHubHousing`
because it did not exist yet when this module was first written; leaving it
out afterward hid exactly the seating faults (B1/B2/B3) the round-18 audit
found, since this is the view most likely to expose them.

Placement: :class:`~vibe_cading.lego_adapters.poweredup_hub.housing.PoweredUpHubHousing`
and :class:`PoweredUpHubCover` share one ``Z = 0`` datum (the lid *is* the
housing's floor -- see ``PoweredUpHubHousing``'s own docstring), so Housing
needs no transform either. The tray's floor rests directly on the cover's
inner face (``PoweredUpHubCover.PLATE_THICKNESS`` above the cover's own
``Z = 0`` datum).
"""

from __future__ import annotations

import cadquery as cq

from vibe_cading.lego_adapters.poweredup_hub.battery_tray import PoweredUpHubBatteryTray
from vibe_cading.lego_adapters.poweredup_hub.cover import PoweredUpHubCover
from vibe_cading.lego_adapters.poweredup_hub.housing import PoweredUpHubHousing
from vibe_cading.print_settings import ToleranceProfile


def assemble(
    profile: ToleranceProfile | str | None = None,
) -> list[tuple[cq.Workplane, str, str]]:
    """Housing + Cover + BatteryTray, seated as they seat when the lid is closed.

    ``profile`` forwards to all three parts' own ``profile`` constructor
    argument (each resolves ``None`` to the process-global default via
    :func:`vibe_cading.print_settings.get_profile`), so a caller can render
    the seated assembly under a non-default tolerance profile. This is the
    repo's first ``assemble()`` -- per *Assembly modules* in
    ``vibe/INSTRUCTIONS.md``, its signature is the convention future
    cross-class assembly modules copy, so it carries only parameters every
    consumer can actually supply (TL phase-4 review, finding M3 -- the
    prior ``**kwargs`` / ``*_kwargs`` shape was unreachable dead surface:
    ``vibe_cading/tools/view.py``'s ``--assembly`` path calls ``assemble()``
    with no arguments).
    """
    housing = PoweredUpHubHousing(profile=profile)
    cover = PoweredUpHubCover(profile=profile)
    tray = PoweredUpHubBatteryTray(profile=profile)

    tray_solid = tray.solid.translate((0, 0, PoweredUpHubCover.PLATE_THICKNESS))

    return [
        (housing.solid, "Housing", "lightgray"),
        (cover.solid, "Cover", "gold"),
        (tray_solid, "BatteryTray", "royalblue"),
    ]
