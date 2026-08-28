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

"""12 mm hex prism carrying a heat-set-insert pocket -- one component of the
fused Lego Technic axle -> 12 mm hex hub adapter (see
:mod:`vibe_cading.lego_adapters.axle_hex_hub.axle_hex_hub_adapter`).

Coordinate system
------------------
Z = 0            : bottom (mating) face -- fuses flush against
                    :class:`~vibe_cading.lego_adapters.axle_hex_hub.compression_collet.AxleCompressionCollet`.
Z = ``thickness``: top (outward) face -- carries the heat-set-insert pocket.
Centred at X = 0, Y = 0 on the hex prism's own rotation axis.

Design intent
-------------
Per the approved design brief
(``docs/design_plans/2026-08-25-lego-axle-hex-hub-adapter_design.md``, D6/D7,
Round 2), this component carries **no axle-bore-related feature at all** --
the axle bore is entirely self-contained in
:class:`~vibe_cading.lego_adapters.axle_hex_hub.compression_collet.AxleCompressionCollet`
(D3b).  The only feature here is a straight-walled heat-set-insert pocket,
reusing :class:`~vibe_cading.mechanical.inserts.HeatSetInsert`'s generic
constructor directly with ``top_diameter == bot_diameter`` (degenerating its
taper to a straight pocket).
"""

from __future__ import annotations

import math

import cadquery as cq

from vibe_cading.mechanical.inserts import HeatSetInsert
from vibe_cading.print_settings import get_profile


class HexInsertHub:
    """12 mm hex prism with a parametrized heat-set-insert pocket.

    Parameters
    ----------
    hex_across_flats : float
        Hex outer profile measured flat-to-flat (mm).  Default 12.0 mm,
        matching :class:`~vibe_cading.rc.hex_hub_bearing.hex_hub_nut.HexHubNut`
        / :class:`~vibe_cading.rc.freespin_hex_hub.FreespinHexHub`'s
        established RC-hex-part convention.
    thickness : float
        Axial thickness of the hex prism (mm).  Default 6.0 mm.
    hex_chamfer : float
        Chamfer size applied to all sharp hex edges (mm).  Default 0.5 mm,
        matching the same RC-hex-part family convention.
    insert_diameter : float
        Heat-set-insert pocket diameter (mm), raw nominal -- no profile
        allowance, since heat-set inserts rely on knurl-bite into the
        plastic rather than a designed cold mechanical fit (D6).  Default
        5.0 mm, matching the user's on-hand M3-class inserts.
    insert_length : float
        Heat-set-insert pocket depth (mm).  Constructor parameter -- one of
        3.0 / 4.0 / 5.0 mm are the user's on-hand physical options; default
        5.0 mm (D6, Round 3 -- the human's final choice, prioritizing
        thread-engagement / pull-out and torque-out holding power over
        floor-margin conservatism).  3.0 mm and 4.0 mm remain fully valid,
        equally-safe ``--params`` overrides for a user who prefers more
        floor margin.
    profile : str | None
        Tolerance profile name from ``print_profiles.json``.  ``None`` uses
        the globally-configured default.  Currently only consulted for
        forward-compatibility / consistency with the sibling component --
        the insert pocket itself takes no profile-driven allowance (D6).

    Raises
    ------
    ValueError
        If ``thickness - insert_length < MIN_INSERT_FLOOR_MARGIN`` -- a
        defensive floor-thickness guard (D6/D7, Post-Fix Hardening).  Not
        expected to fire for any of the three intended insert-length
        options (1.0 - 3.0 mm computed margin, all well above the 0.5 mm
        floor); it exists to catch a future pathological parameter override.
    """

    # Fixed structural constant (D6/D7) -- a durable guard against a future
    # override that sets `insert_length` unreasonably large relative to
    # `thickness`, generalized from Round 1's now-moot axle-bore-collision
    # check (Post-Fix Hardening: the original failure class this guarded
    # against is gone, but the guard itself is retained against the next
    # regression of a similar class).
    MIN_INSERT_FLOOR_MARGIN: float = 0.5

    def __init__(
        self,
        hex_across_flats: float = 12.0,
        thickness: float = 6.0,
        hex_chamfer: float = 0.5,
        insert_diameter: float = 5.0,
        insert_length: float = 5.0,
        profile: str | None = None,
    ) -> None:
        self.hex_across_flats = float(hex_across_flats)
        self.thickness = float(thickness)
        self.hex_chamfer = float(hex_chamfer)
        self.insert_diameter = float(insert_diameter)
        self.insert_length = float(insert_length)

        margin = self.thickness - self.insert_length
        if margin < self.MIN_INSERT_FLOOR_MARGIN:
            raise ValueError(
                f"HexInsertHub: insert_length={self.insert_length} leaves a "
                f"floor margin of {margin:.3f} mm, below "
                f"MIN_INSERT_FLOOR_MARGIN={self.MIN_INSERT_FLOOR_MARGIN} mm. "
                f"Reduce insert_length or increase thickness."
            )

        self._prof = get_profile(profile)
        self._solid = self._build()

    # ── Derived geometry ────────────────────────────────────────────────

    @property
    def _hex_circumdia(self) -> float:
        """Circumscribed circle diameter (vertex-to-vertex) of the hex (mm).

        CadQuery's ``polygon(nSides, diameter)`` takes the circumscribed
        diameter (tip-to-tip); convert from the user-facing across-flats
        measurement: ``AF = circumdia * cos(30deg)`` -- matches
        :class:`~vibe_cading.rc.hex_hub_bearing.hex_hub_nut.HexHubNut`.
        """
        return self.hex_across_flats / math.cos(math.radians(30))

    # ── Build ───────────────────────────────────────────────────────────

    def _build(self) -> cq.Workplane:
        # ── 1. Hexagonal prism (Z = 0 -> thickness) ─────────────────────
        part = (
            cq.Workplane("XY")
            .polygon(6, self._hex_circumdia)
            .extrude(self.thickness)
        )

        # ── 2. Heat-set-insert pocket, opening at the top (outward) face ─
        # HeatSetInsert.to_cutter() builds its pocket open at its own local
        # Z = 0 (top_diameter) descending to Z = -depth (bot_diameter).
        # top_diameter == bot_diameter degenerates the taper to a straight
        # pocket (D6). Translate so the open face lands at this
        # component's own top face (Z = thickness).
        pocket = HeatSetInsert(
            top_diameter=self.insert_diameter,
            bot_diameter=self.insert_diameter,
            depth=self.insert_length,
        ).to_cutter()
        pocket = pocket.translate((0, 0, self.thickness))
        part = part.cut(pocket)

        # ── 3. Chamfer all sharp hex edges ──────────────────────────────
        # Matches HexHubNut's identical chamfer pattern -- the hex's
        # inradius (across_flats / 2 = 6.0 mm) comfortably clears the
        # collet's OD footprint (~4.85 mm radius) once fused, so the bottom
        # chamfer does not interact with the internal join.
        if self.hex_chamfer > 0:
            part = part.edges("|Z").chamfer(self.hex_chamfer)
            part = (
                part
                .edges("<Z").chamfer(self.hex_chamfer)
                .edges(">Z").chamfer(self.hex_chamfer)
            )

        assert len(part.solids().vals()) == 1, (
            "HexInsertHub: expected a single contiguous solid."
        )
        return part

    @property
    def solid(self) -> cq.Workplane:
        """The CadQuery solid.  Z = 0 is the bottom (mating) face."""
        return self._solid
