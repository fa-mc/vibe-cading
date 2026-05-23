# Planned CAD Components Library

We are expanding this repository into a broader Code-CAD mechanical toolkit. Here are the components planned for future development:

## 🔩 Mechanical & Hardware Utilities
- [x] Add fastener drive types: Support generating drive sockets (hex, phillips, slotted, torx) into screw heads for accurate visual rendering and modeling.

## 🛠️ Architecture Refactors
- [x] Refactor hole generation: Extract hole logic from fastener `.to_cutter()` methods into dedicated feature classes (e.g. `ClearanceHole`, `CounterboreHole`, `TeardropHole`) to handle tolerance injections and specialized print profiles independently.
- [x] Establish initial FDM Tolerance baselines: Run grid searches to find the optimal global values for `radial_clearance` and `screw_radial_allowance` to dial-in a standard Bambu Studio hardware profile with `XY Hole Compensation = 0.0mm`.
- [x] Refactor primitive classes (Joints, Screws, Bearings, Axles) to seamlessly support `models.print_settings.ToleranceProfile` injections instead of hardcoded float parameters.
- [ ] Explore true 3D helical thread generation for screws/nuts (behind a `render_threads: bool` flag), carefully evaluating AGPL compliance, performance regressions, and OCCT boolean stability.
- [x] Revisit Technic axle hole clearance tuning (concave radius sweep failed). Issue may be systemic to the base `AXLE_TIP_TO_TIP` or `AXLE_ARM_WIDTH` parameters or FDM corner blowout rather than just the corner fillet. — Stage 1 (tip-to-tip) resolved by `AxleHoleGauge` — see `.agents/plans/2026-05-20-axle-hole-tip-to-tip-gauge`.
- [x] Stage 2 — cross-profile axle-hole validation (corner-relief parameter found unnecessary — confirmation print passed; see Stage 2c).
  - [x] Stage 2 (arm-width) — `AxleCrossHoleGauge` delivered: a row of `+` cross
    axle-hole cutters, tip-to-tip fixed (profile-derived), arm-slot width swept,
    with a dog-bone corner relief at each concave corner so the sweep isolates
    arm-slot width. See `.agents/plans/2026-05-21-axle-cross-hole-gauge_design.md`.
  - [x] Stage 2b (arm-slot clearance) — `AxleCrossHoleGauge` gave `W_good =
    2.25 mm`; added `FitGrade.slot` (narrow-slot FDM-tightening allowance) so
    `TechnicAxleHole` arm = `nominal + 2·radial + 2·slot`. Ships
    `fdm_standard.slip.slot = 0.10` as a conservative default. See
    `.agents/plans/2026-05-22-axle-cross-arm-slot-clearance_design.md`.
  - [x] Stage 2c — concave corner: confirmation print of
    `tmp/axle_cross_hole_sample.step` (2026-05-22) — 2 of 3 production cross
    holes fit well, 1 slightly tight, **none bind**. The `concave_radius 0.6`
    fillet corner is acceptable; no `corner_relief` parameter needed. The
    slightly-tight hole is FDM print-to-print variation (arm 2.25 = band
    centre, optimally placed). Cross axle-hole calibration complete.
- [ ] Build a guided calibration helper (e.g. `tools/calibrate.py`) that walks the user through the `AxleHoleGauge` print + fit test and writes the resulting `slip.radial` into `machine_profiles_user.json` — replacing the manual print → feel-test → compute → hand-edit-JSON workflow.
- [ ] Rename the "machine profile" concept — tolerance depends on the machine
  **and** the filament (and brand), not the machine alone. `machine_profiles*.json`
  → `print_profiles*.json`, `VIBE_MACHINE_PROFILE` → `VIBE_PRINT_PROFILE`; adopt a
  `<machine>__<material>[__<brand>]` user-profile key convention (e.g.
  `bambu_p1s__pla_overture`), keeping the generic shipped fallbacks
  (`fdm_standard`, `resin_precise`, `cnc`) as coarse defaults. This is a rename +
  key convention, **not** a structural change — the loader already accepts any
  key string, and one flat per-stack calibrated key is the honest model
  (machine/material clearances interact; do **not** build a machine×material
  composition matrix). Keep the old file + env-var names working as deprecated
  fallbacks for one transition window. Pre-OSS naming debt; also resolves the
  mismatch with the `ToleranceProfile` dataclass name. (Raised 2026-05-22.)
  - [ ] As part of this, rewrite the README "Print Tolerances & Calibration"
    section to document calibrating a per-printer-**and-filament** profile:
    the `<machine>__<material>` profile workflow, the `AxleHoleGauge` /
    `AxleCrossHoleGauge` print-and-measure procedure, and where the calibrated
    `slip.radial` value lands. The current section predates the rename and the
    Stage-2 gauge and is framed machine-only.
- [ ] Field-level profile merge in `_load_json_profiles` — change today's
  grade-level merge (where a user override of one `slip` field requires
  restating the whole grade dict) to **field-level**, so a
  `machine_profiles_user.json` entry like `{"fdm_standard": {"slip":
  {"radial": 0.11}}}` overrides only `radial` and inherits `axial` + `slot`
  from the shipped profile. Direct serve to the "fewer knobs" preference (see
  the `feedback-fewer-calibration-knobs` memory). Touches the shared profile
  loader's semantics — interacts with the legacy-flat migration path, the
  `_FALLBACK_PROFILES` fallback, and override layering — so it **needs a
  proper design-flow review** (`@designer` + `@tl` architecture consult,
  brief, then implementation) before any code change. (Raised 2026-05-23.)

## 🚀 Transition to "Open Core" Engine
Based on the new SaaS strategy, this repository (`vibe-cading`) will act as the public core engine for the `vibe-cading-platform`. We need to prepare it for external consumption:
