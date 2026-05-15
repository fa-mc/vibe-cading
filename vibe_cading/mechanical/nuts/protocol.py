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

"""Structural-typing protocol for parametric nut generators.

This module defines :class:`NutProtocol`, the PEP 544 structural-typing
contract every concrete nut class in the library must satisfy.  A
concrete nut is a class that produces both a positive solid (the
physical nut body, accessed via ``.solid``) and a boolean-subtraction
pocket cutter (accessed via ``.to_cutter(profile=None)``).

The Phase 5 design replaces the historical ``Nut`` ABC with this
``Protocol``.  Concrete classes no longer inherit from a shared base;
they implement the protocol structurally and are recognised by
``isinstance(obj, NutProtocol)`` at runtime (the protocol is decorated
``@runtime_checkable``).

Optional captive-slot extension
-------------------------------
Some nuts (notably :class:`vibe_cading.mechanical.nuts.tnut.TNut`)
additionally expose ``to_captive_slot(slot_length, ...)`` for sliding /
captive trap geometry.  This is a nut-specific extension and is
explicitly **not** part of ``NutProtocol``; nuts that don't support
slot-trap geometry are still valid implementers.

See also
--------
* :class:`vibe_cading.mechanical.protocols.CutterProtocol` — superset
  contract every cutter-producer satisfies; ``NutProtocol`` adds the
  ``.solid`` accessor on top.
* :class:`vibe_cading.mechanical.screws.protocol.ScrewProtocol` and
  :class:`vibe_cading.mechanical.joints.protocol.JointProtocol` — sibling
  family protocols introduced alongside this one in Phase 5.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import cadquery as cq


@runtime_checkable
class NutProtocol(Protocol):
    """Structural-typing contract for any parametric nut generator.

    A class satisfies ``NutProtocol`` if it exposes both:

    * a ``solid`` property returning the positive nut geometry, and
    * a ``to_cutter(profile=None)`` method returning the negative
      boolean-subtraction pocket cutter.

    The protocol is ``@runtime_checkable`` so callers can write
    ``isinstance(obj, NutProtocol)`` to gate generic nut pipelines on
    the contract.  Note that ``isinstance`` with a ``Protocol`` only
    checks method *presence*, not signatures — full signature validation
    requires a static type checker (mypy / pyright).
    """

    @property
    def solid(self) -> cq.Workplane:
        """Return the positive physical model of the nut."""
        ...

    def to_cutter(self, profile: "object | None" = None) -> cq.Workplane:
        """Return a static pocket cutter for press-fitting the nut.

        :param profile: Optional ``ToleranceProfile`` driving per-grade
            allowances.  When ``None``, implementations fall back to
            ``get_profile()`` (the env-configured default).
        """
        ...
