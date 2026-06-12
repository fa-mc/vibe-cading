# Design: Stage 2b — Cross-Arm Slot Clearance (`FitGrade.slot`)

## Meta
- **Requirements ref**: Interactive request (this session); follows Stage 2 —
  `.agents/plans/2026-05-21-axle-cross-hole-gauge_design.md`.
- **Requester role**: User (acting as Admin)
- **Date**: 2026-05-22
- **Dialog rounds**: 1 + a TL architecture consult (see Design Dialog Log).

---

> ⚠️ **AMENDMENT (2026-05-22, user-approved)** — Section D and the
> shipped-`slot` decision are revised: `slot` ships a **non-zero default
> (0.10)** so the user calibrates only `slip.radial`. Tests #5, Known Risks,
> and Alternatives are affected. Implement Section D / shipped values / Tests
> from **`## Amendment`** at the end of this brief; the rest stands.

## Objective

Give the `+` cross axle hole's **arm slot** the extra clearance it needs
beyond the round tip-to-tip envelope, via a new profile-level allowance, so
the calibration propagates automatically to every `TechnicAxleHole` consumer.

---

## Background

Stage 2's `AxleCrossHoleGauge` (cross holes, concave corners neutralised by a
dog-bone relief, arm-slot width swept) produced a clean physical result:

- `W_good = 2.25 mm` modelled arm slot — band 2.15 (slightly tight) … 2.35
  (slightly loose), 2.25 well-centred.
- The production `TechnicAxleHole` derives the arm slot as
  `AXLE_HOLE_ARM_WIDTH (1.83) + 2·slip.radial (0.11) = 2.05 mm`.
- So the arm slot needs **+0.20 mm** beyond what `2·slip.radial` gives.

This is a real physical asymmetry: a narrow `+` slot prints ~0.20 mm tighter
than the round envelope on this printer/material. The round tip-to-tip and the
narrow arm slot have *physically distinct* clearance needs, and a single
shared `slip.radial` cannot serve both. Stage 2b adds the mechanism for the
second need.

---

## Architecture / Approach

The architecture below is the TL's recommendation from the 2026-05-22 consult
(Design Dialog Log) — recorded here as the agreed design.

### A. New `FitGrade.slot` field

Add an optional fourth field to the `FitGrade` dataclass:

```python
@dataclass
class FitGrade:
    radial: float
    axial: float = 0.0
    slot: float = 0.0   # extra half-width for narrow-slot FDM tightening
```

`slot` is *additional* half-extra-material applied **only** to narrow-slot
features, **on top of** `radial`. It is a per-grade value (it belongs on
`FitGrade`, not `ToleranceProfile`: a press-fit slot and a free-fit slot
tighten by different absolute amounts, exactly as `radial` does).

Three orthogonal allowances: `radial` = half-extra on diameter (all features);
`axial` = along-axis allowance; `slot` = *additional* half-extra applied only
to narrow-slot widths. The `FitGrade` docstring must state this crisply.

### B. `print_settings.py` loader — all defaulted, ~6 one-liners

- `_fitgrade_from_dict` — read `slot=float(data.get("slot", default_slot))`,
  `default_slot=0.0`.
- `_profile_from_nested` — pass `default_slot=0.0` for all three grades.
- `_migrate_flat_to_nested` (legacy flat schema) — **no change**. The legacy
  schema has no slot concept; migrated grades omit `slot` →
  `_fitgrade_from_dict` defaults it to `0.0` → a legacy-flat profile gets
  pre-Stage-2b behaviour. Safe and correct.
- `_FALLBACK_PROFILES` — leave `slot` out (defaults to `0.0`).

### C. `TechnicAxleHole` arm formula

```python
grade = getattr(profile, fit)
self.TIP_TO_TIP = AXLE_HOLE_TIP_TO_TIP + 2 * grade.radial             # unchanged
self.ARM_WIDTH  = AXLE_HOLE_ARM_WIDTH  + 2 * grade.radial + 2 * grade.slot
```

The round envelope is untouched; only the arm slot widens, by `2·slot`.

### D. Shipped vs user profiles

- **`machine_profiles.json` (tracked)** — `slot` stays absent (= 0.0). Shipping
  `slot > 0` would impose one printer's n=1 calibration on every user — the
  exact mistake Amendment 2 rejected for `slip.radial`. Shipped behaviour is
  unchanged.
- **`machine_profiles.json.example`** — gains a commented `slot` line so users
  discover the knob.
- **`machine_profiles_user.json` (this user)** — currently legacy-flat schema.
  It must be **migrated to the nested schema** to carry a `slot` value, and
  the migration MUST preserve the calibrated `slip_fit: 0.11 → slip.radial`.
  Target:
  ```json
  {
    "bambu_p1s": {
      "free":  {"radial": 0.15, "axial": 0.20},
      "slip":  {"radial": 0.11, "axial": 0.20, "slot": 0.10},
      "press": {"radial": 0.04, "axial": 0.20}
    }
  }
  ```
  `slot = 0.10` because `2·slot = W_good − (1.83 + 2·0.11) = 2.25 − 2.05 = 0.20`.

### The concave corner — explicitly NOT in this stage

Stage 2b ships the **arm-width** fix only. The production concave corner (the
`concave_radius = 0.6` fillet) is **kept as-is** — no dog-bone, no
`corner_relief` parameter.

Rationale: the Stage-2 gauge's dog-bone was a *measurement instrument* — it
removed the corner from contact so the sweep read arm width alone. It follows
that **the production fillet corner is untested either way** — the gauge never
fit-tested a filleted corner, and adopting the gauge's dog-bone would ship an
undercut whose production sizing was never calibrated (the gauge's
`corner_relief = 0.35` was a gauge-geometry compromise, not a production
value). The disciplined move — consistent with the whole calibration arc — is
to ship the arm fix, then test the production corner separately. The +0.20 mm
arm widening also opens the corner geometry slightly, which de-risks blowout
without committing to an unproven change. A Stage-2b verification print
(Task T8) confirms the corner in practice; a dedicated **Stage 2c** corner
gauge follows only if it binds.

### Visual contract

Not applicable — Stage 2b adds a tolerance-profile field and a clearance term.
No new model class; no axis / orientation / hole-pattern change. The arm-slot
delta is a sub-mm dimension change, gated on a non-default profile value. Per
the *Visual Contract Deliverable* carve-outs (internal API / additive change),
no preview SVG is produced; Task T8 verifies the geometry numerically.

### Alternatives rejected

- **Derived multiplier off `slip.radial`** (`arm_excess ≈ 2·slip.radial`).
  Rejected — it asserts a physical law ("narrow-slot tightening is always ~2×
  the radial allowance") from a single printer/material data point, bakes it
  invisibly into code, and gives the user nothing to calibrate or override.
  Violates option-(b). The `slot` field keeps the printer-specific number in
  the user-tunable profile where it belongs.
- **`slot` on `ToleranceProfile`** (one value for all three grades). Rejected —
  narrow-slot tightening is grade-dependent like `radial`; one cross-grade
  value repeats the pre-nested flat-schema modelling error.
- **Adopt the dog-bone relief into production `TechnicAxleHole`.** Rejected —
  see *The concave corner* above.
- **Name the field `axle_cross_arm`.** Rejected — over-fits to one part; a
  future keyway / spline slot wants the same allowance. Named for the
  mechanism (narrow-slot FDM tightening), consumed today only by
  `TechnicAxleHole`.

---

## Data & Interface Contracts

- `FitGrade` gains `slot: float = 0.0`. Purely additive; all ~40 existing
  `FitGrade` consumers read only `.radial` / `.axial` and are unaffected.
- `TechnicAxleHole` public signature unchanged. Internal: `ARM_WIDTH` gains
  `+ 2·grade.slot`; `TIP_TO_TIP` unchanged.
- `cq_utils.axle_cross_section(tip_to_tip, arm_width, length)` — signature
  unchanged; `TechnicAxleHole` simply passes a larger `arm_width`.
- Profile JSON nested schema gains an optional `"slot"` key per grade;
  absent → `0.0`.

## Implementation Plan

Sequencing constraint (TL): land the schema change (T1–T2) **before** the
formula change (T3) — `grade.slot` must exist and default before anything
reads it.

- [x] **T1** — Add `slot: float = 0.0` to `FitGrade`; update its docstring
  (the three orthogonal allowances).
- [x] **T2** — `print_settings.py`: `_fitgrade_from_dict` and
  `_profile_from_nested` read/default `slot`. Confirm `_migrate_flat_to_nested`
  needs no change. Update the module docstring's schema description.
- [x] **T3** — `TechnicAxleHole`: `ARM_WIDTH += 2 * grade.slot`; update the
  class docstring.
- [x] **T4** — Migrate `machine_profiles_user.json` to the nested schema and
  add `slip.slot = 0.10`, preserving `slip.radial = 0.11` and the other
  grades. (User-local config — performed with the user's approval of this
  brief.)
- [x] **T5** — `machine_profiles.json.example`: add a commented `slot` line
  on one example grade.
- [x] **T6** — Tests (see below).
- [x] **T7** — Docs: `docs/lego-technic.md` *Tuning Tolerances* — note `slot`
  as the cross-arm calibration knob.
- [x] **T8** — Verify: with the migrated profile active, export a sample of
  `TechnicAxleHole` cross holes to `tmp/` and confirm the arm slot measures
  **2.25 mm** and tip-to-tip is **unchanged** (5.02 mm). This STEP is also the
  user's corner-confirmation print.

## Tests

| # | Test | Expected assertion | File |
|---|------|--------------------|------|
| 1 | `slot` defaults to 0.0 | `FitGrade(radial=.05, axial=.2).slot == 0.0` | `tests/test_env_parser.py` or a print-settings test |
| 2 | Nested entry omitting `slot` | `_fitgrade_from_dict` / loaded profile → `slot == 0.0` | print-settings test |
| 3 | Legacy-flat profile migrates with `slot=0.0` | a flat `slip_fit` entry → `slip.slot == 0.0` (pre-Stage-2b behaviour preserved) | print-settings test |
| 4 | `slot` widens the arm only | a profile with `slip.slot > 0` → `TechnicAxleHole.ARM_WIDTH` grows by `2·slot`, `TIP_TO_TIP` unchanged | `tests/test_axle_hole_gauge.py` |
| 5 | Shipped default unchanged | `TechnicAxleHole` at `fdm_standard` slip → arm `1.93`, tip-to-tip `4.90` (slot absent → 0.0) | existing test, still passes |
| 6 | Calibrated profile result | `bambu_p1s` (nested, `slip.slot 0.10`) → `TechnicAxleHole` arm `2.25`, tip-to-tip `5.02` | `tests/` |

## Success Criteria

1. `FitGrade.slot` exists, defaults `0.0`, documented; all existing `FitGrade`
   consumers unaffected.
2. `TechnicAxleHole` arm slot = `AXLE_HOLE_ARM_WIDTH + 2·radial + 2·slot`;
   tip-to-tip unchanged.
3. Shipped `machine_profiles.json` produces identical geometry to pre-Stage-2b
   (no `slot` value shipped).
4. Legacy-flat profiles still load (migrate with `slot = 0.0`).
5. The user's migrated `bambu_p1s` profile yields a 2.25 mm `TechnicAxleHole`
   arm slot; T8 sample STEP confirms it.
6. No CI regressions; linters clean.

## Out of Scope

- The production concave corner — the `concave_radius` fillet, corner blowout,
  any `corner_relief` parameter, the dog-bone relief. Deferred to a future
  **Stage 2c** corner gauge, gated on the T8 confirmation print.
- Generalising `slot` to non-axle-hole features — the field is named for the
  mechanism but `TechnicAxleHole` is its only consumer for now.
- Re-baselining the shipped `fdm_standard` profile.

## Known Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `slot ≈ 0.10` is n=1 — may not generalise to other printers. | It lives in the user-tunable profile, never a code constant; shipped `machine_profiles.json` keeps `slot` absent (0.0); the value is *demonstrated* in `machine_profiles.json.example`, never imposed. |
| The user's legacy-flat `machine_profiles_user.json` can't carry a nested-only `slot`. | T4 migrates it flat→nested explicitly, preserving `slip_fit 0.11 → slip.radial`. If missed, `slot` is silently ignored and cross arms print 0.20 mm tight — one wasted print. T4 is a named task, not an afterthought. |
| `slot` confused with `axial`. | `FitGrade` docstring states the three orthogonal allowances crisply; Test #4 pins `slot`→arm-only. |
| Shipping the schema change in the wrong order breaks every `FitGrade(...)` call and JSON load. | Sequencing constraint: T1–T2 (defaulted field + loader) before T3 (formula). |
| The production corner is still untested after Stage 2b. | Explicitly scoped out; T8's sample STEP is the confirmation print; Stage 2c follows if the corner binds. Flagged to the user. |

---

## Design Dialog Log

### Round 1 — TL architecture consult (2026-05-22)
**Designer question:** Where should the +0.20 mm cross-arm clearance live so it
propagates to all `TechnicAxleHole` consumers (option-(b): tune the profile,
not constants/params)? Should production adopt the gauge's dog-bone relief?

**TL recommendation:**
> Add `slot: float = 0.0` to `FitGrade` — additional half-extra applied only to
> narrow-slot features. Reject a derived multiplier (n=1, un-tunable, invisible).
> `slot` belongs on `FitGrade` not `ToleranceProfile` (grade-dependent). Schema
> change is ~6 defaulted-field one-liners; legacy migration needs no change; no
> non-axle consumer is touched. Ship `machine_profiles.json` with `slot` absent;
> demonstrate in `.example`. **Do not** adopt the dog-bone into production: it
> was a measurement instrument, the production corner is untested either way,
> and the gauge's `corner_relief 0.35` was a gauge-geometry compromise. Keep the
> `concave_radius` fillet; the corner is a separate future stage.

**Resolution:** Adopted as the Stage-2b design above. Designer refinement on the
corner: framed as test-first (the fillet corner is genuinely untested; the arm
widening de-risks it; T8 confirms in practice; Stage 2c only if it binds) —
same conclusion as the TL, reasoning made explicit for the user.

---

## Sign-off

### Author sign-off (drafting role — Step 3 termination)
- [ ] Domain expert co-sign  *(N/A — domain integrity gate NO)*
- [ ] Requester sign-off
- [x] Designer sign-off (drafting author)

### Independent reviewer sign-off (fresh-context — Step 3.5 termination)
- [ ] Independent TL
- [ ] Independent Developer

---

## Implementation Status
- [x] All Implementation Plan tasks completed
- [x] Test suite executed — result: **208 passed, 2 xfailed** (full
  `pytest`, unchanged pre-existing xfails). The 4 new `print_settings`
  `slot` tests (`test_tolerance_profile.py`) and the 4 new
  `TechnicAxleHole` arm tests (`test_axle_hole_gauge.py`) all pass.
- [x] No new linter / static-check errors — `flake8 .` clean (CI-equivalent
  invocation, exit 0); `tools/check_no_main_blocks.py` OK.
- Developer note: Stage 2b implemented with the Amendment's deltas applied.
  `FitGrade` gains `slot: float = 0.0` (T1); `print_settings.py` loader
  reads/defaults `slot` and the module docstring documents the three
  orthogonal allowances (T2) — `_migrate_flat_to_nested` unchanged, so
  legacy-flat profiles migrate to `slot = 0.0` as designed.
  `TechnicAxleHole.ARM_WIDTH = AXLE_HOLE_ARM_WIDTH + 2·radial + 2·slot`,
  `TIP_TO_TIP` unchanged (T3). Shipped `machine_profiles.json` `fdm_standard`
  gains `slip.slot = 0.10` (`free`/`press` 0.0); `_FALLBACK_PROFILES`
  mirrors it; `resin_precise`/`cnc` ship no `slot`.
  - **Verified shipped `fdm_standard` slip arm = 2.13 mm** (tip-to-tip 4.90)
    — Amendment Test #5; the intentional shipped-behaviour change.
  - **Verified `bambu_p1s` (nested, migrated) slip arm = 2.25 mm**
    (tip-to-tip 5.02) — Test #6.
  - Legacy-flat profile migrates to arm 1.93 mm (new divergence-pin test).
  - **T8 sample STEP** — `tmp/axle_cross_hole_sample.step`, built with the
    ambient migrated `bambu_p1s` profile (`VIBE_MACHINE_PROFILE` in `.env`):
    `ARM_WIDTH = 2.2500 mm`, `TIP_TO_TIP = 5.0200 mm`, single contiguous
    solid (topology assertion passed). This STEP doubles as the user's
    corner-confirmation print.
  - **T5 note for review:** strict JSON has no comment syntax, so the
    `slot`-documenting comment in `machine_profiles.json.example` is carried
    as a top-level `"_comment"` string key (a no-op for the loader — the
    `.example` file is never loaded) plus a live demonstrating `slip.slot`
    value on the `my_custom_ender3` example grade. The comment text itself
    states `_comment` is not a real profile.
  - One instruction-gap observation for the Admin: the *Visual Contract
    Deliverable* gate and the design brief both correctly classify Stage 2b
    as SVG-exempt (tolerance-field + clearance-term, no new class / axis /
    hole-pattern change) — no escalation, noted for completeness only.

---

## Post-Implementation Sign-Off

### TL Review
- [ ] **TL sign-off**
- TL review notes:

### Human Final Approval
- [ ] **Human approved** for merge / release
- Human notes:

---

## Amendment (2026-05-22) — Option (b): `slot` ships a non-zero default

**Status:** user-approved. Supersedes Section D ("Shipped vs user profiles"),
the Section B `_FALLBACK_PROFILES` note, Test #5, and the first Known-Risks
row. Origin: a Designer + TL re-consult after the user found "calibrate both
`slip.radial` and `slip.slot`" overly complicated and asked for a single
calibration knob.

### Decision

The `FitGrade.slot` field, the `print_settings.py` loader changes, the
`TechnicAxleHole` arm formula (`ARM_WIDTH = AXLE_HOLE_ARM_WIDTH + 2·radial +
2·slot`), and the corner scope-out all **stand unchanged**. What changes is
the *default value* of `slot`:

`slot` ships a **conservative non-zero default of 0.10** on the FDM profile,
so a user calibrates only `slip.radial` (the fussy, narrow-band tip-to-tip
number) and leaves `slot` at its default — the arm fit is forgiving (~0.20 mm
acceptable band), so it does not need per-printer calibration.

### Why 0.10 is a default, not an imposed calibration

Shipping `slip.slot = 0.10` widens every FDM axle-hole arm by ~0.20 mm —
legitimate, and categorically different from re-baselining `slip.radial`
(which Stage-1 Amendment 2 rejected):

- `0.10` is a **conservative geometric floor**. The shipped `fdm_standard.slip`
  (radial 0.05) arm goes 1.93 → `1.93 + 2·0.10 = 2.13 mm` — the *tight half*
  of the proven 2.15–2.35 working band. It moves every printer toward the
  known-good band without overshooting "loose".
- The arm fit is **forgiving** (~0.20 mm band, vs the near-one-hole tip-to-tip
  band). A single default has slack across printers; tip-to-tip does not —
  which is why tip-to-tip stays calibrated and the arm rides a default.
- Same class of decision as the shipped `fdm_standard.slip.radial = 0.05` — a
  reasonable default nobody calibrated to a specific printer, overridable by a
  power user on an unusual printer.

### Revised Section D — shipped vs user profiles

- **`machine_profiles.json` (tracked)** — `fdm_standard` gains
  `slip.slot = 0.10`; `free.slot` / `press.slot` ship `0.0` (no non-slip
  narrow-slot feature consumes them yet). `resin_precise` / `cnc` ship `slot`
  absent / `0.0` — they do not exhibit FDM narrow-slot tightening.
- **`_FALLBACK_PROFILES`** — mirror the shipped JSON (`fdm_standard` slip.slot
  0.10; resin/cnc 0.0).
- **`_fitgrade_from_dict`** — `default_slot` stays `0.0` (an omitted `slot`
  key → 0.0). The 0.10 lives in the shipped `fdm_standard` *data*, not the
  dataclass-load default — so a legacy-flat profile migrates to `slot = 0.0`
  and keeps pre-Stage-2b arm behaviour.
- **`machine_profiles_user.json` (this user, T4)** — migrate flat→nested and
  set `slip.slot = 0.10`, preserving `slip.radial = 0.11`. Result:
  `ARM_WIDTH = 1.83 + 2·0.11 + 2·0.10 = 2.25 mm` — exactly the Stage-2
  `W_good`. For this user the calibrated value and the shipped default
  coincide at 0.10.

### Revised tests

- **Test #5** — shipped `fdm_standard` + `fit="slip"` arm is now **2.13 mm**
  (`1.83 + 2·0.05 + 2·0.10`), not 1.93; tip-to-tip unchanged at 4.90. Re-spec
  the assertion (this is the intentional shipped-behaviour change).
- **New test** — a legacy-flat profile migrates with `slot = 0.0` → arm
  `1.93` (pins the legacy/nested divergence against silent regression).
- **Test #6** (`bambu_p1s` nested, `slip.slot 0.10`) → arm 2.25 — unchanged.

### Revised Known Risks — first row replaced

| Risk | Mitigation |
|------|-----------|
| Shipped `slip.slot = 0.10` widens every FDM axle-hole arm ~0.20 mm; a printer that tightens less than `bambu_p1s` could see a marginally loose arm. | `0.10` is a conservative floor — the shipped-profile arm (2.13) sits in the *tight half* of the proven 2.15–2.35 working band, so even a low-tightening printer stays inside it; `slot` is per-profile overridable. |
| Legacy-flat profiles migrate to `slot = 0.0` (arm 1.93) while nested `fdm_standard` ships `slot = 0.10` (arm 2.13) — a behaviour divergence. | Intentional and contract-correct (legacy-flat = stale config → pre-Stage-2b behaviour); pinned by the new migration test; called out in T2 / docs. |

### Alternatives rejected — added

- **Fixed `constants.py` arm-relief value** (`.env`-overridable) instead of a
  profile field. Rejected (TL) — splits one part's clearance across two
  override mechanisms (`machine_profiles_user.json` vs `.env`) and re-creates
  the Amendment-2 anti-pattern of printer clearance baked into a constant. The
  sound principle: all printer/material clearance → the profile, all fixed
  geometry → `constants.py`. "Fussiness" sets the default *value*, not the
  owning *module*.

### Implementation Plan delta

T1–T3 unchanged. **T4** — write `slip.slot = 0.10`. **T5** —
`machine_profiles.json.example`: `slot` now ships in `machine_profiles.json`
itself, so the example just needs a comment noting `slot` is an overridable
field. **T6** — tests per *Revised tests*. **New** — update
`_FALLBACK_PROFILES`. T7/T8 unchanged.

### Design Dialog Log — Round 2 (2026-05-22)

**User:** Two calibration numbers (`radial` + `slot`) is overly complicated;
wants one knob.

**Designer:** The +0.20 mm gap is physical — one number cannot carry two
measurements. But tip-to-tip is *fussy* and the arm is *forgiving* → the arm
need not be per-printer-calibrated; it can ride a default.

**TL:** Agrees — but that means *ship a non-zero default*, not *delete the
field* (wide-band-on-one-printer ≠ wide everywhere; keep `slot` overridable).
Reject the fixed-constant option. Ship `slot = 0.10` as a conservative floor.

**Resolution:** Option (b) — `slot` retained, ships `0.10`. User-approved
2026-05-22. The user also recorded a standing preference for minimal
calibration knobs.
