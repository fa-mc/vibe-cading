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
from vibe_cading.cq_utils import axle_cross_section
from vibe_cading.print_settings import ToleranceProfile, get_profile
from vibe_cading.lego.constants import (
    AXLE_HOLE_TIP_TO_TIP,
    AXLE_HOLE_ARM_WIDTH,
)


class TechnicAxleHole:
    """Lego Technic cross axle hole profile.

    Builds a + cross solid sized to the Technic axle *hole* dimensions.

    The base cross dimensions come from the ``AXLE_HOLE_TIP_TO_TIP`` /
    ``AXLE_HOLE_ARM_WIDTH`` constants, which are **fixed real-world Lego
    nominals** — the geometric envelope of the cross axle hole, with no
    printer clearance baked in.  Printer / material clearance is supplied
    by the active :class:`~vibe_cading.print_settings.ToleranceProfile`:

    * ``TIP_TO_TIP`` (the round envelope) is sized
      ``nominal + 2 * grade.radial``, matching the ``Bearing`` /
      ``magnets`` / clearance-hole pattern used throughout the library.
    * ``ARM_WIDTH`` (the narrow ``+`` cross slot) is sized
      ``nominal + 2 * grade.radial + 2 * grade.slot``.  The extra
      ``2 * grade.slot`` term widens *only* the arm slot: a narrow ``+``
      slot prints tighter on FDM than the round envelope of the same
      nominal, so it carries its own clearance.  See
      :class:`~vibe_cading.print_settings.FitGrade` for ``slot``.

    To tune a printed fit, calibrate the profile
    (``slip.radial`` for the round envelope, ``slip.slot`` for the arm
    slot, in ``print_profiles_user.json``) — not the constants.  The
    shipped ``fdm_standard`` already carries a conservative
    ``slip.slot = 0.10``, so most users calibrate only ``slip.radial``.

    The ``concave_radius`` inner-valley fillet default (``0.3 mm``) is
    best-current-evidence on one calibrated FDM stack
    (``bambu_p1s`` + PLA at ``slip.slot = 0.1125``, validated
    2026-05-28), **not** a universally optimal value.  Users on other
    printers may override per-instance via the ``concave_radius=``
    constructor kwarg — already public API, no profile-level field
    needed (the concave fillet does not participate in the fit
    envelope).

    Use the :pymeth:`to_cutter` method as a boolean cutter::

        from vibe_cading.lego.cutters.technic_axle_hole import TechnicAxleHole

        hole = TechnicAxleHole(depth=my_thickness, fit="slip")
        part = part.cut(hole.to_cutter())

    The legacy ``.solid`` accessor remains as an alias for backwards
    compatibility and is read-only.

    Through-vs-blind: this cutter is built flush — entry at Z=0 and
    terminal exactly at Z=depth.  Consumers that need a through-hole
    typically construct the cutter with ``depth`` already equal to the
    host body's full thickness, so no class-level overcut is required.

    Parameters
    ----------
    depth:
        Axial depth of the hole (mm).
    fit:
        Tolerance fit type: "press", "slip", or "free".
    profile:
        Manufacturing tolerance profile. Defaults to global profile.
    convex_radius:
        Fillet radius on the 8 outer convex junction edges — where the
        curved arm tip meets the flat arm side (mm).  Set to 0 to skip.
    concave_radius:
        Fillet radius on the 4 inner concave corners — the valleys between
        perpendicular arms (mm).  Set to 0 to skip.  Default ``0.3 mm``
        validated 2026-05-28 on ``bambu_p1s`` + PLA at
        ``slip.slot = 0.1125`` / ``slip.radial = 0.11``
        (sweep: ``tmp/print_concave_sweep_2.py``).  Best-current-evidence
        on one calibrated FDM stack — override per-instance for other
        printers.
    """

    # ── Hole-specific corner radius defaults ───────────────────────────────
    DEFAULT_CONVEX_RADIUS: float = 0  # Convex junction (arm tip meets flat side)
    # 0.3 validated 2026-05-28 on bambu_p1s + PLA (slip.slot=0.1125,
    # slip.radial=0.11); was 0.6 pre-2026-05-28 — see
    # tmp/print_concave_sweep_2.py.  See also docs/lego-technic.md
    # §"Concave-corner blowout — verified adequate" and
    # .agents/plans/2026-05-28-concave-radius-default_design.md.
    DEFAULT_CONCAVE_RADIUS: float = 0.3  # Concave inner corner (valley between arms)

    # Cutter is built flush by construction; per-class through/blind policy
    # is degenerate for this class (no extra entry/terminal overcut).
    _THROUGH: bool = False

    def __init__(
        self,
        depth: float,
        fit: str = "slip",
        profile: ToleranceProfile | None = None,
        convex_radius: float = DEFAULT_CONVEX_RADIUS,
        concave_radius: float = DEFAULT_CONCAVE_RADIUS,
    ):
        self.depth = depth
        self.convex_radius = convex_radius
        self.concave_radius = concave_radius

        profile = profile or get_profile()
        # Pick the radial allowance off the requested fit grade.
        # ``fit`` is one of "free" / "slip" / "press" → maps directly to
        # the matching FitGrade on the nested ``ToleranceProfile``.
        grade = getattr(profile, fit)

        # AXLE_HOLE_* are fixed real-Lego nominals (no clearance baked in),
        # so the fit grade is applied as a plain absolute clearance —
        # matching the Bearing / magnets / clearance-hole pattern.
        # ``grade.radial`` is half-extra-material on diameter, so the
        # diametrical/width features each widen by 2 * grade.radial.
        self.TIP_TO_TIP = AXLE_HOLE_TIP_TO_TIP + (2 * grade.radial)
        # The narrow + cross slot also takes the narrow-slot allowance
        # ``grade.slot`` (additional half-width) on top of ``radial``: a
        # narrow slot prints ~2*slot tighter on FDM than the round
        # envelope. ``slot`` defaults to 0.0 (legacy-flat profiles, resin,
        # cnc) → arm reduces to nominal + 2*radial in that case.
        self.ARM_WIDTH = AXLE_HOLE_ARM_WIDTH + (2 * grade.radial) + (2 * grade.slot)

        self._solid = self._build()

    def _build(self) -> cq.Workplane:
        """Build the + cross solid using the axle hole dimensions."""
        tip = self.TIP_TO_TIP
        arm = self.ARM_WIDTH
        half_arm = arm / 2

        # Curved-tip + cross: cylinder ∩ cross mask.  Shared construction —
        # see vibe_cading.cq_utils.axle_cross_section.
        cross = axle_cross_section(tip, arm, self.depth)

        # Fillet the 4 inner concave corners first (larger radius).
        # These sit at (±half_arm, ±half_arm) in XY — select via a tight
        # central box that excludes the outer junction edges.
        if self.concave_radius > 0:
            eps = 0.01
            inner_sel = cq.selectors.BoxSelector(
                (-half_arm - eps, -half_arm - eps, -eps),
                (half_arm + eps, half_arm + eps, self.depth + eps),
            )
            cross = cross.edges(inner_sel).fillet(self.concave_radius)

        # Fillet the remaining outer convex junction edges.
        # After the concave fillet above the only remaining |Z edges are
        # the 8 outer junctions where cylinder arc meets flat arm side.
        if self.convex_radius > 0:
            cross = cross.edges("|Z").fillet(self.convex_radius)

        return cross

    def to_cutter(self, profile: ToleranceProfile | None = None) -> cq.Workplane:
        """Return the + cross cutter solid for boolean subtraction.

        The tolerance profile is consulted at constructor time (via the
        ``fit`` argument) and baked into the geometry.  The call-time
        ``profile`` argument is accepted to satisfy
        :class:`vibe_cading.mechanical.protocols.CutterProtocol` but
        does not re-resolve clearance — pass a different ``profile``
        to ``__init__`` if you need a non-default machine profile.
        """
        return self._solid

    @property
    def solid(self) -> cq.Workplane:
        """Legacy alias for :pymeth:`to_cutter` — returns the cutter solid."""
        return self._solid

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Show a depth-8 axle hole cut into a small Ø8 cylinder."""
        depth = 8.0
        hole_cutter = cls(depth=depth).to_cutter()
        main_body = cq.Workplane("XY").circle(8.0 / 2).extrude(depth)
        part = main_body.cut(hole_cutter)
        return [(part, "TechnicAxleHole demo", "tan")]
