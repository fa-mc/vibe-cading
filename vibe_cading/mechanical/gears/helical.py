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

"""HelicalGear — parametric involute helical gear (single or double helix).

Inherits from :class:`SpurGear`.  The 2D toothed cross-section comes from
:meth:`Gear.gear_blank_with_teeth_2d` (per Phase 6 §T6.7); the only
helical-specific bit is replacing ``extrude(face_width)`` with
``twistExtrude(face_width, twist_degrees)`` so the teeth follow a helix.

Setting ``double_helix=True`` produces a *herringbone* gear: two opposite-hand
helical halves of ``face_width / 2`` meeting at a chevron apex on the
mid-plane.  The mirrored hand cancels the axial thrust that a single helix
generates, which is the whole point of a double-helical gear.
"""

from __future__ import annotations

import math

import cadquery as cq

from .base import Gear
from .bore import Bore
from .spur import SpurGear


class HelicalGear(SpurGear):
    """Parametric involute helical gear.

    Parameters
    ----------
    module : float
        Normal module (mm). Standard values: 0.5, 1, 1.5, 2...
    teeth : int
        Number of teeth.
    face_width : float
        Axial thickness (mm).
    helix_angle : float
        Helix angle in degrees. Positive for right-hand, negative for left-hand.
        For ``double_helix=True`` the sign sets the hand of the *bottom* half;
        the top half is always the mirror image.
    bore : float | Bore | None
        Central through-bore (see :class:`SpurGear`).
    pressure_angle : float
        Normal pressure angle in degrees. Default 20°.
    n_flank : int
        Number of points per flank.
    double_helix : bool
        When ``True``, build a herringbone (double-helical) gear: two
        opposite-hand halves of ``face_width / 2`` meeting at a chevron apex
        on the mid-plane.  Default ``False`` (single helix).
    """

    def __init__(
        self,
        module: float,
        teeth: int,
        face_width: float,
        helix_angle: float,
        bore: float | Bore | None = None,
        pressure_angle: float = 20.0,
        n_flank: int = 32,
        double_helix: bool = False,
    ) -> None:
        self.normal_module = float(module)
        self.helix_angle = float(helix_angle)
        self.normal_pressure_angle = float(pressure_angle)
        self.double_helix = bool(double_helix)

        # Calculate transverse properties — the 2D cross-section uses the
        # transverse module and transverse pressure angle, then we twist
        # the extrusion to produce the helix.
        beta_rad = math.radians(self.helix_angle)
        transverse_module = self.normal_module / math.cos(beta_rad)

        # tan(alpha_t) = tan(alpha_n) / cos(beta)
        tan_alpha_t = (
            math.tan(math.radians(self.normal_pressure_angle))
            / math.cos(beta_rad)
        )
        transverse_pressure_angle = math.degrees(math.atan(tan_alpha_t))

        super().__init__(
            module=transverse_module,
            teeth=teeth,
            face_width=face_width,
            bore=bore,
            pressure_angle=transverse_pressure_angle,
            n_flank=n_flank,
        )

    def _twist_over(self, height: float) -> float:
        """Helix twist (degrees) accumulated over an axial *height*.

        twist = 360 * height * tan(beta) / (pi * d)  where d = m_t * z is the
        transverse pitch diameter.  Derived from the helix lead so the tooth
        rotation matches the requested helix angle.
        """
        d = self.pitch_radius * 2.0
        return (
            360.0
            * float(height)
            * math.tan(math.radians(self.helix_angle))
            / (math.pi * d)
        )

    def _build(self) -> cq.Workplane:
        pts = Gear.gear_blank_with_teeth_2d(
            module=self.module,
            teeth=self.teeth,
            pressure_angle=self.pressure_angle,
            n_flank=self._n_flank,
        )

        if self.double_helix:
            # Herringbone: bottom half twists +twist over face_width/2; the top
            # half is the bottom mirrored across the mid-plane, giving the
            # opposite hand.  The two halves share an identical cross-section at
            # the mid-plane (the mirror plane), so the union is seam-clean.
            half_h = self.face_width / 2.0
            bottom = (
                cq.Workplane("XY")
                .polyline(pts)
                .close()
                .twistExtrude(half_h, self._twist_over(half_h))
            )
            top = bottom.mirror("XY", (0, 0, half_h))
            gear = bottom.union(top)
        else:
            gear = (
                cq.Workplane("XY")
                .polyline(pts)
                .close()
                .twistExtrude(self.face_width, self._twist_over(self.face_width))
            )

        if self.bore is not None:
            gear = gear.cut(Gear.bore_cutter(self.bore, self.face_width))

        return gear

    # ------------------------------------------------------------------
    # Crossed-axis ("screw" gear) meshing — posing helpers.
    #
    # Crossed helical gears are ordinary single-helical gears whose shafts
    # are skew (typically 90°) rather than parallel.  "Crossed" is therefore
    # purely a *posing* relationship — the single-gear ``solid`` is unchanged
    # — so these live on the meshing layer, not the constructor.  The mesh
    # condition differs from the parallel case: crossed gears must share the
    # same *normal* module and *normal* pressure angle, but may have different
    # helix angles (hence different transverse modules), so the base-class
    # ``center_distance_to`` / ``mesh_with`` (which assume equal transverse
    # module on parallel axes) cannot be reused.  See
    # ``docs/design_plans/2026-06-26-crossed-helical-mesh_design.md``.
    # ------------------------------------------------------------------

    def _assert_crossed_meshable(self, other: "HelicalGear") -> None:
        """Validate that *other* can form a crossed-helical pair with *self*.

        The single source of truth for the crossed mesh condition: *other*
        must be a :class:`HelicalGear` (a spur/rack gear has no helix and
        cannot screw-mesh) sharing the same normal module and normal
        pressure angle.  Helix angles may differ — that is what sets the
        shaft angle.
        """
        if not isinstance(other, HelicalGear):
            raise TypeError(
                "crossed_mesh_with requires a HelicalGear; got "
                f"{type(other).__name__}. Crossed-axis meshing is defined "
                "for single-helical (screw) gears."
            )
        # Compare the *normal* inputs (user-supplied, usually exact); abs_tol
        # mirrors from_iso and avoids float-equality brittleness.
        if not math.isclose(
            self.normal_module, other.normal_module, rel_tol=0, abs_tol=1e-9
        ):
            raise ValueError(
                "Crossed gears must share the same NORMAL module to mesh; got "
                f"{self.normal_module} vs {other.normal_module}."
            )
        if not math.isclose(
            self.normal_pressure_angle,
            other.normal_pressure_angle,
            rel_tol=0,
            abs_tol=1e-9,
        ):
            raise ValueError(
                "Crossed gears must share the same NORMAL pressure angle to "
                f"mesh; got {self.normal_pressure_angle} vs "
                f"{other.normal_pressure_angle}."
            )

    def _derived_shaft_angle(self, other: "HelicalGear") -> float:
        """Shaft angle Σ (degrees) for the crossed pair, from the helix angles.

        Same hand (signs of the two helix angles agree) → ``Σ = |β₁| + |β₂|``;
        opposite hand → ``Σ = ||β₁| − |β₂||``.  This is the standard
        crossed-helical relation; the common Σ = 90° case falls out of e.g.
        45°+45° or 60°+30° same-hand pairs.
        """
        b1, b2 = self.helix_angle, other.helix_angle
        same_hand = (b1 >= 0) == (b2 >= 0)
        if same_hand:
            return abs(b1) + abs(b2)
        return abs(abs(b1) - abs(b2))

    def crossed_center_distance_to(self, other: "HelicalGear") -> float:
        """Common-perpendicular centre distance for a crossed-helical pair.

        ``a = r₁ + r₂`` — the sum of the two *transverse* pitch radii,
        measured along the common perpendicular between the skew shaft axes.
        Validates the crossed mesh condition (equal normal module / normal
        pressure angle) rather than the parallel one (equal *transverse*
        module), which crossed gears legitimately violate.  Distinct from the
        base :meth:`Gear.center_distance_to`, which is the coplanar
        centre-to-centre distance for a *parallel*-axis pair.
        """
        self._assert_crossed_meshable(other)
        return self.pitch_radius + other.pitch_radius

    def crossed_mesh_with(
        self,
        other: "HelicalGear",
        *,
        shaft_angle: float | None = None,
        phase: float = 0.0,
    ) -> tuple[cq.Workplane, cq.Workplane]:
        """Pose ``self`` and ``other`` as a crossed-axis (screw) gear pair.

        ``self`` is left at the origin with its axis along +Z; ``other`` is
        spun about its own axis, tilted so its shaft crosses ``self``'s at the
        shaft angle, and translated out to the mesh line.  Returns
        ``(self_solid, other_solid)`` for visualisation/layout — like
        :meth:`Gear.mesh_with`, this is a static pose, not a motion sim
        (crossed-helical contact is point-contact).

        Parameters
        ----------
        other
            The meshing :class:`HelicalGear`.  Must share ``self``'s normal
            module and normal pressure angle.  Crossed pairs are normally
            same-hand single-helical; a ``double_helix`` gear has a valid axis
            and is not blocked, but is an unusual crossed configuration.
        shaft_angle
            Shaft angle Σ in degrees.  ``None`` (default) auto-derives Σ from
            the two helix angles (see :meth:`_derived_shaft_angle`); a supplied
            value is used verbatim for the pose (e.g. force an idealised 90°
            for a tidy layout).
        phase
            Extra CCW degrees about ``other``'s own axis for fine alignment.
        """
        self._assert_crossed_meshable(other)
        sigma = (
            self._derived_shaft_angle(other)
            if shaft_angle is None
            else float(shaft_angle)
        )
        cd = self.crossed_center_distance_to(other)

        # Half-tooth-pitch offset so a tooth pocket faces self's tip. Unlike
        # the parallel mesh this carries NO 180° flip — crossed gears engage
        # point-contact on skew axes, not the opposite-sense rotation of a
        # parallel external pair. This term is a visual alignment nicety only,
        # not a kinematic guarantee.
        half_pitch_flip = 180.0 / other.teeth

        # Order is fixed: spin about other's own +Z axis (phase), THEN tilt the
        # shaft about +X by Σ (swinging the axis from +Z toward −Y), THEN
        # translate out along +X. Both rotations pass through the origin while
        # the gear is still centred there, so `phase` stays a clean spin about
        # other's own axis regardless of Σ.
        other_solid = (
            other.solid
            .rotate((0, 0, 0), (0, 0, 1), half_pitch_flip + float(phase))
            .rotate((0, 0, 0), (1, 0, 0), sigma)
            .translate((cd, 0, 0))
        )
        return self.solid, other_solid

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Single, double-helix, and a crossed-axis (screw) pair side by side."""
        single = cls(module=2, teeth=20, face_width=15, helix_angle=30, bore=5)
        double = cls(
            module=2, teeth=20, face_width=15, helix_angle=30, bore=5,
            double_helix=True,
        )
        # Crossed-axis pair: two 45° gears meshing at a 90° shaft angle.
        cross_a = cls(module=2, teeth=18, face_width=12, helix_angle=45, bore=5)
        cross_b = cls(module=2, teeth=18, face_width=12, helix_angle=45, bore=5)
        pa, pb = cross_a.crossed_mesh_with(cross_b)
        off = (0, -80, 0)  # shift the pair clear of the single/double row
        return [
            (single.solid.translate((-25, 0, 0)), "Single helix", "gold"),
            (double.solid.translate((25, 0, 0)), "Double helix", "royalblue"),
            (pa.translate(off), "Crossed (driver)", "seagreen"),
            (pb.translate(off), "Crossed (driven)", "darkorange"),
        ]
