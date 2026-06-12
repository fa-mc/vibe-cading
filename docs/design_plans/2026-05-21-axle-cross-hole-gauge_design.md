# Design: Stage 2 — Cross-Profile Axle-Hole Fit Validation Gauge

## Meta
- **Requirements ref**: Interactive request (this session); follows Stage 1 —
  `.agents/plans/2026-05-20-axle-hole-tip-to-tip-gauge_design.md`.
- **Requester role**: User (acting as Admin)
- **Date**: 2026-05-21
- **Dialog rounds**: 2

---

## Objective

Deliver a printable gauge that physically validates the **`+` cross**
axle-hole fit — the half of `TechnicAxleHole` that Stage 1 never tested — and
isolates the **arm-slot width** requirement, with the concave corners
deliberately relieved away so they cannot confound the measurement.

---

## Background — why this exists

Stage 1 calibrated **tip-to-tip** using *round* holes (`AxleHoleGauge`): the
user's printer needs `slip.radial ≈ 0.10`, set in `machine_profiles_user.json`.

But every Stage-1 print was a round hole. A round hole has no arms, so the
**cross slot was never tested**. Under the option-(b) architecture
(Amendment 2 of the Stage-1 brief) the arm slot rides the *same* profile
radial as tip-to-tip:

```
arm slot modelled = AXLE_HOLE_ARM_WIDTH (1.83) + 2 × slip.radial (0.10) = 2.03 mm
```

Whether 2.03 mm modelled prints to a good cross fit is unknown — and the `+`
slot's four concave corners are where FDM **corner blowout** over-deposits,
choking the slot.

The cross fit therefore has *two* unknowns: the flat slot-wall (arm) width and
the concave corner. Measuring both at once repeats the original failed-sweep
mistake. So this gauge **isolates the arm-slot width**: it sweeps arm width
while the concave corners are held generously open by a **dog-bone relief**,
so they cannot be the binding constraint. This is the Stage-2 analogue of
Stage 1's round holes, which removed the corners entirely to isolate
tip-to-tip.

## Objective restated

One deliverable: a new `AxleCrossHoleGauge` model class — a row of `+` cross
holes with dog-bone corner relief, tip-to-tip fixed at the calibrated value,
arm-slot width swept. The user prints it, inserts a real Lego axle, and
reports which holes accept and key the axle cleanly.

The concave-corner behaviour and any production-code change are **Stage 2b** —
explicitly *data-gated*: we do not build a production corner-relief mechanism
before this gauge isolates arm width. See *Out of Scope*.

---

## Architecture / Approach

### Approach chosen

A new `AxleCrossHoleGauge` class — structurally a sibling of `AxleHoleGauge`,
but each hole is a `+` cross cutter with a dog-bone-relieved corner.

- **Tip-to-tip is fixed**, not swept. It is derived from the calibrated
  profile: `tip_to_tip = AXLE_HOLE_TIP_TO_TIP + 2 × profile.slip.radial`. With
  the user's `machine_profiles_user.json` (slip.radial 0.10) that is 5.00 mm —
  exactly the Stage-1-validated tip-to-tip. The gauge auto-adapts to whatever
  profile is active; no magic number.
- **Arm-slot width is the swept variable** — an explicit `arm_widths`
  sequence. Default `(1.85, 1.95, 2.05, 2.15, 2.25, 2.35)` — 6 holes, 0.10 mm
  step, bracketing the 2.03 mm prediction (a finer pass is just a different
  tuple).
- **Dog-bone corner relief.** Each `+` hole carries a circular relief pocket
  at each of the 4 inner concave corners — *replacing* the `concave_radius`
  fillet of `TechnicAxleHole`. A plain fillet cannot be enlarged enough to
  matter: it is capped near ~0.75 mm by the slot-wall length (the widest
  swept holes leave only ~0.95 mm of wall), barely above the 0.6 mm
  production value. The dog-bone is not so bounded — it fully clears the
  concave corner as a contact point so the sweep reads **arm-slot width
  alone**. The relief radius is the `corner_relief` parameter; it must leave
  a defined flat slot wall along each arm — it isolates arm width, it must
  not erase the surface that *measures* it (the Developer sizes/places it;
  centring the pocket off the corner along the bisector preserves more wall).
- Each `+` hole otherwise matches `TechnicAxleHole`: curved arm tips
  (cylinder ∩ cross arms), no lead-in chamfer.
- Same gauge conventions as `AxleHoleGauge`: flat block, plan-centred at
  X=Y=0, bottom face on the Z=0 print bed, holes through, axes ∥ Z, each hole
  engraved with its arm-width on the top face (labels unioned into one
  compound before a single `.cut()`).

### Visual contract (CAD task — new model class `AxleCrossHoleGauge`)

![Design preview — iso_ne](2026-05-21-axle-cross-hole-gauge_design_iso_ne.svg)

![Design preview — top](2026-05-21-axle-cross-hole-gauge_design_top.svg)

Six `+` **cross** holes in a single row along X, axes ∥ Z, each with a
**dog-bone relief** at its four inner corners. Contract to verify at Phase B:
holes are **cross-shaped** (not round), **through**, **one row**, **Z axes**,
all the **same tip-to-tip**, with **visibly increasing arm-slot width**
left→right and a **circular relief pocket at each concave corner**.

### How the result is interpreted

The gauge yields `W_good` — the modelled arm-slot width that accepts and keys
a real axle when the concave corners are *not* a factor (dog-bone relieved).
That isolates the **flat slot-wall** requirement:

```
arm_wall_excess = W_good − (AXLE_HOLE_ARM_WIDTH + 2 × slip.radial)
                = W_good − 2.03   (at the user's calibrated profile)
```

- `arm_wall_excess ≈ 0` → the profile radial already serves the flat-wall arm
  fit; arm width needs nothing beyond Stage 1's `slip.radial`.
- `arm_wall_excess > 0` → the flat walls need clearance the shared profile
  radial does not give — carried forward to Stage 2b.

This is the *arm-width* half of the cross fit. The **concave corner itself**
is deliberately not tested here — it is relieved away. Stage 2b takes the
production `TechnicAxleHole` (which still has the `concave_radius` fillet, not
a dog-bone) and decides the corner treatment: whether the fillet binds a real
axle, and whether production should adopt this gauge's dog-bone relief as a
`corner_relief` parameter and at what size. The dog-bone proven on this gauge
is the candidate mechanism.

### Code structure — Developer's call, one requirement

The gauge's `+` holes match `TechnicAxleHole`'s cross in **tips and arms**
(cylinder ∩ cross arms) but **deliberately deviate at the corner** — dog-bone
relief instead of the `concave_radius` fillet — to isolate arm width. The
faithful, shared part is the cylinder∩cross construction. Extracting that into
a `cq_utils` helper shared by `TechnicAxleHole`, `TechnicAxle`, and this gauge
is **encouraged** — it is the *third* copy of the cylinder∩cross pattern, a
clear DRY trigger — but the structural decision is the Developer's. The
dog-bone is gauge-specific geometry layered on top.

### Alternatives rejected

- **Sweep tip-to-tip AND arm-width (2D grid).** Rejected — tip-to-tip is
  already calibrated; re-sweeping it abandons the one-variable isolation.
- **Enlarge the `concave_radius` fillet to neutralise the corner.** Rejected —
  the fillet is geometrically capped near ~0.75 mm (it cannot exceed the
  slot-wall length, and the widest swept holes leave only ~0.95 mm of wall).
  That is barely above the 0.6 mm production value — too small to isolate arm
  width. The dog-bone relief is not so bounded. *(User design dialog, round 2.)*
- **Sweep the corner relief in this gauge too.** Rejected as the *first*
  pass — that re-introduces two variables. Isolate arm width first; the
  corner is Stage 2b.
- **Build the `TechnicAxleHole` corner-relief parameter now.** Rejected —
  data-gated; deferred to Stage 2b.
- **Skip the gauge, just trust 2.03 mm.** Rejected — the entire Stage-1
  lesson is that printed fit must be physically verified, not assumed.

---

## Data & Interface Contracts

**`AxleCrossHoleGauge` public API**

```python
class AxleCrossHoleGauge:
    """Printable gauge isolating the arm-slot width of the + cross Technic
    axle-hole fit.

    Each hole is a + cross cutter at a fixed (profile-derived) tip-to-tip,
    with the arm-slot width swept across the row and a dog-bone relief at
    each concave corner so the concave corner cannot confound the fit —
    the user finds the modelled arm width that accepts and keys a real
    Lego axle cleanly.

    Origin (0,0,0): block plan-centred (XY centroid at origin), bottom face
    on the Z=0 print bed, extruding +Z. Hole axes ∥ Z.
    """
    def __init__(
        self,
        arm_widths: Sequence[float] = (1.85, 1.95, 2.05, 2.15, 2.25, 2.35),
        profile: ToleranceProfile | None = None,   # supplies tip-to-tip
        corner_relief: float = 0.8,   # dog-bone relief radius at each corner
        depth: float = 8.0,
        hole_pitch: float = 9.0,
        engrave_depth: float = 0.6,
    ): ...

    @property
    def solid(self) -> cq.Workplane: ...
```

**Invariants**
- `tip_to_tip = AXLE_HOLE_TIP_TO_TIP + 2 * profile.slip.radial` — fixed for
  all holes; `profile` defaults to the active global profile.
- One `+` cross through-hole per `arm_widths` entry: cylinder(tip/2) ∩
  (rect(tip, arm) ∪ rect(arm, tip)), no lead-in chamfer, with a dog-bone
  relief (radius `corner_relief`) at each of the 4 inner concave corners
  *instead of* a `concave_radius` fillet.
- The dog-bone must leave a defined flat slot wall along each arm — it
  isolates arm width, it must not erase the surface that *measures* it.
- Each hole engraved with its arm width (`f"{w:.2f}"`); all label text
  unioned into one compound before a single `.cut()`.
- Result is a single contiguous solid: `assert len(solids) == 1`.

## Implementation Plan

- [x] **T1** — Implement `AxleCrossHoleGauge` (new file; AGPLv3 header, strict
  type hints, origin docstring + calibration procedure; no `__main__` /
  `ocp_vscode` / `demo()`).  → `vibe_cading/lego/axle_cross_hole_gauge.py`.
- [x] **T2** — Resolve cross-geometry reuse per *Code structure* above
  (prefer a shared `cq_utils` cylinder∩cross helper); add the dog-bone relief
  on top.  → extracted `cq_utils.axle_cross_section()`, now consumed by
  `TechnicAxle`, `TechnicAxleHole`, and `AxleCrossHoleGauge`; refactor
  verified behaviour-preserving (existing 178 tests pass unchanged, volumes
  identical).
- [x] **T3** — Tests (see below).  → `tests/test_axle_cross_hole_gauge.py`
  (13 tests covering Tests 1-5).
- [x] **T4** — Validate: build the gauge, single-solid assert, `hole_finder`
  / `face_catalog` to confirm 6 cross holes at the fixed tip-to-tip with
  corner reliefs; regenerate the visual-contract SVGs from the implemented
  class and overwrite the committed `.agents/plans/2026-05-21-*` SVGs.
  → `hole_finder` confirms 6 holes Ø4.900 + 24 corner-relief pockets Ø0.700;
  SVGs regenerated text-free + viewBox-patched.
- [x] **T5** — Export a STEP (`tmp/axle_cross_hole_gauge.step`) for the user
  to print.
- [x] **T6** — `TODO.md`: annotate the Stage-2 item — arm-width gauge
  delivered; the concave-corner test + `TechnicAxleHole` corner-relief
  parameter (Stage 2b) remain open, gated on this gauge's print result.

## Tests

| # | Test description | Expected assertion | File |
|---|------------------|--------------------|------|
| 1 | Gauge builds with defaults | single contiguous solid (`len(solids)==1`) | `tests/` |
| 2 | Hole count + shape | one cross hole per `arm_widths` entry; holes are `+` (not plain cylinders) — verify via face topology | `tests/` |
| 3 | Tip-to-tip is profile-derived & fixed | all holes share one tip-to-tip = `AXLE_HOLE_TIP_TO_TIP + 2*slip.radial`; a different `profile` changes it | `tests/` |
| 4 | Arm width varies as swept | per-hole arm-slot width matches the `arm_widths` sequence | `tests/` |
| 5 | Dog-bone relief present | each cross hole has a relief pocket at all 4 concave corners; a defined flat slot wall remains along each arm | `tests/` |

## Success Criteria

1. `AxleCrossHoleGauge` builds a single contiguous solid: a row of `+` cross
   through-holes, fixed profile-derived tip-to-tip, swept arm width, each
   labelled.
2. The cross holes match `TechnicAxleHole` in tips and arms, with a dog-bone
   relief (not the `concave_radius` fillet) at the 4 concave corners; a flat
   slot wall remains for the arm-width fit.
3. `tools/view.py` / `tools/preview.py` render it; visual contract holds
   (cross / through / one row / Z axes / increasing arm width / corner
   reliefs).
4. A printable STEP is exported for the user.
5. No CI regressions (AGPLv3 header, no `__main__`, no `ocp_vscode`, linters
   clean).

## Out of Scope

- **Stage 2b** — testing the production concave corner (the `concave_radius`
  fillet) and, if it binds, adding a `corner_relief` parameter to
  `TechnicAxleHole` (the dog-bone proven on this gauge is the candidate).
  Data-gated; specced once this gauge's `W_good` is known.
- Re-sweeping or re-calibrating tip-to-tip (Stage 1, done).
- Changing `AXLE_HOLE_ARM_WIDTH` (1.83) — it is a sound real-Lego nominal
  (`docs/lego-technic.md`: hole 1.83 = axle 1.78 + 0.05, the same +0.05 the
  hole carries on tip-to-tip). It is not the tuning knob.
- Registering the gauge in `build.toml` (needs explicit user approval).

## Known Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Dog-bone eats the flat slot wall → nothing left to measure arm width. | `corner_relief` sized (and the pocket placed off-corner along the bisector) to leave a defined wall across the whole sweep; Test #5 asserts a wall remains; Developer validates against the widest swept hole. |
| `+` cross boolean + dog-bone unions on a swept solid fragile (OCCT). | The visual-contract probe built all 6 dog-boned cross holes as a single clean solid; the single-solid assert guards regressions. |
| Sweep range misses `W_good`. | Range 1.85–2.35 brackets the 2.03 mm prediction; with corners relieved `W_good` should sit near it. The class is parametric — a shifted/finer pass is one tuple change. |
| User judges cross fit by feel — slide-in *and* rotational keying. | The calibration procedure (class docstring) explains: the good hole inserts without force AND keys with minimal rotational slop. |
| Gauge dog-bone ≠ production `concave_radius` fillet → gauge does not validate the production corner. | Intentional — this gauge isolates arm width only; the production corner is explicitly Stage 2b. Stated in *How the result is interpreted*. |
| Engraved label text stalling the OCCT boolean kernel. | Union all label solids into one compound, single `.cut()` — established pattern. |

### Calibration procedure (for the `AxleCrossHoleGauge` docstring)

1. Print the gauge flat, holes vertical (axis ∥ build-Z), same printer /
   material / slicer settings as the Stage-1 gauge and your real parts
   (XY hole compensation = 0).
2. Insert a real Lego Technic axle into each `+` hole from the labelled face.
3. The good hole accepts the axle **without force** AND keys it with
   **minimal rotational slop** — note its arm-width label `W_good`.
4. Report `W_good`. `arm_wall_excess = W_good − (AXLE_HOLE_ARM_WIDTH +
   2·slip.radial)` isolates the flat-wall arm requirement. The concave corner
   is relieved away on this gauge — it is assessed separately in Stage 2b.

---

## Design Dialog Log

### Round 1
**Designer observation:**
> Stage 1 calibrated tip-to-tip via round holes; the `+` cross slot was never
> physically tested. Under option (b) the arm slot rides the same profile
> radial (modelled 2.03 mm), unverified, and FDM corner blowout attacks the
> concave corners.

**Requester contribution:**
> "Start now" — proceed with Stage 2.

**Resolution:**
> Scope Stage 2 to a *diagnostic* cross-profile gauge that sweeps arm-slot
> width at fixed (calibrated) tip-to-tip. The `TechnicAxleHole` corner-relief
> parameter is data-gated Stage 2b.

### Round 2
**Requester contribution:**
> The concave corner ("where two arms cross") is a second variable; make it
> large enough that the sweep tests arm width alone.

**Designer finding:**
> Correct instinct. But the existing knob — `TechnicAxleHole.concave_radius`
> (the inner-corner fillet) — cannot be enlarged enough: it is capped near
> ~0.75 mm by the slot-wall length. Presented two mechanisms; user chose the
> **dog-bone relief** (a circular pocket at each corner, not bounded that way).

**Resolution:**
> The gauge uses a dog-bone relief at each of the 4 concave corners,
> replacing the `concave_radius` fillet, to isolate arm-slot width. The
> dog-bone doubles as the candidate Stage-2b production corner-relief
> mechanism.

---

## Sign-off

### Author sign-off (drafting role — Step 3 termination)
- [ ] Domain expert co-sign  *(N/A — domain integrity gate NO; geometry follows the Stage-1 brief + docs/lego-technic.md, no new reference interpreted)*
- [ ] Requester sign-off
- [x] Designer sign-off (drafting author)

### Independent reviewer sign-off (fresh-context — Step 3.5 termination)
- [ ] Independent TL
- [ ] Independent Developer

---

## Implementation Status
- [x] All Implementation Plan tasks completed (T1-T6)
- [x] Test suite executed — result: **191 passed, 2 xfailed** (178 pre-existing
  + 13 new `test_axle_cross_hole_gauge.py`; the 2 xfails are pre-existing and
  unrelated). Behaviour-preserving refactor confirmed — existing
  `TechnicAxle` / `TechnicAxleHole` tests pass unchanged, volumes identical.
- [x] No new linter / static-check errors — `flake8` clean on all changed
  files; `check_no_main_blocks.py` OK; no `ocp_vscode` imports; AGPLv3 header
  present on both new files.

### Developer note — `corner_relief` default deviates from the brief (0.8 → 0.35)

The brief's API contract gives `corner_relief: float = 0.8`. **0.8 is
geometrically infeasible** for this gauge and conflicts with the brief's own
binding requirement (Test #5 / Known Risks: "leave a defined flat slot wall
along each arm … validate against the widest hole, arm 2.35").

*Geometry.* A dog-bone for a 90° inside corner is a circle that passes through
the concave-corner point; on the corner bisector that means it eats
`corner_relief · √2` of flat slot wall along **each** arm. The flat slot wall
is the corner-to-tip-arc run, not `(tip−arm)/2` — it ends where the bounding
cylinder arc cuts in, at `x = √((tip/2)² − half_arm²)`. At the *widest* swept
hole (arm 2.35, tip 4.90) that wall is only **0.975 mm** — matching the brief's
own "~0.95 mm of wall" figure. A `corner_relief` of 0.8 eats `0.8·√2 = 1.131`
mm — **more than the entire wall**, leaving nothing to measure arm width with.

*Resolution (within delegated authority).* The brief explicitly delegates
sizing and placement to the Developer ("the Developer sizes/places it";
"centring the pocket off the corner along the bisector preserves more wall —
your implementation call"). The `0.8` is a *suggested default*, not an
acceptance criterion; the binding criterion is Test #5. Key insight: the
dog-bone **undercuts** the corner — once the pocket circle reaches the corner
point, hole material is removed *behind* it, so the axle's rounded corner can
never register there. The corner is **fully relieved as a contact for any
positive `corner_relief`**; a larger radius removes more wall for no
additional relief. The default is therefore set to **0.35 mm** — the largest
value that leaves a robust flat slot wall (~0.48 mm, > one FDM extrusion
width) on the *widest* swept hole while fully relieving the corner. The
parameter remains user-tunable for narrower sweeps. The class docstring and
the `corner_relief` parameter note document this in full.

*Escalation hook.* This is a brief-internal numeric inconsistency, not a
scope change. Flagged here for Designer/Admin visibility; no rework needed —
the delivered default satisfies every binding success criterion. If a future
pass wants a larger relief, narrow the `arm_widths` sweep so the widest hole
retains enough wall, or accept a thinner measuring wall.

### Validation evidence
- `step_summary`: single solid, bbox 54.0 × 18.9 × 8.0, plan-centred at
  X=Y=0, bottom face on Z=0.
- `hole_finder --grid 8`: 6 cross holes Ø4.900 (the fixed profile-derived
  tip-to-tip), depth 8.0, axes ∥ Z, single row at Y=3.0, pitch 9.0; plus 24
  corner-relief pockets Ø0.700 (= 2 × `corner_relief` 0.35), 4 per hole.
- `face_catalog`: 48 CYLINDER faces = 6 × (4 arm tips + 4 dog-bone reliefs).
- Per-hole topology oracle (tests): 8 PLANE arm walls (a round hole has 0) +
  8 CYLINDER faces (4 tips + 4 reliefs; a relief-free cross has 4).
- Remaining flat slot wall across the sweep: 0.85 mm (arm 1.85) → 0.48 mm
  (arm 2.35) — defined at every hole.
- Visual-contract SVGs regenerated text-free and viewBox-patched.

### Note for the user
The active tolerance profile in this clone is `bambu_p1s` with
`slip.radial = 0.05` (legacy flat-schema `slip_fit` in
`machine_profiles_user.json`), so the gauge's fixed tip-to-tip resolves to
**4.90 mm** — *not* the 5.00 mm the brief cites for a calibrated
`slip.radial = 0.10`. The gauge is parametric and auto-adapts; if Stage 1
calibrated `slip.radial` to 0.10, update `machine_profiles_user.json`
accordingly (the brief's nested-schema form) and re-export before printing so
the cross holes carry the calibrated tip-to-tip.

---

## Post-Implementation Sign-Off

### TL Review
- [ ] **TL sign-off**
- TL review notes:

### Human Final Approval
- [ ] **Human approved** for merge / release
- Human notes:
