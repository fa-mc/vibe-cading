# Requirements: TechnicAxleHole default concave radius — 0.6 → 0.3
<!-- Filename: 2026-05-28-concave-radius-default_req.md  (tracked in git under .agents/plans/) -->

## Meta
- **Initiator role**: @admin (via @designer drafting)
- **Date**: 2026-05-28
- **Domain integrity gate**: NO

---

## Problem Statement
`TechnicAxleHole.DEFAULT_CONCAVE_RADIUS` is currently 0.6 mm, a value
validated 2026-05-22 (Stage-2c) on the maintainer's then-current printer.
Subsequent calibration on `bambu_p1s + PLA` produced a tighter, better-defined
profile (`slip.slot 0.10 → 0.1125`), and the in-script 2026-05-28 sweep
(`tmp/print_concave_sweep_2.py`, variants `0.35` and `0.30`) showed `0.30`
prints clean while `0.35` does not. With the corrected `slip.slot`, the
0.6 mm fillet is needlessly large — the inner corner valleys consume slot
wall and slow the print without contributing to fit. The shipped default
should reflect the current best evidence, with the per-call `concave_radius`
kwarg remaining the per-printer override path.

## User Story / Motivation
As a vibe-cading user printing a `TechnicAxleHole`-derived part on a
mainstream FDM machine with the shipped `fdm_standard` / a calibrated
`bambu_p1s`-style profile, I want the default inner-corner fillet to reflect
the most recent calibrated evidence (0.3 mm) so that I get a clean, well-fitting
`+` cross hole out-of-the-box without having to know about — or override —
the `concave_radius` kwarg.

## Functional Requirements
1. `vibe_cading/lego/cutters/technic_axle_hole.py` MUST set
   `DEFAULT_CONCAVE_RADIUS = 0.3` (down from `0.6`).
2. The `TechnicAxleHole` class docstring entry for the `concave_radius`
   parameter MUST state the new default (`0.3 mm`) and cite the validating
   evidence (2026-05-28, `bambu_p1s + PLA`,
   `slip.slot = 0.1125` + `slip.radial = 0.11`,
   sweep script `tmp/print_concave_sweep_2.py`).
3. The class docstring MUST note that `0.3` is best-current-evidence on one
   calibrated FDM stack, not a universally optimal value, and that users
   on other printers may override per-instance via the `concave_radius=`
   constructor kwarg (which is already public API — no new surface needed).
4. The constructor signature (`__init__`) and kwarg name MUST be unchanged.
   Existing callers that pass `concave_radius=...` explicitly MUST be
   bit-for-bit unaffected.
5. A regression-net unit test MUST assert
   `TechnicAxleHole(depth=8.0).concave_radius == 0.3` so the default cannot
   silently drift again without a failing test.
6. The `TODO.md` Stage-2c entry (line 24-29) MUST be annotated (footnote
   or inline parenthetical) clarifying that `0.6` was the maintainer's
   then-current-printer value and that the shipped default is now `0.3`
   per the 2026-05-28 `bambu_p1s` follow-up. The historical Stage-2c text
   itself MUST NOT be rewritten — only annotated.
7. `docs/lego-technic.md` §"Concave-corner blowout — verified adequate"
   (line ~321-333) MUST be updated: the parenthetical "(default 0.6 mm)"
   becomes "(default 0.3 mm)" and the surrounding narrative reconciled
   with the new evidence (the 2026-05-22 confirmation stays as history;
   the 2026-05-28 follow-up appends).

## Non-Functional Constraints
- **Backward compatibility (source).** Pure kwarg-default change — no
  signature change, no removed symbol, no renamed field. Source-level
  callers compile/import identically.
- **Backward compatibility (geometry).** Downstream `TechnicAxleHole`
  consumers — `lego_adapters/technic_axle_to_bearing_sleeve.py`,
  `lego_adapters/servos/shaft.py`,
  `lego_adapters/servos/shaft_body.py`,
  `lego_adapters/servos/sg90/servo_mount.py`,
  `lego_adapters/servos/sg90/servo_mount_half.py`,
  `lego/gears/gear_28t.py` — that do NOT pass
  `concave_radius=` will get slightly sharper inner-valley corners
  (radius `0.3` instead of `0.6`). This is a visible geometry change
  but NOT a tolerance/fit change: the cross-axle fit envelope is
  dominated by `AXLE_HOLE_TIP_TO_TIP + 2·slip.radial` (round envelope)
  and `AXLE_HOLE_ARM_WIDTH + 2·slip.radial + 2·slip.slot` (arm slot),
  both of which are unchanged.
- **`AxleCrossHoleGauge` unaffected.** That class uses dog-bone corner
  relief and explicitly *replaces* the `concave_radius` fillet
  (`vibe_cading/lego/axle_cross_hole_gauge.py:58-71`), so its sweep
  semantics are unchanged.
- **Pinned-bore profile snapshot tests unaffected.**
  `tests/test_technic_pin_hole_profile.py` pins `TechnicPinHole`
  bore diameters per profile and does not exercise `TechnicAxleHole`
  corner geometry, so the existing T9b snapshot does not need updating.
- **Test surface.** Single regression-net assertion (FR-5) is sufficient.
  A parametrized "still resolves at multiple radii" smoke test is OPTIONAL
  and at the developer's discretion; see Open Question Q3.

## Known Domain Constraints
- **`DEFAULT_CONCAVE_RADIUS` is a geometric kwarg default, not a profile
  knob.** It is intentionally NOT a field on `FitGrade` and MUST NOT be
  promoted to one as part of this task ("fewer calibration knobs" anchor;
  see `memory/feedback_fewer_calibration_knobs.md`).
- **Override path is already public.** `concave_radius=` is a constructor
  kwarg on `TechnicAxleHole.__init__`; per-printer divergence is handled
  by passing the kwarg, not by adding env-var or profile-field plumbing.
- **Fit envelope is owned by `slip.radial` + `slip.slot`.** The concave
  fillet does not participate in tip-to-tip or arm-width measurement; it
  only shapes the four inner valleys between perpendicular arms.
- **0.6 → 0.3 is a refinement, not a contradiction.** The 2026-05-22
  Stage-2c report ("0.6 acceptable, none binding") and the 2026-05-28
  follow-up ("0.3 prints clean at the corrected `slip.slot`") describe
  two valid points; the latter is shipped because it sits at the better-
  calibrated operating point.

## Out of Scope
- **No promotion to a `FitGrade` field** (e.g. `FitGrade.corner_radius`).
  User has explicitly rejected this path; the "fewer calibration knobs"
  anchor pushes back on adding profile fields for geometric defaults
  that do not enter the fit envelope.
- **No `os.getenv`-style env-var override for `concave_radius`.** The
  constructor kwarg already IS the override path.
- **No change to `AXLE_HOLE_TIP_TO_TIP`, `AXLE_HOLE_ARM_WIDTH`,
  `slip.radial`, `slip.slot`, or any `_FALLBACK_PROFILES` value.** This
  task touches one kwarg default only.
- **No change to `AxleCrossHoleGauge`.** Dog-bone corner relief is a
  separate code path; the `DEFAULT_CONCAVE_RADIUS` constant does not
  reach it.
- **No new `tools/calibrate.py` extension** to support `concave_radius`
  calibration. Calibration tooling targets the fit envelope
  (`slip.radial`, `slip.slot`); the concave fillet is a geometric default,
  not a calibrated knob.
- **No new public API.** No new kwarg, no new method, no new module.
- **No rewrite of the Stage-2c history in `TODO.md`.** History text stays;
  only a footnote/annotation is added.

## Open Questions
- [ ] **Q1 — Citation locus.** Where should the "0.30 validated on
  `bambu_p1s + PLA`, 2026-05-28" line live? Options: (a) only in the
  `concave_radius` kwarg docstring, (b) only in the class-level docstring,
  (c) both, (d) class docstring + an in-code comment next to the constant
  itself. Recommendation: (d) — a one-line comment on the constant
  ("# 0.3 validated 2026-05-28 on bambu_p1s; was 0.6 pre-2026-05-28")
  plus an updated kwarg-docstring line, since the constant is what a
  contributor edits and the docstring is what a user reads.
- [ ] **Q2 — TODO.md annotation form.** Inline parenthetical, dated
  footnote, or a new dated bullet beneath the Stage-2c entry? The
  existing TODO pattern (line 30 — "Re-scoped 2026-05-23") suggests an
  inline parenthetical with a date marker is the house style. TL to
  confirm or override.
- [ ] **Q3 — Test depth.** FR-5 mandates the equality assertion. Should
  the test ALSO include (a) a `pytest.parametrize` sweep over a few
  `concave_radius` values that asserts the cutter still builds (no
  `OCCT` blowup) and produces a single contiguous solid via the
  established `assert len(.solids().vals()) == 1` pattern, and/or
  (b) a default-vs-explicit equivalence check
  (`TechnicAxleHole(8.0).solid` identical to
  `TechnicAxleHole(8.0, concave_radius=0.3).solid`)? Designer leans
  "yes to (a), skip (b)" — (a) is cheap insurance against a future kwarg
  default change accidentally hitting an unbuildable edge; (b) duplicates
  what the equality assertion already implies.
- [ ] **Q4 — Should `docs/print-tolerances.md` §6 reference the
  `concave_radius` kwarg at all?** §6 ("When to Add a New Consumer /
  New Knob") and §6.1 ("When NOT to add a new field to `FitGrade`") is
  the natural home for the "don't promote geometric kwargs to `FitGrade`
  fields just because one printer wants a different value" rule. A
  one-paragraph addition there would memorialize the decision for future
  contributors who encounter the same pattern (e.g. a chamfer default
  that someone wants to calibrate). Open question: does that paragraph
  belong here, or as a separate follow-up doc task?
- [ ] **Q5 — Test file placement.** No `tests/test_technic_axle_hole.py`
  exists today (only `tests/test_technic_pin_hole_profile.py`). New file
  or fold the regression-net assertion into an existing test module?
  Designer recommends a new `tests/test_technic_axle_hole.py` — keeps
  the per-class test naming convention and gives a clean home for any
  future Q3-(a) smoke parametrize.

---

## Human Confirmation Checkpoint
- [x] Requirements reviewed and confirmed by human _(2026-05-28, PM-relayed; Q1–Q5 deferred to TL Step-3 co-design)_
<!-- Do not proceed to design until this box is checked. -->
