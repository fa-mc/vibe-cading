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

"""Structural-typing protocol for parametric screw generators.

This module defines :class:`ScrewProtocol`, the PEP 544 structural-typing
contract every concrete screw class in the library must satisfy.  A
concrete screw is a class that produces both a positive solid (the
physical screw body, accessed via ``.solid``) and a boolean-subtraction
cutter (accessed via ``.to_cutter(profile=None, fit="clearance")``).

The Phase 5 design replaces the historical ``Screw`` ABC with this
``Protocol``.  Concrete classes no longer inherit from a shared base;
they implement the protocol structurally and are recognised by
``isinstance(obj, ScrewProtocol)`` at runtime (the protocol is decorated
``@runtime_checkable``).

Why a Protocol rather than an ABC
---------------------------------
- **No shared implementation.**  Concrete screws share no helper code;
  every method is fully concrete-specific.  An ABC would advertise
  "is-a Screw" without delivering inheritable behaviour, mis-signalling
  to OSS contributors that there's shared machinery to discover.
- **Honest contract.**  Past versions of the ABC drifted from the
  concrete signatures (``to_cutter(mode, radial_allowance, head_recess_depth)``
  on the ABC vs ``to_cutter(profile=None, fit="clearance")`` on the
  concretes).  A Protocol is checked structurally, so signature drift
  shows up as a static-typing error rather than a lying superclass.
- **Extensibility.**  External OSS contributors adding new screw
  families (`AcmeThreadScrew`, `BallScrew`, ...) need no inheritance
  arrow; they ship a concrete class that exposes the right methods.

See also
--------
* :class:`vibe_cading.mechanical.protocols.CutterProtocol` — superset
  contract every cutter-producer satisfies; ``ScrewProtocol`` adds the
  call-time ``fit`` keyword and the ``.solid`` accessor on top.
* :class:`vibe_cading.mechanical.nuts.protocol.NutProtocol` and
  :class:`vibe_cading.mechanical.joints.protocol.JointProtocol` — sibling
  family protocols introduced alongside this one in Phase 5.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import cadquery as cq


@runtime_checkable
class ScrewProtocol(Protocol):
    """Structural-typing contract for any parametric screw generator.

    A class satisfies ``ScrewProtocol`` if it exposes both:

    * a ``solid`` property returning the positive screw geometry, and
    * a ``to_cutter(profile=None, fit="clearance")`` method returning
      the negative boolean-subtraction solid.

    ``fit`` selects between ``"clearance"``, ``"tap"``, and
    ``"interference"`` at call time per Round 4 Q3 resolution; the
    optional ``profile`` argument carries per-grade tolerance data
    (see :class:`vibe_cading.print_settings.ToleranceProfile`).

    The protocol is ``@runtime_checkable`` so callers can write
    ``isinstance(obj, ScrewProtocol)`` to gate generic screw pipelines on
    the contract.  Note that ``isinstance`` with a ``Protocol`` only
    checks method *presence*, not signatures — full signature validation
    requires a static type checker (mypy / pyright).
    """

    @property
    def solid(self) -> cq.Workplane:
        """Return the positive physical model of the screw."""
        ...

    def to_cutter(
        self,
        profile: "object | None" = None,
        fit: str = "clearance",
    ) -> cq.Workplane:
        """Return a boolean-subtraction tool sized for this screw.

        :param profile: Optional ``ToleranceProfile`` driving per-grade
            allowances.  When ``None``, implementations fall back to
            ``get_profile()`` (the env-configured default).
        :param fit: ``"clearance"`` (loose fit), ``"tap"`` (tight fit),
            or ``"interference"`` (press fit).  Concrete families may
            constrain the supported set (e.g. ``SetScrew`` only accepts
            ``"clearance"`` or ``"tap"``).
        """
        ...
