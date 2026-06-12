# Requirements: Env-var prefix drop — `VIBE_PRINT_PROFILE` → `PRINT_PROFILE` (hard cut)
<!-- Filename: 2026-05-28-env-var-prefix-drop_req.md  (tracked under .agents/plans/) -->

> **SUPERSEDED — 2026-05-28 by @admin.**  Process-weight advisory triggered
> by the human's `@admin do we really need the full ... workflow` directive.
> Path C (direct small PR, no design-flow) was chosen: the YES gate was
> borrowed framing from PR #8 (which earned it via brand-new field-level
> merge logic across 27 leaf floats), not earned here.  This change deletes
> two resolver branches and renames one canonical name — no new code path,
> failure mode is "resolver returns wrong profile" which a single
> integration test catches.  The req's FR list and touchpoint inventory
> are kept verbatim below as a checklist for the implementer; the Open
> Questions are pre-resolved by the Admin call (see below).  Driven via
> Developer subagent → branch + PR + `/review` gate.
>
> **Pre-resolved Open Questions (Admin call, hard-cut posture):**
> - **Q1 — Pointed warning vs silent fallback:** **silent fallback.**  Hard-cut
>   posture per the human's directive; calibrated-fit drift is self-diagnosing
>   on first print.  Saves the implementation of the legacy-name watcher.
> - **Q2 — `.env.example` history header:** **no history header.**  Present
>   the canonical name only.
> - **Q3 — README scope:** **surgical touch only.**  Excise the legacy-env-var
>   clause; keep the file-name deprecation paragraph as-is.
> - **Q4 — Test coverage:** **add one negative test** in
>   `tests/test_tolerance_profile.py` covering the
>   "`VIBE_*_PROFILE` set, `PRINT_PROFILE` unset → resolves to `fdm_standard`"
>   path.  Drop T11.  Q1 = silent fallback so no warning-emission assertion.
> - **Q5 — `lego/constants.py` line 118 stale cross-reference:** **drop the
>   cross-reference entirely** (simpler standalone phrasing).

---

## Meta
- **Initiator role**: @designer (per @admin direction in 2026-05-28 session)
- **Date**: 2026-05-28
- **Domain integrity gate**: **NO** — superseded.  Resolver-chain simplification
  is pure deletion (two branches removed, one rename).  Failure mode is
  "resolver returns wrong canonical name" caught by the FR7 negative test.
  No `_FALLBACK_PROFILES` / `FitGrade` / `_deep_merge_profiles` touched.
  The 27-leaf T9b snapshot remains bit-identical.

---

## Problem Statement

PR #8 (merged 2026-05-24, `dc877a7`) renamed the canonical env var
`VIBE_MACHINE_PROFILE` → `VIBE_PRINT_PROFILE` while keeping the legacy
name honoured under a one-shot `DeprecationWarning` for a single
deprecation window targeted at the OSS publication release.

Two follow-on signals make a second rename desirable **before** that
publication, in the same pre-OSS window:

1. **Noise in maintainer workflow.** The maintainer's `.env` still
   carries `VIBE_MACHINE_PROFILE=…`; every Python invocation that
   touches `print_settings` (`pytest`, `tools/check_topology.py`, etc.)
   emits a `_emit_deprecation_once("env_var_VIBE_MACHINE_PROFILE", …)`
   warning, polluting test runs and tool output with stderr lines that
   the contributor cannot silence by configuration alone.
2. **Naming convention.** The `VIBE_` prefix on a single env var is
   inconsistent with the project's other env vars (`PIN_HOLE_PRINTED`,
   `DEFAULT_CORNER_RADIUS`, `DEFAULT_LEAD_IN`, `GH_TOKEN`), none of
   which carry a project-scoping prefix.  The prefix originated as a
   namespace defence that no longer earns its keep.

The pre-OSS state is the right time for a clean break: the universe of
users is the maintainer plus possible early testers (private fork
contributors).  The cost of a one-time hard cut now is bounded; the
cost of carrying a second deprecation window through OSS publication
is structural drag on every contributor onboarding.

## User Story / Motivation

As the project maintainer (and the future OSS contributor base), I need
the global manufacturing-profile env var to be named `PRINT_PROFILE`
(no `VIBE_` prefix, no legacy fallback) so that test runs and tooling
output are free of deprecation noise, and so that the env-var naming
convention is uniform across the project before OSS publication.

## Functional Requirements

1. **FR1 — Canonical env var.** `vibe_cading.print_settings.get_default_profile_name()`
   MUST resolve in the following order:
     1. `os.getenv("PRINT_PROFILE")` — wins if non-empty.
     2. Hardcoded `"fdm_standard"` default.
   It MUST NOT read `VIBE_PRINT_PROFILE` or `VIBE_MACHINE_PROFILE`
   from the environment.
2. **FR2 — Source-level back-compat preserved.** The function signature
   of `get_default_profile_name()` MUST remain `() -> str`.  Every
   Python caller (`get_profile`, `tools/calibrate.py`, any test) MUST
   continue to import and call it without modification.
3. **FR3 — Module docstring refresh.** The `vibe_cading/print_settings.py`
   module docstring's **Resolution order at runtime** section MUST cite
   `PRINT_PROFILE` (not `VIBE_PRINT_PROFILE`) at step 3.  The
   **Deprecation window** section MUST drop the
   `VIBE_MACHINE_PROFILE` clause (the env var is no longer honoured);
   the file-name deprecation clauses (`machine_profiles.json` →
   `print_profiles.json`) MUST remain — they are orthogonal to env-var
   naming and continue under PR #8's deprecation window.
4. **FR4 — Deprecation emitter cleanup.** The
   `_emit_deprecation_once("env_var_VIBE_MACHINE_PROFILE", …)` call in
   `get_default_profile_name()` MUST be removed.  Every other
   `_emit_deprecation_once(…)` call site (the four `*_file_*` keys
   governing `machine_profiles*.json` file fallbacks) MUST remain
   untouched.  The `_emit_once` / `_emit_deprecation_once` helpers
   themselves stay — they are still consumed by the file-fallback path
   and by the unknown-profile-name `UserWarning` path.
5. **FR5 — `.env.example` refresh.** The shipped `.env.example` MUST
   replace `VIBE_PRINT_PROFILE="fdm_standard"` with
   `PRINT_PROFILE="fdm_standard"` and remove the
   "legacy name VIBE_MACHINE_PROFILE is honoured" comment block.  The
   `PIN_HOLE_PRINTED`, `DEFAULT_CORNER_RADIUS`, `DEFAULT_LEAD_IN`, and
   `GH_TOKEN` sections MUST be left unchanged.
6. **FR6 — `tools/calibrate.py` resolver refresh.**
   `_resolve_active_profile_name()` MUST resolve `PRINT_PROFILE` as the
   sole env-var branch (no `VIBE_PRINT_PROFILE`, no
   `VIBE_MACHINE_PROFILE`).  All `--help` text and module-level
   docstrings that name the env var (lines ~809, ~861, ~925 in the
   current file) MUST cite `PRINT_PROFILE`.
7. **FR7 — Test refresh.**
     - `tests/test_tolerance_profile.py` MUST replace every
       `VIBE_PRINT_PROFILE` reference with `PRINT_PROFILE` and DROP
       every `VIBE_MACHINE_PROFILE` test (T11 specifically — the
       legacy env-var deprecation case is gone).  The file-level
       legacy-fallback tests (covering `machine_profiles*.json` file
       deprecation) MUST remain.
     - `tests/test_env_parser.py` — update the docstring example
       (line 5) and any test fixtures from `VIBE_PRINT_PROFILE` to
       `PRINT_PROFILE`.
     - `tests/test_axle_hole_gauge.py` — update the comment citation
       (line 90).
     - `tests/tools/test_calibrate.py` — replace every
       `VIBE_PRINT_PROFILE` reference with `PRINT_PROFILE`; drop every
       `VIBE_MACHINE_PROFILE` reference (lines 477, 720, 755, 783 use
       `monkeypatch.delenv` defensively — those calls become
       unnecessary noise once the var is no longer honoured).
8. **FR8 — Documentation refresh.**
     - `README.md` — three citations (lines 75, 144, 174) MUST be
       updated to `PRINT_PROFILE`.  Line 186's
       "legacy env var `VIBE_MACHINE_PROFILE`" clause MUST be removed
       from the **Deprecation window** paragraph (the file-name
       deprecation sentence remains).
     - `docs/screws.md` — line 82 MUST cite `PRINT_PROFILE`.
     - `vibe/INSTRUCTIONS.md` — line 122 currently cites
       `VIBE_MACHINE_PROFILE` (it predates PR #8 and was missed in
       that rename).  MUST be updated to `PRINT_PROFILE` in this PR;
       the file-name citation (`machine_profiles.json` →
       `print_profiles.json`) MUST be updated in the same sentence
       for consistency.  *(This is a passive PR #8 cleanup absorbed
       into this PR — call out in design as a small bonus, not a
       scope expansion.)*
9. **FR9 — Source-code docstring refresh.**
     - `vibe_cading/_env.py` line 84 docstring example MUST cite
       `PRINT_PROFILE`.
     - `vibe_cading/lego/constants.py` line 118 docstring MUST drop
       the "mirroring the `VIBE_MACHINE_PROFILE` precedent" clause
       (the precedent has been removed in this PR; the citation is
       now stale).  Replace with the equivalent
       `PRINT_PROFILE`-tense phrasing OR drop the cross-reference
       entirely — TL to decide in design.
     - `vibe_cading/rc/freespin_hex_hub.py` line 88 docstring MUST
       cite `PRINT_PROFILE`.
     - `examples/screw_cutter.py` line 47 comment MUST cite
       `PRINT_PROFILE`.
10. **FR10 — `engine_api.json` regen.** The
    `engine_api.json` file MUST be regenerated as the final
    implementation step so its embedded docstrings reflect the
    new env-var name (the freespin-hex-hub doc cited at JSON line
    ~3471 will pick up the change automatically).
11. **FR11 — TODO.md cleanup.** The TODO.md row referencing the
    PR #8 rename (line 36, `VIBE_MACHINE_PROFILE` →
    `VIBE_PRINT_PROFILE`) MUST be reviewed.  If the row is
    closed-but-not-yet-pruned, this PR removes it.  If it is still
    open, it MUST be amended to reflect the current end state
    (`PRINT_PROFILE`).  Designer recommends drop the row entirely
    (PR #8 + this PR jointly close it).
12. **FR12 — Geometric invariance.** The shipped 27-leaf T9b snapshot
    in `tests/test_tolerance_profile.py` MUST remain bit-identical.
    No `_FALLBACK_PROFILES`, `FitGrade`, `ToleranceProfile`, or
    `_deep_merge_profiles` field is touched — only the resolver chain
    upstream of them.

## Non-Functional Constraints

- **Source-level back-compat:** `get_default_profile_name() -> str`
  signature unchanged.  Public API of `get_profile()`, `FitGrade`,
  `ToleranceProfile` unchanged.
- **Geometric back-compat:** Zero impact.  An env-var rename does
  not touch geometry.  Every shipped CadQuery model class produces
  bit-identical STEP output before and after this PR (assuming the
  env var is set consistently — see "User-level back-compat" below).
- **User-level back-compat (intentional silent break):** Any
  pre-OSS user (= maintainer + possible private-fork early testers)
  with `VIBE_PRINT_PROFILE` or `VIBE_MACHINE_PROFILE` in their `.env`
  will silently fall back to `fdm_standard` post-merge.  Their
  calibrated values stop applying until they rename the env-var
  entry to `PRINT_PROFILE`.  This is the explicit hard-cut posture
  the human-Admin signed off on for 2026-05-28; see Q1 for the
  ergonomic-mitigation question.
- **Resolution chain depth:** drops from 3 (`VIBE_PRINT_PROFILE` →
  `VIBE_MACHINE_PROFILE` → `fdm_standard`) to 2 (`PRINT_PROFILE` →
  `fdm_standard`).  Net code reduction.
- **Test runtime / artifact size:** dropping T11 saves one test;
  all other test changes are renames.  No `engine_api.json` size
  change beyond docstring text deltas.
- **Configuration convention:** the project's env-var naming
  becomes uniform — every env var the project reads
  (`PRINT_PROFILE`, `PIN_HOLE_PRINTED`, `DEFAULT_CORNER_RADIUS`,
  `DEFAULT_LEAD_IN`, `GH_TOKEN`) is unprefixed.

## Known Domain Constraints

- The **file-name** legacy fallbacks (`machine_profiles.json` /
  `machine_profiles_user.json`) are orthogonal to env-var naming.
  Their PR #8 deprecation window MUST remain in force until the OSS
  publication release — this PR does NOT touch
  `_resolve_shipped_file()` or `_resolve_user_file()`.
- The `_emit_once` / `_emit_deprecation_once` helper machinery is
  still consumed by four call sites (`shipped_file_both_present`,
  `shipped_file_legacy_only`, `user_file_both_present`,
  `user_file_legacy_only`) plus the `unknown_profile_*`
  `UserWarning` path.  The helpers themselves stay — only the
  `env_var_VIBE_MACHINE_PROFILE` call site is removed.
- The 27-leaf T9b shipped-profile snapshot is the integrity
  contract for `_FALLBACK_PROFILES` and `print_profiles.json`.
  Nothing under that contract is touched by this PR.

## Out of Scope

*Explicit anti-scope — DO NOT include in this PR:*

- **No file rename.** `print_profiles.json` /
  `print_profiles_user.json` filenames stay.
- **No `PIN_HOLE_PRINTED` change.** PR #12 finished that deprecation;
  the `.env.example` row stays as-is.
- **No `_FALLBACK_PROFILES`, `FitGrade`, `ToleranceProfile`, or
  `_deep_merge_profiles` change.** Loader resolver chain only.
- **No `AXLE_HOLE_TIP_TO_TIP` / `AXLE_HOLE_ARM_WIDTH` change.**
  Real-Lego nominals, unrelated.
- **No `tools/calibrate.py` flag rename.** `--profile` stays.
- **No CI workflow change.** CI does not set this env var.
- **No file-fallback chain change.** PR #8's `machine_profiles*.json`
  file-name deprecation window is unaffected.
- **No new tests beyond the resolver-chain coverage** (see Q4).
- **No `print_profiles.json` shipped-content change.**

## Open Questions

*For the TL/Designer Step-3 co-design dialog.  Designer recommendations
are noted inline — they reflect the designer's first-principles take
and are not binding on the TL.*

- [ ] **Q1 — Pointed-warning vs silent-fallback for legacy env-var
      names.**  When the loader sees `VIBE_PRINT_PROFILE=…` or
      `VIBE_MACHINE_PROFILE=…` in the environment but **not**
      `PRINT_PROFILE`, should it emit a one-shot `UserWarning`
      (`"WARNING: VIBE_*_PROFILE is no longer supported; rename to
      PRINT_PROFILE"`) before silently falling back to
      `fdm_standard`?  Or stay strictly silent — trust the
      contributor to notice their calibrated fits stopped applying
      and consult docs?
      *Designer recommends:* **pointed warning.**  The hard cut breaks
      PR #8's "one deprecation window" implicit contract; giving the
      contributor a clear migration message is the right ergonomic
      move and costs ~10 lines of code routed through the existing
      `_emit_once` helper.  The warning is one-shot per (process,
      env-var-name) so it cannot become noise.  Implementation note:
      the keys would be `"env_var_VIBE_PRINT_PROFILE_unsupported"`
      and `"env_var_VIBE_MACHINE_PROFILE_unsupported"`.
- [ ] **Q2 — `.env.example` rename-history header.**  Should the
      shipped `.env.example` carry a brief comment explaining the
      rename history (`VIBE_MACHINE_PROFILE` →
      `VIBE_PRINT_PROFILE` → `PRINT_PROFILE`) so a contributor
      with a stale fork can self-diagnose, or just present the
      current canonical name with no archaeological context?
      *Designer recommends:* **no history header.**  The pointed
      warning from Q1 (if adopted) carries the migration message
      at the moment of friction; the `.env.example` should
      present the clean OSS-publication-ready interface.  A
      contributor who copies a stale `.env` from a private fork
      gets the warning the first time they run any Python tool.
- [ ] **Q3 — README "Print Tolerances & Calibration" section
      scope.**  Touch only the env-var line, or rewrite the
      surrounding paragraph (the **Deprecation window** subsection
      at line ~186) once the env-var legacy fallback is gone?
      *Designer recommends:* **surgical touch only.**  Line 186's
      paragraph remains correct for the **file-name** deprecation
      window (still in force); only the
      "and the legacy env var `VIBE_MACHINE_PROFILE`" clause is
      excised.  No paragraph rewrite.
- [ ] **Q4 — Test coverage for the new resolver chain.**  Is the
      existing `tests/test_tolerance_profile.py` coverage (T10
      adapted to `PRINT_PROFILE`, T11 dropped, T12 unchanged)
      sufficient?  Or does the resolver-chain simplification
      warrant a new test in `tests/test_env_parser.py` exercising
      the .env-file `PRINT_PROFILE=…` round trip + an explicit
      negative test that confirms `VIBE_PRINT_PROFILE` /
      `VIBE_MACHINE_PROFILE` in `.env` do NOT influence the
      resolved profile?
      *Designer recommends:* **add one negative test in
      `tests/test_tolerance_profile.py`** covering the
      "`VIBE_*_PROFILE` set, `PRINT_PROFILE` unset → resolves to
      `fdm_standard`" path.  This is the regression guard the
      hard-cut posture earns — without it, a future contributor
      accidentally re-introducing the legacy branch goes
      undetected.  If Q1 is YES (pointed warning), the same test
      asserts the `_emit_once` key fires exactly once.
- [ ] **Q5 — `vibe_cading/lego/constants.py` line 118 stale
      cross-reference.**  The docstring currently says
      "mirroring the `VIBE_MACHINE_PROFILE` precedent in
      `print_settings.py`".  Post-PR, that precedent is gone.
      Replace with `PRINT_PROFILE` (re-tense the analogy), or
      drop the cross-reference entirely (the
      `PIN_HOLE_PRINTED` deprecation is self-contained and
      doesn't need to lean on another module's pattern)?
      *Designer recommends:* **drop the cross-reference.**  PR #12
      completed the `PIN_HOLE_PRINTED` deprecation; the docstring
      is documenting a historical mirror that no longer aids
      comprehension.  Simpler standalone phrasing is cleaner.

---

## Touchpoint Inventory (informational — confirmed by repo-wide grep)

`grep -l 'VIBE_PRINT_PROFILE\|VIBE_MACHINE_PROFILE'` returns **17
files**:

| # | File | Nature of change |
|---|---|---|
| 1 | `vibe_cading/print_settings.py` | Resolver + docstring + emitter call site removal |
| 2 | `vibe_cading/_env.py` | Docstring example rename |
| 3 | `vibe_cading/lego/constants.py` | Stale cross-reference (see Q5) |
| 4 | `vibe_cading/rc/freespin_hex_hub.py` | Class docstring rename |
| 5 | `.env.example` | Env-var line + legacy comment block |
| 6 | `tools/calibrate.py` | Resolver chain + 3 docstring/help citations |
| 7 | `tests/test_tolerance_profile.py` | T10 rename, T11 drop, docstring lines |
| 8 | `tests/test_env_parser.py` | Docstring example |
| 9 | `tests/test_axle_hole_gauge.py` | Comment citation |
| 10 | `tests/tools/test_calibrate.py` | 5 monkeypatch sites + 1 docstring |
| 11 | `examples/screw_cutter.py` | Comment citation |
| 12 | `README.md` | 3 prose citations + deprecation-window edit |
| 13 | `docs/screws.md` | 1 prose citation |
| 14 | `vibe/INSTRUCTIONS.md` | Line 122 (passive PR #8 cleanup) |
| 15 | `engine_api.json` | Regen-only — picks up docstring deltas |
| 16 | `TODO.md` | Row pruning (see FR11) |
| 17 | *(this artifact itself)* | n/a — referenced in design follow-on |

Excluding (15) `engine_api.json` (regen-only) and (17) this artifact:
**15 hand-edited files**, within the 8–12 estimate's tolerance.

`docs/print-tolerances.md` and `docs/lego-technic.md` were checked and
contain **no** env-var citations — no edits required.

---

## Human Confirmation Checkpoint
- [ ] Requirements reviewed and confirmed by human
<!-- Do not proceed to design until this box is checked. -->
