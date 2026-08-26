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

"""Fused Lego Technic axle -> 12 mm RC hex hub adapter -- the actual
printed deliverable.

Coordinate system
------------------
Z = 0 -> ``hex_thickness``                    : the fused
                                                  :class:`~vibe_cading.lego_adapters.axle_hex_hub.hex_insert_hub.HexInsertHub`
                                                  region (unmodified from its
                                                  own datum).
Z = -collet_height + overlap_eps -> 0         : the fused
                                                  :class:`~vibe_cading.lego_adapters.axle_hex_hub.compression_collet.AxleCompressionCollet`
                                                  region, translated flush
                                                  against the hex piece's
                                                  bottom face.
Centred at X = 0, Y = 0 on the shared rotation axis.

Design intent
-------------
Per the approved design brief
(``docs/design_plans/2026-08-25-lego-axle-hex-hub-adapter_design.md``,
Assembly Datum, Round 2), :class:`AxleCompressionCollet` and
:class:`HexInsertHub` are **not** a two-part assembly joined by a
register/spigot feature -- they print as a single fused body.  This wrapper
builds both components, positions the collet flush against the hex piece's
bottom face with a small (0.02 mm nominal) overlap epsilon, and
``.union()``s them.  The overlap epsilon is a fixed geometric
boolean-robustness margin (Known Modelling Pitfalls: two solids sharing an
*exactly* coincident planar face are a well-known OCCT boolean reliability
risk) -- it is **not** a fit-grade / tolerance-profile value, since there is
no separable mating surface to correct for print shrink/growth.  Identical
convention to
:class:`~vibe_cading.rc.hex_hub_bearing.hex_hub_with_bearing.HexHubWithBearing`'s
own D2a.

The collet's keyed axle bore (cut fully through its own 10 mm height, D3b)
becomes *blind* only as an emergent property of this union: ``HexInsertHub``'s
plain, cavity-free solid caps the collet's open top -- a standard,
well-understood boolean outcome, not a coincident-face boolean-cut risk (see
:mod:`~vibe_cading.lego_adapters.axle_hex_hub.compression_collet` module
docstring for the full argument).  ``HexInsertHub`` carries no
axle-bore-related feature of its own at all.
"""

from __future__ import annotations

import cadquery as cq

from vibe_cading.lego_adapters.axle_hex_hub.compression_collet import AxleCompressionCollet
from vibe_cading.lego_adapters.axle_hex_hub.hex_insert_hub import HexInsertHub


class AxleHexHubAdapter:
    """Fused axle-compression-collet + hex-insert-hub single-print body.

    Parameters
    ----------
    collet_od : float
        Forwarded to :class:`AxleCompressionCollet`. Default 10.0 mm.
    collet_height : float
        Forwarded to :class:`AxleCompressionCollet` as its own axial height,
        and used here to compute the flush-join translation. Default
        10.0 mm.
    slot_count : int
        Forwarded to :class:`AxleCompressionCollet`. Default 2.
    slot_angles : tuple[float, ...]
        Forwarded to :class:`AxleCompressionCollet`. Default (0.0, 180.0).
    slot_width : float
        Forwarded to :class:`AxleCompressionCollet`. Default 0.6 mm.
    slot_depth : float
        Forwarded to :class:`AxleCompressionCollet`. Default 7.5 mm.
    slot_fillet : float
        Forwarded to :class:`AxleCompressionCollet`. Default 0.5 mm.
    stop_ring_offset : float
        Forwarded to :class:`AxleCompressionCollet`. Default 6.5 mm.
    stop_ring_height : float
        Forwarded to :class:`AxleCompressionCollet`. Default 1.0 mm.
    stop_ring_od : float
        Forwarded to :class:`AxleCompressionCollet`. Default 11.0 mm.
    dent_diameter : float
        Forwarded to :class:`AxleCompressionCollet`. Default 2.0 mm.
    dent_depth : float
        Forwarded to :class:`AxleCompressionCollet`. Default 0.5 mm.
    dent_z : float
        Forwarded to :class:`AxleCompressionCollet`. Default 3.5 mm.
    dent_angles : tuple[float, ...] | None
        Forwarded to :class:`AxleCompressionCollet`. Default
        ``(90.0, 270.0)`` -- 90 deg off the slots.
    axle_bore_extra_clearance : float
        Forwarded to :class:`AxleCompressionCollet`. Default 0.1 mm
        (Round 5 -- extra radial allowance on top of ``free.radial``).
    hex_across_flats : float
        Forwarded to :class:`HexInsertHub`. Default 12.0 mm.
    hex_thickness : float
        Forwarded to :class:`HexInsertHub` as its own axial thickness.
        Default 6.0 mm.
    hex_chamfer : float
        Forwarded to :class:`HexInsertHub`. Default 0.5 mm.
    insert_diameter : float
        Forwarded to :class:`HexInsertHub`. Default 5.0 mm.
    insert_length : float
        Forwarded to :class:`HexInsertHub`. Default 5.0 mm (D6, Round 3).
    overlap_eps : float
        Fixed boolean-robustness overlap (mm) applied at the flush join
        between the two components. Default 0.02 mm -- not profile-derived,
        since this is not a printed-vs-printed mating fit.
    profile : str | None
        Tolerance profile name from ``print_profiles.json``, forwarded to
        both component classes so the whole fused body reads one consistent
        tolerance profile. ``None`` uses the globally-configured default.
    """

    def __init__(
        self,
        collet_od: float = 10.0,
        collet_height: float = 10.0,
        slot_count: int = 2,
        slot_angles: tuple[float, ...] = (0.0, 180.0),
        slot_width: float = 0.6,
        slot_depth: float = 7.5,
        slot_fillet: float = 0.5,
        stop_ring_offset: float = 6.5,
        stop_ring_height: float = 1.0,
        stop_ring_od: float = 11.0,
        dent_diameter: float = 2.0,
        dent_depth: float = 0.5,
        dent_z: float = 3.5,
        dent_angles: tuple[float, ...] | None = (90.0, 270.0),
        axle_bore_extra_clearance: float = 0.1,
        hex_across_flats: float = 12.0,
        hex_thickness: float = 6.0,
        hex_chamfer: float = 0.5,
        insert_diameter: float = 5.0,
        insert_length: float = 5.0,
        overlap_eps: float = 0.02,
        profile: str | None = None,
    ) -> None:
        self.overlap_eps = float(overlap_eps)
        # Forward the same `profile` argument (name or None) to both
        # components so they each resolve an identical ToleranceProfile and
        # the whole fused body reads one consistent tolerance profile.
        self.collet = AxleCompressionCollet(
            collet_od=collet_od,
            height=collet_height,
            slot_count=slot_count,
            slot_angles=slot_angles,
            slot_width=slot_width,
            slot_depth=slot_depth,
            slot_fillet=slot_fillet,
            stop_ring_offset=stop_ring_offset,
            stop_ring_height=stop_ring_height,
            stop_ring_od=stop_ring_od,
            dent_diameter=dent_diameter,
            dent_depth=dent_depth,
            dent_z=dent_z,
            dent_angles=dent_angles,
            axle_bore_extra_clearance=axle_bore_extra_clearance,
            profile=profile,
        )
        self.hex_hub = HexInsertHub(
            hex_across_flats=hex_across_flats,
            thickness=hex_thickness,
            hex_chamfer=hex_chamfer,
            insert_diameter=insert_diameter,
            insert_length=insert_length,
            profile=profile,
        )
        self._solid = self._build()

    # ── Build ───────────────────────────────────────────────────────────

    def _build(self) -> cq.Workplane:
        # HexInsertHub needs no translation -- its own local Z = 0 (bottom
        # face) already sits at the assembly's Z = 0.
        hex_part = self.hex_hub.solid

        # AxleCompressionCollet is translated so its top (solid, joint-side)
        # face lands overlap_eps past global Z = 0, rather than exactly
        # coincident with it (design brief Assembly Datum).
        collet_positioned = self.collet.solid.translate(
            (0, 0, -self.collet.height + self.overlap_eps)
        )

        fused = hex_part.union(collet_positioned)

        assert len(fused.solids().vals()) == 1, (
            "AxleHexHubAdapter: expected a single fused solid -- the "
            ".union() between HexInsertHub and AxleCompressionCollet did "
            "not produce a single contiguous body. Check overlap_eps."
        )
        return fused

    @property
    def solid(self) -> cq.Workplane:
        """The fused CadQuery solid.  Z = 0 is the flush join between the
        hex-insert-hub and compression-collet regions (see module docstring
        for the full coordinate span)."""
        return self._solid
