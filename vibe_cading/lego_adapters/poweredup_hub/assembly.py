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

"""Combined Housing + Cover seated view -- a cross-class composition.

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

**Both parts shown** -- an earlier version omitted
:class:`~vibe_cading.lego_adapters.poweredup_hub.housing.PoweredUpHubHousing`
because it did not exist yet when this module was first written; leaving it
out afterward hid exactly the seating faults (B1/B2/B3) the round-18 audit
found, since this is the view most likely to expose them.

**Round 22 -- the BatteryTray is gone.** A separate tray part could not fit
under a 3-stud (24.0 mm) bottom layer alongside a 20 mm pack: the stack
(cover plate 1.2 + tray floor 1.5 + pack 20.0 + strap 1.8 = 24.5 mm) blew
the 22.0 mm available below the deck by 2.5 mm even after the tray's raised
floor standoff was reclaimed.

**Round 47 -- the 20 mm pack figure above is WRONG, and the box is 0.1 mm
too short.** The target pack (Spektrum SPMX812SH2) is listed by every
vendor at 58 x 32 x 20 mm, which is what rounds 22-46 designed against.
Caliper-measured on the real part, it is **20.9 mm** tall. The interior is
``DECK_Z - DECK_THICKNESS - PLATE_THICKNESS`` = 24.0 - 2.0 - 1.2 =
**20.800 mm** (measured on the built solids, not just derived: the deck
underside is at Z = 22.000 exactly, flat across the whole footprint), so
the real pack interfered by 0.100 mm and held the Cover proud of its latch.
X and Y were never the problem -- the pack has 12.0 mm of free width each
side.

**Fixed in the same round** by thinning the deck: ``DECK_THICKNESS``
2.000 -> 1.600, so the interior is 21.200 mm and the measured pack clears
by 0.300 mm. The user chose this over raising ``DECK_STUDS``, so the
external 3-stud / 24.000 mm height is deliberately unchanged. Guarded by
``test_interior_clears_the_target_battery``, which measures the built
solids against the pack rather than re-deriving the constants -- until
round 47 every test here checked the two printed parts against each other
and none checked them against their payload. Per the user's round-22 direction the tray was
deleted outright and its side extraction tabs re-homed onto
:class:`PoweredUpHubCover` (which already spans the same |X| = 27.200 mm
edge), so the pack now sits directly on the cover with the handles still
reachable through the housing's own side windows.

Placement: :class:`~vibe_cading.lego_adapters.poweredup_hub.housing.PoweredUpHubHousing`
and :class:`PoweredUpHubCover` share one ``Z = 0`` datum (the lid *is* the
housing's floor -- see ``PoweredUpHubHousing``'s own docstring), so neither
part needs a transform.
"""

from __future__ import annotations

import cadquery as cq

from vibe_cading.lego_adapters.poweredup_hub.cover import PoweredUpHubCover
from vibe_cading.lego_adapters.poweredup_hub.housing import PoweredUpHubHousing
from vibe_cading.print_settings import ToleranceProfile


def assemble(
    profile: ToleranceProfile | str | None = None,
) -> list[tuple[cq.Workplane, str, str]]:
    """Housing + Cover, seated as they seat when the lid is closed.

    ``profile`` forwards to both parts' own ``profile`` constructor
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

    return [
        (housing.solid, "Housing", "lightgray"),
        (cover.solid, "Cover", "gold"),
    ]
