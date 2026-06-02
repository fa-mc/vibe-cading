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
    (Followed up 2026-05-28: default lowered to 0.3 mm on bambu_p1s +
    slip.slot 0.1125 — see
    `.agents/plans/2026-05-28-concave-radius-default_design.md`.)
- [x] Build a guided calibration helper (e.g. `tools/calibrate.py`) that walks the user through the `AxleHoleGauge` print + fit test and writes the resulting `slip.radial` into `machine_profiles_user.json` — replacing the manual print → feel-test → compute → hand-edit-JSON workflow. — **Re-scoped 2026-05-23**: narrow axle-only scope rejected at design Step-4 gate; replaced by the generic multi-knob calibration helper (≤5 gauges, M3-screw + M3-nut defaults with Lego axle as opt-in for delicate fits). Foundation pre-req shipped in [PR #8](https://github.com/fa-mc/vibe-cading/pull/8); Brief #2 (`.agents/plans/2026-05-23-calibration-helper-generic_req.md`) now unblocked and Designer-pending. SUPERSEDED prior-art at `.agents/plans/2026-05-23-calibrate-helper_*`.
- [x] Rename the "machine profile" concept — tolerance depends on the machine
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
  mismatch with the `ToleranceProfile` dataclass name. (Raised 2026-05-22.) —
  **Resolved 2026-05-24 by [PR #8](https://github.com/fa-mc/vibe-cading/pull/8)** (merge commit `dc877a7`):
  filename + env-var rename landed, `<machine>__<material>__<brand>` convention
  documented in the `print_settings.py` module docstring + README, deprecation
  emitter via `_emit_deprecation_once` honours legacy names for one window.
  See `.agents/plans/2026-05-23-print-profile-foundation_*`.
  - [x] As part of this, rewrite the README "Print Tolerances & Calibration"
    section to document calibrating a per-printer-**and-filament** profile:
    the `<machine>__<material>` profile workflow, the `AxleHoleGauge` /
    `AxleCrossHoleGauge` print-and-measure procedure, and where the calibrated
    `slip.radial` value lands. The current section predates the rename and the
    Stage-2 gauge and is framed machine-only. — **Resolved 2026-05-24 by PR #8**
    (T12 — README §"Print Tolerances & Calibration" rewritten + worked example for
    `<machine>__<material>` convention + field-level merge override example).
- [x] Field-level profile merge in `_load_json_profiles` — change today's
  grade-level merge (where a user override of one `slip` field requires
  restating the whole grade dict) to **field-level**, so a
  `machine_profiles_user.json` entry like `{"fdm_standard": {"slip":
  {"radial": 0.11}}}` overrides only `radial` and inherits `axial` + `slot`
  from the shipped profile. Direct serve to the "fewer knobs" preference (see
  the `feedback-fewer-calibration-knobs` memory). Touches the shared profile
  loader's semantics — interacts with the legacy-flat migration path, the
  `_FALLBACK_PROFILES` fallback, and override layering — so it **needs a
  proper design-flow review** (`@designer` + `@tl` architecture consult,
  brief, then implementation) before any code change. (Raised 2026-05-23.) —
  **Resolved 2026-05-24 by [PR #8](https://github.com/fa-mc/vibe-cading/pull/8)** (merge commit `dc877a7`):
  `_deep_merge_profiles` implements recursive leaf-wins merge with hard-error
  on type mismatch + null leaves (both with JSON-pointer-style key paths in
  the error message); T9b snapshot test pins 27 leaf-float values across
  `fdm_standard` / `resin_precise` / `cnc` to lock backward-compat against
  silent tolerance drift. Inline PR-review follow-ups (`3690705`) added
  null-leaf recursion into override-only sub-trees + dynamic `stacklevel` +
  once-guarded unknown-profile warning. Full design-flow trail with Step 3.5
  fresh-context reviewers + Phase B/C post-implementation reviewers (per
  `Domain integrity gate: YES`) at `.agents/plans/2026-05-23-print-profile-foundation_*`.
- [x] Visual-contract SVG size — investigate multi-variant gauge previews.
  The per-gauge iso_ne SVGs for `MThreeClearanceGauge` (404 KB) and
  `MThreeNutPocketGauge` (275 KB) shipped via [PR #10](https://github.com/fa-mc/vibe-cading/pull/10)
  exceed the visual-contract rule's "~10-25 KB each" guidance
  (`vibe/INSTRUCTIONS.md` §Visual Contract Deliverable). Live precedent
  shows `2026-05-15-lego-technic-beam_design_iso_ne.svg` already at 251 KB,
  so the guidance pre-dates multi-variant CAD previews. Two paths to
  evaluate: (a) tune projection complexity / render single-variant gauge
  previews to bring SVGs back under the budget; (b) update the
  visual-contract guidance to reflect multi-variant CAD reality and raise
  the size budget. Non-blocking for downstream work — the SVGs still serve
  the visual contract (axis, hole pattern, labels visible) and remain
  diffable as XML — but accumulating ~700 KB per design brief is repo
  bloat worth addressing before OSS publication. Phase B Independent TL
  flagged + recommended ACCEPT + DEFER. (Raised 2026-05-25.) —
  **Resolved 2026-05-29 by [PR #17](https://github.com/fa-mc/vibe-cading/pull/17).**
  Root cause was neither path (a) nor (b) as originally framed: the real
  driver was `tools/preview.py` emitting path coords at full 15-digit float
  precision (pure byte-waste). Fix = a post-export `_round_svg_coords` text
  transform rounding `d="..."` coordinates to 3 dp (1 µm). `showHidden=False`
  was evaluated and **rejected** by designer review — the dashed occluded
  edges are the primary cue for catching hole-axis errors, so hidden lines
  are kept. The two calibration gauges dropped precision-only (404→165 KB,
  275→116 KB); the guidance figure in `vibe/INSTRUCTIONS.md` was corrected to
  the measured post-rounding range with the `text()`-label heavy-tail caveat.
  Net tracked SVG footprint 1.5 MB → 1.0 MB.
- [x] Visual-contract SVG freshness — contracts silently drift from model
  code. PR #17's regeneration revealed 7 of 9 tracked design SVGs had drifted
  from current model code (beam pin-hole radius refactor; axle-gauge engraved
  `text()` labels absent from the committed contracts despite being in the
  model). Root cause: when a model class is refactored, nothing re-runs the
  Step-5 Phase-A SVG regeneration, so the committed visual contract goes
  stale and the `committed == regenerable` invariant silently breaks.
  Evaluate a CI freshness check (regenerate each tracked `_design_*.svg` from
  its source class + params and fail if the committed file differs beyond
  coordinate precision), or a lighter lint that flags design SVGs older than
  their source model file. (Raised 2026-05-29.)
  **Resolved 2026-06-01 (PR pending) — CI regenerate-and-compare check.**
  Added `visual_contracts.toml` (the SVG→`(class, view, params)` manifest)
  and `tools/check_visual_contract_freshness.py`, which reuses
  `tools.preview.export_previews` to regenerate each tracked `_design_*.svg`
  into a temp dir and byte-compares it against the committed file, plus a
  bidirectional coverage gate (unregistered tracked SVG → fail; manifest row
  with a missing target → fail).  Wired as the `Visual contract freshness`
  step in `.github/workflows/ci.yml` after `Topology check`.  The mtime-lint
  alternative was rejected (git does not preserve mtimes; meaningless on a
  fresh CI checkout).  Design: `.agents/plans/2026-05-29-visual-contract-freshness_design.md`.

## 🚀 Transition to "Open Core" Engine
Based on the ***REMOVED***, this repository (`vibe-cading`) will act as the public core engine for the `***REMOVED***`. We need to prepare it for external consumption:
