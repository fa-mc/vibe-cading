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
from vibe_cading.lego.constants import PIN_HOLE_DIAMETER
from vibe_cading.cq_utils import cylinder
from vibe_cading.print_settings import ToleranceProfile, get_profile


# Standard Technic counterbore spec (measured from STP loose-fit file)
TECHNIC_PIN_CB_DIAMETER: float = 6.2   # outer flange / counterbore diameter
TECHNIC_PIN_CB_DEPTH: float = 1.0      # depth of each counterbore end


class TechnicPinHole:
    """Lego Technic pin hole profile.

    Builds a cylindrical cutter sized to the Technic pin *hole* dimensions,
    with optional counterbores on both ends (matching the flanged recess on
    the real part).

    Use the :pymeth:`to_cutter` method as a boolean cutter::

        from vibe_cading.lego.cutters.technic_pin_hole import TechnicPinHole

        hole = TechnicPinHole(depth=8.0)
        part = part.cut(hole.to_cutter())

    The legacy ``.solid`` accessor remains as an alias for backwards
    compatibility and is read-only.

    Through-vs-blind: this cutter is **blind** by design — the bore
    terminates exactly at the requested ``depth`` so the upper
    counterbore forms a defined-floor cavity.  A 0.01 mm entry overcut
    is baked at Z=0 so the cutter clears the host face cleanly.

    Profile awareness
    -----------------

    ``PIN_HOLE_DIAMETER`` (4.8 mm) is the **real-Lego nominal** envelope —
    no printer clearance is baked into the constant.  Printer / material
    clearance is supplied by the active
    :class:`~vibe_cading.print_settings.ToleranceProfile`:

    * The **bore** diameter is sized ``PIN_HOLE_DIAMETER + 2 *
      grade.radial`` (the round envelope), matching ``TechnicAxleHole`` /
      ``Bearing`` / ``ClearanceHole`` patterns.  ``fit`` selects the
      :class:`~vibe_cading.print_settings.FitGrade` ("slip" / "free" /
      "press"); default ``fit="slip"`` per ``docs/print-tolerances.md``
      §1 (pin-in-printed-socket = slip semantics).
    * The **counterbore** diameter is **NOT** profile-widened.  It is a
      seating surface for the real LEGO pin's flanged head (Cailliau
      6.0–6.2 mm range) — a one-time press-down-and-seat interface, not
      a sliding interface.  The default ``6.2 mm`` is already the
      loose-FDM edge of the Cailliau range; adding ``2 * slip.radial``
      on top would exceed the range and risk loss of seat.  The
      counterbore stays printer-independent at this scale.

    To tune the printed pin fit, calibrate ``slip.radial`` in
    ``print_profiles_user.json`` via ``python3 tools/calibrate.py slip``
    — not the constants.  See ``docs/print-tolerances.md`` §4.

    Parameters
    ----------
    depth:
        Total axial depth of the hole (mm).
    diameter:
        Explicit bore-diameter override (mm).  When ``None`` (the
        default) the bore is computed as ``PIN_HOLE_DIAMETER + 2 *
        profile.<fit>.radial``.  When non-``None`` the value wins
        as-is — **no profile widening is applied on top**.  This
        precedence is load-bearing for
        :class:`~vibe_cading.mechanical.tolerance_gauge.ToleranceGauge`,
        which pre-computes the exact bore it wants per column.
    counterbore_depth:
        Depth of each counterbore end cap (mm). Pass 0 to omit. Default 1.0.
    counterbore_diameter:
        Diameter of the counterbore flanges (mm). Default 6.2 mm.
        Stays at nominal — see the *Profile awareness* note above.
    fit:
        Tolerance fit grade selector — ``"slip"`` / ``"free"`` /
        ``"press"``.  Default ``"slip"`` (pin-in-socket semantics).
        Ignored when ``diameter`` is passed explicitly.
    profile:
        Manufacturing tolerance profile.  Accepts a
        :class:`~vibe_cading.print_settings.ToleranceProfile` instance,
        a string profile name (resolved via
        :func:`~vibe_cading.print_settings.get_profile`), or ``None`` to
        resolve the process-global profile lazily at construction time.
        Ignored when ``diameter`` is passed explicitly.
    """

    DEFAULT_DIAMETER: float = PIN_HOLE_DIAMETER
    DEFAULT_CB_DEPTH: float = TECHNIC_PIN_CB_DEPTH
    DEFAULT_CB_DIAMETER: float = TECHNIC_PIN_CB_DIAMETER

    # Blind cutter — terminal face exactly at ``depth``; small entry overcut.
    _THROUGH: bool = False
    _ENTRY_OVERCUT: float = 0.01

    @classmethod
    def standard(
        cls,
        depth: float,
        *,
        fit: str = "slip",
        profile: ToleranceProfile | str | None = None,
    ) -> "TechnicPinHole":
        """Factory: standard Technic pin hole with default counterbore spec.

        Forwards ``fit`` and ``profile`` through to the constructor so
        the printed bore tracks the active
        :class:`~vibe_cading.print_settings.ToleranceProfile`.  Counterbore
        defaults remain at the real-liftarm Cailliau spec.
        """
        return cls(
            depth=depth,
            diameter=None,                                # route through profile
            counterbore_depth=cls.DEFAULT_CB_DEPTH,
            counterbore_diameter=cls.DEFAULT_CB_DIAMETER,
            fit=fit,
            profile=profile,
        )

    def __init__(
        self,
        depth: float,
        diameter: float | None = None,
        counterbore_depth: float = DEFAULT_CB_DEPTH,
        counterbore_diameter: float = DEFAULT_CB_DIAMETER,
        fit: str = "slip",
        profile: ToleranceProfile | str | None = None,
    ):
        # Bore-diameter resolution — the single load-bearing formula.
        # An explicit ``diameter=`` kwarg wins as-is; the profile path is
        # only taken when the caller leaves the override at its ``None``
        # default.  This precedence is documented in the class docstring
        # and is load-bearing for tolerance_gauge.py (which sweeps the
        # radial-allowance landscape directly via explicit diameters).
        if diameter is not None:
            bore_diameter = diameter
        else:
            # ``profile`` may be a ToleranceProfile instance, a string
            # profile name, or None (lazy process-global lookup).
            if profile is None or isinstance(profile, str):
                profile = get_profile(profile) if isinstance(profile, str) else get_profile()
            # ``fit`` maps to one of FitGrade("free"|"slip"|"press") on
            # the resolved ToleranceProfile.  ``grade.radial`` is
            # half-extra-material on diameter — the bore widens by
            # ``2 * grade.radial``.  Mirrors TechnicAxleHole.TIP_TO_TIP.
            grade = getattr(profile, fit)
            bore_diameter = PIN_HOLE_DIAMETER + 2 * grade.radial

        self.depth = depth
        self.diameter = bore_diameter
        # Counterbore stays at nominal — printer-independent seating
        # surface; see the *Profile awareness* note in the class docstring.
        self.counterbore_depth = counterbore_depth
        self.counterbore_diameter = counterbore_diameter
        self._solid = self._build()

    def _build(self) -> cq.Workplane:
        # Standard bore strictly bounded to the requested depth.
        # We use a small overcut at the bottom (Z=0) so it cuts cleanly
        # when placed flush against a face, but it ends exactly at self.depth.
        overcut = self._ENTRY_OVERCUT
        bore = cylinder(self.diameter / 2, self.depth + overcut, center=(0, 0, -overcut))

        if self.counterbore_depth > 0:
            cb_bottom = cylinder(
                self.counterbore_diameter / 2,
                self.counterbore_depth + overcut,
                center=(0, 0, -overcut)
            )
            # Top counterbore stops exactly at self.depth, forming the blind cavity
            cb_top = cylinder(
                self.counterbore_diameter / 2,
                self.counterbore_depth,
                center=(0, 0, self.depth - self.counterbore_depth),
            )
            bore = bore.union(cb_bottom).union(cb_top)

        return bore

    def to_cutter(self, profile: ToleranceProfile | None = None) -> cq.Workplane:
        """Return the cutter solid for boolean subtraction.

        The Technic pin hole's geometry is fully defined by its
        constructor parameters; the ``profile`` argument is accepted to
        satisfy :class:`vibe_cading.mechanical.protocols.CutterProtocol`
        but currently does not affect output.  (Tolerance bake-in would
        be a future deepening — apply ``profile.free.radial`` to the
        bore diameter for an explicit slip/press fit.)
        """
        return self._solid

    @property
    def solid(self) -> cq.Workplane:
        """Legacy alias for :pymeth:`to_cutter` — returns the cutter solid."""
        return self._solid

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Show a depth-8 standard pin hole cut into a small Ø8 cylinder."""
        depth = 8.0
        hole_cutter = cls.standard(depth=depth).to_cutter()
        main_body = cq.Workplane("XY").circle(8.0 / 2).extrude(depth)
        part = main_body.cut(hole_cutter)
        return [(part, "TechnicPinHole demo", "tan")]
