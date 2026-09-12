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

# Minimum material on each side of a "perp" bore's counterbore, in mm — mirrors
# this project's own default 0.8 mm FDM two-perimeter wall convention (used
# consistently elsewhere, e.g. the powered-up-hub housing design brief's
# default 0.8 mm shell walls).  Sets the `thickness` floor below which a
# "perp" hole cannot be carried without a severed/wafer-thin wall around the
# counterbore (see the constructor's thickness validation).
_MINIMUM_WALL_MM: float = 0.8


class _MainAxisChamferSelector(cq.Selector):
    """Local selector for main-hole (Z-face) chamfer rims at an arbitrary thickness.

    The shared :class:`~vibe_cading.lego.cutters.hole_mouth_selector._HoleMouthSelector`
    (``axis="z"``) folds candidate edges around the *module constant*
    ``BEAM_THICKNESS / 2`` — correct only when the beam's own Z-extent equals
    ``BEAM_THICKNESS``.  ``PerpendicularHolesLiftarm``'s ``thickness`` keyword
    (TL round, 2026-08-19) lets the Z-extent diverge from that constant, so the
    fold centre must track the instance's own ``thickness`` instead.  Rather than
    changing the shared selector's contract (used unmodified by
    :class:`~vibe_cading.lego.technic_beam.LegoTechnicBeam` and
    :class:`~vibe_cading.lego.technic_l_liftarm.LegoTechnicLLiftarm`, neither of
    which varies thickness), this is a small, file-local selector scoped to this
    class's own per-part code structure.

    Predicate: a ``CIRCLE`` edge of the target counterbore radius whose centre
    sits at ``Z ≈ 0`` or ``Z ≈ thickness`` — i.e. directly on one of the two
    flat Z-faces.  This directly identifies the two face-entry rims without a
    fold, and — as a side effect — naturally excludes the interior
    counterbore-floor circles (which sit near mid-height, not at either Z
    extreme) without needing a second exclusion clause.
    """

    def __init__(self, target_radius: float, thickness: float, tol: float = 0.05):
        self.target_radius = target_radius
        self.thickness = thickness
        self.tol = tol

    def filter(self, edges):
        kept = []
        for e in edges:
            try:
                if e.geomType() != "CIRCLE":
                    continue
                if abs(e.radius() - self.target_radius) >= self.tol:
                    continue
                z = e.Center().z
                if abs(z) < self.tol or abs(z - self.thickness) < self.tol:
                    kept.append(e)
            except Exception:
                # geomType()/radius()/Center() may raise on non-circular edge
                # types; treat any failure as "not a hole-mouth edge" and skip.
                continue
        return kept


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
      × Z ∈ [0, thickness]`` (``thickness`` defaults to ``BEAM_THICKNESS`` =
      ``7.8``, matching every prior release of this class byte-for-byte).

    Hole axis convention
    --------------------
    * ``"main"`` — bore axis is +Z; cutter is the standard
      :class:`~vibe_cading.lego.cutters.technic_pin_hole.TechnicPinHole` translated
      to ``Z = -_ENTRY_OVERCUT`` so it pierces both flat faces with strictly positive
      overcut.  Chamfer on the counterbore rims at ``Z = 0`` and ``Z = thickness``.
    * ``"perp"`` — bore axis is ±Y; the same cutter is rotated ``-90°`` about the
      X-axis (so the native +Z bore maps to +Y), then translated to pierce both
      narrow side faces from ``Y = -BEAM_WIDTH/2 - _ENTRY_OVERCUT`` to
      ``Y = +BEAM_WIDTH/2 + _ENTRY_OVERCUT``, centred at mid-height
      ``Z = thickness/2``.  Chamfer on the counterbore rims at
      ``Y = -BEAM_WIDTH/2`` and ``Y = +BEAM_WIDTH/2``.
    * ``"none"`` — no bore at all; the position is left solid.  Added in the
      TL round (2026-08-19) so a caller (e.g. a housing composing its own
      middle-hole geometry) can reserve a position for call-site-local
      cutting without first accepting, then un-cutting, this class's own
      symmetric bore — un-cutting already-cut geometry is exactly the
      duct-tape shape this project's conventions reject.

    Alternating default
    -------------------
    When ``hole_axes`` is ``None``, the class applies the **alternating pattern**
    ``["perp", "main", "perp", "main", …]`` — position 0 is perpendicular, position 1
    is main, and so on.  For the canonical 5-hole example this produces 3 perp (at
    positions 0, 2, 4) and 2 main (at positions 1, 3) holes.

    Non-intersection guarantee
    --------------------------
    Each position carries at most one bore axis (FR 5 — no cross-drilling;
    ``"none"`` carries zero).  For the alternating default pattern, adjacent main
    and perp counterbores (Ø 6.2 mm) are separated by the 8 mm stud pitch, giving
    1.8 mm clearance; their bore cylinders do not intersect.

    Parameters
    ----------
    num_holes:
        Number of hole positions along the beam.  Must be ≥ 1.
    hole_axes:
        Per-position bore-axis selector.  Each element must be ``"main"``,
        ``"perp"``, or ``"none"``.  Length must equal ``num_holes`` when
        provided.  When ``None`` (the default), the alternating pattern
        ``["perp", "main", …]`` is used.
    fit:
        Tolerance fit grade forwarded to
        :meth:`~vibe_cading.lego.cutters.technic_pin_hole.TechnicPinHole.standard`.
        Default ``"slip"`` (pin-in-socket semantics).
    profile:
        Manufacturing tolerance profile forwarded to
        :meth:`~vibe_cading.lego.cutters.technic_pin_hole.TechnicPinHole.standard`.
        Default ``None`` (process-global profile).
    thickness:
        Beam height along Z, in millimetres.  Keyword-only.  Defaults to
        ``BEAM_THICKNESS`` (the project's own Cailliau-calibrated liftarm
        thickness), preserving every existing caller's geometry exactly.
        Added in the TL round (2026-08-19) as a general per-instance override
        for the LEGO liftarm family's real thick/thin variants — e.g. a caller
        matching a real part's LDraw-measured thickness (a *mating datum*, per
        the TL ruling: a dimension that serves as a mating datum follows the
        mate; one that does not follows the family calibration) passes
        ``thickness=8.0`` without moving the shared ``BEAM_THICKNESS``
        constant that every other caller still relies on.  A perpendicular
        (``"perp"``) hole needs enough thickness to carry its own counterbore
        with material on both sides; too-thin values are rejected at
        construction (see *Raises* below) rather than silently producing a
        severed body.

    Raises
    ------
    ValueError:
        If ``num_holes < 1``, ``hole_axes`` has the wrong length or an
        invalid token, or ``thickness`` is too small to host a ``"perp"``
        bore (only checked when ``"perp"`` appears in ``hole_axes``).
    """

    def __init__(
        self,
        num_holes: int,
        hole_axes: list[Literal["main", "perp", "none"]] | None = None,
        fit: Literal["free", "slip", "press"] = "slip",
        profile: ToleranceProfile | str | None = None,
        *,
        thickness: float = BEAM_THICKNESS,
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
            valid = {"main", "perp", "none"}
            for idx, ax in enumerate(hole_axes):
                if ax not in valid:
                    raise ValueError(
                        f"hole_axes[{idx}] must be 'main', 'perp', or 'none', got {ax!r}"
                    )

        # A "perp" bore's counterbore (Ø TechnicPinHole.DEFAULT_CB_DIAMETER) must
        # fit inside `thickness` with at least _MINIMUM_WALL_MM of material on
        # each side (matching this project's own default 0.8 mm FDM wall
        # convention used elsewhere, e.g. the powered-up-hub housing brief).
        # Rejected here, at construction, rather than producing a body with a
        # severed/wafer-thin wall around the bore.
        if "perp" in hole_axes:
            min_thickness_for_perp = TechnicPinHole.DEFAULT_CB_DIAMETER + 2 * _MINIMUM_WALL_MM
            # 1e-9 mm epsilon absorbs float round-off in the sum above (e.g.
            # 6.2 + 2*0.8 evaluates to 7.800000000000001 in IEEE-754 double
            # precision) so the default thickness=BEAM_THICKNESS=7.8 mm — which
            # sits exactly at this floor — is never spuriously rejected.
            if thickness < min_thickness_for_perp - 1e-9:
                raise ValueError(
                    f"thickness={thickness} mm is too thin to host a 'perp' bore: "
                    f"the Ø{TechnicPinHole.DEFAULT_CB_DIAMETER} mm counterbore needs "
                    f"thickness >= {min_thickness_for_perp} mm ({_MINIMUM_WALL_MM} mm "
                    f"of material on each side).  Remove 'perp' from hole_axes at "
                    f"this thickness, or increase thickness."
                )

        self.num_holes: int = num_holes
        self.hole_axes: list[Literal["main", "perp", "none"]] = list(hole_axes)
        self.fit: Literal["free", "slip", "press"] = fit
        self.profile: ToleranceProfile | str | None = profile
        self.thickness: float = thickness
        self.length_mm: float = num_holes * STUD_PITCH

        self._solid: cq.Workplane | None = None
        self._solid = self._build()

    def _build(self) -> cq.Workplane:
        """Build the liftarm: stadium body → main holes → perp holes → chamfers."""
        length_mm = self.length_mm
        hole_axes = self.hole_axes
        thickness = self.thickness

        # ── Step 1: stadium body via shared helper ───────────────────────────
        body = stadium_beam_body(length_mm, thickness=thickness)

        # ── Step 2: main-axis holes (+Z bore, through flat faces) ───────────
        # The cutter depth is `thickness + 2*_ENTRY_OVERCUT` so it clears both
        # flat faces (Z=0 and Z=thickness) with strictly positive overcut.
        # Translation to Z=-_ENTRY_OVERCUT anchors the cutter entry at the
        # bottom face with a small undercut, guaranteeing the cutter breaks
        # through both ±Z faces cleanly (FR 6, 7).
        #
        # NB (TL round, 2026-08-19 — fixes a latent crossed-constant bug):
        # the main bore runs through `thickness` (the beam's Z-extent), NOT
        # `BEAM_WIDTH` (its Y-extent) — a prior version of this line read
        # `cutter_depth_main = BEAM_WIDTH + 2*_ENTRY_OVERCUT`, which was latent
        # only because BEAM_WIDTH == BEAM_THICKNESS == 7.8 by coincidence; at
        # thickness=8.0 it produced blind main holes (a 0.19 mm wafer left
        # uncut).  See test_thickness_override_main_holes_break_through for the
        # durable regression guard.
        cutter_depth_main = thickness + 2 * TechnicPinHole._ENTRY_OVERCUT
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
        #   2. Translated to (x_i, -BEAM_WIDTH/2 - _ENTRY_OVERCUT, thickness/2)
        #      so the bore entry face starts _ENTRY_OVERCUT past the -Y side face
        #      and the bore terminates _ENTRY_OVERCUT past the +Y side face,
        #      centred at mid-height (Z = thickness/2).
        # Depth = BEAM_WIDTH + 2*_ENTRY_OVERCUT so the cutter spans the full
        # ±Y side-face extent with strictly positive overcut on BOTH ends (FR 9, 10).
        #
        # NB (TL round, 2026-08-19 — the other half of the crossed-constant bug):
        # the perp bore runs through `BEAM_WIDTH` (the beam's Y-extent), NOT
        # `BEAM_THICKNESS` — a prior version of this line read
        # `cutter_depth_perp = BEAM_THICKNESS + 2*_ENTRY_OVERCUT`, latent for the
        # same reason as the main-side crossing above (harmless over-shoot, not
        # a blind hole, since BEAM_WIDTH never varies per-instance — but crossed
        # nonetheless, and left crossed would silently misdescribe the geometry
        # if BEAM_WIDTH itself is ever parametrised).
        cutter_depth_perp = BEAM_WIDTH + 2 * TechnicPinHole._ENTRY_OVERCUT
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
                # cutter entry clears the -Y face; thickness/2 centres the bore
                # at mid-height of the cross-section (FR 12).
                placed = perp_cutter.translate(
                    (x_i, -BEAM_WIDTH / 2 - TechnicPinHole._ENTRY_OVERCUT, thickness / 2)
                )
                body = body.cut(placed)

        # ── Step 4a: lead-in chamfer — main-hole rims (Z-face counterbore edges) ─
        # Two sequential chamfer passes are MANDATORY (OQ-5 / OCCT homogeneity):
        # mixing edge families (Z-face rims + Y-face rims) in a single .chamfer()
        # call causes "BRep_API: command not done".  Each pass selects only its own
        # family of edges for a homogeneous edge set.
        #
        # Uses the file-local _MainAxisChamferSelector (not the shared
        # _HoleMouthSelector's axis="z" branch) because that shared selector
        # folds around the fixed module constant BEAM_THICKNESS/2, which is
        # only correct when thickness == BEAM_THICKNESS — see the selector's
        # own docstring above for the full rationale.
        n_main = hole_axes.count("main")
        if n_main > 0:
            main_sel = _MainAxisChamferSelector(
                target_radius=TechnicPinHole.DEFAULT_CB_DIAMETER / 2,  # 3.1 mm
                thickness=thickness,
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
