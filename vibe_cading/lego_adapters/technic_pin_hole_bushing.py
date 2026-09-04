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

import warnings
from typing import Literal

import cadquery as cq

from vibe_cading.lego.constants import BEAM_THICKNESS, PIN_HOLE_DIAMETER
from vibe_cading.lego.cutters.technic_pin_hole import (
    TECHNIC_PIN_CB_DEPTH,
    TECHNIC_PIN_CB_DIAMETER,
)
from vibe_cading.cq_utils import cylinder

# Default flange OD sits on the shoulder between the through-hole and the
# standard Technic pin-hole counterbore (TECHNIC_PIN_CB_DIAMETER = 6.2 mm,
# TECHNIC_PIN_CB_DEPTH = 1.0 mm on real Lego beams and this codebase's
# TechnicPinHole.standard()): a flange wider than PIN_HOLE_DIAMETER (4.8 mm)
# cannot pass through the hole itself, so it catches on that step, while a
# flange narrower than the counterbore diameter sinks below the beam's flat
# outer face instead of standing proud on top of it. The midpoint gives even
# margin against both boundaries.
_FLANGE_OD_DEFAULT = (PIN_HOLE_DIAMETER + TECHNIC_PIN_CB_DIAMETER) / 2
from vibe_cading.mechanical.holes import _THROUGH_OVERCUT
from vibe_cading.mechanical.screws.metric import MetricMachineScrew
from vibe_cading.print_settings import ToleranceProfile, get_profile


# Per-value glosses for the engine_api `value_doc` field (schema 1.1).
# This class carries TWO independent `fit`-shaped params with OPPOSITE sign
# conventions, so both need explicit glosses:
#
# `fit` (OD) — the codebase's first MALE `fit` consumer. Every other
# ``fit: Literal["free", "slip", "press"]`` site (TechnicPinHole,
# TechnicAxleHole, LegoTechnicLLiftarm, PerpendicularHolesLiftarm,
# TechnicPinHoleBushing.bore_fit below) sizes a printed VOID against a
# rigid real part, so "press" reads as the tightest *hole*. `fit` instead
# sizes a printed PEG against a rigid real Lego pin hole, so the per-grade
# meaning is inverted: "press" is the tightest *peg* (largest OD, most
# material removed from the allowance budget), "free" is the loosest *peg*
# (smallest OD). An LLM/engine-api client reading only the allowed_values
# list would otherwise infer the female (hole-widening) semantics from the
# sibling rows and get the direction backwards.
#
# `bore_fit` (bore) — ordinary FEMALE/void semantics, matching every other
# `fit` site in the codebase (the bore is a hole that receives the M3
# screw shaft, not a peg pressed into anything).
_VALUE_DOC = {
    "TechnicPinHoleBushing.fit": {
        "free":  "loosest peg — smallest OD, generous clearance in the real pin hole",
        "slip":  "middle grade — snug peg, slides into the pin hole with light resistance "
                 "(default; measured to match this fit's real-world behavior — see class docstring)",
        "press": "tightest peg — largest OD; at shipped radial values this still measures as "
                 "a snug fit, not genuine interference — calibrate a negative press.radial for "
                 "true interference (scopes the OUTER diameter only; see bore_fit for the bore)",
    },
    "TechnicPinHoleBushing.bore_fit": {
        "free":  "loosest bore — most clearance around the M3 screw shaft",
        "slip":  "middle grade — snug clearance around the M3 screw shaft (default: "
                 "still a free pass-through, just less rattle than 'free')",
        "press": "tightest bore — least clearance around the M3 screw shaft; a fit "
                 "this tight risks binding on the screw, not just removing rattle",
    },
}


class TechnicPinHoleBushing:
    """Plain round bushing that fits into a real Lego Technic pin hole.

    A two-cylinder union (barrel + optional retaining flange) with a single
    clearance through-bore, bridging a real Lego Technic pin hole
    (``PIN_HOLE_DIAMETER`` = 4.8 mm) to a machine screw — M3 by default, or
    any size via ``bore_nominal_diameter`` (e.g.
    ``MetricMachineScrew.from_size("M2", length=1.0).clearance_diameter``
    for an M2 variant). Every diameter is derived from ``PIN_HOLE_DIAMETER``
    / the screw's clearance catalog entry and the active
    :class:`~vibe_cading.print_settings.ToleranceProfile` — nothing here is
    a hardcoded magic number.

    Origin / datum
    ---------------
    ``(0, 0, 0)`` is the boundary between the barrel and the optional
    flange, with the bore axis on ``+Z``. ``length`` is the TOTAL axial
    span of the whole part — barrel plus flange combined, when the flange
    is enabled — chosen so that a caller sets ``length`` to the target
    insertion depth (e.g. one beam thickness) and gets exactly that depth
    back, regardless of the ``flange`` flag. Concretely: the optional
    flange occupies ``Z in [-flange_thickness, 0]`` (nested inside the
    real beam's own counterbore recess, see *Flange* below — it is NOT
    extra length beyond the beam), and the barrel occupies
    ``Z in [0, length - flange_thickness]`` when ``flange=True`` or
    ``Z in [0, length]`` when ``flange=False``. Either way the total
    Z-span (``bbox.zmax - bbox.zmin``) equals ``length``.

    **This means the barrel's own Z-extent is NOT invariant under the**
    **``flange`` flag** — toggling ``flange`` off at a fixed ``length``
    makes the barrel ``flange_thickness`` mm longer, because that length
    is no longer reserved for the nested flange. This is deliberate: a
    caller reasons about ``length`` as "how deep a hole this bushing
    fills," and that quantity — not the barrel-only length — is what must
    stay invariant against the beam it is sized for.

    Outer-diameter formula (male fit — sign is NEGATED vs. female holes)
    ----------------------------------------------------------------------
    ``OD = PIN_HOLE_DIAMETER - 2 * getattr(profile, fit).radial``, default
    ``fit="slip"`` (see *Why the default is `slip`, not `press`* below).
    The sign is the opposite of every existing ``fit`` consumer in this
    codebase (e.g. ``TechnicPinHole``'s ``PIN_HOLE_DIAMETER + 2 *
    grade.radial``), and that is correct: every existing consumer sizes a
    printed VOID against a rigid real part, so "widen the hole" is "add
    material removal". This class sizes a printed PEG against a rigid
    real hole, so "add material removal" instead *shrinks* the peg —
    hence the ``-`` sign. Subtraction is also the only sign that preserves
    grade monotonicity (shipped ``fdm_standard``: ``press.radial=0.04 <
    slip.radial=0.05 < free.radial=0.15``, so subtraction gives ``press``
    OD (4.72) > ``slip`` OD (4.70) > ``free`` OD (4.50) — "press" is
    always the largest / tightest peg, matching
    ``docs/print-tolerances.md``, regardless of which grade the *default*
    happens to be. Addition would invert this ordering.

    **Why the default is `slip`, not `press` — measured, not assumed.**
    An earlier revision defaulted to ``fit="press"``, reasoning that a
    friction-fit bushing *should* want the tightest grade. A printed and
    measured M3 unit (PETG, `fdm_standard`-equivalent calibration)
    contradicted that: the OD landed within measurement error of the
    *modelled* 4.72 mm target — 0.08 mm **under** the 4.8 mm nominal pin
    hole — and it spun freely, exactly what "under nominal" predicts.
    ``press`` at the shipped radial values does not model genuine
    interference on this printer; it models a fit that behaves like
    ``slip``. Rather than ship a `press` label a calibrated user will
    reliably find loose, the default is `slip` — the grade whose *name*
    matches the measured behavior. A user who wants to chase true
    interference can still pass ``fit="press"`` explicitly and calibrate
    a **negative** ``press.radial`` (see
    :func:`~vibe_cading.print_settings.get_profile`) — but that is now an
    opt-in, not the default promise.

    Bore
    ----
    The bore is an M3 clearance hole sized as
    ``bore_nominal_diameter + 2 * getattr(profile, bore_fit).radial``
    (ordinary female/void sign convention — unlike ``fit`` above, this is
    NOT inverted). It is cut with a hand-rolled through-hole cutter
    (same ``_THROUGH_OVERCUT`` convention as
    :class:`~vibe_cading.mechanical.holes.ClearanceHole`, but with a
    caller-selectable grade — ``ClearanceHole`` itself hardcodes
    ``free.radial`` with no override), never
    ``MetricMachineScrew.to_cutter()``, which delegates to a counterbore
    cutter that would blow a Ø5.5 mm x 3.0 mm-deep crater through this
    part's thin flange and barrel.

    ``fit`` and ``bore_fit`` are INDEPENDENT — ``fit`` governs the OD only,
    ``bore_fit`` governs the bore only. Default ``bore_fit="slip"``: a
    screw must still pass through *freely* (this is a clearance hole, not
    a thread), but "slip" removes the rattle "free" leaves at the default
    M3 nominal. At defaults (OD 4.72, bore ``3.2 + 2*0.05`` = 3.30 on
    ``fdm_standard``) this leaves a 0.71 mm wall — a user needing a
    thicker wall still calibrates the profile or ``bore_nominal_diameter``
    downward, exactly as before, just against ``bore_fit``'s grade instead
    of an unconditional ``free``.

    ``bore_nominal_diameter``, when given, replaces only the *nominal*
    catalog diameter (e.g. M3's 3.2 -> M4's 4.3); profile widening via
    ``bore_fit``'s grade always applies on top — unlike ``TechnicPinHole``'s
    ``diameter=`` override, which wins as-is with no profile widening (that
    carve-out exists solely for ``ToleranceGauge``, which has no analogue
    here).

    Flange
    ------
    A single optional retaining flange (default enabled, Ø5.5 x 0.8 mm)
    sits strictly at ``Z <= 0``, nested inside the real beam's own
    counterbore recess — its thickness is carved out of ``length``, not
    added on top of it (see *Origin / datum* above). The default OD is
    the midpoint between
    ``PIN_HOLE_DIAMETER`` (4.8 mm) and the standard Technic pin-hole
    counterbore diameter (``TECHNIC_PIN_CB_DIAMETER`` = 6.2 mm, from
    :mod:`vibe_cading.lego.cutters.technic_pin_hole`): wide enough that it
    cannot pass through the pin hole itself (it catches on the step
    between the through-hole and the counterbore), but narrow enough that
    it sinks *below* the beam's flat outer face into that counterbore
    recess rather than standing proud on top of it. The default
    ``flange_thickness`` (0.8 mm) is likewise kept under
    ``TECHNIC_PIN_CB_DEPTH`` (1.0 mm) so the flange face never protrudes
    past the beam's outer face. It is deliberately NOT profile-widened —
    it is a free-standing face touching nothing dimensionally critical, and
    the fit against the counterbore step is not itself a friction fit.

    Parameters
    ----------
    length:
        TOTAL axial length of the whole part (mm) — barrel plus flange
        combined when ``flange=True`` (the flange is nested within this
        span, not additional to it; see *Origin / datum* above). Must be
        strictly greater than ``flange_thickness`` when ``flange=True``.
        Default ``BEAM_THICKNESS`` (7.8 mm) — one beam's worth of
        insertion depth.
    fit:
        Tolerance fit grade selector for the barrel OUTER diameter only —
        ``"free"`` / ``"slip"`` / ``"press"``. Default ``"slip"`` — see
        *Why the default is `slip`, not `press`* above; pass
        ``fit="press"`` (with a calibrated negative ``press.radial``) if
        you want to chase genuine interference instead. Independent of
        ``bore_fit`` (see *Bore* above).
    bore_fit:
        Tolerance fit grade selector for the BORE only — ``"free"`` /
        ``"slip"`` / ``"press"``. Default ``"slip"`` (snug clearance
        around the M3 screw shaft, no rattle). Ordinary female/void sign
        convention (NOT inverted like ``fit``). Independent of ``fit``.
    flange:
        Whether to add the retaining flange below ``Z=0``. Default
        ``True``.
    flange_od:
        Flange outer diameter (mm). Must be strictly greater than the
        barrel OD or it cannot act as an axial stop. Default is the
        midpoint between ``PIN_HOLE_DIAMETER`` and
        ``TECHNIC_PIN_CB_DIAMETER`` (5.5 mm) — see *Flange* above.
    flange_thickness:
        Flange axial thickness (mm). Must be strictly positive when
        ``flange=True``. Default 0.8 mm, kept under
        ``TECHNIC_PIN_CB_DEPTH`` (1.0 mm) — see *Flange* above.
    bore_nominal_diameter:
        Explicit override for the bore's *nominal* (pre-profile) diameter
        (mm). When ``None`` (the default), the nominal is
        ``MetricMachineScrew.from_size("M3").clearance_diameter`` (3.2 mm).
        Profile widening via ``free.radial`` always applies on top of
        whichever nominal is in effect.
    profile:
        Manufacturing tolerance profile. Accepts a
        :class:`~vibe_cading.print_settings.ToleranceProfile` instance, a
        string profile name (resolved via
        :func:`~vibe_cading.print_settings.get_profile`), or ``None`` to
        resolve the process-global default profile (honouring the
        ``PRINT_PROFILE`` env override).
    """

    def __init__(
        self,
        length: float = BEAM_THICKNESS,
        fit: Literal["free", "slip", "press"] = "slip",
        bore_fit: Literal["free", "slip", "press"] = "slip",
        flange: bool = True,
        flange_od: float = _FLANGE_OD_DEFAULT,
        flange_thickness: float = 0.8,
        bore_nominal_diameter: float | None = None,
        profile: ToleranceProfile | str | None = None,
    ) -> None:
        # Hoisted ahead of all other construction so a degenerate `length`
        # fails fast with a named error instead of propagating into the
        # MetricMachineScrew factory call below (see N2 in the Phase B TL
        # review — the factory happens to tolerate a negative length, so
        # this guard was previously correct only by that incidental luck).
        if length <= 0:
            raise ValueError(f"length must be > 0, got {length}")
        if flange and flange_thickness <= 0:
            raise ValueError(
                f"flange_thickness must be > 0 when flange=True, got {flange_thickness}"
            )
        # `length` is the TOTAL span (flange nested within it, not added on
        # top) — see class docstring's Origin/datum section — so the flange
        # cannot consume the whole span and leave nothing for the barrel.
        if flange and length <= flange_thickness:
            raise ValueError(
                f"length ({length}) must be > flange_thickness ({flange_thickness}); "
                "the flange is nested within the total length, not additional to it"
            )

        # ``profile`` may be a ToleranceProfile instance, a string profile
        # name, or None (lazy process-global lookup) — mirrors
        # TechnicPinHole's profile-resolution pattern.
        if profile is None or isinstance(profile, str):
            prof = get_profile(profile) if isinstance(profile, str) else get_profile()
        else:
            prof = profile

        self.length = length
        self.fit = fit
        self.bore_fit = bore_fit
        self.flange = flange
        self.flange_od = flange_od
        self.flange_thickness = flange_thickness
        self._profile = prof

        # Informational only (not a construction-time guard): a flange
        # thicker than the standard counterbore depth would stand proud of
        # the beam's outer face instead of sinking into the recess, which
        # defeats the point of narrowing flange_od to fit that recess.
        if flange and flange_thickness > TECHNIC_PIN_CB_DEPTH:
            warnings.warn(
                f"flange_thickness ({flange_thickness}) exceeds the standard "
                f"Technic pin-hole counterbore depth ({TECHNIC_PIN_CB_DEPTH}); "
                "the flange will stand proud of the beam's outer face instead "
                "of sinking into the counterbore recess.",
                stacklevel=2,
            )

        # D1 — male fit: subtract, don't add. Every existing `fit` consumer
        # in this codebase sizes a printed VOID (add 2*radial to widen a
        # hole); this is a printed PEG entering a rigid real hole, so
        # removing material from the printed side instead SHRINKS the OD.
        # Subtraction is also the only sign under which grade monotonicity
        # holds (press > slip > free OD) — see class docstring.
        grade = getattr(prof, fit)
        self.od = PIN_HOLE_DIAMETER - 2 * grade.radial

        # `length` is already the total span (flange included when
        # enabled) — see Origin/datum in the class docstring — so the bore
        # depth is just `length`, and the barrel's own Z-extent is
        # `length` minus whatever the nested flange consumes.
        self.total_height = length
        self.barrel_length = length - flange_thickness if flange else length

        # `.clearance_diameter` is a length-independent catalog lookup —
        # `length=` is required by the factory signature but no screw
        # geometry is actually built here, so its value is irrelevant.
        if bore_nominal_diameter is not None:
            self.bore_nominal = bore_nominal_diameter
        else:
            self.bore_nominal = MetricMachineScrew.from_size(
                "M3", length=self.total_height
            ).clearance_diameter

        # --- Degenerate-geometry guards (construction-time, named) ---
        # (length / flange_thickness guards are hoisted above — see there.)
        if flange and flange_od <= self.od:
            raise ValueError(
                f"flange_od ({flange_od}) must be > barrel OD ({self.od}) "
                "for the flange to act as an axial stop"
            )
        # Informational only, mirrors the flange_thickness warning above:
        # a flange this wide can no longer sink into the counterbore recess.
        if flange and flange_od >= TECHNIC_PIN_CB_DIAMETER:
            warnings.warn(
                f"flange_od ({flange_od}) meets or exceeds the standard "
                f"Technic pin-hole counterbore diameter ({TECHNIC_PIN_CB_DIAMETER}); "
                "the flange will land on the beam's flat outer face instead "
                "of sinking into the counterbore recess.",
                stacklevel=2,
            )
        # As-cut bore diameter: widened by bore_fit's grade (D2/bore_fit),
        # never by `fit` (the OD's grade) — the two are independent knobs.
        as_cut_bore = self.bore_nominal + 2 * getattr(prof, bore_fit).radial
        if as_cut_bore >= self.od:
            raise ValueError(
                f"as-cut bore diameter ({as_cut_bore}) must be < barrel OD "
                f"({self.od}); this bore_nominal_diameter would consume the "
                "entire barrel wall"
            )

        self._solid = self._build()

    def _build(self) -> cq.Workplane:
        """Construct the barrel (+ optional flange) and cut the through-bore."""
        part = cylinder(self.od / 2, self.barrel_length, center=(0, 0, 0))

        if self.flange:
            flange_disc = cylinder(
                self.flange_od / 2,
                self.flange_thickness,
                center=(0, 0, -self.flange_thickness),
            )
            part = part.union(flange_disc)

        # Hand-rolled through-bore cutter (same _THROUGH_OVERCUT convention
        # as ClearanceHole.to_cutter(), but with a caller-selectable grade
        # via bore_fit — ClearanceHole itself hardcodes free.radial with no
        # override). Untranslated: spans -(total_height+overcut) to
        # +overcut about its own Z=0 origin, engulfing the whole body
        # without needing a translation.
        bore_radius = self.bore_nominal / 2.0 + getattr(self._profile, self.bore_fit).radial
        overcut = _THROUGH_OVERCUT
        bore_cutter = (
            cq.Workplane("XY", origin=(0, 0, -(self.total_height + overcut)))
            .circle(bore_radius)
            .extrude(self.total_height + 2 * overcut)
        )
        part = part.cut(bore_cutter)

        assert len(part.solids().vals()) == 1, "Expected single solid, got multiple pieces"
        return part

    @property
    def solid(self) -> cq.Workplane:
        return self._solid
