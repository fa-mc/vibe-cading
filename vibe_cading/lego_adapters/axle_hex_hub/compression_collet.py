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

"""Slotted split-collet cylinder — one component of the fused Lego Technic
axle -> 12 mm hex hub adapter (see
:mod:`vibe_cading.lego_adapters.axle_hex_hub.axle_hex_hub_adapter`).

Coordinate system
------------------
Z = 0            : bottom (open, slotted) face — axle entry, outward-facing
                    once fused.
Z = ``height``   : top (solid, unslotted) face — mates flush with
                    :class:`~vibe_cading.lego_adapters.axle_hex_hub.hex_insert_hub.HexInsertHub`.
Centred at X = 0, Y = 0 on the shared rotation axis.

Design intent
-------------
Per the approved design brief
(``docs/design_plans/2026-08-25-lego-axle-hex-hub-adapter_design.md``, D3/D3b/D4,
Round 2), this is a plain cylinder sized to slip through an off-the-shelf
10 mm ID compression collar (D2 — the collar itself is out of scope, not
modelled).  A keyed cross-shaped Technic-axle bore is cut fully through the
cylinder's own height via :class:`~vibe_cading.lego.cutters.technic_axle_hole.TechnicAxleHole`
at ``fit="free"`` -- a genuine through-cut of this one solid, not a blind
pocket (D3b: no class-level overcut is required, matching
:class:`TechnicAxleHole`'s own "depth equals the host's full thickness"
convention).  It only becomes *blind* once fused against
:class:`HexInsertHub`'s plain, cavity-free solid, which caps the open top --
a standard boolean-union outcome, not a Known-Modelling-Pitfalls blind-hole
case.

Two axial collet slots (D4), aligned with the keyed bore's own arm-tip axis,
let an off-the-shelf compression collar's grub screws compress the printed
wall down onto the axle.

Round 4 (post-implementation refinement, undocumented in the design brief --
small enough to apply directly): the OD fit was tightened from ``free`` to
``slip`` (less play sliding through the 10 mm ID collar), the slot gap was
narrowed to 0.6 mm, and two new features were added -- a raised stop ring
6.5 mm from the open (shaft) end that limits how far the collar can be
pushed on, and two shallow dimples (aligned with the slots, so a grub screw
seats directly over each split) that help a set screw locate and bite.
"""

from __future__ import annotations

import dataclasses

import cadquery as cq

from vibe_cading.lego.cutters.technic_axle_hole import TechnicAxleHole
from vibe_cading.print_settings import get_profile


class AxleCompressionCollet:
    """Slotted collet cylinder carrying a keyed Technic-axle through-bore.

    Parameters
    ----------
    collet_od : float
        Nominal cylinder outer diameter (mm).  Default 10.0 mm -- must slip
        through a 10 mm ID off-the-shelf compression collar (D2).  The
        *printed* OD is shrunk by ``2 * profile.slip.radial`` (Round 4 --
        tightened from ``free`` to ``slip`` to remove the play reported on
        the printed part) -- see :attr:`_od_printed`.
    height : float
        Axial height of the cylinder (mm).  Default 10.0 mm.  The keyed
        axle bore is always cut to exactly this depth (D3b) -- there is no
        separate bore-depth parameter, since ``bore_depth == height`` by
        construction.
    slot_count : int
        Number of collet slots.  Default 2 (D4).  Must equal
        ``len(slot_angles)`` -- kept as an explicit, self-validating
        parameter (Explicit Public APIs) rather than silently derived, so a
        caller who edits one without the other gets a clear error instead of
        a silently mismatched part.
    slot_angles : tuple[float, ...]
        Angular position (degrees, measured from +X) of each slot, aligned
        with the keyed bore's arm-tip axis.  Default ``(0.0, 180.0)`` (D4).
    slot_width : float
        Tangential width of each slot (mm).  Default 0.6 mm (D4, Round 4 --
        narrowed from 1.0 mm).
    slot_depth : float
        Axial depth of each slot, measured from the open (``Z = 0``) face
        (mm).  Default 7.5 mm (D4, Round 3 -- rescaled proportionally,
        0.75 x height, for the 10 mm collet), leaving a solid base ring of
        ``height - slot_depth`` (2.5 mm nominal) that anchors the flexing
        fingers to the joint end.
    slot_fillet : float
        Root-fillet radius (mm) at each slot's blind (``Z = slot_depth``)
        end.  Default 0.5 mm (D4) -- stress-concentration relief for the
        cantilevered finger.  Implemented as a round-nosed cap on the slot
        *cutter* itself (a clean primitive union of a box + half-cylinder,
        rotated into place) rather than a post-cut ``.fillet()`` call on
        freshly-cut internal edges -- the latter is a known-fragile OCCT
        operation on concave geometry; the former is a reliable boolean of
        clean primitives (see module docstring / Known Modelling Pitfalls).
    stop_ring_offset : float
        Axial distance (mm) from the open (``Z = 0``, shaft-entry) end to
        the *near* face of the raised stop ring.  Default 6.5 mm (Round 4,
        explicit user requirement).  The ring limits how far an
        off-the-shelf compression collar can be pushed onto the collet.
    stop_ring_height : float
        Axial thickness of the stop ring (mm).  Default 1.0 mm -- kept
        small per the user's own framing ("the collar has 10 mm ID so the
        ring doesn't have to be large").
    stop_ring_od : float
        Outer diameter of the stop ring (mm).  Default 11.0 mm -- 1.0 mm
        (diametral) proud of the collar's 10 mm ID, printed at raw nominal
        with no fit-grade shrink (this is a hard mechanical stop, not a
        mating/sliding fit, so it deliberately does *not* read a tolerance
        profile).
    dent_diameter : float
        Diameter (mm) of each grub-screw locating dimple.  Default 2.0 mm.
    dent_depth : float
        Depth (mm) each dimple cuts into the nominal OD surface.  Default
        0.5 mm -- shallow enough not to meaningfully weaken the collet
        wall at that cross-section.
    dent_z : float
        Axial position (mm) of each dimple's centre, measured from the
        open (``Z = 0``) end.  Default 3.5 mm -- derived from the actual
        6 mm-tall compression collar: pushed until its leading face meets
        the stop ring at ``stop_ring_offset`` (6.5 mm), the collar spans
        ``[0.5, 6.5]``, and its grub screw sits at the collar's own
        mid-height -- 3 mm in from either end, i.e. 3 mm from the ring.
    dent_angles : tuple[float, ...] | None
        Angular position (degrees) of each dimple.  Default
        ``(90.0, 270.0)`` -- 90 deg off the collet slots (``slot_angles``,
        default ``(0.0, 180.0)``), i.e. on solid, unslotted wall rather
        than straddling the split (corrected in Round 4: an earlier
        assumption placed the dimples directly over the slots, which the
        human explicitly rejected -- the grub screws seat on the intact
        wall between the two flexing fingers, not on the split itself).
        Pass ``None`` to instead reuse ``slot_angles`` verbatim, or any
        other explicit tuple for a different collar's screw layout.
    axle_bore_extra_clearance : float
        Additional radial allowance (mm) added on top of the ``free``
        grade's own ``radial`` value, for the axle bore only.  Default
        0.1 mm (Round 5 -- ``free`` is already the loosest named fit
        grade, so a human report of "still too tight" can't be answered
        by picking a looser grade name; this is a local, per-bore bump on
        top of it, applied via a one-off :class:`ToleranceProfile` copy so
        it does not affect the collet OD's own ``slip`` fit or any other
        ``free``-fit consumer elsewhere in the library). Set to 0.0 to
        fall back to the profile's bare ``free.radial`` value.
    profile : str | None
        Tolerance profile name from ``print_profiles.json`` (Material-Specific
        Tolerances convention).  ``None`` uses the globally-configured
        default.  The axle bore uses ``free`` fit grade (D5) -- a Lego axle
        passes through loosely, no press/snug-fit function; the outer OD
        shrink reads ``slip.radial`` (Round 4).
    """

    def __init__(
        self,
        collet_od: float = 10.0,
        height: float = 10.0,
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
        profile: str | None = None,
    ) -> None:
        if len(slot_angles) != slot_count:
            raise ValueError(
                f"AxleCompressionCollet: slot_count ({slot_count}) must "
                f"match len(slot_angles) ({len(slot_angles)})."
            )
        self.collet_od = float(collet_od)
        self.height = float(height)
        self.slot_count = int(slot_count)
        self.slot_angles = tuple(float(a) for a in slot_angles)
        self.slot_width = float(slot_width)
        self.slot_depth = float(slot_depth)
        self.slot_fillet = float(slot_fillet)
        self.stop_ring_offset = float(stop_ring_offset)
        self.stop_ring_height = float(stop_ring_height)
        self.stop_ring_od = float(stop_ring_od)
        self.dent_diameter = float(dent_diameter)
        self.dent_depth = float(dent_depth)
        self.dent_z = float(dent_z)
        self.dent_angles = (
            self.slot_angles if dent_angles is None
            else tuple(float(a) for a in dent_angles)
        )
        self.axle_bore_extra_clearance = float(axle_bore_extra_clearance)
        self._prof = get_profile(profile)
        self._solid = self._build()

    # ── Derived geometry ────────────────────────────────────────────────

    @property
    def _bore_profile(self):
        """The ``ToleranceProfile`` used for the axle bore only -- ``free``
        with ``axle_bore_extra_clearance`` added on top of its ``radial``
        (Round 5).  A local copy, not a mutation of ``self._prof``, so the
        collet OD's own ``slip`` fit is unaffected."""
        if self.axle_bore_extra_clearance == 0.0:
            return self._prof
        bumped_free = dataclasses.replace(
            self._prof.free,
            radial=self._prof.free.radial + self.axle_bore_extra_clearance,
        )
        return dataclasses.replace(self._prof, free=bumped_free)

    @property
    def _od_printed(self) -> float:
        """Printed outer diameter after applying ``slip`` radial clearance
        (mm) -- shrunk so the collet slides through the 10 mm ID compression
        collar with minimal play (D2, Round 4: tightened from ``free``)."""
        return self.collet_od - 2.0 * self._prof.slip.radial

    # ── Build ───────────────────────────────────────────────────────────

    def _slot_cutter(self, angle_deg: float) -> cq.Workplane:
        """One collet-slot cutter: a radial slit through the wall, open at
        ``Z = 0`` and blind at ``Z = slot_depth``, capped with a round nose
        at its root.  Built along the local +/-X axis, spanning the full
        collet diameter plus a generous overcut so it unambiguously clears
        the OD on both sides regardless of rotation, then rotated into
        place (Known Modelling Pitfalls: infinite-cutter-overcut pattern).
        """
        overcut = 1.0
        half_len = self._od_printed / 2.0 + overcut
        # The cap radius can't geometrically exceed half the slot width
        # (it would no longer be tangent to both slot walls) -- clamp
        # defensively rather than producing a self-intersecting cutter.
        cap_radius = min(self.slot_fillet, self.slot_width / 2.0)
        flat_h = max(self.slot_depth - cap_radius, 0.0)

        box = cq.Workplane("XY").box(
            2 * half_len, self.slot_width, flat_h, centered=(True, True, False)
        )
        if cap_radius > 0:
            # Half-cylinder cap swept along local X, tangent to the slot's
            # two side walls -- reproduces the round-end-mill profile a real
            # cut collet slot would carry.
            cyl = (
                cq.Workplane("YZ")
                .circle(cap_radius)
                .extrude(half_len, both=True)
                .translate((0, 0, flat_h))
            )
            cutter = box.union(cyl)
        else:
            cutter = box
        return cutter.rotate((0, 0, 0), (0, 0, 1), angle_deg)

    def _stop_ring(self) -> cq.Workplane:
        """Raised ring at ``[stop_ring_offset, stop_ring_offset +
        stop_ring_height]`` that mechanically limits how far a compression
        collar can be pushed onto the collet.  Printed at raw nominal
        diameter (no fit-grade shrink) -- it is a hard stop, not a mating
        surface."""
        return (
            cq.Workplane("XY")
            .workplane(offset=self.stop_ring_offset)
            .circle(self.stop_ring_od / 2.0)
            .extrude(self.stop_ring_height)
        )

    def _dent_cutter(self, angle_deg: float) -> cq.Workplane:
        """One grub-screw locating dimple: a shallow cylindrical cut into
        the OD surface at ``dent_z``, radial depth ``dent_depth``.  Built
        along the local +X axis starting from inside the nominal surface
        and extending past it by a generous overcut, so the cut cleanly
        engulfs the boundary (Known Modelling Pitfalls: infinite-cutter
        overcut) regardless of the current ``_od_printed`` value, then
        rotated into place."""
        overcut = 1.0
        start_x = self._od_printed / 2.0 - self.dent_depth
        cutter = (
            cq.Workplane("YZ")
            .workplane(offset=start_x)
            .circle(self.dent_diameter / 2.0)
            .extrude(self.dent_depth + overcut)
            .translate((0, 0, self.dent_z))
        )
        return cutter.rotate((0, 0, 0), (0, 0, 1), angle_deg)

    def _build(self) -> cq.Workplane:
        # ── 1. Plain cylinder (Z = 0 -> height) ─────────────────────────
        part = cq.Workplane("XY").circle(self._od_printed / 2.0).extrude(self.height)

        # ── 2. Stop ring (Round 4) -- unioned before the bore/slot cuts so
        # it inherits the same slotting at the slot angles as the rest of
        # the wall (a full, uninterrupted ring is not required -- see the
        # class docstring's stop_ring_offset note).
        part = part.union(self._stop_ring())

        # ── 3. Keyed axle through-bore, cut to exactly `height` (D3/D3b) ─
        # Uses `_bore_profile` (free + axle_bore_extra_clearance), not the
        # raw `_prof`, so this bore alone gets the Round 5 clearance bump.
        bore = TechnicAxleHole(
            depth=self.height, fit="free", profile=self._bore_profile
        ).to_cutter()
        part = part.cut(bore)

        # ── 4. Collet slots, aligned with the bore's arm-tip axis (D4) ──
        for angle in self.slot_angles:
            part = part.cut(self._slot_cutter(angle))

        # ── 5. Grub-screw locating dimples (Round 4) ────────────────────
        for angle in self.dent_angles:
            part = part.cut(self._dent_cutter(angle))

        assert len(part.solids().vals()) == 1, (
            "AxleCompressionCollet: expected a single contiguous solid "
            "after the bore, slot, and dimple cuts."
        )
        return part

    @property
    def solid(self) -> cq.Workplane:
        """The CadQuery solid.  Z = 0 is the open, slotted (axle-entry)
        face; Z = height is the solid, unslotted face that mates with
        HexInsertHub."""
        return self._solid
