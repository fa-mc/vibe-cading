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

"""Arrma 223S-platform ESC/receiver-box mount plate (BLX185 3S replacement).

Reverse-engineered from ``tmp/BLX185_3s_ReceiverBox_Mount.stl`` (mesh-only,
no STEP available) — see
``docs/design_plans/2026-08-31-arrma-223s-receiver-mount_design.md`` for the
full measurement log and reconciliation checklist.

Coordinate system
------------------
Z = 0     : the shared chassis-mating face.  The main body (plate) slab
            extrudes the full ``body_thickness`` upward from here (Z ∈
            [0, body_thickness]), where ``body_thickness`` is now a
            *derived* value = ``base_thickness + accessory_thickness`` —
            see the 2026-09-01 correction note below (this supersedes the
            2026-09-01 resize note's original independent-parameter
            contract, which the orchestrator had mis-specified). The arm
            and south ear occupy only the top ``accessory_thickness`` band
            of that same plate slab (Z ∈ [base_thickness, body_thickness]),
            flush with its top face — they do not extend past it.
Local X=0 : main body horizontal centerline.
Local Y=0 : main body's "north" edge — the edge the arm projects from.
            The main body spans Y in [-body_length, 0]; the south ear
            projects further past Y = -body_length.

.. note::
   **Correction (2026-08-31):** the previous implementation put the body's
   footprint at 58.5x40.86 mm and modelled each ear as a plain 9.0 mm OD
   circular boss. Both were wrong. A human reviewer caught the ear shape
   ("the shape is wrong ... it's like an ear"); re-tracing the STL's Z=3
   boundary polyline (see the design brief's "Corrections during
   measurement" §3) showed the true footprint is 58.5x46.00 mm and each ear
   is a "stadium"/slot lug — two parallel straight walls tangent to a
   semicircular cap, not a free-standing circle. See
   ``docs/design_plans/2026-08-31-arrma-223s-receiver-mount_design.md`` §1/§3
   for the full re-derivation.

.. note::
   **Correction (2026-09-01):** four further human corrections. (1) Ear
   fasteners are M2.5 **pan-head**, not flat-head. (2) The arm tip cap is
   now a flush ``ARM_TIP_R = ARM_WIDTH / 2.0`` semicircle (was a
   free-floating ``5.0`` literal that necked in from the shaft's full
   width). (3) The arm-root-to-plate fillet's *construction* — not just
   its docstring — was wrong: it was tangent to an artificial mid-height
   line anchored to the ear's own edge rather than to the plate's Y=0
   edge directly (confirmed by section-slicing the built solid; see
   ``_arm_root_fillet``). (4) Both motor-mount holes now cut a standard
   M3 pan-head cutter from the top face; the LEFT hole additionally keeps
   an as-measured 7.0 mm OD x 2.0 mm deep mesh-fidelity relief pocket on
   the bottom face (design brief §5, Open Question 3). See
   ``docs/design_plans/2026-08-31-arrma-223s-receiver-mount_design.md``
   §3-§5 for the full re-derivation.

.. note::
   **User-specified resize (2026-09-01) — supersedes the reference
   measurements above and the original Z-stacking contract.** The user
   found the physical reference part is the wrong SIZE for their vehicle
   and specified five overriding dimension/architecture changes directly
   — these are NOT re-derived from the STL and intentionally override it
   where the two disagree:

   1. **Plate width (north-south, ``BODY_LENGTH``) is now 38.00 mm** (was
      46.00). The north edge stays pinned at local Y=0, so the plate now
      spans Y in [-38, 0]. East-west width (``BODY_WIDTH``) and corner
      fillets are unchanged.
   2. **The north ear is removed entirely.** Its M2.5 fastener becomes a
      hole in the main plate body at local ``HOLE1_CENTER`` = (1.026,
      -5.0) — 5 mm south (inward) of the north edge, on the old ear's
      centerline X. **Revised 2026-09-02** (was a flat-head countersink):
      it is now a **round-head counterbore**, sized to the M2.5 pan head.
      The screw is still inserted from below, but its head is no longer
      seated flush in the bottom face — a head-diameter bore runs the
      whole ``base_thickness`` so the head passes freely up through it,
      and the screw binds only on the shoulder at Z = ``base_thickness``,
      clamping just the top ``accessory_thickness`` band. That mirrors the
      south ear's plain bore, which likewise clamps only its accessory
      band. See ``_hole1_counterbore_cutter`` (a 180 deg X-axis flip of a
      ``CounterboreHole``, which normally opens at its own local Z=0 and
      sinks toward -Z).
   3. **The south ear's hole is exactly 38.00 mm from hole 1** (local Y =
      -43.0, i.e. ``HOLE1_CENTER`` minus ``HOLE_SPACING`` along Y). Its
      stadium-lug outline is unchanged in shape/radius. Its hole is now a
      **plain M2.5 clearance through-hole — no countersink, no
      counterbore, no recess of any kind** (previously a pan-head
      recess). See ``_south_ear_clearance_cutter``.
   4. **The arm's XY outline is unchanged** (12 mm wide shaft, R6.0 flush
      tip, R9.06 root-to-plate fillet).
   5. **Z-stacking contract — CORRECTED 2026-09-01 (this note supersedes
      item 5 as originally written; the orchestrator had mis-specified
      it as a perched, cantilevered accessory layer).** The accessory
      thickness is added ON TOP OF the base thickness, not stacked as a
      separate layer floating over open air: ``body_thickness`` is now a
      *derived*, read-only property = ``base_thickness + accessory_thickness``
      (12.0 mm at the defaults of 7.0 + 5.0). The **plate itself is the
      full ``body_thickness``** (Z ∈ [0, body_thickness]) — the arm and
      south ear are ``accessory_thickness``-tall tabs occupying only the
      plate's own top band (Z ∈ [base_thickness, body_thickness]),
      flush with the plate's own top face. Z=0 remains the chassis-mating
      datum; the overall envelope is Z ∈ [0, 12] at defaults. Relative to
      the (wrong) perched-layer version this moved the plate's own
      thickness from just the base value up to the full ``body_thickness``.

      Because this makes the arm and south ear butt against the plate's
      own full-height vertical side wall (real 2D contact area = accessory
      width x accessory_thickness) rather than touching it only along a
      degenerate zero-area edge line, the large "bonding overlap" XY
      extensions this note previously described (``ARM_PLATE_OVERLAP`` =
      9.0 mm, ``EAR_PLATE_OVERLAP`` = 5.0 mm) are no longer needed and have
      been removed. Only a small (0.02 mm) boolean-robustness overlap
      remains, matching the project's existing convention for a flush
      union join (see ``vibe_cading/rc/hex_hub_bearing/hex_hub_with_bearing.py``
      and ``vibe_cading/lego_adapters/axle_hex_hub/axle_hex_hub_adapter.py``,
      both of which document the identical "known OCCT coincident-face
      boolean reliability risk, not a fit-grade tolerance" rationale).

      **Print-support implication (revised):** the arm and south ear are
      no longer cantilevered over open air across their whole span — where
      they meet the plate, they now rest on solid plate material below
      them. Only the portions that extend beyond the plate's own XY
      footprint (most of the arm's shaft/tip, the south ear's semicircular
      cap) remain unsupported tabs; printing in the native orientation
      will still want support material under those specific overhangs, but
      the blanket "overhangs open air" statement from the prior note no
      longer applies to the whole accessory layer.

``base_thickness`` and ``accessory_thickness`` are the two independent
constructor parameters; ``body_thickness`` is derived from them
(``base_thickness + accessory_thickness``) and is exposed only as a
read-only property, not a constructor argument. The plate slab extrudes
the full ``body_thickness`` from Z=0; the arm and south ear extrude
``accessory_thickness`` starting at Z=``base_thickness`` (see the
2026-09-01 correction note above for the full rationale). Z=0 remains the
fixed chassis-mating datum regardless of either parameter's value.
"""

from __future__ import annotations

import cadquery as cq

from vibe_cading.cq_utils import cylinder
from vibe_cading.mechanical.holes import CounterboreHole
from vibe_cading.mechanical.screws.metric import METRIC_SIZES, MetricMachineScrew
from vibe_cading.print_settings import get_profile

# ── Main body (measured; corrected 2026-08-31 — footprint was wrongly
# 58.5x40.86; length overridden by the user 2026-09-01, see module note) ────
BODY_WIDTH: float = 58.5
BODY_LENGTH: float = 38.00  # user-specified 2026-09-01 (was 46.00, then 40.86)
BODY_CORNER_R: float = 5.0

# ── Default thicknesses (user-specified; revised 2026-09-02 from 6.0/4.0 —
# no longer derived from the reference part's single-slab REF_THICKNESS; see
# the module's Z-stacking contract note). ``body_thickness`` is NOT a default
# here — it is a derived, read-only property (base + accessory); only these
# two independent inputs have defaults. ────────────────────────────────────
DEFAULT_BASE_THICKNESS: float = 7.0
DEFAULT_ACCESSORY_THICKNESS: float = 5.0

# ── Back recess (measured; flush with the body's right edge) ───────────────
RECESS_WIDTH: float = 12.1
RECESS_LENGTH: float = 18.0
RECESS_DEPTH: float = 2.0
RECESS_TOP_INSET: float = 4.493  # inset from the body's top (Y=0) edge

# ── Motor-mount holes in the main body (measured; both unconditional per
# the human's "keep faithfully" resolution — design brief §5, Open Q2;
# hybrid M3-standard-vs-mesh resolution per Open Question 3).
#
# ── M3 CHASSIS-mounting holes: the plate bolts down to the chassis rail
# through these. Distinct from the M2.5 MOTOR-mounting pair below
# (HOLE1_CENTER / SOUTH_EAR_CENTER), which the motor itself bolts to.
# These were originally named `MOTOR_*` from the reference-teardown rounds,
# which inverted the two roles; renamed 2026-09-01. Defined here (above the
# M2.5 pair) because the motor hole's X is *derived* from these two centers
# — see below. ─────────────────────────────────────────────────────────────
CHASSIS_LEFT_CENTER: tuple[float, float] = (-23.752, -18.05)
CHASSIS_LEFT_RELIEF_OD: float = 7.0
CHASSIS_LEFT_RELIEF_DEPTH: float = 2.0
CHASSIS_RIGHT_CENTER: tuple[float, float] = (21.752, -18.05)

# ── Hole 1 (former north-ear fastener, now a hole in the plate body itself
# — see module note item 2). X position user-specified 2026-09-01: derived
# from the real motor's dimensions and its centering between the two M3
# chassis-mounting holes above, rather than a bare measured literal, so it
# survives any future change to the M3 hole positions. ─────────────────────
MOTOR_BODY_LENGTH: float = 37.0  # real motor length along X, mm
MOTOR_HOLE_FROM_LEFT_EDGE: float = 16.0  # motor's mounting-hole offset from its own left edge
MOTOR_HOLE_FROM_RIGHT_EDGE: float = 21.0  # cross-check only, not an independent input (16 + 21 = 37)
assert abs(
    MOTOR_HOLE_FROM_LEFT_EDGE + MOTOR_HOLE_FROM_RIGHT_EDGE - MOTOR_BODY_LENGTH
) < 1e-9, (
    "Motor hole-offset constants are inconsistent: "
    f"{MOTOR_HOLE_FROM_LEFT_EDGE} + {MOTOR_HOLE_FROM_RIGHT_EDGE} != {MOTOR_BODY_LENGTH}"
)

# The motor is centered between the two M3 chassis-hole centers (equal
# clearance from each M3 hole to the nearest motor edge), so its X span is
# derived from their midpoint.
_M3_MIDPOINT_X: float = (CHASSIS_LEFT_CENTER[0] + CHASSIS_RIGHT_CENTER[0]) / 2.0  # -1.0
_MOTOR_X_LO: float = _M3_MIDPOINT_X - MOTOR_BODY_LENGTH / 2.0  # -19.5
_MOTOR_X_HI: float = _M3_MIDPOINT_X + MOTOR_BODY_LENGTH / 2.0  # +17.5
MOTOR_HOLE_X: float = _MOTOR_X_LO + MOTOR_HOLE_FROM_LEFT_EDGE  # -3.5; shared by hole 1 and the south ear
assert abs(MOTOR_HOLE_X - (_MOTOR_X_HI - MOTOR_HOLE_FROM_RIGHT_EDGE)) < 1e-9, (
    "MOTOR_HOLE_X derivation mismatch between left-edge and right-edge cross-checks"
)
HOLE1_Y: float = -5.0  # 5 mm south (inward) of the plate's north edge
HOLE1_CENTER: tuple[float, float] = (MOTOR_HOLE_X, HOLE1_Y)
HOLE_SPACING: float = 38.0  # hole 1 -> south-ear hole center distance, along local Y

# ── South ear (measured; stadium-lug shape unchanged, hole hardware and
# position overridden by the user 2026-09-01 — see module note item 3) ─────
# Each ear = a rectangle (width = 2*radius) whose far short edge sits on the
# arc center, unioned with a circle of that same radius centered there. The
# circle's near half is redundant with the rectangle (harmless under union);
# its far half is the semicircular cap. The two straight walls meet the
# body's flat edge at a sharp, unfilleted 90 degree corner (no fillet
# observed in the mesh at current resolution).
EAR_BOTTOM_ARC_R: float = 4.4943
SOUTH_EAR_HOLE_Y: float = HOLE1_Y - HOLE_SPACING  # -43.0
SOUTH_EAR_CENTER: tuple[float, float] = (MOTOR_HOLE_X, SOUTH_EAR_HOLE_Y)
EAR_HOLE_CLEARANCE_D: float = METRIC_SIZES["M2.5"]["clearance"]  # plain clearance bore, no recess (module note item 3)

# Small boolean-robustness overlap for the south ear's union onto the
# plate's top band — NOT a bonding-area fix (the ear now butts against the
# plate's own full-height vertical side wall over a real area = ear width x
# accessory_thickness, so no XY footprint extension is needed for that).
# This is the same "two solids sharing an exactly coincident face is an
# OCCT boolean reliability risk" margin used elsewhere in the project — see
# ``vibe_cading/rc/hex_hub_bearing/hex_hub_with_bearing.py`` and
# ``vibe_cading/lego_adapters/axle_hex_hub/axle_hex_hub_adapter.py``
# (``overlap_eps = 0.02``), not a fit-grade/tolerance-profile value.
EAR_UNION_OVERLAP_EPS: float = 0.02

# ── Extended arm (measured; tip/root CORRECTED 2026-09-01 — see design
# brief §4; XY outline unaffected by this round's resize) ──────────────────
ARM_WIDTH: float = 12.0
ARM_X_CENTER: float = BODY_WIDTH / 2.0 - ARM_WIDTH / 2.0  # flush with body's right edge
# Derived, not a free-floating literal (the old ARM_TIP_R = 5.0 hardcode
# is exactly how the tip cap drifted out of flush with the shaft in the
# first place — design brief §4 "Parametric note for the Developer").
# A flush semicircular cap tangent to both shaft walls with no neck is a
# deliberate simplification of the mesh's true flat-topped double-fillet
# tip (see the brief's "Corrections during measurement" §4).
ARM_TIP_R: float = ARM_WIDTH / 2.0
ARM_TIP_CENTER_Y: float = 28.0
ARM_ROOT_BLEND_R: float = 9.06
ARM_HOLE1_D: float = 3.202
ARM_HOLE1_CENTER: tuple[float, float] = (25.259, 16.998)  # near root
ARM_HOLE2_D: float = 2.801
ARM_HOLE2_CENTER: tuple[float, float] = (23.865, 30.002)  # near tip

# Small boolean-robustness overlap for the arm/root-fillet union onto the
# plate's top band — same rationale as EAR_UNION_OVERLAP_EPS above (the
# arm root now butts against the plate's own full-height Y=0 wall over a
# real area, so no XY footprint extension is needed for bonding — this is
# only the standard anti-coincident-face margin).
ARM_UNION_OVERLAP_EPS: float = 0.02
_ROOT_COLLAR_Y_LO: float = -ARM_UNION_OVERLAP_EPS

_OVERCUT: float = 100.0  # through-cut overcut past body faces, mm


def _edges_near_xy(
    solid: cq.Workplane, x: float, y: float, tol: float = 0.6
) -> cq.Workplane:
    """Select the vertical (|Z) edge(s) whose XY midpoint is near (x, y).

    CadQuery has no built-in "nearest in XY, ignore Z" selector, so this
    filters ``|Z`` edges by hand — the standard pattern for picking a
    single named corner out of a multi-corner solid (used here to fillet
    exactly one concave edge without disturbing the others).
    """
    candidates = solid.edges("|Z").vals()
    picked = [
        e
        for e in candidates
        if abs(e.Center().x - x) < tol and abs(e.Center().y - y) < tol
    ]
    return solid.newObject(picked)


class Arrma223sEscMount:
    """ESC/receiver-box mount plate for the Arrma 223S platform, replacing
    the stock BLX185 3S motor plate.

    (0, 0, 0) is the shared mating face that contacts the chassis rail.
    ``body_thickness`` (the plate's own full thickness, extruded from
    Z=0) is a *derived*, read-only property — ``base_thickness +
    accessory_thickness`` — NOT a constructor parameter. The arm and
    south ear occupy only the plate's own top ``accessory_thickness``
    band (Z ∈ [base_thickness, body_thickness]), flush with the plate's
    top face; they do not extend past it (see the module docstring's
    2026-09-01 correction note for the full rationale — the accessory
    thickness is added ON TOP OF the base thickness, not stacked as a
    separate perched layer).

    Parameters
    ----------
    base_thickness : float
        Plate slab's own base thickness (mm) before the accessory band
        is added on top. Independent of ``accessory_thickness``.
    accessory_thickness : float
        Thickness (mm) of the top band the arm and south ear occupy;
        also the amount added on top of ``base_thickness`` to form the
        plate's full ``body_thickness``. Independent of
        ``base_thickness``.
    material : str | None
        Tolerance profile name resolved via
        :func:`vibe_cading.print_settings.get_profile` (shipped keys:
        ``fdm_standard`` / ``resin_precise`` / ``cnc`` / ``petg``, plus
        any user-defined ``print_profiles_user.json`` entry). Defaults to
        ``"petg"`` — this mount sits next to a motor/ESC, and PETG's heat
        resistance matters more here than for a generic part; pass an
        explicit name (or ``None`` to defer to the project's configured
        ``PRINT_PROFILE`` env default) to calibrate for a different
        printer/material.
    """

    def __init__(
        self,
        base_thickness: float = DEFAULT_BASE_THICKNESS,
        accessory_thickness: float = DEFAULT_ACCESSORY_THICKNESS,
        material: str | None = "petg",
    ) -> None:
        self.base_thickness = float(base_thickness)
        self.accessory_thickness = float(accessory_thickness)
        self.material = material
        self._profile = get_profile(material)

        # Hole 1 is a counterbore whose head-clearance bore runs the full
        # base_thickness, leaving the top accessory_thickness band as the
        # shoulder the screw head bears on (see
        # ``_hole1_counterbore_cutter``). Both bands must therefore be
        # non-degenerate: a zero/negative base gives the head nothing to
        # pass through, and a zero/negative accessory band gives it no
        # shoulder to bind against at all — the latter would silently
        # produce a plain through-hole with no clamping face, which is
        # exactly the failure this check exists to make loud.
        if self.base_thickness <= 0.0:
            raise ValueError(
                f"base_thickness ({self.base_thickness} mm) must be positive"
            )
        if self.accessory_thickness <= 0.0:
            raise ValueError(
                f"accessory_thickness ({self.accessory_thickness} mm) must be "
                "positive — it is the band hole 1's screw head bears against, "
                "and it is the arm's and south ear's whole thickness"
            )

        self._solid = self._build()

    @property
    def body_thickness(self) -> float:
        """The plate's full thickness (mm), derived as
        ``base_thickness + accessory_thickness``. Read-only — set
        ``base_thickness`` and/or ``accessory_thickness`` instead.
        """
        return self.base_thickness + self.accessory_thickness

    # ── Main body ────────────────────────────────────────────────────────

    def _main_body(self) -> cq.Workplane:
        """Rounded-rect main body slab, Z=0 -> body_thickness.

        Fillets 3 of 4 corners with BODY_CORNER_R; the 4th (top-right, at
        local (+BODY_WIDTH/2, 0)) is deliberately left sharp — corner
        fillets are explicitly unchanged by the 2026-09-01 resize (the
        arm-root transition still blends over it, now one Z band up).
        """
        body = (
            cq.Workplane("XY")
            .moveTo(0, -BODY_LENGTH / 2.0)
            .rect(BODY_WIDTH, BODY_LENGTH)
            .extrude(self.body_thickness)
        )
        corners = [
            (-BODY_WIDTH / 2.0, -BODY_LENGTH),
            (BODY_WIDTH / 2.0, -BODY_LENGTH),
            (-BODY_WIDTH / 2.0, 0.0),
        ]
        for cx, cy in corners:
            body = _edges_near_xy(body, cx, cy).fillet(BODY_CORNER_R)
        return body

    def _back_recess_cutter(self) -> cq.Workplane:
        """12.1x18.0x2.0 mm pocket, flush with the body's right edge,
        inset RECESS_TOP_INSET from the top (Y=0) edge, cut from Z=0
        upward. No corner radius was reported for this feature in the
        design brief's measurements, so it is modelled as a plain
        rectangle rather than inventing an unmeasured fillet value.
        """
        x_hi = BODY_WIDTH / 2.0
        x_lo = x_hi - RECESS_WIDTH
        y_hi = -RECESS_TOP_INSET
        y_lo = y_hi - RECESS_LENGTH
        cx, cy = (x_lo + x_hi) / 2.0, (y_lo + y_hi) / 2.0
        return (
            cq.Workplane("XY", origin=(cx, cy, -0.01))  # small entry overcut
            .rect(x_hi - x_lo, y_hi - y_lo)
            .extrude(RECESS_DEPTH + 0.01)
        )

    # ── Hole 1 (former north-ear fastener, now in the plate body) ─────────

    def _hole1_counterbore_cutter(self) -> cq.Workplane:
        """M2.5 round-head COUNTERBORE cutter at HOLE1_CENTER, cut into
        the main plate body (user-specified 2026-09-02; supersedes the
        countersink of 2026-09-01, module note item 2).

        The screw is still inserted from below, but its head is no longer
        seated flush in the bottom face. Instead the head passes *freely*
        up through the whole ``base_thickness``, and the screw binds only
        against the top ``accessory_thickness`` band — the same "clamps
        only the accessory band" behaviour the south ear's plain bore has,
        which is what the user asked this hole to match. So:

        - Z ∈ [0, base_thickness]         — head-diameter clearance bore
        - Z ∈ [base_thickness, body_thickness] — shaft clearance bore; the
          shoulder at Z = base_thickness is the bearing face the head
          lands on.

        Sized to the M2.5 **pan** head (``pan_head_dia`` = 5.0 mm), the
        larger of the project's two round-head catalog diameters — a bore
        that clears a pan head also clears a socket head (4.5 mm), so this
        is the safe reading of "flat round head" and keeps the hardware
        consistent with the M3 chassis pair, which is also pan.

        Built from ``CounterboreHole`` directly rather than via
        ``MetricMachineScrew.to_cutter()`` because the head recess here is
        deliberately ``base_thickness`` deep — a pass-through, not a
        head-height seat, so the catalog ``pan_head_h`` is not the depth
        we want.

        ``CounterboreHole`` puts its head recess at the cutter's own local
        Z=0 "entry" face sinking toward -Z, with the shaft continuing
        further -Z — built for a screw entering from above. Ours enters
        from below, so the cutter is rotated 180 deg about X. It is a
        solid of revolution about its own Z axis, so the accompanying
        Y-flip has no geometric effect; only the Z-flip matters. After
        rotation the local Z=0 entry face lands back on itself, so placing
        it at the part's Z=0 needs only an XY translation.
        """
        m2_5 = METRIC_SIZES["M2.5"]
        # ``CounterboreHole`` sinks its head recess an extra
        # ``profile.free.axial`` past the nominal depth, so the recess floor
        # lands at ``free.axial + head_depth``. That allowance is right for a
        # normal counterbore (it keeps the head below the surface rather than
        # proud), but wrong here: this floor is the *bearing* shoulder the
        # head clamps against, so extra axial clearance only eats into the
        # clamped band — and worse, it would make a functional datum drift
        # with the active print profile (the shoulder would sit at 7.25 on
        # petg, 7.20 on fdm_standard, 7.00 on cnc). Pre-subtracting the
        # allowance pins the shoulder at exactly ``base_thickness`` on every
        # profile, so the clamped band is exactly ``accessory_thickness``.
        head_depth = max(self.base_thickness - self._profile.free.axial, 0.0)
        cutter = CounterboreHole(
            shaft_diameter=m2_5["clearance"],
            shaft_depth=self.body_thickness,
            head_diameter=m2_5["pan_head_dia"],
            head_depth=head_depth,
            head_type="cylinder",
            profile=self._profile,
        ).to_cutter(profile=self._profile)
        cutter = cutter.rotate((0, 0, 0), (1, 0, 0), 180)
        cx, cy = HOLE1_CENTER
        return cutter.translate((cx, cy, 0.0))

    # ── South ear ────────────────────────────────────────────────────────

    def _south_ear(self) -> cq.Workplane:
        """"Stadium"/slot lug: a rectangle unioned with a tangent circle
        of the same radius centered on the rectangle's far short edge,
        accessory_thickness tall, occupying the plate's own top band
        (Z ∈ [base_thickness, body_thickness]) flush with its top face.

        The rectangle's near (north) edge extends only
        EAR_UNION_OVERLAP_EPS past the plate's own south edge — a small
        boolean-robustness margin, not a bonding-area fix, since the ear
        now butts against the plate's full-height vertical side wall over
        a real 2D area (ear width x accessory_thickness) rather than a
        zero-area edge line.
        """
        near_edge_y = -BODY_LENGTH + EAR_UNION_OVERLAP_EPS  # onto the plate's own side wall
        arc_center_y = SOUTH_EAR_HOLE_Y  # -43.0
        radius = EAR_BOTTOM_ARC_R
        y_lo, y_hi = sorted((near_edge_y, arc_center_y))
        rect = (
            cq.Workplane(
                "XY", origin=(MOTOR_HOLE_X, (y_lo + y_hi) / 2.0, self.base_thickness)
            )
            .rect(2.0 * radius, y_hi - y_lo)
            .extrude(self.accessory_thickness)
        )
        cap = cylinder(
            radius,
            self.accessory_thickness,
            center=(MOTOR_HOLE_X, arc_center_y, self.base_thickness),
        )
        return rect.union(cap)

    def _south_ear_clearance_cutter(self) -> cq.Workplane:
        """Plain M2.5 clearance through-hole for the south ear — NO
        countersink, counterbore, or recess of any kind (user-specified
        2026-09-01, module note item 3; previously a pan-head recess).

        Minimum annular wall at the ear's narrowest point (through the
        straight walls): (8.9886 - 2.7) / 2 ≈ 3.14 mm — comfortably
        positive; the semicircular cap has more clearance everywhere
        else.
        """
        r = EAR_HOLE_CLEARANCE_D / 2.0 + self._profile.free.radial
        cx, cy = SOUTH_EAR_CENTER
        return (
            cq.Workplane("XY", origin=(cx, cy, -_OVERCUT))
            .circle(r)
            .extrude(self.body_thickness + 2 * _OVERCUT)
        )

    # ── Arm ─────────────────────────────────────────────────────────────

    def _arm_root_fillet(self) -> cq.Workplane:
        """Concave R=ARM_ROOT_BLEND_R wedge blending the arm's own left
        wall into the main body's flat top (Y=0, local) edge —
        accessory_thickness tall, occupying the plate's own top band
        (Z ∈ [base_thickness, body_thickness]) flush with its top face.

        Tangent to the plate's own Y=0 edge at
        ``(arm_left_x - ARM_ROOT_BLEND_R, 0.0)`` and tangent to the arm's
        own left wall at ``(arm_left_x, ARM_ROOT_BLEND_R)`` — no
        reference to the ear's geometry or edge position at all (see the
        design brief's T12 correction). Dips ``_ROOT_COLLAR_Y_LO``
        (= -ARM_UNION_OVERLAP_EPS) only a small boolean-robustness margin
        south of the plate's own Y=0 edge — the root now butts against
        the plate's full-height vertical side wall over a real area, so
        no XY bonding-area extension is needed, just the standard
        anti-coincident-face epsilon.
        """
        arm_left_x = ARM_X_CENTER - ARM_WIDTH / 2.0
        p_horiz = (arm_left_x - ARM_ROOT_BLEND_R, 0.0)
        p_vert = (arm_left_x, ARM_ROOT_BLEND_R)
        x_margin = 1.0  # mm past arm_left_x — anti-coincident-face margin (X direction)

        return (
            cq.Workplane("XY", origin=(0, 0, self.base_thickness))
            .moveTo(p_horiz[0] - x_margin, _ROOT_COLLAR_Y_LO)
            .lineTo(p_horiz[0] - x_margin, 0.0)
            .lineTo(*p_horiz)
            .radiusArc(p_vert, -ARM_ROOT_BLEND_R)
            .lineTo(arm_left_x + x_margin, p_vert[1])
            .lineTo(arm_left_x + x_margin, _ROOT_COLLAR_Y_LO)
            .close()
            .extrude(self.accessory_thickness)
        )

    def _arm(self) -> cq.Workplane:
        """12.0 mm wide shaft + flush R=ARM_WIDTH/2 tip cap + R9.06 root
        blend into the main body's flat top edge, accessory_thickness
        tall, occupying the plate's own top band (Z ∈ [base_thickness,
        body_thickness]) flush with its top face.

        Built from three overlapping pieces:
          - ``root_fillet``: the concave root-blend wedge (see
            ``_arm_root_fillet``), now also carrying the small
            boolean-robustness overlap onto the plate's own side wall.
          - ``shaft``: the plain 12 mm-wide rectangle, extended south to
            local Y=-ARM_UNION_OVERLAP_EPS (was Y=0) for the same reason.
          - ``tip``: the flush tip cap circle, tangent to both shaft
            walls with no neck (``ARM_TIP_R = ARM_WIDTH / 2.0``).

        An earlier attempt built the root wedge and shaft as two
        independently extruded solids sharing an exact coincident vertical
        face, then tried ``.fillet(ARM_ROOT_BLEND_R)`` on the resulting
        edge — this is precisely the coincident-face boolean pitfall
        documented in CLAUDE.md's Known Modelling Pitfalls, and OCCT
        rejected the fillet (``StdFail_NotDone``). Baking the blend into
        the wire geometry directly, with a genuine area overlap against
        its neighbours, sidesteps that failure mode entirely.
        """
        y_lo = -ARM_UNION_OVERLAP_EPS
        shaft = (
            cq.Workplane(
                "XY",
                origin=(ARM_X_CENTER, (y_lo + ARM_TIP_CENTER_Y) / 2.0, self.base_thickness),
            )
            .rect(ARM_WIDTH, ARM_TIP_CENTER_Y - y_lo)
            .extrude(self.accessory_thickness)
        )
        tip = cylinder(
            ARM_TIP_R,
            self.accessory_thickness,
            center=(ARM_X_CENTER, ARM_TIP_CENTER_Y, self.base_thickness),
        )
        return self._arm_root_fillet().union(shaft).union(tip)

    def _arm_hole_cutters(self) -> list[cq.Workplane]:
        holes = []
        for (cx, cy), d in (
            (ARM_HOLE1_CENTER, ARM_HOLE1_D),
            (ARM_HOLE2_CENTER, ARM_HOLE2_D),
        ):
            r = d / 2.0 + self._profile.free.radial
            holes.append(
                cq.Workplane("XY", origin=(cx, cy, -_OVERCUT))
                .circle(r)
                .extrude(self.body_thickness + 2 * _OVERCUT)
            )
        return holes

    # ── Motor-mount holes (main body) ───────────────────────────────────

    def _chassis_mount_cutter(self, center: tuple[float, float]) -> cq.Workplane:
        """Standard M3 pan-head clearance cutter (bore + top-face recess)
        for one motor-mount hole, cut from the top (Z=body_thickness)
        face.

        One ``MetricMachineScrew(...).to_cutter()`` call supplies both the
        through-bore and the top-face recess. See
        ``_chassis_left_bottom_relief_cutter`` for the LEFT hole's separate
        bottom-face mesh-fidelity pocket.
        """
        cutter = MetricMachineScrew.from_size(
            "M3", length=self.body_thickness, head_type="pan"
        ).to_cutter(profile=self._profile, fit="clearance")
        cx, cy = center
        return cutter.translate((cx, cy, self.body_thickness))

    def _chassis_left_bottom_relief_cutter(self) -> cq.Workplane:
        """As-measured mesh material-relief pocket on the LEFT motor-mount
        hole's bottom (Z=0) face: 7.0 mm OD x 2.0 mm deep, a plain
        cylindrical pocket.

        This is not a fastener-seating recess — no screw head sits
        against the bottom face — so it is a plain cylinder, not a
        ``MetricMachineScrew`` cutter, sized to the reference mesh rather
        than any hardware standard. The RIGHT hole gets no equivalent:
        its bottom face is already cleared by the much larger back-recess
        pocket (§2), so a separate relief pocket there would be
        redundant.
        """
        cx, cy = CHASSIS_LEFT_CENTER
        r = CHASSIS_LEFT_RELIEF_OD / 2.0 + self._profile.free.radial
        return (
            cq.Workplane("XY", origin=(cx, cy, -0.01))
            .circle(r)
            .extrude(CHASSIS_LEFT_RELIEF_DEPTH + 0.01)
        )

    # ── Build ────────────────────────────────────────────────────────────

    def _build(self) -> cq.Workplane:
        part = self._main_body()
        part = part.union(self._south_ear())
        part = part.union(self._arm())

        part = part.cut(self._back_recess_cutter())
        part = part.cut(self._hole1_counterbore_cutter())
        part = part.cut(self._south_ear_clearance_cutter())
        for hole in self._arm_hole_cutters():
            part = part.cut(hole)
        part = part.cut(self._chassis_mount_cutter(CHASSIS_LEFT_CENTER))
        part = part.cut(self._chassis_mount_cutter(CHASSIS_RIGHT_CENTER))
        part = part.cut(self._chassis_left_bottom_relief_cutter())

        assert len(part.solids().vals()) == 1, (
            "Arrma223sEscMount: expected a single contiguous solid — check "
            "ear/arm overlap with the main body and hole/recess depths."
        )
        return part

    @property
    def solid(self) -> cq.Workplane:
        """The CadQuery solid. Z=0 is the shared chassis-mating face."""
        return self._solid
