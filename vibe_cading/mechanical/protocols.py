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

"""Structural-typing protocols for boolean cutter producers.

This module defines :class:`CutterProtocol`, the PEP 544 structural
typing contract every cutter-producing class in the library must satisfy.

A *cutter producer* is any class whose primary contribution to a parent
assembly is a boolean-subtraction solid — holes (``ClearanceHole``,
``CounterboreHole``, ``TeardropHole``, ...), inserts (``HeatSetInsert``),
joint sockets (``DovetailJoint.to_cutter``), drive recesses
(``HexDrive``, ``TorxDrive``, ...), ventilation grilles, and so on.

The unified call shape is::

    cutter_solid = obj.to_cutter(profile=None)

The single optional ``profile`` argument is a :class:`ToleranceProfile`
that the implementation may consult to inflate / deflate per-grade
allowances.  Producers that don't need tolerance data simply accept
``profile`` and ignore it.

Through-vs-blind overcut policy
-------------------------------
The overcut policy — how far the cutter extends past the entry and
terminal faces — is **baked per class as a class-level constant**, not
exposed as a call-time keyword argument.  This makes the geometric
contract explicit at the class definition site:

* Through-hole cutters (``ClearanceHole``, ``CounterboreHole``,
  ``TeardropHole``, ``SlottedHole``, ``TaperedHole``, ``Keyhole``,
  ``HexDrive``, ``SlottedDrive``, ``PhillipsDrive``, ``TorxDrive``,
  ``HexVentilationGrille``, ``SlottedVentilationGrille``) extend the
  cutter past both faces by a large value (typically 100 mm), so the
  subtraction is reliable even when the cutter is placed flush against
  the host body's boundary.

* Blind-hole cutters (``CaptiveNutPocket``) extend only past the entry
  face; the terminal face sits exactly at the design depth so the
  resulting pocket has the intended floor.

Tests assert this policy at the bounding-box level (see
``tests/test_cutter_overcut.py``, design §Tests T13).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import cadquery as cq


# Forward reference — avoid an eager import of ``print_settings`` to keep
# this module's import surface minimal.  Concrete implementations import
# ``ToleranceProfile`` directly.
@runtime_checkable
class CutterProtocol(Protocol):
    """Structural-typing contract for any boolean-cutter producer.

    A class satisfies ``CutterProtocol`` if it exposes a ``to_cutter``
    method with the unified call signature.  The protocol is
    ``@runtime_checkable`` so callers can write
    ``isinstance(obj, CutterProtocol)`` to gate generic cutter pipelines
    on the contract.

    Note that ``isinstance`` with a ``Protocol`` only checks method
    *presence*, not signatures — full signature validation requires a
    static type checker (mypy / pyright).
    """

    def to_cutter(self, profile: "object | None" = None) -> cq.Workplane:
        """Return a boolean-subtraction solid sized for this feature.

        :param profile: Optional ``ToleranceProfile`` driving the
            per-grade allowances.  When ``None``, implementations fall
            back to ``get_profile()`` (the env-configured default).
        """
        ...
