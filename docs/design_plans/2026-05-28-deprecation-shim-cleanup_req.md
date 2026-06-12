# Requirements: OSS-publication deprecation hard-cuts (`machine_profiles*.json` filenames + `PIN_HOLE_PRINTED` constant)
<!-- Filename: 2026-05-28-deprecation-shim-cleanup_req.md  (tracked under .agents/plans/) -->

> **Path C — direct PR, no separate design brief.**  Following the
> [2026-05-28 env-var prefix-drop](2026-05-28-env-var-prefix-drop_req.md)
> precedent: both targeted deprecations were already designed and
> scheduled "for removal at the OSS publication release" in their own
> docstrings (`print_settings.py:104`, `lego/constants.py:49`).  This PR
> executes that scheduled hard-cut; the design contract was set when the
> shims were introduced (PR #8 for the file-name shim, PR #12 for the
> `PIN_HOLE_PRINTED` shim).  Failure mode is "loader/import raises or
> returns wrong value" — caught by the existing tests after we adapt them
> + one positive resolver test.

---

## Meta
- **Initiator role**: human contributor (acting as Admin)
- **Date**: 2026-05-28
- **Domain integrity gate**: **NO** — pure deletion of two pre-scheduled
  deprecation shims.  No `_FALLBACK_PROFILES` / `FitGrade` /
  `_deep_merge_profiles` / `TechnicPinHole` / `TechnicAxleHole` field
  touched.  The 27-leaf T9b shipped-profile snapshot remains
  bit-identical.  Geometric output of every shipped CadQuery class is
  invariant under the cleanup.

## Problem Statement

Two orthogonal deprecation shims live in-tree.  Each was introduced with
an explicit "removed at the OSS publication release" sunset clause that
is visible in both the source code and the user-facing README:

1. **Filename shim** (PR #8, merged 2026-05-24).
   `_resolve_shipped_file()` and `_resolve_user_file()` in
   [vibe_cading/print_settings.py:498-562](../../vibe_cading/print_settings.py#L498-L562)
   honour the legacy filenames `machine_profiles.json` /
   `machine_profiles_user.json` alongside the canonical
   `print_profiles.json` / `print_profiles_user.json`.  Four
   `_emit_deprecation_once(…)` call sites
   (`shipped_file_both_present`, `shipped_file_legacy_only`,
   `user_file_both_present`, `user_file_legacy_only`) carry the
   deprecation message and the OSS-publication-removal promise.

2. **`PIN_HOLE_PRINTED` constant shim** (PR #12, merged 2026-05-26).
   [vibe_cading/lego/constants.py:109-141](../../vibe_cading/lego/constants.py#L109-L141)
   defines a PEP 562 `__getattr__` hook that returns
   `float(os.getenv("PIN_HOLE_PRINTED", "4.85"))` plus a one-shot
   `DeprecationWarning` on every read.  No callsite under
   `vibe_cading/` reads the name any more — the migration
   (`TechnicPinHole` now consumes `profile.<fit>.radial`) was completed
   by PR #12.  The hook exists solely as a soft landing for any
   downstream user still importing the legacy constant.

The pre-OSS-publication window is the right time to execute both
hard-cuts simultaneously:
- The user universe is the maintainer + possibly a small number of
  private-fork early testers (same population as PR #14's env-var
  hard-cut).
- The README already publicly promises both removals
  ([README.md:186](../../README.md#L186) and the equivalent
  `constants.py:49` source comment).
- Both shims add resolver-chain depth and warning-emission noise to
  every `pytest` / `tools/*.py` invocation when the legacy file or
  constant is present.
- Carrying either shim through OSS publication anchors a contract that
  the README explicitly disclaims — a new contributor reading the
  README and the source code would receive contradictory signals about
  which names are live.

## User Story / Motivation

As the project maintainer (and the future OSS contributor base), I need
both deprecated shims to be removed in a single coordinated PR before
OSS publication so that:
- The loader resolves a single canonical filename per slot (shipped +
  user), with no dual-path emission machinery.
- `vibe_cading.lego.constants` exposes only the names that are part of
  the live public surface — no PEP 562 hook redirecting to a legacy
  env-overridable value.
- The README, in-source docstrings, and tests are mutually consistent
  about the live API surface at the moment of OSS publication.

## Functional Requirements

1. **FR1 — Drop the shipped-file legacy fallback.**
   `_resolve_shipped_file()` in
   [vibe_cading/print_settings.py](../../vibe_cading/print_settings.py)
   MUST be reduced to: return `print_profiles.json` if it exists, else
   `None`.  The `machine_profiles.json` branch + both
   `shipped_file_*` `_emit_deprecation_once(…)` call sites MUST be
   removed.

2. **FR2 — Drop the user-file legacy fallback.**
   `_resolve_user_file()` in
   [vibe_cading/print_settings.py](../../vibe_cading/print_settings.py)
   MUST be reduced to: return `print_profiles_user.json` if it exists,
   else `None`.  The `machine_profiles_user.json` branch + both
   `user_file_*` `_emit_deprecation_once(…)` call sites MUST be
   removed.

3. **FR3 — Module-docstring refresh.**  The
   [`vibe_cading/print_settings.py`](../../vibe_cading/print_settings.py)
   module docstring's **Deprecation window** section MUST drop the
   `machine_profiles*.json` paragraph (lines 99-104).  The
   `VIBE_PRINT_PROFILE` / `VIBE_MACHINE_PROFILE` paragraph
   (lines 106-110, kept by PR #14 for historical record) MAY remain or
   be pruned — designer/implementer choice; the post-OSS audience does
   not need the migration history.  Recommendation: **drop both
   paragraphs entirely** — the module is now resolver-chain-clean.

4. **FR4 — Drop `PIN_HOLE_PRINTED` `__getattr__` hook.**
   The module-level `__getattr__` function in
   [vibe_cading/lego/constants.py:111-141](../../vibe_cading/lego/constants.py#L111-L141)
   MUST be removed in its entirety.  The deprecation-block comment at
   lines 47-50 MUST be removed.

5. **FR5 — `_emit_once` machinery preservation.**
   The `_emit_once` and `_emit_deprecation_once` helpers themselves
   MUST remain in
   [`vibe_cading/print_settings.py`](../../vibe_cading/print_settings.py).
   The `unknown_profile_*` `UserWarning` call site (warns when a
   user-named profile is not in the loaded set) still consumes
   `_emit_once`; the helpers stay live for that path and any future
   per-process-once warning need.  The
   `_emitted_warnings` / `_emitted_deprecations` set + alias MUST
   remain.

6. **FR6 — Test refresh.**
     - [tests/test_tolerance_profile.py](../../tests/test_tolerance_profile.py)
       — DROP the legacy-file tests T7 (lines ~583-599: "only
       `machine_profiles.json` present → loaded with one deprecation")
       and T8 (lines ~600-620: legacy filename happy-path).  The
       comment "(or the legacy-named `machine_profiles_user.json`)" at
       line ~302 MUST be removed.  Module docstring line ~27 MUST drop
       the `machine_profiles_user.json` citation.
     - [tests/test_technic_pin_hole_profile.py](../../tests/test_technic_pin_hole_profile.py)
       — DROP the `PIN_HOLE_PRINTED` deprecation-warning test at
       lines ~139-160.  No replacement — the constant is removed.
     - [tests/test_axle_hole_gauge.py:184](../../tests/test_axle_hole_gauge.py#L184)
       — comment update: drop the
       "(or the legacy-named `machine_profiles_user.json`)" clause.
     - [tests/test_env_parser.py:5](../../tests/test_env_parser.py#L5)
       — module docstring example: drop the `PIN_HOLE_PRINTED="4.85"`
       half of the example.  Replace with a still-live env var
       (`DEFAULT_CORNER_RADIUS="0.4"` is the closest live analogue).

7. **FR7 — README refresh.**
   [README.md:186](../../README.md#L186) — the **Deprecation window**
   paragraph MUST be removed entirely.  Both deprecations referenced in
   that paragraph (filename + env-var) are now resolved; the paragraph
   only documents transitional state that no longer exists at OSS
   publication.

8. **FR8 — `vibe/INSTRUCTIONS.md` refresh.**
   [vibe/INSTRUCTIONS.md:156](../../vibe/INSTRUCTIONS.md#L156) currently
   reads `Copy machine_profiles.json.example to machine_profiles_user.json…`.
   MUST be updated to
   `Copy print_profiles.json.example to print_profiles_user.json…`.
   The `machine_profiles_user.json` citation at line 24 (Scoped Staging
   rule, lists examples of sensitive files to keep out of `git add .`)
   MUST be updated to `print_profiles_user.json` for current accuracy
   — but the rule itself stays.

9. **FR9 — `memories/session/ideas.md` cleanup.**
   The parked follow-up bullet
   "Migrate `PIN_HOLE_PRINTED` → `PIN_HOLE_DIAMETER` (4.80) nominal +
   profile" in
   [memories/session/ideas.md](../../memories/session/ideas.md)
   MUST be removed — the migration completed via PR #12 and the legacy
   constant is removed in this PR.

10. **FR10 — `engine_api.json` regen.**
    The
    [engine_api.json](../../engine_api.json)
    file MUST be regenerated as the final implementation step so its
    embedded docstrings reflect the deletions.  No structural schema
    change is expected — only docstring text deltas.

11. **FR11 — Resolver positive test.**
    Add one positive test to
    [tests/test_tolerance_profile.py](../../tests/test_tolerance_profile.py)
    that exercises `_resolve_shipped_file` and `_resolve_user_file`
    with the canonical `print_profiles.json` /
    `print_profiles_user.json` files present and confirms each returns
    the canonical path.  This is the regression guard the hard-cut
    earns: without it, a future contributor accidentally re-introducing
    a legacy branch with the wrong precedence order goes undetected.

12. **FR12 — Geometric invariance.**  The shipped 27-leaf T9b snapshot
    in [tests/test_tolerance_profile.py](../../tests/test_tolerance_profile.py)
    MUST remain bit-identical.  No `_FALLBACK_PROFILES`, `FitGrade`,
    `ToleranceProfile`, `TechnicPinHole`, or `TechnicAxleHole` field
    is touched — only the resolver chain (shim removal) and the
    `PIN_HOLE_PRINTED` re-export.

## Non-Functional Constraints

- **Source-level back-compat (intentional silent break):** A
  downstream Python module that imports the legacy name —
  `from vibe_cading.lego.constants import PIN_HOLE_PRINTED` — raises
  `ImportError` post-merge.  This is the intentional break.
- **User-level back-compat (intentional silent break):** A
  pre-OSS user whose repo carries `machine_profiles.json` or
  `machine_profiles_user.json` (not yet renamed) gets `None` for that
  slot post-merge — silently falls back to `_FALLBACK_PROFILES` for
  the shipped slot, or empty-overrides for the user slot.  Their
  calibrated values stop applying until they rename the file.
- **Geometric back-compat:** Zero impact.  Shipped CadQuery models
  produce bit-identical STEP output before and after this PR
  (assuming the user has renamed their override file, or had no
  override).
- **Resolution chain depth:** drops from 2 paths × 2 names each
  (shipped + user × canonical + legacy) to 1 name each.  Net code
  reduction in `print_settings.py`.
- **Warning emission load:** drops 4 `_emit_deprecation_once` call
  sites in `print_settings.py` + 1 in `lego/constants.py`.  Tooling
  output is fully clean of these specific warnings.

## Known Domain Constraints

- The `print_profiles.json` shipped-defaults file is the single live
  source of truth post-merge.  It MUST NOT be renamed by this PR.
- The `print_profiles_user.json` user-override file is the single live
  override slot post-merge.  Its location
  (`<REPO_ROOT>/print_profiles_user.json`) is unchanged.
- `_emit_once` continues to serve the `unknown_profile_*`
  `UserWarning` path — DO NOT remove the helper.
- `PIN_HOLE_DIAMETER = 4.8` in
  [vibe_cading/lego/constants.py](../../vibe_cading/lego/constants.py)
  is the live nominal that replaces `PIN_HOLE_PRINTED` (per PR #12).
  DO NOT touch it.

## Out of Scope

*Explicit anti-scope — DO NOT include in this PR:*

- **No `_FALLBACK_PROFILES` / `FitGrade` / `ToleranceProfile` /
  `_deep_merge_profiles` change.**  Resolver shim removal only.
- **No `TechnicPinHole` / `TechnicAxleHole` change.**  Constant removal
  only — the consumers were migrated in PR #12 (pin-hole) and
  PR #14 (env-var).
- **No `print_profiles.json` shipped-content change.**
- **No `PIN_HOLE_DIAMETER` change.**  Live nominal stays.
- **No `tools/calibrate.py` change.**  Calibrate writes to
  `print_profiles_user.json` already — no resolver-chain entanglement.
- **No CI workflow change.**  CI does not set the env vars or reference
  the legacy filenames.
- **No `LICENSE-FAQ.md` authoring.**  Separate OSS-prep checklist
  item; out of scope here.
- **No `docs/business-strategy.md` purge.**  Final-step destructive
  history rewrite is owned by human-Admin at release-prep time.

## Touchpoint Inventory (informational — confirmed by repo-wide grep)

`grep -l "PIN_HOLE_PRINTED\|machine_profile" --include="*.py" --include="*.md"`
returns **9 in-scope files** (excluding `.agents/`, `tmp/`, `build/`,
`.claude/`):

| # | File | Nature of change |
|---|---|---|
| 1 | `vibe_cading/print_settings.py` | Drop legacy branches in `_resolve_*_file`; docstring refresh |
| 2 | `vibe_cading/lego/constants.py` | Drop `__getattr__` hook + deprecation comment |
| 3 | `tests/test_tolerance_profile.py` | Drop T7/T8; comment update; add FR11 positive test |
| 4 | `tests/test_technic_pin_hole_profile.py` | Drop `PIN_HOLE_PRINTED` test |
| 5 | `tests/test_axle_hole_gauge.py` | Comment update |
| 6 | `tests/test_env_parser.py` | Module-docstring example update |
| 7 | `README.md` | Drop **Deprecation window** paragraph |
| 8 | `vibe/INSTRUCTIONS.md` | Lines 24 + 156 — citation refresh |
| 9 | `memories/session/ideas.md` | Drop the PIN_HOLE_PRINTED migration bullet |
| 10 | `engine_api.json` | Regen-only — picks up docstring deltas |
| 11 | *(this artifact itself)* | n/a |

`TODO.md` was checked and contains no references that need updating
(the rows that mention `machine_profiles*.json` describe historical
work and are immutable record).

`docs/lego-technic.md`, `docs/print-tolerances.md`, `docs/screws.md`
were checked and contain no in-prose citations of the legacy names
that need updating.

---

## Human Confirmation Checkpoint
- [x] Requirements reviewed and confirmed by human
  *(2026-05-28: user direction "Continue the OSS preparation" →
  selected "Clean up deprecated staff" — Path C posture inherited
  from PR #14 precedent; the hard-cut disposition was already
  signed off when the shims were introduced with their
  OSS-publication-removal clauses.)*
