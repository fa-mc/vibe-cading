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

"""
Printable cross-profile gauge for calibrating the arm-slot width of the
Technic ``+`` cross axle-hole fit on a specific FDM printer / material.
"""

import math
from typing import Sequence

import cadquery as cq

from vibe_cading.cq_utils import axle_cross_section
from vibe_cading.lego.constants import AXLE_HOLE_TIP_TO_TIP
from vibe_cading.print_settings import ToleranceProfile, get_profile


class AxleCrossHoleGauge:
    """Printable gauge isolating the arm-slot width of the ``+`` cross
    Technic axle-hole fit.

    Each hole is a ``+`` cross cutter at a fixed (profile-derived)
    tip-to-tip, with the arm-slot width swept across the row and a
    **dog-bone relief** at each of the four inner concave corners so the
    concave corner cannot confound the fit — the user finds the modelled
    arm width that accepts and keys a real Lego axle cleanly.

    Why this gauge exists
    ---------------------
    Stage 1 (``AxleHoleGauge``) calibrated *tip-to-tip* using round
    holes.  A round hole has no arms, so the ``+`` cross slot — the flat
    arm walls and the four concave corners — was never physically
    tested.  The cross fit has two unknowns: the flat slot-wall (arm)
    width, and the concave corner where FDM "corner blowout"
    over-deposits.  Measuring both at once repeats the failed-sweep
    mistake.  This gauge therefore **isolates the arm-slot width**: it
    sweeps arm width while the concave corners are held generously open
    by a dog-bone relief, so the corners cannot be the binding
    constraint.  The concave-corner treatment itself is Stage 2b
    (data-gated; see the design brief).

    Dog-bone corner relief
    ----------------------
    Each ``+`` hole carries a circular relief pocket at each of its four
    inner concave corners, *replacing* the ``concave_radius`` fillet of
    :class:`~vibe_cading.lego.cutters.technic_axle_hole.TechnicAxleHole`.
    The pocket centre sits on the corner's 45-degree bisector, offset
    outward by ``corner_relief / sqrt(2)`` per axis so the pocket circle
    passes exactly through the geometric corner point.  Passing through
    the corner point **undercuts** the corner — hole material is removed
    *behind* the corner point — so the axle's rounded corner can never
    register against hole material there.  The corner is fully relieved
    as a contact for *any* positive ``corner_relief``; a larger radius
    only removes more (functionally wasted) material and eats more flat
    slot wall.  ``corner_relief`` is therefore sized to fully clear the
    corner while leaving a defined flat slot wall along each arm — the
    surface that actually *measures* arm width — across the whole sweep
    (see the ``corner_relief`` parameter note).

    Origin (0, 0, 0): the block is plan-centred — its XY centroid sits at
    the origin — and its bottom face lies on the Z=0 print bed; the block
    extrudes up into +Z.  Hole axes are parallel to Z.

    Calibration procedure
    ---------------------
    1. Print the gauge flat, holes vertical (axis parallel to build-Z),
       on the same printer / material / slicer settings as the Stage-1
       gauge and your real parts (XY hole compensation = 0).
    2. Insert a real Lego Technic axle into each ``+`` hole from the
       labelled (top) face.
    3. The good hole accepts the axle **without force** AND keys it with
       **minimal rotational slop** — note its arm-width label
       ``W_good``.  Judge by both the axial slide *and* the rotational
       keying: a ``+`` hole that slides but spins freely is too wide.
    4. Report ``W_good``.  The flat-wall arm requirement is then::

           arm_wall_excess = W_good - (AXLE_HOLE_ARM_WIDTH
                                       + 2 * profile.slip.radial)

       ``arm_wall_excess ~ 0`` means the profile radial already serves
       the flat-wall arm fit; ``> 0`` means the flat walls need
       clearance the shared profile radial does not give.  The concave
       corner is relieved away on this gauge — it is assessed separately
       in Stage 2b.  See ``docs/lego-technic.md`` > Tuning Tolerances.
    5. Write the calibrated value ``slip.slot = arm_wall_excess / 2``
       onto the ``slip`` grade in ``machine_profiles_user.json``.  The
       ``/ 2`` converts the total arm-width excess to a per-side slot
       clearance, since ``ARM_WIDTH = nominal + 2 * radial + 2 * slot``.

    Parameters
    ----------
    arm_widths:
        Swept arm-slot widths (mm), one ``+`` cross through-hole per
        entry.  The default range 1.85-2.35 in 0.10 mm increments
        brackets the 2.03 mm prediction (``AXLE_HOLE_ARM_WIDTH`` 1.83 +
        2 * the user's calibrated ``slip.radial``).  A shifted or finer
        pass is just a different tuple.
    profile:
        Manufacturing tolerance profile.  Supplies the fixed tip-to-tip
        via ``slip.radial``; defaults to the active global profile.
    corner_relief:
        Dog-bone relief radius (mm) at each of the four inner concave
        corners.  The pocket passes through the corner point, eating
        ``corner_relief * sqrt(2)`` of flat slot wall along each arm.
        The default 0.35 mm fully relieves the corner while leaving a
        defined flat slot wall (~0.48 mm) even on the *widest* swept
        hole (arm 2.35), whose flat wall — the corner-to-tip-arc run —
        is the shortest in the sweep at ~0.97 mm.  Larger values relieve
        no more (the corner is already a full undercut once the pocket
        reaches the corner point) but consume more wall; raise it only
        for a narrower sweep whose widest hole still leaves enough wall.
        The design brief's nominal of 0.8 mm is geometrically infeasible
        here — at 0.8 the pocket would eat ~1.13 mm, more than the entire
        ~0.97 mm flat wall of the widest hole — see the brief's
        Implementation Status / Developer note.
    depth:
        Block thickness = hole depth (mm).  Default 8.0 = one stud unit.
    hole_pitch:
        Cell width per hole along X (mm) — centre-to-centre hole
        spacing.
    engrave_depth:
        Depth of the arm-width label engraving on the top face (mm).
    """

    def __init__(
        self,
        arm_widths: Sequence[float] = (1.85, 1.95, 2.05, 2.15, 2.25, 2.35),
        profile: ToleranceProfile | None = None,
        corner_relief: float = 0.35,
        depth: float = 8.0,
        hole_pitch: float = 9.0,
        engrave_depth: float = 0.6,
    ) -> None:
        if not arm_widths:
            raise ValueError("AxleCrossHoleGauge requires at least one arm width")
        if corner_relief <= 0:
            raise ValueError("AxleCrossHoleGauge requires a positive corner_relief")

        self.arm_widths: tuple[float, ...] = tuple(float(w) for w in arm_widths)
        self.corner_relief: float = float(corner_relief)
        self.depth: float = float(depth)
        self.hole_pitch: float = float(hole_pitch)
        self.engrave_depth: float = float(engrave_depth)

        profile = profile or get_profile()
        self.profile: ToleranceProfile = profile

        # ── Fixed, profile-derived tip-to-tip ─────────────────────────────
        # Tip-to-tip is NOT swept — it was calibrated in Stage 1.  It is
        # derived from the active profile exactly as TechnicAxleHole sizes
        # its cutter (AXLE_HOLE_TIP_TO_TIP nominal + 2 * slip.radial), so
        # the gauge auto-adapts to whatever profile is active — no magic
        # number.  Every hole in the row shares this one value.
        self.tip_to_tip: float = AXLE_HOLE_TIP_TO_TIP + 2 * profile.slip.radial

        # ── Derived layout ────────────────────────────────────────────────
        # Block length (X) packs one cell per hole; width (Y) leaves a
        # label band on the -Y side of the hole row.  Kept compact to
        # minimise material waste (Parameter Sweeps rule).  The cross
        # hole's XY envelope is the tip_to_tip bounding circle, so the
        # block sizing uses tip_to_tip as the hole's extent.
        n = len(self.arm_widths)
        self._label_band: float = 6.0           # -Y strip carrying the labels
        self._margin: float = 4.0               # solid wall around the hole row
        self.length: float = n * self.hole_pitch
        self.width: float = self.tip_to_tip + 2 * self._margin + self._label_band
        # Hole-row centreline sits +label_band/2 above block centre so the
        # label band occupies the -Y portion of the top face.
        self._hole_row_y: float = self._label_band / 2.0
        self._label_y: float = self._hole_row_y - self.tip_to_tip / 2.0 - 2.0

        self._solid: cq.Workplane = self._build()

    def _hole_x(self, index: int) -> float:
        """X centre of the hole at *index*, plan-centred about X=0."""
        start_x = -((len(self.arm_widths) - 1) / 2.0) * self.hole_pitch
        return start_x + index * self.hole_pitch

    def _cross_hole_cutter(self, arm_width: float) -> cq.Workplane:
        """Build one ``+`` cross through-hole cutter with dog-bone relief.

        The cutter is plan-centred at the XY origin, extruding up from
        ``-overcut`` to ``depth + overcut`` so it cleanly breaks through
        both block faces (coincident cutter/body faces are unreliable in
        the OCCT boolean kernel).  No lead-in chamfer — a chamfer would
        guide the axle and bias the "smallest hole that fits" judgment.
        """
        overcut = 0.1
        cut_len = self.depth + 2 * overcut

        # Faithful TechnicAxleHole cross: cylinder ∩ cross arms (shared
        # construction).  The dog-bone relief is layered on top below.
        cross = axle_cross_section(self.tip_to_tip, arm_width, cut_len)

        # ── Dog-bone corner relief ────────────────────────────────────────
        # One circular pocket per concave corner.  The concave corners sit
        # at (±half_arm, ±half_arm); the pocket centre is offset outward
        # along the 45° bisector by delta per axis, with delta chosen so
        # the pocket circle passes exactly through the corner point
        # (delta = corner_relief / sqrt(2), since sqrt(delta² + delta²)
        # must equal corner_relief).  This undercuts the corner — see the
        # class docstring — fully relieving it as an axle contact.
        half_arm = arm_width / 2.0
        delta = self.corner_relief / math.sqrt(2.0)
        cx = half_arm + delta
        cy = half_arm + delta
        for sign_x in (+1, -1):
            for sign_y in (+1, -1):
                pocket = (
                    cq.Workplane("XY")
                    .circle(self.corner_relief)
                    .extrude(cut_len)
                    .translate((sign_x * cx, sign_y * cy, 0))
                )
                cross = cross.union(pocket)

        return cross.translate((0, 0, -overcut))

    def _build(self) -> cq.Workplane:
        """Build the flat block, cut the cross through-holes, then engrave."""
        # Base block: plan-centred in XY, bottom face on Z=0.
        base = (
            cq.Workplane("XY")
            .box(self.length, self.width, self.depth)
            .translate((0, 0, self.depth / 2.0))
        )

        # ── Cross through-holes with dog-bone relief ──────────────────────
        # One + cross cutter per swept arm width, axis parallel to Z.
        hole_cutters: list[cq.Workplane] = []
        for index, arm_width in enumerate(self.arm_widths):
            cutter = self._cross_hole_cutter(arm_width).translate(
                (self._hole_x(index), self._hole_row_y, 0)
            )
            hole_cutters.append(cutter)

        holes = hole_cutters[0]
        for cutter in hole_cutters[1:]:
            holes = holes.union(cutter)
        base = base.cut(holes)

        # ── Arm-width labels ──────────────────────────────────────────────
        # Each hole engraved with its arm width on the top face.  All
        # label text solids are unioned into one compound *before* a
        # single ``.cut()`` — engraving each label separately stalls the
        # OCCT boolean kernel (the established gauge pattern).
        label_solids: list[cq.Workplane] = []
        for index, arm_width in enumerate(self.arm_widths):
            text = (
                cq.Workplane("XY")
                .text(
                    f"{arm_width:.2f}",
                    fontsize=3.0,
                    distance=self.engrave_depth,
                    halign="center",
                    valign="center",
                )
                # Sit the engraving on the top face: text() extrudes the
                # glyphs symmetrically about its plane, so place the plane
                # engrave_depth/2 below the top so the cut bites downward.
                .translate(
                    (
                        self._hole_x(index),
                        self._label_y,
                        self.depth - self.engrave_depth / 2.0,
                    )
                )
            )
            label_solids.append(text)

        all_labels = cq.Workplane("XY")
        for label in label_solids:
            all_labels.add(label.vals())
        result = base.cut(all_labels.combine())

        # Topological guard: the gauge must be a single contiguous solid.
        # A floating sliver here would mean a hole or label cutter severed
        # the block — catch it at the source rather than at print time.
        assert len(result.solids().vals()) == 1, (
            "AxleCrossHoleGauge expected a single solid, got "
            f"{len(result.solids().vals())}"
        )
        return result

    @property
    def solid(self) -> cq.Workplane:
        """The gauge block — a single contiguous solid (read-only)."""
        return self._solid
