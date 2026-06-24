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

"""90°-bent Lego Technic studless liftarm (L-shaped / bent beam).

Design brief: docs/design_plans/2026-06-24-lego-technic-l-liftarm_design.md
Human design gate approved 2026-06-24 (default 3×5, no build.toml registration).
"""

from typing import Literal

import cadquery as cq

from vibe_cading.lego.constants import (
    BEAM_END_RADIUS,
    BEAM_THICKNESS,
    BEAM_WIDTH,
    LEAD_IN,
    STUD_PITCH,
)
from vibe_cading.lego.cutters.technic_pin_hole import TechnicPinHole
from vibe_cading.print_settings import ToleranceProfile, get_profile


class _HoleMouthSelector(cq.Selector):
    """Pick counterbore-rim circle edges at hole entries on the top/bottom (Z) faces.

    Identical predicate logic to LegoTechnicBeam._HoleMouthSelector — filters
    edges to: (a) geomType() == 'CIRCLE', (b) radius ≈ counterbore radius
    (TechnicPinHole.DEFAULT_CB_DIAMETER / 2 = 3.1 mm), and (c)
    |Center().z - BEAM_THICKNESS/2| ≈ BEAM_THICKNESS/2 (i.e. on the top face
    Z=BEAM_THICKNESS or bottom face Z=0, not interior counterbore floor).
    """

    def __init__(
        self,
        target_radius: float,
        target_z_abs_from_mid: float,
        tol: float = 0.05,
    ) -> None:
        self.target_radius = target_radius
        self.target_z_abs_from_mid = target_z_abs_from_mid
        self.tol = tol

    def filter(self, edges):
        kept = []
        for e in edges:
            try:
                if e.geomType() != "CIRCLE":
                    continue
                if abs(e.radius() - self.target_radius) >= self.tol:
                    continue
                # Fold through the mid-plane Z=BEAM_THICKNESS/2 so top face
                # (Z=BEAM_THICKNESS) and bottom face (Z=0) both pass the same
                # |center.z - BEAM_THICKNESS/2| ≈ BEAM_THICKNESS/2 threshold.
                if abs(abs(e.Center().z - BEAM_THICKNESS / 2) - self.target_z_abs_from_mid) >= self.tol:
                    continue
                kept.append(e)
            except Exception:
                continue
        return kept


class LegoTechnicLLiftarm:
    """90°-bent Lego Technic studless liftarm (L-shaped / bent beam).

    Builds two perpendicular arms sharing a corner hole, with pin holes on
    the 8 mm stud grid along both arms, rounded ends, and standard 7.8×7.8 mm
    beam cross-section.

    Origin convention
    -----------------
    Bottom face at Z = 0 (FDM print-bed).

    Arm-A runs along +X:
        X ∈ [0, arm_a_studs × 8]
        Y ∈ [−STUD_PITCH/2 − BEAM_END_RADIUS, −STUD_PITCH/2 + BEAM_END_RADIUS]
        ≈ Y ∈ [−7.9, −0.1]

    Arm-B runs along −Y:
        X ∈ [STUD_PITCH/2 − BEAM_END_RADIUS, STUD_PITCH/2 + BEAM_END_RADIUS]
        ≈ X ∈ [0.1, 7.9]
        Y ∈ [−arm_b_studs × 8, 0]

    Corner hole centre at (STUD_PITCH/2, −STUD_PITCH/2) = (4.0, −4.0, *).
    Pin holes are parallel to Z (vertical when part is laid flat on a table).

    Subtle geometry note — 0.1 mm offset between hole centres and end-cap centres
    (inherited from LegoTechnicBeam / constants.py NOTE block):
        End-cap centres sit at one BEAM_END_RADIUS (3.9 mm) from each arm's
        outer tangent face; outermost hole centres sit at STUD_PITCH/2 = 4.0 mm.
        This 0.1 mm offset preserves n × 8 mm arm-length conformance.

    Parameters
    ----------
    arm_a_studs:
        Number of pin holes along Arm-A (running +X), including the corner
        hole. Must be ≥ 1.
    arm_b_studs:
        Number of pin holes along Arm-B (running −Y), including the corner
        hole. Must be ≥ 1.
    fit:
        Tolerance fit grade for pin holes: "slip" (default), "free", "press".
    profile:
        Manufacturing tolerance profile (ToleranceProfile instance, string
        name, or None to use the process-global profile).
    """

    def __init__(
        self,
        arm_a_studs: int = 3,
        arm_b_studs: int = 5,
        fit: Literal["free", "slip", "press"] = "slip",
        profile: "ToleranceProfile | str | None" = None,
    ) -> None:
        if arm_a_studs < 1:
            raise ValueError(f"arm_a_studs must be >= 1, got {arm_a_studs}")
        if arm_b_studs < 1:
            raise ValueError(f"arm_b_studs must be >= 1, got {arm_b_studs}")

        self.arm_a_studs: int = arm_a_studs
        self.arm_b_studs: int = arm_b_studs
        self.fit: str = fit
        # Resolve the tolerance profile at construction time so _build() can
        # pass the resolved instance to TechnicPinHole.standard() directly.
        if profile is None or isinstance(profile, str):
            self._profile: ToleranceProfile = (
                get_profile(profile) if isinstance(profile, str) else get_profile()
            )
        else:
            self._profile = profile

        self._solid: cq.Workplane = self._build()

    def _arm_body(
        self,
        length_mm: float,
        centre_x: float,
        centre_y: float,
        along_x: bool,
    ) -> cq.Workplane:
        """Build one straight arm's stadium body at the requested centreline position.

        Each arm is constructed at its canonical centreline, centred on
        (centre_x, centre_y), extending either along X (along_x=True, length
        along X dimension) or along Y (along_x=False, length along Y
        dimension).  The 2D-sketch pattern is identical to LegoTechnicBeam:
        a rectangle between the two end-cap centres + two semicircular
        end-caps, extruded along +Z by BEAM_THICKNESS.

        Parameters
        ----------
        length_mm:
            Full arm length (mm) = studs × STUD_PITCH.
        centre_x, centre_y:
            XY position of the arm's centreline midpoint.
        along_x:
            True → arm extends along the X axis (like LegoTechnicBeam).
            False → arm extends along the Y axis (Arm-B).
        """
        # Distance from each end-cap centre to the arm's outermost tangent face.
        # The end-cap radius (3.9 mm) differs from the stud-pitch half (4.0 mm)
        # by 0.1 mm — intentional per the NOTE in constants.py.
        r = BEAM_END_RADIUS

        # Rectangle between the two end-cap centres, width = BEAM_WIDTH.
        rect_span = length_mm - 2 * r  # distance between the two cap centres

        if along_x:
            # Arm runs along X: rect is wide in X, narrow in Y.
            # Cap centres at (centre_x ± rect_span/2, centre_y).
            cap_left = (centre_x - rect_span / 2, centre_y)
            cap_right = (centre_x + rect_span / 2, centre_y)
            sketch = (
                cq.Workplane("XY")
                .sketch()
                .push([(centre_x, centre_y)])
                .rect(rect_span, BEAM_WIDTH)
                .reset()
                .push([cap_left, cap_right])
                .circle(r)
                .clean()
                .finalize()
            )
        else:
            # Arm runs along Y: rect is wide in Y, narrow in X.
            # Cap centres at (centre_x, centre_y ± rect_span/2).
            cap_top = (centre_x, centre_y - rect_span / 2)
            cap_bot = (centre_x, centre_y + rect_span / 2)
            sketch = (
                cq.Workplane("XY")
                .sketch()
                .push([(centre_x, centre_y)])
                .rect(BEAM_WIDTH, rect_span)
                .reset()
                .push([cap_top, cap_bot])
                .circle(r)
                .clean()
                .finalize()
            )

        return sketch.extrude(BEAM_THICKNESS)

    def _build(self) -> cq.Workplane:
        """Build the L-liftarm: two arm bodies → union → de-duplicated hole pass → chamfer."""
        # ── Arm dimensions ────────────────────────────────────────────────────
        arm_a_len = self.arm_a_studs * STUD_PITCH  # e.g. 3 × 8 = 24 mm
        arm_b_len = self.arm_b_studs * STUD_PITCH  # e.g. 5 × 8 = 40 mm

        # ── Arm-A centreline position ─────────────────────────────────────────
        # Arm-A runs along +X.  Its centreline (Y mid) sits at Y = −STUD_PITCH/2
        # = −4 mm, so hole centres land at (k×8+4, −4) for k in 0..arm_a_studs−1.
        # The arm body extends from X=0 to X=arm_a_len; its centroid in X is
        # arm_a_len/2 and centroid in Y is −STUD_PITCH/2.
        arm_a_cx = arm_a_len / 2
        arm_a_cy = -STUD_PITCH / 2  # centreline Y = −4 mm

        # ── Arm-B centreline position ─────────────────────────────────────────
        # Arm-B runs along −Y.  Its centreline (X mid) sits at X = STUD_PITCH/2
        # = 4 mm.  The arm body extends from Y=0 to Y=−arm_b_len; its centroid
        # in X is STUD_PITCH/2 and centroid in Y is −arm_b_len/2.
        arm_b_cx = STUD_PITCH / 2   # centreline X = 4 mm
        arm_b_cy = -arm_b_len / 2   # centroid in Y (negative — arm goes down)

        # ── Step 1: Build the two arm solids and union them ───────────────────
        arm_a = self._arm_body(arm_a_len, arm_a_cx, arm_a_cy, along_x=True)
        arm_b = self._arm_body(arm_b_len, arm_b_cx, arm_b_cy, along_x=False)
        body = arm_a.union(arm_b)

        # ── Step 2: Accumulate hole centres, deduplicate (corner hole shared) ─
        # Arm-A holes: along +X at Y = −STUD_PITCH/2.
        #   Centre at (STUD_PITCH*i + STUD_PITCH/2, −STUD_PITCH/2) for i in 0..arm_a_studs−1
        #   For default 3M: (4, −4), (12, −4), (20, −4)
        arm_a_holes = [
            (STUD_PITCH * i + STUD_PITCH / 2, -STUD_PITCH / 2)
            for i in range(self.arm_a_studs)
        ]
        # Arm-B holes: along −Y at X = STUD_PITCH/2.
        #   Centre at (STUD_PITCH/2, −(STUD_PITCH*j + STUD_PITCH/2)) for j in 0..arm_b_studs−1
        #   For default 5M: (4, −4), (4, −12), (4, −20), (4, −28), (4, −36)
        arm_b_holes = [
            (STUD_PITCH / 2, -(STUD_PITCH * j + STUD_PITCH / 2))
            for j in range(self.arm_b_studs)
        ]
        # Deduplicate: the corner hole (4, −4) appears at arm_a_holes[0] and
        # arm_b_holes[0].  dict.fromkeys preserves insertion order and drops the
        # second occurrence.  Corner hole appears exactly once in the result.
        all_holes = list(dict.fromkeys(arm_a_holes + arm_b_holes))
        # Sanity: expect arm_a_studs + arm_b_studs − 1 unique holes.
        expected_count = self.arm_a_studs + self.arm_b_studs - 1
        assert len(all_holes) == expected_count, (
            f"Hole deduplication produced {len(all_holes)} holes; "
            f"expected {expected_count} (arm_a={self.arm_a_studs}, arm_b={self.arm_b_studs})."
        )

        # ── Step 3: Cut all pin holes ─────────────────────────────────────────
        # Cutter depth = BEAM_THICKNESS + 2 × _ENTRY_OVERCUT so it clears both
        # Z faces (same formula as LegoTechnicBeam).  BEAM_WIDTH == BEAM_THICKNESS
        # for the square cross-section, so cutter_depth == BEAM_WIDTH + 2*overcut.
        overcut = TechnicPinHole._ENTRY_OVERCUT
        cutter_depth = BEAM_THICKNESS + 2 * overcut
        cutter = TechnicPinHole.standard(
            depth=cutter_depth, fit=self.fit, profile=self._profile
        ).to_cutter()

        for hx, hy in all_holes:
            # Translate so cutter bottom face sits at Z = −overcut, piercing
            # beam vertically with strictly positive overcut on both Z faces.
            placed = cutter.translate((hx, hy, -overcut))
            body = body.cut(placed)

        # ── Step 4: Lead-in chamfer at every counterbore-rim edge ────────────
        chamfer_selector = _HoleMouthSelector(
            target_radius=TechnicPinHole.DEFAULT_CB_DIAMETER / 2,  # 3.1 mm
            target_z_abs_from_mid=BEAM_THICKNESS / 2,              # 3.9 mm
        )
        total_holes = len(all_holes)
        expected_edges = 2 * total_holes  # one rim circle per hole per Z face
        got_edges = len(body.edges(chamfer_selector).vals())
        assert got_edges == expected_edges, (
            f"Expected {expected_edges} chamfer-rim edges for {total_holes} holes, "
            f"got {got_edges}.  Likely cause: cutter translation-Z sign wrong "
            f"(0 edges → cutters landed outside body) or selector predicate drifted."
        )
        body = body.edges(chamfer_selector).chamfer(LEAD_IN)

        # ── Step 5: Single-solid topological guard ────────────────────────────
        solid_count = len(body.solids().vals())
        assert solid_count == 1, (
            f"Expected single solid after L-liftarm union+cut, got {solid_count}.  "
            f"Likely cause: arm overlap region did not merge (check STUD_PITCH/2 "
            f"vs BEAM_END_RADIUS corner geometry) or a cut produced a wafer."
        )

        return body

    @property
    def solid(self) -> cq.Workplane:
        """The finished L-liftarm body as a CadQuery Workplane."""
        return self._solid

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Three L-liftarms side by side: 3×3, 3×5, 2×4, separated along X for clarity.

        Demonstrates symmetric (3×3), canonical (3×5), and compact (2×4)
        configurations.  Each instance is offset so bounding boxes do not
        overlap.
        """
        # Spacing between demo instances: max arm_a extent across instances plus
        # a 12 mm clear gap.  Arm-A extents: 24 mm (3M), 24 mm (3M), 16 mm (2M).
        # We offset along X by a fixed 40 mm step (generous for all three).
        step_x = 40.0

        l_3x3 = cls(arm_a_studs=3, arm_b_studs=3).solid
        l_3x5 = cls(arm_a_studs=3, arm_b_studs=5).solid.translate((step_x, 0, 0))
        l_2x4 = cls(arm_a_studs=2, arm_b_studs=4).solid.translate((2 * step_x, 0, 0))

        return [
            (l_3x3, "LegoTechnicLLiftarm(3×3)", "royalblue"),
            (l_3x5, "LegoTechnicLLiftarm(3×5)", "gold"),
            (l_2x4, "LegoTechnicLLiftarm(2×4)", "tan"),
        ]
