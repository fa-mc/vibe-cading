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

"""Combined Cover + BatteryTray seated view -- a cross-class composition.

Per this project's *Assembly modules* convention (see the root
``CLAUDE.md``), a demonstration spanning more than one class belongs in a
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

Placement: the tray's floor rests directly on the cover's inner face
(``PoweredUpHubCover.PLATE_THICKNESS`` above the cover's own Z = 0 datum) --
the real hub's housing (task 3, not built here) will slot both parts inside
its own cavity, but this two-part seating is well-defined without it.
"""

from __future__ import annotations

import cadquery as cq

from vibe_cading.lego_adapters.poweredup_hub.battery_tray import PoweredUpHubBatteryTray
from vibe_cading.lego_adapters.poweredup_hub.cover import PoweredUpHubCover


def assemble(**kwargs) -> list[tuple[cq.Workplane, str, str]]:
    """Cover + BatteryTray, seated as they seat when the lid is closed."""
    cover = PoweredUpHubCover(**kwargs.get("cover_kwargs", {}))
    tray = PoweredUpHubBatteryTray(**kwargs.get("tray_kwargs", {}))

    tray_solid = tray.solid.translate((0, 0, PoweredUpHubCover.PLATE_THICKNESS))

    return [
        (cover.solid, "Cover", "gold"),
        (tray_solid, "BatteryTray", "royalblue"),
    ]
