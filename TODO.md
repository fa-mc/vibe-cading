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

## Session backlog / parking lot

Short-lived items, ideas, and parked refactors that surfaced during a session
but are not actively being driven. Curated by PM. Promote to
[`.agents/plans/INDEX.md`](.agents/plans/INDEX.md) when an item earns a
design slot.

### Admin follow-ups

- **Upstream Security Rule to `core-agents`:** Propose the "Never Leak Secrets" rule (codified in `vibe/INSTRUCTIONS.md` prohibiting literal secrets in command histories/transcripts) upstream to the `core-agents` shared instruction set (e.g. `base/instructions/base.md`). This ensures all host platforms natively inherit the safeguard.

### Pre-OSS publication checklist (release-blockers for v1)

Added 2026-05-14 per user direction. These are gates on the v1 OSS publication — not deferred features. Owner: human contributor at release-prep time; PM curates status. Promote any non-trivial item to [`docs/design_plans/INDEX.md`](docs/design_plans/INDEX.md) before execution.

- ~~**Top-level `README.md` + getting-started.**~~ — **DONE 2026-05-28** via [PR #15](https://github.com/fa-mc/vibe-cading/pull/15). README audit completed; the calibration story is now front-and-center (header one-liner + TL;DR callout at top of §Print Tolerances); `tools/preview.py` + `tools/view.py` surfaced in §Adding a Model; §Models → §Featured Models with pointer to full `vibe_cading/` tree; getting-started flow walks clone → Dev Container → workspace-init → first preview/export → first build. Library-without-agents framing already present (the §Examples block — four runnable scripts under `examples/`).
- ~~**`CONTRIBUTING.md` audit.**~~ — **DONE 2026-05-28** via [PR #15](https://github.com/fa-mc/vibe-cading/pull/15). Expanded from 5 → 11 sections to cover every item in the original entry: License & CLA (§1, AGPLv3 + bot magic phrase + signatures path + AGPLv3-header rule for new `.py`), agentic workflow (§5 with `[docs/agentic-workflow.md](docs/agentic-workflow.md)` link + correct "two shipped subagents + human-Admin" framing), Project Conventions That Will Fail Your PR (§6 — AGPLv3 header, no-`__main__` blocks under `vibe_cading/`/`parts/`, no `ocp_vscode` imports outside `tools/view.py`, explicit `build.toml` registration, Visual Contract SVG, no inline-code-in-shell), CI Gates explainer (§8 — every check in `ci.yml` + `engine-api.yml`), Print Tolerances forward-pointer (§10).
- ~~**`examples/` directory.**~~ — **DONE (pre-session, status drift)**. Directory exists at [examples/](examples/) with four scripts (`lego_technic_beam.py`, `screw_cutter.py`, `gear_from_iso.py`, `snap_fit_hook.py`) covering the candidates listed; each runs under a vanilla CadQuery install and writes STEP + SVG to `examples/build/<name>/`. Cross-referenced from `README.md` §Examples (lines 27–43). Was already complete by the time of this update; the open status here was stale.
- **GitHub Actions CI — release-readiness pass.** **Substantially DONE 2026-05-28** via [PR #15](https://github.com/fa-mc/vibe-cading/pull/15): added `permissions: contents: read` to `ci.yml` + `engine-api.yml`; `pip` caching via new `requirements-ci.txt`; `python build.py` smoke step (which also enforces AGPLv3 headers via `tools/check_license_headers.py`); tightened `ocp_vscode` grep to catch bare `import ocp_vscode`; SHA-pinned `cla-assistant/github-action`; corrected CLA `path-to-document` URL (`vibe-cading/vibe-cading` → `fa-mc/vibe-cading`); documented `actions: write` provenance (commit `e6583e7` incident). `flake8`, `tools/check_license_headers.py`, `tools/check_no_main_blocks.py` already wired. **Remaining for full closure:** ~~wire `tools/check_topology.py` into `ci.yml` (file exists at `tools/check_topology.py` but isn't called from any workflow)~~ — **DONE 2026-05-29** via `ci-topology-check` PR (see [`docs/design_plans/2026-05-28-ci-topology-check_req.md`](docs/design_plans/2026-05-28-ci-topology-check_req.md)); add preview / section-slice asset-regen checks if desired; add a CI status badge to `README.md` once first post-publication green-build lands.
- ~~**Author `LICENSE-FAQ.md` at repo root.**~~ — **DONE 2026-05-29**. [`LICENSE-FAQ.md`](LICENSE-FAQ.md) authored at repo root covering all six recommended topics: (1) why AGPLv3 vs. MIT / Apache (copyleft + SaaS-loophole rationale); (2) printing parts is not "conveying" — output is yours, commercial sale of printed parts is fine; (3) modify-and-share triggers AGPLv3 source-publication + header rule; (4) network deployment triggers AGPLv3 §13 (offer source to remote users); (5) CLA vs. AGPLv3 relationship (CLA governs upstream contributions, not copyright assignment); (6) common-confusions table covering closed-source desktop app, internal SaaS, CI artifacts, tutorial snippets. Cross-linked from [`README.md`](README.md) §License and [`CONTRIBUTING.md`](CONTRIBUTING.md) §1.
- **Commercial / Dual-Licensing Setup.** Decide on a contact email address and update `README.md` and `LICENSE-FAQ.md` to explicitly offer commercial licenses for closed-source/SaaS use-cases.
- **Branch protection on `main` — apply atomically at the public flip (root-cause fix for [#40](https://github.com/fa-mc/vibe-cading/issues/40)).** Root cause of the unsigned in-wheel external lines (`xing-cqkd` in `vibe_cading/tools/view.py`, `93d5670`): `main` has **no protection** (`"protected": false`) and the CLA check is **advisory, not required** — so a PR merged without a recorded signature. A relicensing-grant CLA *document* alone does not fix this; the blocking control does. **Constraint:** branch protection / rulesets are **unavailable on a private repo on GitHub Free** (the rulesets API returns *"Upgrade to GitHub Pro or make this repository public"*); they unlock the instant the repo goes public — which is also the instant external contributors can first arrive. So this is **not landable now** — it must be applied **in the same change-window as flipping the repo public, before any announcement** (or pull GitHub Pro forward if protecting-while-private is wanted; low value — only the maintainer commits while private). Apply on `main`: (1) **Require a pull request before merging.** (2) **Require status checks to pass** and mark the **CLA Assistant job check required** — this repo uses CLA Assistant *Lite* (`contributor-assistant/github-action`), which gates via the **Actions job check** (job `CLAAssistant` in [`.github/workflows/cla.yml`](.github/workflows/cla.yml)), **not** a `license/cla` commit status — so **select it from the required-checks dropdown** (lists checks observed on recent PRs), never type a guessed context (a wrong name silently makes every PR unmergeable). (3) **Restrict who can push to `main`** so every contribution routes through a PR that hits the gate. **Recommended `enforce_admins: false`** — external contributors are never admins so they stay fully gated, while the maintainer keeps the [`TODO.md`-direct-push carve-out](CLAUDE.md) (fast-forward `main`); `enforce_admins: true` would break that carve-out and require an instruction-graph edit. Owner: human maintainer (needs repo-admin; the session fine-grained PAT lacks Administration write). Promote to a short go-public runbook in `docs/` at execution time.

### Deferred features (gated on real demand)

- **Pip-installable distribution + PyPI publication.** ✅ **Shipped 2026-06** (no longer deferred): packaged as a `hatchling` wheel (`pyproject.toml`, #30); gated release workflow with PyPI **trusted publishing** added ([.github/workflows/release.yml](.github/workflows/release.yml), #35/#36); the `vibe-cading` PyPI name **reserved** via a yanked `0.0.1` placeholder (`0.1.0` preserved for the first real release; the release gate stays closed until repo variable `PYPI_PUBLISH` is set). Versioning policy + release-cut process: [docs/releasing.md](docs/releasing.md). **Before the first real `v0.1.0` tag** (tracked in docs/releasing.md *Outstanding setup*): fix `__commit__` provenance (wheel-from-sdist loses `.git`), start `CHANGELOG.md`, and apply the one-line step-5 doc-mechanism correction.

### Parked refactors — from 2026-05-09 TL deep-modules review (resolved 2026-05-15)

The pre-OSS structural refactor (commits `efdc88a..a14f711`, landed 2026-05-15) subsumed or obsoleted every parked item:

- ~~Rename `SlipperGearBase` → `SlipperGearAssembly`~~ — slipper-gear was moved to `experiments/slipper_gear/` in commit `9ae6ae8` (Phase 1 T1.10), so this is now experimental R&D code outside the library's contributor-facing surface. Rename remains a nice-to-have for an `experiments/` cleanup pass but no longer a publication blocker.
- ~~Harmonize `vibe_cading/mechanical/__init__.py` re-exports~~ — **DONE.** Phase 7 T7.1 (commit `9ae6ae8`) demoted the mid-level package to empty per the two-level `__init__.py` discipline; leaf packages now own their own re-exports consistently.
- ~~Audit `cq_utils.tapered_arm_profile` / `archimedean_spiral_arc`~~ — **DONE.** Phase 1 T1.11 (commit `9ae6ae8`) moved both helpers (plus `fillet_z_edges`) to `experiments/slipper_gear/curves.py` since they had no second consumer. The deep-modules speculative-seam diagnosis was confirmed in action.
