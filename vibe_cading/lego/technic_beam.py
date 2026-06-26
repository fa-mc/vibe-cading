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


import cadquery as cq

from vibe_cading.lego.constants import (
    BEAM_END_RADIUS,
    BEAM_THICKNESS,
    BEAM_WIDTH,
    LEAD_IN,
    STUD_PITCH,
)
from vibe_cading.lego.cutters.hole_mouth_selector import _HoleMouthSelector
from vibe_cading.lego.cutters.technic_pin_hole import TechnicPinHole


def stadium_beam_body(length_mm: float) -> cq.Workplane:
    """Build and return the extruded stadium-shaped beam body.

    The body is the 2D sketch (rect + two hemicircular end-caps) extruded
    along +Z by ``BEAM_THICKNESS``.  No holes, no chamfers — pure positive
    geometry, shared by :class:`LegoTechnicBeam` and
    :class:`~vibe_cading.lego.technic_beam_perp.PerpendicularHolesLiftarm`.

    Bounding box: ``X ∈ [0, length_mm] × Y ∈ [-BEAM_WIDTH/2, +BEAM_WIDTH/2]
    × Z ∈ [0, BEAM_THICKNESS]``.

    Parameters
    ----------
    length_mm:
        Total beam length in millimetres (must satisfy ``length_mm >= 2 *
        BEAM_END_RADIUS``; this is guaranteed by any ``num_holes >= 1``
        caller since ``STUD_PITCH > 2 * BEAM_END_RADIUS``).
    """
    rect_centre_x = length_mm / 2
    rect_width_x = length_mm - 2 * BEAM_END_RADIUS
    end_x_left = BEAM_END_RADIUS
    end_x_right = length_mm - BEAM_END_RADIUS

    sketch = (
        cq.Workplane("XY")
        .sketch()
        .push([(rect_centre_x, 0.0)])
        .rect(rect_width_x, BEAM_WIDTH)
        .reset()
        .push([(end_x_left, 0.0), (end_x_right, 0.0)])
        .circle(BEAM_END_RADIUS)
        .clean()
        .finalize()
    )
    return sketch.extrude(BEAM_THICKNESS)


class LegoTechnicBeam:
    """First-party Lego Technic studless lift-arm (thick) beam primitive.

    Builds a stud-grid-aligned beam body with through pin holes, a 0.3 mm × 45°
    lead-in chamfer at every hole entry, and the symmetric two-end counterbore
    inherited from :pyclass:`TechnicPinHole`.

    Origin convention
    -----------------
    The beam's bounding box is ``X ∈ [0, length_mm] × Y ∈ [-BEAM_WIDTH/2, +BEAM_WIDTH/2] ×
    Z ∈ [0, BEAM_THICKNESS]``.  The bottom face sits at ``Z = 0`` (FDM print-bed
    convention).  ``X = 0`` is the outermost tangent of the first end-cap, **NOT**
    the first hole centre.

    Subtle geometry note — 0.1 mm offset between hole centres and end-cap centres:
        The first hole centre sits at ``X = STUD_PITCH / 2 = 4.0 mm``.
        The first end-cap centre sits at ``X = BEAM_END_RADIUS = 3.9 mm``.
        These are **deliberately offset by 0.1 mm**.  The convention preserves both
        the Lego naming convention (``length_mm = n × 8 mm``) and the Cailliau-measured
        end-cap radius (3.9 mm = ``BEAM_WIDTH / 2``).  Real-world Lego liftarms have
        the end-cap centred on the outermost hole (which would shrink total length to
        ``n × 8 - 0.2 mm``); this project trades 0.2 mm of fidelity for ``n × 8 mm``
        conformance.  See the NOTE block above the constants in
        ``vibe_cading/lego/constants.py`` for the full rationale.  Users placing pins
        or mating parts should reference hole centres at ``X = STUD_PITCH * i +
        STUD_PITCH / 2``, NOT at the end-cap centres.

    Parameters
    ----------
    length_in_studs:
        Length of the beam in stud units (e.g. ``5`` → 40 mm).  Must be ≥ 1.
    """

    def __init__(self, length_in_studs: int) -> None:
        if length_in_studs < 1:
            raise ValueError(
                f"length_in_studs must be >= 1, got {length_in_studs}"
            )
        self.length_in_studs: int = length_in_studs
        self.length_mm: float = length_in_studs * STUD_PITCH

        self._solid: cq.Workplane | None = None
        self._solid = self._build()

    def _build(self) -> cq.Workplane:
        """Build the beam: 2D-sketch stadium body → through-cutter pass → lead-in chamfer."""
        length_mm = self.length_mm

        # ── Step 1: stadium body via shared helper ───────────────────────────
        # The helper extracts the 2D-sketch + extrude so both LegoTechnicBeam
        # and PerpendicularHolesLiftarm share the same body recipe without
        # duplicating code.  Behavior is byte-identical to the inlined version;
        # all visual contracts and tests remain valid (pure internal refactor).
        body = stadium_beam_body(length_mm)

        # ── Step 2 + 3: through-cutter pass ─────────────────────────────────
        # Single cutter instance: depth = BEAM_WIDTH + 2 × _ENTRY_OVERCUT so the
        # cutter clears both Z-side faces with strictly positive overcut (the
        # depth literal is unchanged because BEAM_WIDTH = BEAM_THICKNESS for the
        # square cross-section).  The cutter inherits TechnicPinHole.standard()'s
        # symmetric two-end counterbore automatically (cb_bottom + cb_top); after
        # the +Z-translation they land at world Z ∈ [-0.01, +1.0] and
        # [BEAM_THICKNESS - 1.0, BEAM_THICKNESS + 0.01] respectively — i.e. one
        # 1.0 mm counterbore well inset from each Z face.
        cutter_depth = BEAM_WIDTH + 2 * TechnicPinHole._ENTRY_OVERCUT
        # Profile-awareness inherited from TechnicPinHole.standard default fit="slip".
        cutter = TechnicPinHole.standard(depth=cutter_depth).to_cutter()

        positions = [
            (STUD_PITCH * i + STUD_PITCH / 2, 0.0)
            for i in range(self.length_in_studs)
        ]

        for x, _y in positions:
            # Round 6 hole-axis correction (2026-05-17): holes are parallel to
            # +Z, not Y.  The cutter's native bore axis is already +Z, so no
            # rotation is applied.  Translation places the cutter so its bottom
            # face sits at Z = -_ENTRY_OVERCUT and its top face at
            # Z = BEAM_THICKNESS + _ENTRY_OVERCUT, piercing the beam vertically
            # with strictly positive overcut on both Z faces.
            placed = cutter.translate(
                (
                    x,
                    0.0,
                    -TechnicPinHole._ENTRY_OVERCUT,
                )
            )
            body = body.cut(placed)

        # ── Step 4: lead-in chamfer at every counterbore-rim edge ────────────
        # The selector picks edges by (geomType, radius, |center.z - mid|) — see
        # _HoleMouthSelector docstring for why this is necessary over a string
        # selector or lambda.  The edge count under the Round-6 Z-axis contract
        # is a clean 2*N for ALL N ≥ 1 (one full counterbore-rim CIRCLE per hole
        # per Z face).  Note: the Round-5 special-case "N=1 → 4 edges" applied
        # ONLY under the prior Y-axis contract, where the curved end-cap surfaces
        # wrapped *transverse* to the hole-axis and split the rim into top+bottom
        # arc pairs.  Under Round 6 the end-caps extrude *parallel* to the
        # hole-axis (+Z), so they intersect the Z-faces in r=BEAM_END_RADIUS=3.9
        # circles that sit beside (not across) the rim — the r=3.1 rim circles
        # therefore remain whole, even at N=1.  Live-probe verified
        # (tmp/probe_n1_edges.py, 2026-05-17).
        chamfer_selector = _HoleMouthSelector(
            target_radius=TechnicPinHole.DEFAULT_CB_DIAMETER / 2,  # 3.1 mm
            target_z_abs_from_mid=BEAM_THICKNESS / 2,              # 3.9 mm
        )
        # Defence-in-depth assertion (per design Post-Fix Hardening rule).
        # Catches both (a) cutter-translation-Z-sign regressions (selector returns
        # 0 when no holes were cut) and (b) chamfer-selector predicate drift
        # (selector returns the wrong count when radius/z tolerances are off).
        expected_edges = 2 * self.length_in_studs
        got_edges = len(body.edges(chamfer_selector).vals())
        assert got_edges == expected_edges, (
            f"Expected {expected_edges} chamfer edges at length_in_studs="
            f"{self.length_in_studs}, got {got_edges}.  Likely cause: cutter "
            f"translation-Z sign wrong (0 edges → cutter outside beam) or selector "
            f"predicate drifted (radius/z tolerances)."
        )
        body = body.edges(chamfer_selector).chamfer(LEAD_IN)

        # ── Step 5: FR16 single-solid topological guard ──────────────────────
        solid_count = len(body.solids().vals())
        assert solid_count == 1, (
            f"Expected single solid, got {solid_count}.  Likely cause: cutter "
            f"left a wafer between the two side faces, or the body sketch produced "
            f"disconnected faces."
        )

        return body

    @property
    def solid(self) -> cq.Workplane:
        """The finished beam body as a CadQuery Workplane."""
        return self._solid

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Three beams side-by-side: 3-stud, 5-stud, 9-stud, separated along Y for clarity."""
        # 12 mm clear gap > 0 by a comfortable margin; (BEAM_WIDTH + 12) centre-to-centre.
        spacing_y = BEAM_WIDTH + 12.0
        beam_3 = cls(length_in_studs=3).solid.translate((0, -spacing_y, 0))
        beam_5 = cls(length_in_studs=5).solid.translate((0, 0, 0))
        beam_9 = cls(length_in_studs=9).solid.translate((0, +spacing_y, 0))
        return [
            (beam_3, "LegoTechnicBeam(3)", "royalblue"),
            (beam_5, "LegoTechnicBeam(5)", "gold"),
            (beam_9, "LegoTechnicBeam(9)", "tan"),
        ]
