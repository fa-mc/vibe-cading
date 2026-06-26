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

"""Parametric Lego Technic liftarm with selectable per-position hole axes.

Each hole position can be bored either along the flat-face axis (+Z, ``"main"``)
or the narrow side-face axis (±Y, ``"perp"``), reusing the
:class:`~vibe_cading.lego.cutters.technic_pin_hole.TechnicPinHole` cutter and
lead-in-chamfer pipeline without altering :class:`~vibe_cading.lego.technic_beam.LegoTechnicBeam`.
"""

from typing import Literal

import cadquery as cq

from vibe_cading.lego.constants import (
    BEAM_THICKNESS,
    BEAM_WIDTH,
    LEAD_IN,
    STUD_PITCH,
)
from vibe_cading.lego.cutters.hole_mouth_selector import _HoleMouthSelector
from vibe_cading.lego.cutters.technic_pin_hole import TechnicPinHole
from vibe_cading.lego.technic_beam import stadium_beam_body
from vibe_cading.print_settings import ToleranceProfile


class PerpendicularHolesLiftarm:
    """Parametric studless liftarm with per-position main (Z) or perpendicular (Y) holes.

    Each hole position along the beam length can be independently assigned to bore
    either through the **flat top/bottom faces** (``"main"`` — identical to
    :class:`~vibe_cading.lego.technic_beam.LegoTechnicBeam`) or through the
    **narrow side faces** (``"perp"`` — rotated 90° about X, bored along ±Y).

    Origin convention
    -----------------
    Matches :class:`~vibe_cading.lego.technic_beam.LegoTechnicBeam` exactly:

    * ``Z = 0`` — bottom flat face (FDM print-bed datum).
    * ``X = 0`` — outermost tangent of the first end-cap (NOT the first hole centre).
    * ``Y = 0`` — beam centreline; width spans ``[-BEAM_WIDTH/2, +BEAM_WIDTH/2]``.
    * Bounding box: ``X ∈ [0, num_holes * STUD_PITCH] × Y ∈ [-3.9, +3.9]
      × Z ∈ [0, 7.8]``.

    Hole axis convention
    --------------------
    * ``"main"`` — bore axis is +Z; cutter is the standard
      :class:`~vibe_cading.lego.cutters.technic_pin_hole.TechnicPinHole` translated
      to ``Z = -_ENTRY_OVERCUT`` so it pierces both flat faces with strictly positive
      overcut.  Chamfer on the counterbore rims at ``Z = 0`` and ``Z = BEAM_THICKNESS``.
    * ``"perp"`` — bore axis is ±Y; the same cutter is rotated ``-90°`` about the
      X-axis (so the native +Z bore maps to +Y), then translated to pierce both
      narrow side faces from ``Y = -BEAM_WIDTH/2 - _ENTRY_OVERCUT`` to
      ``Y = +BEAM_WIDTH/2 + _ENTRY_OVERCUT``, centred at mid-height
      ``Z = BEAM_THICKNESS/2``.  Chamfer on the counterbore rims at
      ``Y = -BEAM_WIDTH/2`` and ``Y = +BEAM_WIDTH/2``.

    Alternating default
    -------------------
    When ``hole_axes`` is ``None``, the class applies the **alternating pattern**
    ``["perp", "main", "perp", "main", …]`` — position 0 is perpendicular, position 1
    is main, and so on.  For the canonical 5-hole example this produces 3 perp (at
    positions 0, 2, 4) and 2 main (at positions 1, 3) holes.

    Non-intersection guarantee
    --------------------------
    Each position carries exactly one bore axis (FR 5 — no cross-drilling).  For the
    alternating default pattern, adjacent main and perp counterbores (Ø 6.2 mm) are
    separated by the 8 mm stud pitch, giving 1.8 mm clearance; their bore cylinders
    do not intersect.

    Parameters
    ----------
    num_holes:
        Number of hole positions along the beam.  Must be ≥ 1.
    hole_axes:
        Per-position bore-axis selector.  Each element must be ``"main"`` or
        ``"perp"``.  Length must equal ``num_holes`` when provided.  When ``None``
        (the default), the alternating pattern ``["perp", "main", …]`` is used.
    fit:
        Tolerance fit grade forwarded to
        :meth:`~vibe_cading.lego.cutters.technic_pin_hole.TechnicPinHole.standard`.
        Default ``"slip"`` (pin-in-socket semantics).
    profile:
        Manufacturing tolerance profile forwarded to
        :meth:`~vibe_cading.lego.cutters.technic_pin_hole.TechnicPinHole.standard`.
        Default ``None`` (process-global profile).
    """

    def __init__(
        self,
        num_holes: int,
        hole_axes: list[Literal["main", "perp"]] | None = None,
        fit: Literal["free", "slip", "press"] = "slip",
        profile: ToleranceProfile | str | None = None,
    ) -> None:
        # ── Parameter validation ─────────────────────────────────────────────
        if num_holes < 1:
            raise ValueError(f"num_holes must be >= 1, got {num_holes}")

        if hole_axes is None:
            # Default alternating pattern: "perp" at even indices, "main" at odd.
            hole_axes = ["perp" if i % 2 == 0 else "main" for i in range(num_holes)]
        else:
            if len(hole_axes) != num_holes:
                raise ValueError(
                    f"hole_axes length ({len(hole_axes)}) must equal num_holes ({num_holes})"
                )
            valid = {"main", "perp"}
            for idx, ax in enumerate(hole_axes):
                if ax not in valid:
                    raise ValueError(
                        f"hole_axes[{idx}] must be 'main' or 'perp', got {ax!r}"
                    )

        self.num_holes: int = num_holes
        self.hole_axes: list[Literal["main", "perp"]] = list(hole_axes)
        self.fit: Literal["free", "slip", "press"] = fit
        self.profile: ToleranceProfile | str | None = profile
        self.length_mm: float = num_holes * STUD_PITCH

        self._solid: cq.Workplane | None = None
        self._solid = self._build()

    def _build(self) -> cq.Workplane:
        """Build the liftarm: stadium body → main holes → perp holes → chamfers."""
        length_mm = self.length_mm
        hole_axes = self.hole_axes

        # ── Step 1: stadium body via shared helper ───────────────────────────
        body = stadium_beam_body(length_mm)

        # ── Step 2: main-axis holes (+Z bore, through flat faces) ───────────
        # The cutter depth is BEAM_WIDTH + 2*_ENTRY_OVERCUT so it clears both
        # flat faces (Z=0 and Z=BEAM_THICKNESS) with strictly positive overcut.
        # Translation to Z=-_ENTRY_OVERCUT anchors the cutter entry at the
        # bottom face with a small undercut, guaranteeing the cutter breaks
        # through both ±Z faces cleanly (FR 6, 7).
        cutter_depth_main = BEAM_WIDTH + 2 * TechnicPinHole._ENTRY_OVERCUT
        main_cutter = TechnicPinHole.standard(
            depth=cutter_depth_main, fit=self.fit, profile=self.profile
        ).to_cutter()

        for i, axis in enumerate(hole_axes):
            if axis == "main":
                x_i = STUD_PITCH * i + STUD_PITCH / 2
                placed = main_cutter.translate((x_i, 0.0, -TechnicPinHole._ENTRY_OVERCUT))
                body = body.cut(placed)

        # ── Step 3: perpendicular holes (±Y bore, through narrow side faces) ─
        # The cutter starts as a standard +Z TechnicPinHole, then:
        #   1. Rotated -90° about the X-axis → bore axis flips from +Z to +Y.
        #      Sign choice: rotate(..., (1,0,0), -90) maps (0,0,1) → (0,1,0),
        #      i.e. the native +Z bore becomes +Y.  A +90° rotation would map
        #      to -Y and would require the opposite translation sign.
        #   2. Translated to (x_i, -BEAM_WIDTH/2 - _ENTRY_OVERCUT, BEAM_THICKNESS/2)
        #      so the bore entry face starts _ENTRY_OVERCUT past the -Y side face
        #      and the bore terminates _ENTRY_OVERCUT past the +Y side face,
        #      centred at mid-height (Z = BEAM_THICKNESS/2).
        # Depth = BEAM_THICKNESS + 2*_ENTRY_OVERCUT so the cutter spans the full
        # ±Y side-face extent with strictly positive overcut on BOTH ends (FR 9, 10).
        cutter_depth_perp = BEAM_THICKNESS + 2 * TechnicPinHole._ENTRY_OVERCUT
        perp_cutter = (
            TechnicPinHole.standard(
                depth=cutter_depth_perp, fit=self.fit, profile=self.profile
            )
            .to_cutter()
            # -90° about X: native +Z bore → +Y bore (see rotation-sign comment above)
            .rotate((0, 0, 0), (1, 0, 0), -90)
        )

        for i, axis in enumerate(hole_axes):
            if axis == "perp":
                x_i = STUD_PITCH * i + STUD_PITCH / 2
                # Translation: x_i along beam; -BEAM_WIDTH/2 - _ENTRY_OVERCUT so the
                # cutter entry clears the -Y face; BEAM_THICKNESS/2 centres the bore
                # at mid-height of the square cross-section (FR 12).
                placed = perp_cutter.translate(
                    (x_i, -BEAM_WIDTH / 2 - TechnicPinHole._ENTRY_OVERCUT, BEAM_THICKNESS / 2)
                )
                body = body.cut(placed)

        # ── Step 4a: lead-in chamfer — main-hole rims (Z-face counterbore edges) ─
        # Two sequential chamfer passes are MANDATORY (OQ-5 / OCCT homogeneity):
        # mixing edge families (Z-face rims + Y-face rims) in a single .chamfer()
        # call causes "BRep_API: command not done".  Each pass selects only its own
        # family of edges for a homogeneous edge set.
        n_main = hole_axes.count("main")
        if n_main > 0:
            main_sel = _HoleMouthSelector(
                target_radius=TechnicPinHole.DEFAULT_CB_DIAMETER / 2,  # 3.1 mm
                axis="z",
            )
            got_main = len(body.edges(main_sel).vals())
            assert got_main == 2 * n_main, (
                f"Expected {2 * n_main} main-hole chamfer edges "
                f"(2 per main hole × {n_main} main holes), got {got_main}.  "
                f"Likely cause: main cutter Z-translation sign wrong (0 edges) "
                f"or selector radius/z tolerance drifted."
            )
            body = body.edges(main_sel).chamfer(LEAD_IN)

        # ── Step 4b: lead-in chamfer — perp-hole rims (Y-face counterbore edges) ─
        n_perp = hole_axes.count("perp")
        if n_perp > 0:
            perp_sel = _HoleMouthSelector(
                target_radius=TechnicPinHole.DEFAULT_CB_DIAMETER / 2,  # 3.1 mm
                axis="y",
            )
            got_perp = len(body.edges(perp_sel).vals())
            # Exact assertion for the non-degenerate case (num_holes > 1 OR any
            # mix with n_perp ≥ 2): each perp hole contributes exactly 2 face-entry
            # rim circles (one per ±Y face), so got_perp must equal exactly 2*n_perp.
            #
            # Exception — num_holes=1 all-perp: the single Ø6.2 counterbore at x=4 mm
            # clips both rounded end-caps of the 8 mm beam, splitting each rim into two
            # arcs at Z≈0.8 mm and Z≈7.0 mm.  This yields 4 edges (2 per ±Y face)
            # instead of the normally-expected 2, so for this one degenerate configuration
            # n_perp=1 the count is 4 = 2*2*n_perp.  The upper bound 4*n_perp handles
            # this without masking gross over-selection (> 4 edges per perp hole has no
            # known geometric cause and indicates a selector regression).
            if self.num_holes == 1:
                # Degenerate: single all-perp hole may clip end-caps → 2..4 edges.
                assert 2 * n_perp <= got_perp <= 4 * n_perp, (
                    f"Expected 2–4 perp-hole chamfer edges for the 1-stud end-cap-clip "
                    f"case (n_perp={n_perp}), got {got_perp}.  "
                    f"Likely cause: perp cutter rotation/translation wrong (0 edges) "
                    f"or selector radius/y-face tolerance drifted."
                )
            else:
                assert got_perp == 2 * n_perp, (
                    f"Expected exactly {2 * n_perp} perp-hole chamfer edges "
                    f"(2 per perp hole × {n_perp} perp holes), got {got_perp}.  "
                    f"Likely cause: perp cutter rotation/translation wrong (0 edges), "
                    f"selector radius/y-face tolerance drifted, or over-selection "
                    f"(interior floor circles at |y|≈2.9 mm leaking through)."
                )
            body = body.edges(perp_sel).chamfer(LEAD_IN)

        # ── Step 5: single-solid topology guard (FR 22, AC-1) ───────────────
        solid_count = len(body.solids().vals())
        assert solid_count == 1, (
            f"Expected single solid, got {solid_count}.  Likely cause: a cutter "
            f"left a disconnected wafer, or the body sketch produced disconnected "
            f"faces."
        )

        return body

    @property
    def solid(self) -> cq.Workplane:
        """The finished liftarm body as a CadQuery Workplane (positive geometry)."""
        return self._solid

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Three 5-hole variants side-by-side: all-main, alternating, all-perp.

        The three configurations illustrate the full range of the ``hole_axes``
        parameter:

        * ``all-main`` — identical geometry to ``LegoTechnicBeam(5)``; all holes
          bored along +Z through the flat faces.
        * ``alternating`` — the default pattern (``hole_axes=None``): perp at
          positions 0, 2, 4 and main at positions 1, 3.
        * ``all-perp`` — all holes bored along ±Y through the narrow side faces.

        A single-instance ``view.py PerpendicularHolesLiftarm`` call cannot show all
        three at once; this demo earns its keep because the visual contrast between
        all-main (flat-face entry holes), alternating (mixed), and all-perp (side-face
        entry holes only) is the primary contributor-onboarding comparison for this
        class.
        """
        n = 5
        spacing_y = BEAM_WIDTH + 12.0
        main_part = cls(num_holes=n, hole_axes=["main"] * n).solid.translate((0, -spacing_y, 0))
        alt_part = cls(num_holes=n).solid.translate((0, 0, 0))
        perp_part = cls(num_holes=n, hole_axes=["perp"] * n).solid.translate((0, +spacing_y, 0))
        return [
            (main_part, "all-main (= LegoTechnicBeam)", "royalblue"),
            (alt_part, "alternating (default)", "gold"),
            (perp_part, "all-perp", "tan"),
        ]
