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

"""Gear ABC plus shared involute primitives.

The shared primitives — :meth:`Gear.involute_tooth_profile_2d`,
:meth:`Gear.gear_blank_with_teeth_2d`, :meth:`Gear.bore_cutter`,
:meth:`Gear.from_iso` — are ``@classmethod`` helpers so that any caller
(inheriting subclass or not) can invoke them as
``Gear.involute_tooth_profile_2d(module=…, teeth=…, pressure_angle=…)``.
This shape is deliberately chosen because ``RackGear`` does not inherit
from :class:`Gear` (rack geometry has no ``teeth`` / ``bore`` parameters)
yet still benefits from the shared involute math.  See
``.agents/plans/2026-05-13-pre-oss-models-structure_design.md`` §Phase 6
for the design rationale.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod

import cadquery as cq

from .bore import Bore


# ISO 54 / DIN 780 standard module series for spur gears (subset of common
# values).  Used by :meth:`Gear.from_iso` to validate that the chosen module
# is a real industry value rather than an arbitrary float.
ISO_STANDARD_MODULES: tuple[float, ...] = (
    0.5, 0.8, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0,
)


class Gear(ABC):
    """Abstract base class for parametric involute gears.

    Origin convention: the gear axis is the +Z axis with the pitch circle
    centred on ``(0, 0)``.  The bottom face sits at ``Z = 0`` and the top
    face at ``Z = face_width`` (matching :meth:`SpurGear._build`).

    Shared geometry primitives (involute flank, full toothed cross-section,
    bore cutter, mesh-pair assembly) live on :class:`Gear` itself as
    ``@classmethod`` / instance methods so they can be consumed by callers
    that do *not* inherit from :class:`Gear` (notably :class:`RackGear`).
    """

    def __init__(
        self,
        module: float,
        teeth: int,
        face_width: float,
        bore: float | Bore | None = None,
        pressure_angle: float = 20.0,
    ) -> None:
        self.module = float(module)
        self.teeth = int(teeth)
        self.face_width = float(face_width)
        # Accept either a plain bore-diameter float (legacy interface) or a
        # composable :class:`Bore` instance (new Phase 6 interface).  ``None``
        # still means "no bore" — solid hub.
        self.bore = bore
        self.pressure_angle = float(pressure_angle)

        if self.module <= 0:
            raise ValueError(f"module must be positive, got {self.module}")
        if self.face_width <= 0:
            raise ValueError(f"face_width must be positive, got {self.face_width}")

        phi = math.radians(self.pressure_angle)
        z_min = int(2.0 / math.sin(phi) ** 2)
        if self.teeth < z_min:
            raise ValueError(
                f"teeth={self.teeth} would cause undercut; minimum for "
                f"pressure_angle={self.pressure_angle}° is {z_min}. "
                "Increase tooth count or use profile shift."
            )

        # Derived radii for standard involute gears
        m, z = self.module, self.teeth
        self.pitch_radius = m * z / 2.0
        self.base_radius = self.pitch_radius * math.cos(phi)
        self.tip_radius = self.pitch_radius + m          # addendum = m
        self.root_radius = self.pitch_radius - 1.25 * m  # dedendum = 1.25 m

    @property
    @abstractmethod
    def solid(self) -> cq.Workplane:
        """The CadQuery solid representing the generated gear."""
        ...

    def center_distance_to(self, other: "Gear") -> float:
        """Standard centre-to-centre operating distance to another gear."""
        if self.module != other.module:
            raise ValueError("Gears must have the same module to mesh properly.")
        if self.pressure_angle != other.pressure_angle:
            raise ValueError("Gears must have the same pressure angle to mesh properly.")
        return self.pitch_radius + other.pitch_radius

    # ------------------------------------------------------------------
    # Shared involute primitives (Phase 6 — T6.1 / T6.2)
    # ------------------------------------------------------------------

    @staticmethod
    def _involute(t: float, r_base: float) -> tuple[float, float]:
        """Raw involute point at roll-angle *t* for base circle *r_base*."""
        return (
            r_base * (math.cos(t) + t * math.sin(t)),
            r_base * (math.sin(t) - t * math.cos(t)),
        )

    @staticmethod
    def _rotate_pt(pt: tuple[float, float], angle: float) -> tuple[float, float]:
        """Rotate 2-D point *pt* CCW by *angle* radians."""
        c, s = math.cos(angle), math.sin(angle)
        x, y = pt
        return (c * x - s * y, s * x + c * y)

    @classmethod
    def involute_tooth_profile_2d(
        cls,
        module: float,
        teeth: int,
        pressure_angle: float = 20.0,
        n_flank: int = 32,
    ) -> list[tuple[float, float]]:
        """Return the 2D involute flank curve for a single tooth.

        The returned list traces the right flank (rising involute from root
        to tip) of one tooth centred on the +X axis.  Callers can mirror
        and rotate this curve to form a full tooth and array it around the
        gear (see :meth:`gear_blank_with_teeth_2d`), or linearise it as a
        rack consumes a single tooth in :class:`RackGear`.

        The flank is sampled from the base-circle tangent point (or the
        root circle when the base lies inside the root) up to the tip
        circle.  Coordinate convention: gear centre at ``(0, 0)``, tooth
        symmetric about ``y = 0``, ``x > 0``.
        """
        m = float(module)
        z = int(teeth)
        phi = math.radians(float(pressure_angle))

        pitch_radius = m * z / 2.0
        r_b = pitch_radius * math.cos(phi)
        r_a = pitch_radius + m
        r_f = pitch_radius - 1.25 * m

        inv_phi = math.tan(phi) - phi
        t_tip = math.sqrt((r_a / r_b) ** 2 - 1)
        half_base = math.pi / (2.0 * z) + inv_phi

        if r_f >= r_b:
            t_root = math.sqrt((r_f / r_b) ** 2 - 1)
        else:
            t_root = 0.0

        pts: list[tuple[float, float]] = []
        # Sample the right flank: rotate the raw involute by −half_base so
        # the flank ends at the tip with the tooth centred on +X.  The
        # caller (gear_blank_with_teeth_2d) reuses the per-tooth rotation
        # to array the flank around the full gear.
        for j in range(int(n_flank)):
            t = t_root + (t_tip - t_root) * j / (max(1, int(n_flank) - 1))
            pts.append(cls._rotate_pt(cls._involute(t, r_b), -half_base))
        return pts

    @classmethod
    def gear_blank_with_teeth_2d(
        cls,
        module: float,
        teeth: int,
        pressure_angle: float = 20.0,
        n_flank: int = 32,
        n_tip: int | None = None,
        n_root: int | None = None,
    ) -> list[tuple[float, float]]:
        """Return the full CCW gear cross-section as ``(x, y)`` tuples.

        This is the canonical 2D toothed profile that :class:`SpurGear` and
        :class:`HelicalGear` extrude (the latter with twist).  The sketch
        is closed (first and last points are adjacent across the seam
        between the last tooth's right root and the first tooth's left
        root) and may be passed directly to ``cq.Workplane.polyline(...)
        .close()``.

        The math matches the pre-Phase-6 ``SpurGear._gear_profile_points``
        algorithm bit-for-bit so that geometry-parity holds across the
        refactor.  See Phase 6 §T6.6 in the design artifact.
        """
        m = float(module)
        z = int(teeth)
        phi = math.radians(float(pressure_angle))
        n_flank_i = int(n_flank)
        n_tip_i = int(n_tip) if n_tip is not None else max(2, n_flank_i // 8)
        n_root_i = int(n_root) if n_root is not None else max(3, n_flank_i // 8)

        pitch_radius = m * z / 2.0
        r_b = pitch_radius * math.cos(phi)
        r_a = pitch_radius + m
        r_f = pitch_radius - 1.25 * m

        inv_phi = math.tan(phi) - phi
        t_tip = math.sqrt((r_a / r_b) ** 2 - 1)
        inv_at_tip = t_tip - math.atan(t_tip)
        pitch_angle = 2.0 * math.pi / z
        half_base = math.pi / (2.0 * z) + inv_phi

        if r_f >= r_b:
            t_root = math.sqrt((r_f / r_b) ** 2 - 1)
            use_stub = False
        else:
            t_root = 0.0
            use_stub = True

        pts: list[tuple[float, float]] = []
        for i in range(z):
            tc = i * pitch_angle
            theta_rb = tc - half_base
            theta_lb = tc + half_base
            theta_rt = tc - half_base + inv_at_tip
            theta_lt = tc + half_base - inv_at_tip
            theta_nr = tc + pitch_angle - half_base

            if use_stub:
                pts.append((r_f * math.cos(theta_rb), r_f * math.sin(theta_rb)))

            for j in range(n_flank_i):
                t = t_root + (t_tip - t_root) * j / (n_flank_i - 1)
                pts.append(cls._rotate_pt(cls._involute(t, r_b), tc - half_base))

            for j in range(1, n_tip_i + 1):
                theta = theta_rt + (theta_lt - theta_rt) * j / n_tip_i
                pts.append((r_a * math.cos(theta), r_a * math.sin(theta)))

            for j in range(1, n_flank_i):
                t = t_tip - (t_tip - t_root) * j / (n_flank_i - 1)
                p = cls._involute(t, r_b)
                pts.append(cls._rotate_pt((p[0], -p[1]), tc + half_base))

            if use_stub:
                pts.append((r_f * math.cos(theta_lb), r_f * math.sin(theta_lb)))

            for j in range(1, n_root_i):
                theta = theta_lb + (theta_nr - theta_lb) * j / n_root_i
                pts.append((r_f * math.cos(theta), r_f * math.sin(theta)))

        return pts

    # ------------------------------------------------------------------
    # Bore cutter (T6.3) — takes a :class:`Bore` spec as a parameter so it
    # can be reused across gear types without depending on instance state.
    # ------------------------------------------------------------------

    @classmethod
    def bore_cutter(
        cls,
        bore: Bore | float,
        face_width: float,
        overcut: float = 0.1,
    ) -> cq.Workplane:
        """Return a CSG cutter representing the through-bore through a gear.

        Accepts either a composable :class:`Bore` instance or a plain
        diameter float (legacy interface, treated as a :class:`RoundBore`).
        The returned solid extends from ``Z = -overcut`` to
        ``Z = face_width + overcut`` so it cleanly breaks through both
        gear faces when subtracted (per the
        ``Infinite Cutter Overcuts`` rule in ``CLAUDE.md``).
        """
        # Lazy import — :mod:`.bore` is already imported at module scope,
        # this is just a friendly type-narrowing branch.
        if isinstance(bore, (int, float)):
            spec: Bore = _legacy_round_bore(float(bore))
        else:
            spec = bore

        profile = spec.profile_2d()
        cutter = (
            cq.Workplane("XY")
            .polyline(profile)
            .close()
            .extrude(float(face_width) + 2.0 * float(overcut))
            .translate((0, 0, -float(overcut)))
        )
        return cutter

    # ------------------------------------------------------------------
    # Instance method: mesh two gears for visualisation (T6.4)
    # ------------------------------------------------------------------

    def mesh_with(
        self,
        other: "Gear",
        phase: float = 0.0,
    ) -> tuple[cq.Workplane, cq.Workplane]:
        """Return ``(self_solid, other_solid)`` posed for visualisation.

        ``self`` is left at the origin; ``other`` is translated along +X by
        the centre distance returned by :meth:`center_distance_to` and
        rotated about +Z so the tooth phase aligns at the mesh point.

        Parameters
        ----------
        phase
            Additional phase offset in *degrees*, applied to ``other``.
            Default 0.0 puts the standard "tip-to-root, root-to-tip" mesh
            into place at the contact line.

        Notes
        -----
        The phase math used here is the standard external-mesh rule for a
        pair of involute gears sharing module and pressure angle:

        * Anchor ``self`` so a tooth tip points along +X.
        * Rotate ``other`` by (half a tooth pitch) + (180° — i.e. flip so
          its tooth pocket faces ``self``'s tip), then add ``phase`` for
          fine-tuning.

        This produces a visually-meshed pair for any gear count, but is
        intended for layout / SVG preview only; it does not drive a
        motion simulation.
        """
        cd = self.center_distance_to(other)
        self_solid = self.solid

        # Half-pitch of the OTHER gear in degrees plus a 180° flip so its
        # nearest tooth pocket faces self's tip.  Then add user phase.
        half_pitch_other_deg = 180.0 / other.teeth
        other_rot = half_pitch_other_deg + 180.0 + float(phase)
        # CadQuery uses CCW degrees about an axis; rotate about (0, 0, 0)
        # along +Z, THEN translate to the mesh centre.
        other_solid = (
            other.solid
            .rotate((0, 0, 0), (0, 0, 1), other_rot)
            .translate((cd, 0, 0))
        )
        return self_solid, other_solid

    # ------------------------------------------------------------------
    # Factory: from_iso — validate against ISO standard module series (T6.9)
    # ------------------------------------------------------------------

    @classmethod
    def from_iso(
        cls,
        module: float,
        teeth: int,
        face_width: float,
        bore: float | Bore | None = None,
        pressure_angle: float = 20.0,
        **kwargs,
    ) -> "Gear":
        """Construct a gear after validating *module* against the ISO series.

        ``cls`` must be a concrete subclass (e.g. ``SpurGear.from_iso(...)``);
        calling ``Gear.from_iso`` directly raises ``TypeError`` because
        :class:`Gear` is abstract.  Extra ``**kwargs`` are forwarded to the
        concrete constructor so subclass-specific arguments (e.g.
        ``helix_angle`` for :class:`HelicalGear`, ``n_flank`` for both)
        flow through cleanly.

        Raises
        ------
        ValueError
            If *module* is not one of the values in
            :data:`ISO_STANDARD_MODULES`.
        """
        if not any(math.isclose(float(module), v, rel_tol=0, abs_tol=1e-9)
                   for v in ISO_STANDARD_MODULES):
            raise ValueError(
                f"module={module} is not in the ISO standard series "
                f"{list(ISO_STANDARD_MODULES)}; use the plain constructor "
                "for non-standard modules."
            )
        return cls(
            module=module,
            teeth=teeth,
            face_width=face_width,
            bore=bore,
            pressure_angle=pressure_angle,
            **kwargs,
        )


def _legacy_round_bore(diameter: float) -> Bore:
    """Adapter: wrap a plain diameter float in a :class:`RoundBore`.

    Kept private and at module level so the import graph stays one-way
    (``base.py`` → ``bore.py``) and we don't create a circular import by
    importing :class:`RoundBore` at the top of :class:`Gear`'s methods.
    """
    from .bore import RoundBore
    return RoundBore(diameter=diameter)
