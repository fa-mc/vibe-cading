# Requirements: Re-anchor `TechnicPinHole` to `profile.slip.radial`
<!-- Filename: 2026-05-26-pin-hole-slip-refactor_req.md  (tracked in git under .agents/plans/) -->

## Meta
- **Initiator role**: @designer (on behalf of @admin — human contributor)
- **Date**: 2026-05-26
- **Domain integrity gate**: **YES** — every `TechnicPinHole` consumer in the library shifts its printed bore diameter from the hardcoded `PIN_HOLE_PRINTED=4.85` constant to the calibrated `nominal + 2 * profile.slip.radial` formula. A wrong default fit grade (e.g. `fit="press"` instead of `fit="slip"`) would silently tighten every printed pin hole library-wide. Designer-as-domain-expert co-sign required at Step 3.5 and Step 5 Phase C.

---

## Problem Statement

The 2026-05-26 user calibration verification print (`tmp/verify_calibrated_fits.py`) confirmed that, at the calibrated `slip.radial = 0.11` setting in `print_profiles_user.json`:

- M3 clearance holes fit correctly (consumes `profile.free.radial`).
- M3 press-fit hex-nut pockets fit correctly (consumes `profile.press.radial`).
- Lego Technic cross axle hole fits correctly via the round envelope (`TechnicAxleHole` consumes `profile.slip.radial` + `profile.slip.slot`).
- **The Lego Technic round pin hole printed too tight** — because `TechnicPinHole` reads the bare `PIN_HOLE_PRINTED = 4.85` constant with no profile awareness, ignoring the printer-specific `slip.radial` that the user has already calibrated.

The pin hole's physical fit is governed by the same FDM round-feature shrink that drives `TechnicAxleHole.TIP_TO_TIP` — both are "round peg in printed socket" slip interfaces. Calibrating one but not the other is a contributor-onboarding trap: the user calibrates `slip.radial` against the axle-hole gauge, prints any pin-hole-bearing model, and gets a binding fit with no obvious next step. The taxonomy in [`docs/print-tolerances.md`](../docs/print-tolerances.md) §1 already classifies pin sockets as `slip` semantics; the implementation lags the taxonomy.

## User Story / Motivation

As a contributor who has calibrated `slip.radial` against the axle-hole gauge, I need every Lego Technic socket (pin hole AND axle hole) to consume my calibrated value, so that my printed parts fit Lego pins without needing a second per-feature calibration cycle.

## Functional Requirements

1. `TechnicPinHole.__init__` MUST accept a `profile: ToleranceProfile | str | None = None` keyword argument that resolves via the existing `_resolve_profile` helper pattern (`vibe_cading/mechanical/holes.py:41`) — `None` → lazy `get_profile()`, `str` → named lookup, instance → direct.
2. `TechnicPinHole.__init__` MUST accept a `fit: str = "slip"` keyword argument that selects the `FitGrade` off the resolved profile (`"slip"` / `"free"` / `"press"`), mirroring `TechnicAxleHole`'s convention. Default is `"slip"` (per `docs/print-tolerances.md` §1 — pin-in-socket = slip semantics).
3. The effective printed bore diameter MUST be computed as `PIN_HOLE_DIAMETER + 2 * profile.<fit>.radial`, replacing the current `PIN_HOLE_PRINTED` constant read in `DEFAULT_DIAMETER`.
4. `PIN_HOLE_DIAMETER` (the real-Lego nominal 4.8 mm) MUST remain unchanged. It stays as the geometric nominal — printer clearance is supplied by the profile, mirroring the `AXLE_HOLE_TIP_TO_TIP` pattern documented in `vibe_cading/lego/constants.py:78-90`.
5. `TechnicPinHole.standard(depth=...)` classmethod MUST remain on the public surface with profile-aware behavior (resolves to `get_profile()` at call time when `profile=None`). No new `from_profile()` alternative needed — keep the surface minimal.
6. The constructor MUST continue to support an explicit `diameter=` override that bypasses the profile path entirely (required by `tolerance_gauge.py:124`, which sweeps explicit pin diameters per offset). The interaction rule: if `diameter` is passed explicitly, it wins as-is and no profile widening is applied; if omitted, the bore is sized from `PIN_HOLE_DIAMETER + 2 * profile.<fit>.radial`.
7. `PIN_HOLE_PRINTED` MUST be deprecated with a one-window fallback (matching the PR #8 `machine_profiles.json` → `print_profiles.json` precedent):
    - Reading `PIN_HOLE_PRINTED` (whether the literal default `4.85` or a `.env` override) MUST emit a one-shot `DeprecationWarning` via the existing `_emit_deprecation_once` helper in `vibe_cading/print_settings.py`, identifying the user-facing migration path ("calibrate `slip.radial` in `print_profiles_user.json`").
    - The constant MUST continue to be importable for one deprecation window; removal scheduled for the OSS publication release.
    - The deprecation warning MUST NOT fire during normal `TechnicPinHole` use (the cutter no longer reads `PIN_HOLE_PRINTED`); it fires only when external code or a `.env` override actively references the legacy constant.
8. `docs/print-tolerances.md` §2.1 `radial` consumer table MUST gain an entry for `TechnicPinHole` under the `slip` grade, with file:line reference to the new bore-radius computation site.
9. `docs/print-tolerances.md` §1 worked-example table MUST gain (or `TechnicAxleHole`'s `slip` example MUST be extended to call out) `TechnicPinHole` as a second `slip`-grade `radial` consumer.
10. `docs/lego-technic.md` pin-hole section (~line 143, "Printed hole clearance" row) MUST be updated to reflect that printed clearance is now profile-driven via `slip.radial`, not a hardcoded `+0.1 mm` literal. The narrative MUST cross-reference the calibration workflow in `docs/print-tolerances.md` §4.
11. `.env.example` line 24 (`PIN_HOLE_PRINTED="4.85"`) MUST be annotated with a deprecation comment mirroring the existing `VIBE_MACHINE_PROFILE` deprecation prose at `.env.example:15`, naming `slip.radial` calibration in `print_profiles_user.json` as the replacement.
12. The 27-leaf-float `tests/test_tolerance_profile.py` T9b snapshot MUST remain bit-identical (this refactor does not touch any `FitGrade` field or shipped profile value).
13. Every non-pin consumer in the library (every `MetricMachineScrew`, `Bearing`, `Magnet`, `ClearanceHole`, `CounterboreHole`, `TechnicAxleHole`, etc.) MUST produce numerically identical printed tolerances before vs after this refactor.

## Non-Functional Constraints

- **Backward-compat for `.env`:** any user `.env` file carrying `PIN_HOLE_PRINTED="X.YZ"` MUST continue to load without crashing (just with a deprecation warning).
- **Backward-compat for callers:** the four production consumers (`servo_mount.py`, `servo_mount_half.py`, `tolerance_gauge.py`, `technic_beam.py`) MUST NOT require source changes to keep working — `profile=None` default in the new signature MUST resolve transparently via `get_profile()`. (The refactor MAY add a minor profile-awareness comment to those call sites but MUST NOT require a public-API change at any call site.)
- **`tools/calibrate.py slip`:** continues to be the canonical calibration command for the pin-hole printed fit; the calibration helper does NOT need a new `tools/calibrate.py pin` subcommand — pin hole inherits the same knob `AxleHoleGauge` already calibrates.
- **Deprecation noise floor:** the `PIN_HOLE_PRINTED` warning MUST be one-shot per process via `_emit_deprecation_once` (the helper already de-dupes); a build loop or test sweep MUST NOT spam stderr.
- **AGPLv3 header preserved** on every file touched in `vibe_cading/`.
- **No new pip dependencies** — `_emit_deprecation_once` and the existing `_env.py` `.env` loader are sufficient.

## Known Domain Constraints

- `PIN_HOLE_DIAMETER` (4.8 mm) is the real-Lego nominal envelope — it equals the cross-axle hole's `TIP_TO_TIP` envelope (`docs/lego-technic.md` line 88). Both round-envelope features deliberately share the same nominal and the same `slip.radial` calibration knob.
- `TechnicPinHole.DEFAULT_CB_DIAMETER = 6.2 mm` and `DEFAULT_CB_DEPTH = 1.0 mm` are real-liftarm counterbore-spec constants — they are NOT printer-clearance values and MUST NOT be touched by this refactor (`docs/lego-technic.md` lines 152-160 explains why `6.2 × 1.0` was chosen as the FDM-friendly edge of the Cailliau 6.0-6.2 × 0.8-1.0 range).
- `technic_beam.py` reads `TechnicPinHole._ENTRY_OVERCUT` and `TechnicPinHole.DEFAULT_CB_DIAMETER` as class attributes. These attribute accessors MUST remain available (the chamfer-edge selector at `technic_beam.py:199` and the cutter-depth literal at `technic_beam.py:161` both depend on them).
- `servo_mount.py:356` and `servo_mount_half.py:322` construct a half-counterbore variant via `TechnicPinHole(depth=STUD_PITCH, counterbore_depth=0.0).solid` and then bolt on a single bottom counterbore manually. This bypasses `.standard()` and consumes the new profile path through `__init__` directly — the new signature MUST keep this construction shape working.
- The deprecation warning emitter `_emit_deprecation_once` in `vibe_cading/print_settings.py:201-218` uses a one-shot per-key set (`_emitted_warnings`) and a stderr mirror; the new `PIN_HOLE_PRINTED` warning MUST use a stable key (e.g. `"const_PIN_HOLE_PRINTED"`) so a re-import within the same process does not re-fire.
- The `slip` semantics of the pin hole are taxonomy-correct: a real Lego pin is meant to slide into the printed socket with mild friction, not press-fit or float. This is consistent with `TechnicAxleHole`'s default of `fit="slip"`.

## Out of Scope

The following are explicitly NOT addressed by this refactor and MUST NOT be folded back in by a reviewer:

- **`slip.slot` arm-width recalibration** — the human's 2026-05-26 verification noted the axle arm slot was slightly tight at the calibrated `slip.slot = 0.10` shipped floor, but chose to defer this as a separate observation. Pin-hole geometry does not read `slip.slot` (round envelope, no narrow slot), so this refactor does not affect it. Track separately.
- **`TechnicPinHoleGauge` calibration class** — `slip.radial` is already calibrated by the existing `AxleHoleGauge` (`tools/calibrate.py slip`). Adding a separate pin-hole gauge would be a redundant 4th calibration model exercising the same knob, pushing the ≤5-gauge cap to 4 and adding a knob the user does not need to calibrate separately. Pin hole inherits the existing calibration cycle.
- **Changes to `TechnicAxleHole`** — already profile-aware in its current form; out of scope.
- **`PIN_HOLE_DIAMETER` rename** — that constant is the nominal Lego envelope and stays as-is.
- **New `FitGrade` field** — this refactor uses the existing `slip.radial` knob; no `slip.pin_radial` or similar new field is added. (See Open Question 6 for the v2 follow-up consideration.)
- **Counterbore dimension changes** (`TECHNIC_PIN_CB_DIAMETER`, `TECHNIC_PIN_CB_DEPTH`) — these are real-liftarm-spec constants from the Cailliau range, not printer-clearance values; they remain hardcoded.
- **`tolerance_gauge.py` redesign** — the pin-hole row in the gauge still works as a clearance-variant sweep (now exercising the same knob the axle gauge exercises). A potential rename of the row to "pin clearance variants" or a follow-up consolidation with `AxleHoleGauge` is captured as Open Question 3 for the TL co-design dialog but is not in scope here.
- **`tools/calibrate.py` changes** — no new subcommand; `tools/calibrate.py slip` already covers the knob.

## Open Questions
<!-- For the @designer + @TL Step-3 co-design dialog to resolve. -->
- [ ] **Q1 — `diameter=` vs `profile=` interaction precedence.** Recommended: explicit `diameter=` wins as-is with no profile widening (matches the `tolerance_gauge.py` sweep use case, where the gauge has already pre-computed `PIN_HOLE_DIAMETER + 2*offset`). Should the constructor emit a `UserWarning` when both are passed with non-default values, to flag the ambiguous combination? Or stay silent and document the precedence rule?
- [ ] **Q2 — Deprecation warning trigger point for `PIN_HOLE_PRINTED`.** Three options:
    - (a) on module import of `vibe_cading.lego.constants` (fires every process that touches anything in `lego/`; loudest signal, simplest implementation).
    - (b) on first attribute access via a module-level `__getattr__` (fires only when code actually reads the legacy constant; quieter, slightly more intrusive to implement).
    - (c) only when `.env` carries a non-default `PIN_HOLE_PRINTED` override (fires only on active legacy use; quietest, but invisible to a user who hasn't yet set the override and might be about to).
    Recommended: (b) first-access via module `__getattr__` — visible to anyone reading the constant, silent for users who already migrated. Trade-off: requires a small refactor to push `PIN_HOLE_PRINTED` behind a lazy accessor.
- [ ] **Q3 — `tolerance_gauge.py` pin-hole row semantics post-refactor.** The row currently sweeps `PIN_HOLE_DIAMETER + 2 * offset` per column to visualise the radial-allowance landscape. Once `TechnicPinHole` itself consumes `slip.radial`, this row effectively exercises the same knob as the axle-hole gauge. Options: (a) leave as-is — still useful as a visualisation; (b) rename the row label to "pin clearance variants" to clarify it's not a separate knob; (c) collapse the row out of `ToleranceGauge` entirely (deferred to `AxleHoleGauge`). Recommend (a) — the gauge is documentary, not a calibration source.
- [ ] **Q4 — `.env.example` line treatment.** Two options: (a) keep `PIN_HOLE_PRINTED="4.85"` line with a deprecation comment so users see "this exists but is deprecated, migrate to `slip.radial`"; (b) remove the line entirely and rely on a one-line note in the `# Lego Technic dimensional overrides` block header. Recommend (a) — discoverability for users with existing `.env` files mid-migration outweighs the line-count cost; matches the one-window-fallback pattern.
- [ ] **Q5 — Test coverage shape.** What new tests does this refactor require? Candidates:
    - T(a) `test_pin_hole_consumes_slip_radial` — assert `TechnicPinHole(depth=8.0).solid` cross-section radius equals `(PIN_HOLE_DIAMETER + 2 * profile.slip.radial) / 2` for the active profile.
    - T(b) `test_pin_hole_explicit_diameter_bypasses_profile` — assert `TechnicPinHole(depth=8.0, diameter=5.0)` produces a 5.0 mm bore irrespective of profile.
    - T(c) `test_pin_hole_printed_deprecation_warning` — assert reading `PIN_HOLE_PRINTED` emits one `DeprecationWarning` per process.
    - T(d) snapshot guard: assert `TechnicPinHole.standard(depth=8.0)` printed diameter against a pinned tuple for each shipped profile (`fdm_standard`, `resin_precise`, `cnc`), mirroring the T9b discipline.
    Recommend all four — T(d) is the bit-identical-tolerance guard that prevents silent regression.
- [ ] **Q6 — v2 future: do we need a pin-hole-specific `slip.pin_radial` knob?** The "one `slip.radial` value for both round-envelope features (pin + axle)" assumption rests on the empirical fact that FDM round-feature shrink is geometry-independent at this scale (both are sub-5 mm round bores). If a user's printer prints the 4.8 mm pin hole differently from the 4.78 mm axle envelope at the same `slip.radial`, they would need either two distinct knobs or per-feature material-specific calibration. This is unlikely on consumer FDM at this scale but worth flagging. Recommend: NOT add a new field now (YAGNI — no evidence of divergence); revisit if a user reports the failure mode.

---

## Human Confirmation Checkpoint
- [x] Requirements reviewed and confirmed by human _(2026-05-26, PM-relayed; Q1–Q6 deferred to TL+Designer Step-3 co-design)_
<!-- Do not proceed to design until this box is checked. -->
