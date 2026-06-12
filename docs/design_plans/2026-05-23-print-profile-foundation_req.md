# Requirements: Print-Profile Foundation (rename + key convention + field-level merge)
<!-- Filename: 2026-05-23-print-profile-foundation_req.md  (tracked in git under .agents/plans/) -->

## Meta
- **Initiator role**: @designer (PM-spawned per user direction 2026-05-23 — re-scope of superseded `.agents/plans/2026-05-23-calibrate-helper_req.md`; Brief #1 of 2)
- **Date**: 2026-05-23
- **Domain integrity gate**: **YES**
  - Rationale: this brief changes the *semantics* of `_load_json_profiles()` —
    every model class in `vibe_cading/**` consumes its output via
    `get_profile()` and applies the resulting `FitGrade.radial / axial / slot`
    values to cutter geometry. A wrong field-level merge silently mis-applies
    tolerances across the entire library (every printed Technic adapter,
    every screw cutter, every bearing pocket). The rename + env-var change is
    tooling; the merge change is a *data contract* every model class depends
    on. The design-flow therefore requires a fresh-context Designer co-sign
    at Step 3 and Step 5 Phase C per the design-flow integrity-gate rule.

---

## Problem Statement

Three coupled debts in the print-tolerance subsystem must land together as one
structural pre-req before the generic calibration helper (Brief #2) can be
built on a stable base:

1. **Naming.** `machine_profiles*.json` and `VIBE_MACHINE_PROFILE` predate
   the realisation that printed tolerance depends on the **machine and the
   filament (and brand)**, not the machine alone. The current names mislead
   OSS contributors into thinking one profile-per-machine is the intended
   model. Rename to `print_profiles*.json` / `VIBE_PRINT_PROFILE`.
2. **Key convention.** With per-stack calibration becoming the honest model
   (one flat per-machine + per-material key, no composition matrix —
   `TODO.md` lines 38–40 explicitly forbid one), users need a documented key
   shape: `<machine>__<material>[__<brand>]`, e.g. `bambu_p1s__pla_overture`.
   The loader already accepts any string key — this is convention, not
   schema. Shipped generic fallbacks (`fdm_standard`, `resin_precise`,
   `cnc`) remain as coarse defaults.
3. **Field-level merge.** Today `_load_json_profiles()` performs a
   **grade-level** shallow merge — a user who wants to override only
   `slip.radial` must restate the whole `slip` dict (`radial` + `axial` +
   `slot`), or lose the shipped non-zero `axial = 0.20` and `slot = 0.10`.
   This directly contradicts the *fewer calibration knobs* preference: a
   single calibrated value (`slip.radial`) should not force the user to
   copy two unrelated values to keep them at their shipped defaults.
   Recursive deep-merge at the leaf level closes this gap and is a direct
   enabler of Brief #2's single-knob calibration write-back.

Brief #2 (`tools/calibrate.py` generic gauges + multi-knob helper) is blocked
on this brief: a calibration helper that writes `slip.radial` into a
non-existent profile, or that fights a grade-restating user file, is a
debt-on-debt deliverable.

## User Story / Motivation

As a **vibe-cading contributor maintaining a printer + filament inventory**,
I need **profile filenames, env var, key convention, and user-override
semantics that reflect the actual machine × material tuning reality**, so
that **a one-line `print_profiles_user.json` override
(`{"bambu_p1s__pla_overture": {"slip": {"radial": 0.11}}}`) calibrates the
one knob I measured and inherits every other shipped default unchanged —
and so that future readers of the codebase understand the *machine and
filament* tuning model from the names alone**.

Secondary persona: a **first-time OSS user cloning the repo** must continue
to work with their existing `machine_profiles_user.json` + `.env`
`VIBE_MACHINE_PROFILE=...` for one deprecation window, with a clear
warning telling them what to rename and when the old names stop working.

## Functional Requirements

### A. Rename (filesystem + env var)

1. The repository **MUST** rename the three tracked / template profile
   files:
   - `machine_profiles.json` → `print_profiles.json`
   - `machine_profiles.json.example` → `print_profiles.json.example`
   - `machine_profiles_user.json` (user-local, untracked) — the new name
     `print_profiles_user.json` **MUST** be the canonical filename the
     loader reads, writes, and documents. The old filename **MUST** remain
     a recognised fallback for one transition window (see FR9).

2. The repository **MUST** rename the env var `VIBE_MACHINE_PROFILE` →
   `VIBE_PRINT_PROFILE`. The new name **MUST** be the canonical name in
   all docs, `.env.example`, and code comments. The old name **MUST**
   remain a recognised fallback for one transition window (see FR9).

3. Every code site that reads the env var or the JSON filenames **MUST**
   be updated to the new names as primary, with old-name fallback logic
   localised to the loader / env-resolution helpers (not scattered).
   Concrete known consumers — to be verified exhaustively by TL during
   Implementation Plan drafting (see *Touchpoint Inventory* below) —
   include `vibe_cading/print_settings.py` (loader + resolver),
   `README.md` ("Print Tolerances & Calibration" section), `.env.example`,
   `vibe/commands/init-workspace.md` (the file-copy step), the
   `.claude/commands/init-workspace.md` runtime-alias mirror (regenerated
   by `tools/init-claude-runtime.sh` — verify it picks up the canonical
   change), and `tests/test_tolerance_profile.py`.

### B. `<machine>__<material>[__<brand>]` key convention

4. The repository **MUST** document the
   `<machine>__<material>[__<brand>]` key convention as the recommended
   shape for user-defined profile keys in `print_profiles_user.json`.
   Documented in: the `print_settings.py` module docstring, the README
   "Print Tolerances & Calibration" section, and the
   `print_profiles.json.example` file comments / sample entries.

5. The loader **MUST** continue to accept any string key (no schema
   validation on the key shape). The convention is documented, not
   enforced.

6. The shipped generic fallback keys (`fdm_standard`, `resin_precise`,
   `cnc`) **MUST** remain in `print_profiles.json` unchanged. They serve
   as the coarse-default profiles that calibration-less users fall back
   onto, and as the inheritance source for field-level merges (FR8) when
   a user defines a `<machine>__<material>` key that overrides only one
   field.

7. When `VIBE_PRINT_PROFILE` (or its legacy alias) names a key that does
   not exist in the merged profile set, the loader's behaviour **MUST** be
   one of (a) silent fallback to `fdm_standard`, (b) warn-to-stderr +
   fallback, or (c) hard error. The design-flow Step 3 dialog **MUST**
   resolve which (see Open Question Q2). The current code path silently
   returns `_fallback_profile(name)`, which classifies `name` by
   substring (`"resin"` → resin_precise, else fdm_standard) — that
   behaviour is the *de facto* (a) variant and is the most-likely-correct
   default to preserve.

### C. Field-level merge in `_load_json_profiles`

8. `_load_json_profiles()` **MUST** perform a **recursive deep-merge** of
   the user-overrides file onto the shipped-defaults file, with
   leaf-value-wins semantics. Concretely: a user entry
   `{"fdm_standard": {"slip": {"radial": 0.11}}}` **MUST** produce a
   merged `fdm_standard.slip` that carries `radial = 0.11` (from the
   user) AND `axial = 0.20` + `slot = 0.10` (inherited from
   `print_profiles.json`'s shipped `fdm_standard.slip`). The current
   grade-level shallow merge **MUST** be removed.

9. The merge **MUST** preserve every existing
   `machine_profiles_user.json` file in the wild unchanged. A user file
   that fully restates a grade (the only correct pattern under today's
   shallow merge) continues to produce identical resolved values under
   the new deep merge — restated leaves are leaves the user happens to
   re-declare, and the user value wins either way. Migration is a no-op
   for existing files.

10. The merge **MUST** interact correctly with the legacy-flat schema
    migration path (`_is_legacy_flat_entry`,
    `_migrate_flat_to_nested`): the migration **MUST** run *before* the
    merge, on both sides independently — i.e. a legacy-flat entry in
    either the shipped or the user file is migrated to nested first,
    then deep-merged. The design-flow Step 3 dialog **MUST** decide
    whether a legacy-flat *user* file plus a nested *user* override on
    the same key is a supported combination or a hard error (likely
    irrelevant in practice, but spec it for completeness).

11. The `null` JSON value in a user-override leaf position is a
    semantic the design-flow Step 3 dialog **MUST** resolve (see Open
    Question Q3): candidates are (a) "reset to shipped default"
    sentinel, (b) load as Python `None` and let the dataclass field
    cast raise, (c) reject `null` at load time with a clear error.
    Recommend (c) on the *fewer surprises* principle — `null` is not a
    valid tolerance value and silently substituting a default is a
    foot-gun.

### D. Backward compatibility (deprecation window)

12. The deprecation window covers BOTH the env var
    (`VIBE_MACHINE_PROFILE`) AND the file names (`machine_profiles.json`,
    `machine_profiles_user.json`). During the window:
    - If `print_profiles.json` exists, it **MUST** be loaded; otherwise
      `machine_profiles.json` **MUST** be loaded as a fallback.
    - If `print_profiles_user.json` exists, it **MUST** be loaded;
      otherwise `machine_profiles_user.json` **MUST** be loaded as a
      fallback.
    - The new file name takes precedence: if both new and old exist on
      either side, the new is loaded and the old is **ignored** (with a
      warning — see FR13).
    - If `VIBE_PRINT_PROFILE` is unset and `VIBE_MACHINE_PROFILE` is set,
      the legacy value **MUST** be honoured.

13. When a legacy name (file or env var) is consumed via the
    fallback path, a deprecation warning **MUST** be emitted. The
    warning mechanism (stderr `print`, Python `warnings.warn(...,
    DeprecationWarning)`, or both) is Open Question Q1. The warning text
    **MUST** name the legacy item, the canonical replacement, and the
    cutover criterion (FR14).

14. The cutover criterion — when the legacy fallbacks are removed —
    **MUST** be one of:
    - (a) the first release tagged ≥30 days after this brief lands;
    - (b) the first release that includes an OSS-public announcement of
      the rename;
    - (c) a hardcoded version cut (e.g. v0.2.0).
    The design-flow Step 3 dialog **MUST** pick one and document it in
    the README + the deprecation-warning text. Recommend (b) — the
    project is pre-OSS, no users are running pinned releases, the cutover
    can be the same release that announces OSS publication, and the
    transition window is *announced*, not *time-elapsed*.

15. The README "Print Tolerances & Calibration" section **MUST** be
    rewritten to (i) document the new names as canonical, (ii) document
    the `<machine>__<material>[__<brand>]` key convention with an
    example, (iii) document the field-level merge with a minimal-override
    example (single `slip.radial` line), (iv) name the deprecation
    window and the legacy fallbacks, and (v) cross-reference the
    calibration helper (Brief #2) once it exists — for this brief, a
    forward-pointer placeholder is acceptable.

## Non-Functional Constraints

- **Backward-compatibility floor.** Every existing
  `machine_profiles_user.json` in the wild (the maintainer's own + any
  pre-OSS external tester) **MUST** load without modification and resolve
  to identical numeric tolerances. The deep-merge change is a
  *superset* of today's grade-level merge — a restated grade continues to
  work because leaf-level user-wins absorbs grade-level user-wins.

- **No new third-party pip dependencies.** The deep-merge must be
  implemented with the standard library (a ~10-line recursive helper).
  No `mergedeep`, no `deepmerge`, no equivalent. Matches the project's
  no-`python-dotenv` discipline.

- **Loader runtime budget.** `_load_json_profiles()` is called inside
  `get_profile()`, which is called by every model class on construction.
  The deep-merge **MUST NOT** materially slow profile resolution
  (target: no measurable regression on a single-class
  `tools/preview.py` invocation; cold-import time dominated by CadQuery).

- **Atomicity is not in scope.** Profile *writes* (atomic tempfile +
  rename) are Brief #2's concern. This brief is read-side only.

- **Pre-OSS rename is cheap.** Per `core-agents:core-agents-rule-placement`
  and the project's pre-OSS state, this is the right moment to land the
  rename. Post-OSS, every external user would have to migrate; pre-OSS,
  only the maintainer does.

## Known Domain Constraints

- **Profile-schema ownership.** `vibe_cading/print_settings.py` is the
  sole authority for profile JSON shape, migration, and resolution.
  Every helper added by this brief (deep-merge, dual-filename resolution,
  dual-env-var resolution, deprecation warning) **MUST** live in
  `print_settings.py` or a `print_settings_*` private module — not
  scattered into `lego/constants.py`, `_env.py`, or model classes.

- **Active-profile resolver is `get_default_profile_name()`.** Currently
  returns `os.getenv("VIBE_MACHINE_PROFILE", "fdm_standard")`. This is
  the single env-var consumer site for the rename. Model classes call
  `get_profile()` (which calls `get_default_profile_name()`); none call
  `os.getenv("VIBE_MACHINE_PROFILE")` directly — verified by repo-wide
  grep (2026-05-23): the only matches are in `print_settings.py` itself
  + `README.md` + `.env.example` + `TODO.md`. No model-class code change
  is required for the env-var rename.

- **The `ToleranceProfile` and `FitGrade` dataclass field sets are
  invariant** under this brief. No new fields, no removed fields, no
  renamed fields. Brief #2's "which knobs to expose" conversation is
  *separate* — and that conversation also does not happen in this brief.

- **`.env` parsing is via `vibe_cading/_env.py`'s `load_env_file()`.**
  Both `print_settings.py` and `lego/constants.py` call it at module
  load; the env-var rename rides through this existing path. No change
  to `_env.py` is required.

- **`_FALLBACK_PROFILES` is the disaster-recovery floor.** Used only
  when both JSON files are unreadable. The fallback's keys
  (`fdm_standard`, `resin_precise`, `cnc`) must remain — they are the
  same keys the shipped `print_profiles.json` defines, so removing or
  renaming them would diverge disaster-recovery from steady-state.

## Out of Scope

- **`tools/calibrate.py` (the generic calibration helper).** Brief #2.
  This brief produces the data-contract foundation the helper needs;
  the helper itself is a separate design-flow.
- **New gauge model classes (M3 screw hole for slip, M3 nut for press,
  any other generic gauge).** Brief #2 — they are the calibration
  helper's input geometry, not the profile system's concern.
- **A machine × material composition matrix.** `TODO.md` lines 38–40
  explicitly forbid this. One flat per-stack calibrated key is the
  honest model. Even if the deep-merge makes composition tempting (a
  user could define a `bambu_p1s` base + a `pla_overture` overlay and
  merge them), the documented user-facing pattern remains: one key per
  (machine, material) pair, calibrated as a unit.
- **Renaming the `ToleranceProfile` dataclass.** `TODO.md` notes this
  as an aside but does not commit to it. This brief recommends keeping
  the dataclass name — the rename touches one repository constant
  rename + a class name that is read by every consumer of
  `get_profile()`, and the value is cosmetic. Flag as a future cleanup
  if the OSS pre-flight audit re-surfaces it.
- **Changes to the `FitGrade` / `ToleranceProfile` dataclass field
  set.** No new fields, no removed fields, no renamed fields. The
  "which knobs to expose to the user" conversation is a separate
  brief — it intersects with Brief #2's multi-knob scope but is not
  decided by either brief in isolation.
- **`tools/gen_engine_api.py` / `engine_api.json` regeneration.** The
  `ToleranceProfile` dataclass shape does not change; the engine-API
  extractor walks model classes' public methods (`solid`, `to_cutter`,
  `from_size`, etc.), not the profile system. Open Question Q5 asks
  TL to confirm at Step 3 that regeneration is a no-op — but if it
  *is* a no-op, no code change to the extractor is needed and this
  bullet stays a carve-out. If TL finds the extractor names profile
  fields anywhere, that's a single regeneration step, not an
  architecture change.
- **Migrating the shipped `machine_profiles.json` to use the new
  `<machine>__<material>` key convention.** The shipped file keeps its
  generic-fallback keys (`fdm_standard`, `resin_precise`, `cnc`); the
  convention only governs user-defined keys in
  `print_profiles_user.json`.
- **Pre-existing `__main__` blocks, license headers, or any unrelated
  hygiene.** Scope discipline.

## Touchpoint Inventory

Flat enumeration of files known (via repo-wide grep on
`VIBE_MACHINE_PROFILE` / `machine_profiles` / `machine_profiles.json`
filename strings, 2026-05-23) to require edit or move under this brief.
TL turns this into a sequenced Implementation Plan.

**File moves (3):**
- `machine_profiles.json` → `print_profiles.json`
- `machine_profiles.json.example` → `print_profiles.json.example`
- `machine_profiles_user.json` (local, untracked) → `print_profiles_user.json`
  *(NOTE: this is the maintainer's own untracked file; the rename
  operation is a `git mv` for tracked files and a documented
  local-rename + legacy-fallback for the user file. No tracked file
  contains user data.)*

**Code edits (1 module — all loader/resolver logic localised here):**
- `vibe_cading/print_settings.py`
  - `get_default_profile_name()` — read `VIBE_PRINT_PROFILE`, fall
    back to `VIBE_MACHINE_PROFILE` with deprecation warning.
  - `_load_json_profiles()` — read `print_profiles.json` →
    `machine_profiles.json` fallback; read `print_profiles_user.json` →
    `machine_profiles_user.json` fallback; emit deprecation warning on
    legacy-name use; replace grade-level shallow merge with recursive
    deep-merge.
  - Module docstring (lines 16–73) — update env-var name, file names,
    document key convention, document field-level merge with an
    example, document `null` handling per Q3 resolution.
  - New helper: `_deep_merge_profiles(base: dict, override: dict) ->
    dict` (recursive, leaf-wins).
  - New helper: deprecation-warning emitter (mechanism per Q1
    resolution).

**Test edits (1):**
- `tests/test_tolerance_profile.py` — add field-level-merge tests
  (override `slip.radial` only, assert `axial` + `slot` inherited);
  add legacy-name-fallback tests (env var + both file names); add
  deprecation-warning capture tests. Existing test cases **MUST**
  continue to pass unchanged (backward-compat floor).

**Doc edits (3):**
- `README.md` — rewrite the "Print Tolerances & Calibration" section
  per FR15.
- `.env.example` — rename `VIBE_MACHINE_PROFILE` → `VIBE_PRINT_PROFILE`
  in any example line.
- `vibe/commands/init-workspace.md` — update the
  `machine_profiles.json.example → machine_profiles_user.json` copy
  step to the new filenames. The mirrored
  `.claude/commands/init-workspace.md` is regenerated by
  `tools/init-claude-runtime.sh` — TL confirms during the
  Implementation Plan whether re-running the scaffolder picks it up
  or whether the runtime alias also needs a manual edit.

**Verify-no-change (TL confirms during Implementation Plan):**
- `tests/test_env_parser.py` — `_env.py`'s parser is generic; the
  env-var rename does not touch it.
- `.github/workflows/ci.yml` — repo-wide grep returned no matches on
  `VIBE_MACHINE_PROFILE` or the profile filenames. Confirm during
  implementation that CI does not reference them via globbing or
  cached path.
- `.gitignore` — confirm `machine_profiles_user.json` rule is
  generalised or extended to also cover `print_profiles_user.json`.
- `engine_api.json` / `tools/gen_engine_api.py` — confirm regeneration
  is a no-op per Open Question Q5.
- Every `vibe_cading/**/*.py` and `parts/**/*.py` — confirm none
  references the legacy env var or filename directly (grep already
  confirms; TL re-verifies during Implementation Plan as a routine
  precaution).

Approximate file count: **3 moves + 1 code module + 1 test module + 3 doc
edits = 8 mandatory edits, ~4 verify-no-change touchpoints.**

## Open Questions

<!-- Unresolved questions the TL-led design dialog (Step 3) must answer before sign-off. -->

- [ ] **Q1 — Deprecation-warning mechanism.** Choose: (a) stderr
  `print(f"DEPRECATION: ...")` on every legacy-name consumption, (b)
  Python `warnings.warn(..., DeprecationWarning, stacklevel=2)`
  (filtered to default by user's `warnings` config), (c) both — stderr
  for visibility, `DeprecationWarning` for programmatic filtering. Each
  has a trade-off: (a) noisy for repeat reads (the loader runs on
  every model construction), (b) silent by default in CPython
  (`DeprecationWarning` is hidden unless the user runs `python3 -W
  default`), (c) belt-and-suspenders. Recommend (b) emitted once per
  process via `warnings.warn` + a module-level `_emitted_warnings: set`
  guard, *or* a one-line stderr emit gated on a similar set — the loop
  emission is the real foot-gun. TL picks.

- [ ] **Q2 — Behaviour when `VIBE_PRINT_PROFILE` names a key not in
  the merged profile set.** Today's code falls through to
  `_fallback_profile(name)`, which substring-matches `name` against
  `"resin"` / `"cnc"` and silently returns a default. Options: (a)
  preserve today's silent substring-fallback, (b) warn-to-stderr +
  fall back to the substring match, (c) hard `ValueError` listing the
  known keys, (d) warn-to-stderr + fall back to `fdm_standard` (drop
  the substring-classification heuristic — under the new key
  convention, `<machine>__<material>` strings won't reliably contain
  `"resin"` or `"cnc"`, so the substring match becomes accidental).
  Recommend (d): the substring heuristic was a stopgap; under the new
  convention an unknown key is most-honestly an FDM-standard fallback
  with a visible warning. TL picks.

- [ ] **Q3 — `null` semantic in user-override leaf position.** Spec
  what `{"fdm_standard": {"slip": {"radial": null}}}` does. Options:
  (a) "reset to shipped default" sentinel (semantically convenient,
  but invents a non-JSON convention), (b) load as Python `None` and
  let `_fitgrade_from_dict`'s `float(...)` cast raise `TypeError`
  with the offending file path in the error message, (c) reject
  `null` at deep-merge time with a clear `ValueError` naming the
  key path. Recommend (c) — `null` is not a valid tolerance and
  silent substitution is a foot-gun; explicit rejection is the
  least-surprise behaviour. TL picks.

- [ ] **Q4 — `<machine>__<material>` separator.** `TODO.md` line 34
  uses `__` (double underscore). Alternatives considered: `-`
  (reads cleaner but collides with hyphenated machine names like
  `bambu-p1s`), `.` (collides with JSON-pointer-style nested-key
  notations and looks like a file extension), `/` (path-like but
  invalid in many filesystem contexts and shell-globs poorly).
  `__` survives shell-glob, doesn't collide with hyphenated names,
  reads ugly. Recommend keeping `__` per `TODO.md` — the ugliness is
  the price of separator-collision avoidance. TL confirms or picks
  alternative.

- [ ] **Q5 — `engine_api.json` regeneration.** Confirm whether the
  rename touches the engine-API extractor (`tools/gen_engine_api.py`)
  or its generated artifact (`engine_api.json`). The extractor walks
  model classes' public surface, not the profile system, so the
  expected answer is no-op. TL verifies by reading the extractor and
  grepping `engine_api.json` for any reference to the legacy names.
  If a regeneration *is* needed, it is a single `python3
  tools/gen_engine_api.py` step, not a code change — but
  Implementation Plan must include it.

- [ ] **Q6 — Cutover criterion for the deprecation window** (per
  FR14). Pick (a) time-based ≥30 days, (b) announced-with-OSS-publication,
  (c) hardcoded version cut. Recommend (b) — pre-OSS state, no pinned
  external users, the OSS announcement is the natural cutover boundary.
  TL confirms.

---

## Human Confirmation Checkpoint
- [x] Requirements reviewed and confirmed by human _(2026-05-23, PM-relayed; Q1–Q6 deferred to TL+Designer Step-3 co-design)_
<!-- Do not proceed to design until this box is checked. -->
