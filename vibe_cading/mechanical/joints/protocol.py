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

"""Structural-typing protocol for parametric joint generators.

This module defines :class:`JointProtocol`, the PEP 544 structural-typing
contract every concrete joint class in the library must satisfy.  A
*joint* is a printed-in-place mating pair: a positive ``male`` half that
unions into one body and a negative ``to_cutter`` half that subtracts
from the receiving body.

The Phase 5 design replaces the historical ``Joint`` / ``BaseJoint`` ABC
with this ``Protocol``.  Concrete classes no longer inherit from a
shared base; they implement the protocol structurally and are recognised
by ``isinstance(obj, JointProtocol)`` at runtime (the protocol is
decorated ``@runtime_checkable``).

Why ``male`` is part of the contract
------------------------------------
Joints are the one cutter-producing family where the positive side is
part of the public API.  Concrete joints implement ``CutterProtocol``
(via ``to_cutter``) AND additionally expose ``male(overlap)`` as a
joint-specific extra.  There is no separate ``MateableProtocol`` — the
``male`` half is a joint convention, not a generalisable cutter-protocol
concept.

OSS contributors adding a new joint type implement BOTH ``to_cutter``
(required by :class:`vibe_cading.mechanical.protocols.CutterProtocol`)
AND ``male`` (joint convention, documented here).  A ``.solid`` property
is also conventional (returns ``self.male()`` with the default overlap)
so a single-instance ``tools/view.py`` invocation works without extra
ceremony — but it lives at the concrete class, not on the Protocol,
because joints aren't the only ``.solid`` exposer and forcing it onto
the Protocol would be redundant with ``CutterProtocol`` conventions.

See also
--------
* :class:`vibe_cading.mechanical.protocols.CutterProtocol` — superset
  contract every cutter-producer satisfies.
* :class:`vibe_cading.mechanical.screws.protocol.ScrewProtocol` and
  :class:`vibe_cading.mechanical.nuts.protocol.NutProtocol` — sibling
  family protocols introduced alongside this one in Phase 5.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import cadquery as cq


@runtime_checkable
class JointProtocol(Protocol):
    """Structural-typing contract for any parametric joint generator.

    A class satisfies ``JointProtocol`` if it exposes both:

    * a ``male(overlap=1.0)`` method returning the positive geometry
      (the pin, hook, or peg that unions into one body), and
    * a ``to_cutter(profile=None)`` method returning the negative
      cavity that subtracts from the receiving body.

    The protocol is ``@runtime_checkable`` so callers can write
    ``isinstance(obj, JointProtocol)`` to gate generic joint pipelines
    on the contract.  Note that ``isinstance`` with a ``Protocol`` only
    checks method *presence*, not signatures — full signature validation
    requires a static type checker (mypy / pyright).
    """

    def male(self, overlap: float = 1.0) -> cq.Workplane:
        """Return the positive joint half (pin / hook / peg).

        :param overlap: Extra length extending past the joint's nominal
            entry face for a clean boolean union into the host body.
        """
        ...

    def to_cutter(self, profile: "object | None" = None) -> cq.Workplane:
        """Return the negative joint cavity for boolean subtraction.

        :param profile: Optional ``ToleranceProfile`` accepted to satisfy
            :class:`vibe_cading.mechanical.protocols.CutterProtocol`.
            Joint clearance is typically owned by a geometric
            ``clearance`` constructor argument rather than the profile,
            so most implementations accept and ignore this parameter.
        """
        ...
