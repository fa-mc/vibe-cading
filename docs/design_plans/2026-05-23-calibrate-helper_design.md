# Design: `tools/calibrate.py` — guided print-tolerance calibration helper

> ⚠️ **SUPERSEDED 2026-05-23 at Step-4 human gate.** See the SUPERSEDED
> banner at the top of the sibling
> [`2026-05-23-calibrate-helper_req.md`](2026-05-23-calibrate-helper_req.md)
> for the re-scope rationale and the two replacement briefs. This design's
> raw-JSON read + atomic-write + legacy-flat migration mechanics carry
> forward as prior-art reference for the new usage brief, but the
> Implementation Plan and Tests are NOT load-bearing.
<!-- Filename: 2026-05-23-calibrate-helper_design.md  (tracked in git under .agents/plans/) -->

## Meta
- **Requirements ref**: `.agents/plans/2026-05-23-calibrate-helper_req.md`
- **Requester role**: @designer (PM-spawned 2026-05-23; human-confirmed)
- **Date**: 2026-05-23
- **Dialog rounds**: 3

---

## Objective

Ship a single-file CLI at `tools/calibrate.py` that walks a user from a
printed `AxleHoleGauge` to a correctly-merged `slip.radial` value in
`machine_profiles_user.json`, with explicit change-preview + confirmation,
transparent legacy-flat → nested migration, and an atomic write that cannot
corrupt the existing file.

## Architecture / Approach

### Approach chosen

**One self-contained script under `tools/`. No new public surface in
`vibe_cading/print_settings.py`. No new helper module.**

The tool is a thin orchestration layer over three pieces that already exist:

1. `vibe_cading.print_settings` — `get_default_profile_name()`,
   `_is_legacy_flat_entry`, `_migrate_flat_to_nested`. `calibrate.py`
   imports these directly (including the underscored two) and documents
   in its module docstring that it is a sanctioned in-tree consumer of
   the migration helpers. *No promotion to public API.* Justification:
   the helpers have exactly one external caller (this tool); promoting
   them now is speculative architecture for v2. (See Round 1 of the
   Design Dialog Log.)
2. `vibe_cading.lego.axle_hole_gauge.AxleHoleGauge` — instantiated **once,
   lazily, only when needed** (default-tuple introspection). The default
   `diameters` tuple is read from `AxleHoleGauge().diameters`, so a
   future sweep adjustment propagates without a `calibrate.py` edit
   (FR-derived constraint, req §"Known Domain Constraints").
3. `vibe_cading.lego.constants.AXLE_HOLE_TIP_TO_TIP` — imported and used
   directly in the radial formula (FR6).

**Data flow (one run):**

```
              (user supplies)            (tool resolves)
              ─────────────              ────────────────
  argv  ──▶ parse_args()  ──▶  profile_name  =  --profile flag
                                              or  get_default_profile_name()
                                              (env / "fdm_standard")
                                  │
                                  ▼
              read raw JSON of machine_profiles_user.json
                     (or treat as {} if missing)
                                  │
                                  ▼
              extract target entry (raw dict)
                     migrate legacy-flat → nested if needed
                                  │
                                  ▼
              prompt for diameter (skipped if --diameter)
                     validate against AxleHoleGauge().diameters
                                  │
                                  ▼
              compute radial = (D − AXLE_HOLE_TIP_TO_TIP) / 2
                                  │
                                  ▼
              build target_entry_after = deepcopy(entry_before),
                     then set entry_after["slip"]["radial"] = radial
                     (preserve sibling "axial", "slot", other grades)
                                  │
                                  ▼
              render change preview
                                  │
                                  ▼
              prompt y/N (default N)   ──or── --yes
                                  │
                                  ▼ (only on confirm)
              atomic write: tempfile → os.replace
                                  │
                                  ▼
              print success block (FR15 → Q5 resolution)
```

**File layout (single file, ~250 LOC):**

```
tools/calibrate.py
├── AGPLv3 header
├── module docstring (purpose, v1 scope, README ref)
├── imports (stdlib + 3 in-tree symbols)
├── constants (REPO_ROOT, USER_JSON_PATH, ARG_DIAMETER, etc.)
│
├── # ── Data assembly ──────────────────────────────────────
├── def _read_user_profiles_raw() -> dict        # raw JSON, {} if missing
├── def _resolve_target_entry(raw, name) -> tuple[dict, bool]
│       # returns (entry_dict_or_empty, was_legacy_flat)
├── def _build_after_entry(entry, radial) -> dict
│       # deepcopy + set entry["slip"]["radial"]; preserves siblings
│
├── # ── Interaction ────────────────────────────────────────
├── def _prompt_diameter(valid: tuple[float, ...]) -> float
├── def _prompt_confirm() -> bool                # y/N, default N
├── def _render_preview(...)
│
├── # ── Write ──────────────────────────────────────────────
├── def _atomic_write_json(path: Path, data: dict) -> None
│       # write to <path>.tmp.<pid>, fsync, os.replace
│
├── # ── Validation guards ──────────────────────────────────
├── def _validate_diameter(value, valid) -> float
│       # raises ValueError listing valid choices
│
├── # ── CLI ────────────────────────────────────────────────
├── def _build_parser() -> argparse.ArgumentParser
├── def main(argv=None) -> int
└── if __name__ == "__main__":  sys.exit(main())
```

All functions except `main` are module-private (`_`-prefixed). `main` takes
an explicit `argv` so tests can drive it (see Tests T1, T2, T7).

**Wire-format of the change-preview output (FR7).** Plain-text, fixed
layout, no JSON, no colour codes (stays readable in dumb terminals and is
trivially screenshot-able for bug reports):

```
Calibration target
  File:    machine_profiles_user.json     (will be CREATED)
  Profile: fdm_standard                   (resolved from VIBE_MACHINE_PROFILE)
  Grade:   slip
  Field:   radial

Change
  Before:  slip.radial = 0.050 mm    (inherited from machine_profiles.json)
  After:   slip.radial = 0.100 mm

Derivation
  Modelled fitting diameter D = 5.00 mm   (your input)
  Nominal AXLE_HOLE_TIP_TO_TIP = 4.80 mm  (vibe_cading/lego/constants.py)
  slip.radial = (D − 4.80) / 2 = 0.100 mm

Migration
  (none — profile already in nested schema)
  -- OR --
  Will migrate the existing legacy-flat entry to the nested schema
  before applying the calibration.

Other grades and fields are preserved verbatim.

Apply this change? [y/N]:
```

The three "(will be CREATED)", "(resolved from VIBE_MACHINE_PROFILE)", and
"Migration: …" lines are conditional — the script suppresses or rewrites
them depending on whether the file/profile/grade pre-exists.

### Alternatives rejected

- **(R1) Split into `vibe_cading/print_settings.py` public helpers.** Rejected
  for v1 — `apply_calibration(name, grade, field, value)` would have exactly
  one caller. The out-of-scope clause on "v2 multi-calibration framework"
  warns against exactly this. Re-evaluate when a *second* calibration
  consumer materialises (Stage-2c slot calibration may force it).
- **(R2) Round-trip through the existing `get_profile()` loader.** Rejected.
  `get_profile()` returns a `ToleranceProfile` dataclass with *resolved*
  values — `machine_profiles.json` defaults merged in. Re-serialising those
  to JSON would **inflate** the user file: every key from the tracked
  defaults would be re-written into the user file, defeating FR9's "merge
  into existing tree" requirement and turning the user file from "diffs from
  defaults" into "full snapshot of resolved values." Round-tripping also
  loses any non-schema keys (comments via `// …` are not standard JSON, but
  a user-added `"_note"` field at the profile level would be silently
  dropped). Read **raw JSON** instead; mutate only the targeted leaf.
- **(R3) Auto-detect printer profile from filesystem layout.** Out of scope
  per the req's "fewer knobs" anchor — explicit `--profile` override is the
  escape hatch (Q2 resolution).
- **(R4) Interactive-only (reject `--diameter` / `--yes`).** Rejected on
  predicted-cost grounds — the non-interactive form is ~5 LOC and unlocks
  CI smoke-testing of the actual write path without a pexpect harness.
- **(R5) Heavyweight TUI (curses, questionary, prompt_toolkit).** Rejected
  by req §"Non-Functional Constraints" (no third-party deps).

## Data & Interface Contracts

*Domain integrity gate is **NO** per the req — this tool reads an existing
schema owned by `vibe_cading/print_settings.py` and writes back into the same
schema. No new schema, no new field, no new public API.*

The single non-obvious wire format is the **change-preview block** spelt out
under *Architecture → Approach chosen* above (plain-text, fixed labels). It
is purely human-readable; nothing parses it programmatically.

## Implementation Plan

- [ ] **T1** — Create `tools/calibrate.py` with AGPLv3 header, module
  docstring (states v1 scope, prereq, file modified, gauge class name per
  FR13), and the skeleton sketched under *File layout* above.
- [ ] **T2** — Implement `_read_user_profiles_raw(path) -> dict`. Returns
  `{}` if the file does not exist. **Raises** on parse failure (covers
  FR-NFC "abort with clear error on unparseable file"). Does **not**
  invoke `get_profile()` — raw JSON only (rejected alternative R2).
- [ ] **T3** — Implement `_resolve_target_entry(raw, name) -> (entry, was_legacy)`.
  If `name` not in `raw`, returns `({}, False)`. If present and
  `_is_legacy_flat_entry` returns True, calls `_migrate_flat_to_nested`
  and returns `(migrated, True)`. Otherwise returns `(deepcopy(entry), False)`.
- [ ] **T4** — Implement `_build_after_entry(entry, radial) -> dict`.
  `deepcopy`, then `entry.setdefault("slip", {})["radial"] = radial`. Does
  **not** touch `axial`, `slot`, `free`, `press`, or any other key (FR9).
  Preserves the empty-entry case (file-creation path, FR11): when entry
  starts empty, only `{"slip": {"radial": …}}` is written — *no inherited
  defaults injected*, since the loader's grade-level merge will fill them
  at read time. (R2 rejection rationale.)
- [ ] **T5** — Implement `_validate_diameter(value, valid)`. Accepts
  `float`-castable input; rejects with `ValueError` listing `valid`
  choices to 2 decimal places. Tolerance for float-equality match: a value
  is accepted iff `abs(value - v) < 1e-6` for some `v in valid` (Q1
  resolution: default-sweep only).
- [ ] **T6** — Implement `_prompt_diameter(valid)`. Wraps `input()`, loops
  on `ValueError` from `_validate_diameter`, max 3 attempts before
  exiting non-zero. The prompt text lists the valid choices (e.g.
  `"Modelled diameter that fit best (4.70/4.75/4.80/4.85/4.90/4.95/5.00): "`).
  Skipped entirely when `--diameter` is on the argv.
- [ ] **T7** — Implement `_prompt_confirm()`. Reads one line; accepts
  `y` / `yes` (case-insensitive) as YES; everything else (including bare
  Enter, `n`, EOF, Ctrl-D) is NO (FR7 default-no). Skipped when `--yes`
  is on the argv (Q3/Q4 resolution: simple y/N, no double-confirm).
- [ ] **T8** — Implement `_render_preview(...)`. Pure print to stdout, no
  state. Reads the conditional cases off explicit booleans
  (`file_will_be_created`, `was_legacy_migration`, `before_radial is None`)
  passed in from `main`.
- [ ] **T9** — Implement `_atomic_write_json(path, data)`. Writes to
  `path.with_suffix(path.suffix + f".tmp.{os.getpid()}")`, flushes, fsyncs
  the file handle, then `os.replace(tmp, path)`. On any exception during
  write, the partial tempfile is unlinked in a `finally` block. Uses
  `json.dump(data, fh, indent=4, sort_keys=False)` to match the existing
  `machine_profiles.json` style (4-space indent, key order preserved).
- [ ] **T10** — Implement `_build_parser()` with:
  - positional: none.
  - `--diameter FLOAT` (optional; if set, skip prompt).
  - `--profile NAME` (optional; if set, override `get_default_profile_name()`).
  - `--yes` (optional; if set, skip confirmation).
  - `--help` text per FR13.
- [ ] **T11** — Implement `main(argv=None) -> int`. Flow per *Data flow*
  diagram above. Returns `0` on success or user-cancelled (non-destructive);
  `1` on validation error or unparseable existing file; `2` on prompt-loop
  exhausted. Prints success block at end per Q5 resolution (FR15-derived).
  **`USER_JSON_PATH` resolution is call-time, not import-time:** `main()` must
  read `tools.calibrate.USER_JSON_PATH` (the module attribute) *inside* its body
  and pass the resolved `Path` down as an argument to `_read_user_profiles_raw`
  and `_atomic_write_json`. Do NOT bind `USER_JSON_PATH` as a default-argument
  value on those helpers (e.g. `def _atomic_write_json(path=USER_JSON_PATH, …)`)
  — default args are evaluated at import time and `monkeypatch.setattr` on the
  module attribute would not affect them, breaking test isolation (T13).
- [ ] **T12** — Defer the `AxleHoleGauge` instantiation to *inside*
  `_prompt_diameter` (and `_validate_diameter` when `--diameter` is set).
  No CadQuery import at parser-build time — keeps no-print-path under the
  ~2-second runtime budget (FR-NFC). Confirm via `time python3 tools/calibrate.py --help`.
- [ ] **T13** — Add `tests/test_calibrate.py` covering Tests T1–T8 below.
  The `tests/` directory already exists (alongside `conftest.py`, `test_axle_hole_gauge.py`, etc.) — drop the new file in directly, no directory creation needed.
  Use `argv=[...]` to drive `main`; use `monkeypatch.setattr("builtins.input", …)`
  for prompt paths; use `tmp_path` and `monkeypatch.chdir` (or pass an
  override path constant) to isolate writes from the real
  `machine_profiles_user.json`.
- [ ] **T14** — Update `README.md`'s "Print Tolerances & Calibration"
  section to reference `python3 tools/calibrate.py` as the v1 entry
  point (FR14). One-paragraph addition; keep the existing manual-procedure
  link.
- [ ] **T15** — Run `python3 -m pytest tests/test_calibrate.py -v` and the
  full suite to confirm no regression. Run
  `python3 tools/check_license_headers.py` to confirm FR2.

## Tests

| # | Test description | Expected assertion | File / location | Maps to |
|---|------------------|--------------------|-----------------|---------|
| 1 | `main(["--help"])` returns 0 and prints help text naming `AxleHoleGauge`, `machine_profiles_user.json`, AND a concrete gauge-regeneration invocation (literal `preview.py` substring referencing `vibe_cading.lego.axle_hole_gauge.AxleHoleGauge`) | `SystemExit(0)`, captured stdout contains all three signposts | `tests/test_calibrate.py::test_help_mentions_gauge_and_user_json` | FR4, FR13 |
| 2 | `main(["--diameter", "5.00", "--yes"])` against tmp user-file creates the file with `slip.radial == 0.10` and no other keys at the profile level | JSON loads, `data["fdm_standard"]["slip"]["radial"] == 0.10`, no `free`/`press` written | `tests/test_calibrate.py::test_creates_new_file_with_single_grade_field` | FR11, FR1, FR3, FR6 |
| 3 | Pre-existing nested entry with `slip.radial=0.05` + `slip.axial=0.20` + `slip.slot=0.10` + `free`/`press`: after a calibration to 4.95, only `slip.radial` changes; `axial`, `slot`, `free`, `press` are byte-identical | dict equality on all unchanged paths | `tests/test_calibrate.py::test_preserves_sibling_grades_and_fields` | FR9 |
| 4 | Pre-existing legacy-flat entry (`z_clearance`/`slip_fit`/…) migrates to nested AND applies the calibration in one write | resulting file has nested shape, `slip.axial == old z_clearance`, `slip.radial` = newly calibrated | `tests/test_calibrate.py::test_legacy_flat_migration_atomic` | FR10 |
| 5 | Diameter outside `AxleHoleGauge().diameters` (e.g. 4.60) is rejected with an error listing valid choices; no file write | `main` returns non-zero exit, tmp user-file unchanged on disk, stderr lists `4.70 … 5.00` | `tests/test_calibrate.py::test_out_of_range_diameter_rejected` | FR5, Q1 |
| 6 | Unparseable existing `machine_profiles_user.json` causes abort with clear error; original file bytes unchanged | exit code non-zero, file mtime + bytes unchanged | `tests/test_calibrate.py::test_unparseable_file_aborts_without_write` | FR-NFC ("Filesystem safety") |
| 7 | `--profile bambu_p1s` targets that profile even though `VIBE_MACHINE_PROFILE` resolves elsewhere; if the key doesn't exist, the profile is *created* (entry path = file-creation path applied at the profile-key level) | resulting file contains a new `bambu_p1s` key with `{"slip": {"radial": …}}` | `tests/test_calibrate.py::test_profile_override_creates_new_profile_key` | FR8, Q2 |
| 8 | Default-no confirm: `main(["--diameter", "5.00"])` with `input()` returning empty string does NOT write | tmp user-file unchanged, exit 0 (non-destructive) | `tests/test_calibrate.py::test_default_no_confirmation_does_not_write` | FR7 |
| 9 | Constant-source check: changing `AXLE_HOLE_TIP_TO_TIP` via monkeypatch shifts the computed `radial` (proves no hardcoded `4.80`) | with patched constant of `4.90` and `D=5.00`, `radial == 0.05` (not `0.10`) | `tests/test_calibrate.py::test_uses_live_constant_not_hardcoded` | FR6 |
| 10 | Atomic write: simulate a write-time crash between tempfile flush and rename (raise from a patched `os.replace`); original file is byte-identical, no stray `.tmp.<pid>` left behind | original bytes unchanged, no leftover sibling in `tmp_path` | `tests/test_calibrate.py::test_atomic_write_crash_safety` | FR-NFC ("write atomically") |
| 11 | Active profile resolution echoes to stdout before the prompt; with `VIBE_MACHINE_PROFILE=resin_precise`, the preview header names that profile | captured stdout contains `resin_precise` before any prompt | `tests/test_calibrate.py::test_active_profile_echoed_before_prompt` | FR8 |
| 12 | Runtime budget: `python3 tools/calibrate.py --help` completes in under 2 seconds (no CadQuery import-cascade at parser build) | wall-clock `< 2.0` s on dev-container baseline | `tests/test_calibrate.py::test_help_runtime_under_two_seconds` (subprocess, marked `slow`) | FR-NFC ("Runtime budget") |
| 13 | License header present at file top, byte-identical wording with the other `tools/**/*.py` headers | `tools/check_license_headers.py` passes for `tools/calibrate.py` | CI lint step (no new test file needed) | FR2 |
| 14 | README's "Print Tolerances & Calibration" section names `python3 tools/calibrate.py` | grep of `README.md` finds the literal command | manual review during T14 | FR14 |
| 15 | Success block printed on write: path written, before/after `slip.radial`, "print a real Technic adapter and confirm fit" next-step line | captured stdout contains the file path and both numeric values | `tests/test_calibrate.py::test_success_block_after_write` | FR15 (Q5 resolution) |
| 16 | Import-surface check: `ast.parse(tools/calibrate.py)` shows every top-level `import` / `from … import` resolves to a stdlib module OR to `vibe_cading.*` — no third-party package names | parsed import list is a subset of `stdlib_module_names ∪ {names starting with "vibe_cading"}` | `tests/test_calibrate.py::test_imports_are_stdlib_or_in_tree_only` | FR12 |

Notes on test isolation:
- Every test that exercises the write path uses a `tmp_path / "machine_profiles_user.json"` and passes an internal override (a module-level `USER_JSON_PATH` that tests monkeypatch) so the developer's real user file is never touched.
- Tests T6 and T10 are the only ones that need filesystem fault injection (patched `open`, patched `os.replace`); both follow the project's "no `os` mock against the real filesystem" guidance by operating against `tmp_path`.

## Success Criteria

1. `python3 tools/calibrate.py --help` exits 0 in under 2 seconds, names `AxleHoleGauge`, names `machine_profiles_user.json`, names the v1 scope.
2. `python3 tools/calibrate.py --diameter 5.00 --yes` against a fresh checkout (no existing user file) creates `machine_profiles_user.json` containing exactly `{"fdm_standard": {"slip": {"radial": 0.1}}}` and exits 0.
3. The same command against a pre-existing user file with siblings (`free`, `press`, `slip.axial`, `slip.slot`, other profile keys) modifies exactly `<active>.slip.radial` and nothing else.
4. The same command against a legacy-flat user file produces a fully-migrated nested user file in one atomic write — no intermediate half-migrated state observable on disk.
5. `tests/test_calibrate.py` has at least 15 tests; every test passes; every FR1–FR15 row appears in at least one test's `Maps to` column.
6. `python3 tools/check_license_headers.py` passes after T1.
7. README's "Print Tolerances & Calibration" section names `python3 tools/calibrate.py` (FR14).
8. The full pytest suite (`python3 -m pytest`) passes with no regressions.

## Out of Scope

(Mirrored from req §"Out of Scope" — no scope changes surfaced in dialog.)

- Cross-hole arm-slot calibration (`slip.slot`).
- Other tolerance fields (`axial`, `free.radial`, `press.radial`).
- Auto-measurement (webcam / caliper).
- Auto-print dispatch.
- Stage 2c production-corner calibration.
- Build-pipeline integration / `build.toml` registration.
- Project-wide pluggable calibration registry (v2 architecture).

Surfaced in dialog (new exclusions):

- **No interactive selection from a list of profile keys** when multiple
  exist (Q2 resolution: `--profile` flag covers the use-case without a
  prompt regression).
- **No double-confirm / type-the-diameter-back** (Q4 resolution: default-no
  on a single prompt is sufficient).
- **No re-validation step that suggests re-printing the gauge** (Q5: the
  gauge was printed with the *old* profile; the real verification is the
  next real-part print, which the success block points the user at).
- **No promotion of `_is_legacy_flat_entry` / `_migrate_flat_to_nested` to
  the public API** in this task (R1 in *Alternatives rejected*); deferred
  until a second consumer materialises.

## Known Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Underscored-helper-import discipline: `calibrate.py` imports `_is_legacy_flat_entry` and `_migrate_flat_to_nested` from `print_settings`. A future refactor that renames them silently breaks the tool. | Test T4 exercises the legacy-flat migration end-to-end; a rename would fail the import at collection time. Module docstring of `calibrate.py` calls this out explicitly: "in-tree consumer of `print_settings._*` helpers — keep them in sync." |
| Float-equality on user-typed diameters: a user typing `4.95` vs the tuple value `4.949999…` from float parsing could spuriously reject. | T5's tolerance check (`abs(diff) < 1e-6`) covers normal float-print round-tripping. The displayed valid choices are 2-decimal-formatted, matching what `AxleHoleGauge` engraves on the part. |
| `--profile` pointing at a non-existent printer profile key silently creates a typo'd entry (e.g. `--profile bambo_p1s`). | The change-preview names the resolved profile and flags it as `(will be CREATED)` when the key is new — the user sees the typo before confirming. Tested by T7. Listed in Q2 resolution. |
| The default-tuple read requires constructing an `AxleHoleGauge()`, which imports CadQuery. The req sets a 2-second budget on the no-print path. | T12 defers the import to the prompt path. `--help` does not touch the gauge. `--diameter` + `--yes` does not strictly need the prompt path but DOES need validation; validation still loads the gauge — acceptable, the budget is on the **interactive no-print path**, not on every code path. T12 also adds a runtime-budget test on `--help` specifically. |
| Concurrent invocations racing on the user file (two terminals, same user). | `os.replace` is POSIX-atomic. The last writer wins; the loser's calibration is silently overwritten. Predicted-cost-of-failure: one debug-hour, recoverable by re-running. Documented as a known limitation in the module docstring; no locking mechanism in v1. |

---

## Design Dialog Log

### Round 1 — File layout & helper boundary

**TL proposal:**
> Single self-contained `tools/calibrate.py`. Import `_is_legacy_flat_entry`
> and `_migrate_flat_to_nested` directly from `print_settings`, even though
> they are underscored. Do not promote them to public API for this task.

**Requester challenge / contribution (Designer-as-requester):**
> The req's "Known Domain Constraints" explicitly says: *"If a helper is
> currently `_`-prefixed and the tool needs it as a public surface,
> promoting it (or wrapping it) is a TL call for the design phase."*
> Importing an underscored helper from another module is a smell. At
> minimum, wrap them in a `vibe_cading.print_settings` public façade
> (`apply_slip_radial_calibration(name, radial)`), so `calibrate.py`'s
> dependency is on a *contract*, not on a private implementation detail.

**TL counter:**
> Apply the structural-optimization deletion test to the proposed façade.
> Lens (a) — maintainer-locality: zero current internal callers benefit;
> the only consumer is `calibrate.py` itself. Lens (b) — contributor
> extension: no external OSS contributor adds a new family member here.
> A façade fails both lenses. It is shallow indirection that adds a
> module surface area for one caller. Inline-import discipline + a
> module-docstring callout ("this tool reads `_`-prefixed helpers; keep
> in sync on rename") satisfies the constraint without the indirection.
> If a *second* consumer (e.g. a `slot` calibrator in Stage 2c) appears,
> *that* design moment is when the façade earns its keep, not now.

**Resolution:**
> Accept the direct-import path. Document the coupling in the
> `calibrate.py` module docstring and in a new "Known Risks" row. Add a
> test (T4) that exercises the migration through the tool, so a rename
> would fail noisily at test-collection time. **Substantive revision
> negotiated:** added the Known Risks row and the docstring callout that
> were not in TL's first proposal.

### Round 2 — Read path: raw JSON vs `get_profile()` loader

**TL proposal:**
> Read `machine_profiles_user.json` as raw JSON. Do not round-trip through
> `get_profile()`.

**Requester challenge:**
> But `get_profile()` already handles legacy-flat migration in-memory and
> returns a clean `ToleranceProfile` dataclass. Re-implementing the
> migration on the write path duplicates work. Why not call
> `get_profile(name)`, mutate the dataclass, and serialise back?

**TL counter:**
> Trace what `get_profile()` actually returns. It calls `_load_json_profiles()`
> which merges `machine_profiles.json` (defaults) under `machine_profiles_user.json`
> (overrides) and returns the **resolved** values. If the user file is
> empty and we call `get_profile("fdm_standard")`, we get back the full
> shipped defaults (`free.radial=0.15`, `slip.radial=0.05`, `press.radial=0.04`,
> all three `axial`/`slot` keys populated). Serialising that back to the
> user file would write out *every key* of the resolved profile,
> defeating FR9's "merge into existing tree" — the user file morphs from
> "diffs from defaults" into "full snapshot." It also loses any
> non-schema keys the user may have added (e.g. a comment-like
> `"_note": "calibrated 2026-05-23"`). Read raw, mutate the targeted
> leaf, write raw.

**Requester accepts; pushes for a related concern:**
> Then we still need migration logic on the write path for the
> legacy-flat case. Calling `_migrate_flat_to_nested` directly is fine
> per Round 1, but we need to make sure the migration is **atomic** with
> the calibration application — never observe a half-migrated state on
> disk. FR10 says so, but the implementation needs to enforce it.

**Resolution:**
> Build the entire post-write dict in memory first (migration + leaf
> mutation), then `os.replace` the tempfile over the existing file. The
> filesystem sees one transition: old bytes → new bytes. No half-state
> reachable. Added Test T4 (legacy migration end-to-end), T6
> (unparseable file abort), and T10 (crash-injection between flush and
> rename). **Substantive revision negotiated:** added the rejected-
> alternative R2 to the design with the full inflation rationale,
> and the deepcopy-then-set discipline in T3/T4.

### Round 3 — Argparse surface (Q1–Q5 resolution)

**TL proposal:**
> Resolve the open questions:
> - Q1: option (a) — default-tuple only, helpful error on out-of-range.
> - Q2: option (a)+(b) — default to active, `--profile NAME` override.
> - Q3: accept the non-interactive form (`--diameter`, `--yes`).
> - Q4: no double-confirm. Default-no on a single y/N prompt is enough.
> - Q5: short success block — path, before/after, suggested next step.

**Requester challenge:**
> Q3 is the only one with real friction. Adding `--diameter` AND `--yes`
> means the script can be silently mis-invoked from CI with the wrong
> profile and overwrite a user's calibration. Should we require both
> flags **plus** an explicit `--profile`, so non-interactive runs cannot
> default-resolve the profile?

**TL counter:**
> No — that re-introduces the "fewer knobs" regression for the most
> common case (a single-printer user wanting to re-calibrate from CI
> after changing nozzles). The threat model here is a single-user dev
> environment, not a shared CI runner with multiple profiles. The change
> preview is the safety net for both interactive AND non-interactive
> use: `--yes` still echoes the preview to stdout before applying, so a
> CI log captures exactly what was changed. The user can grep their CI
> log for the preview block to audit a calibration run. Reject the
> mandatory-`--profile` rule.

**Requester:**
> Accepted. But add a test asserting that `--yes` still *prints* the
> preview block (just doesn't prompt). That makes the audit trail a
> testable contract, not a coincidence.

**Resolution:**
> Q1–Q5 resolved per TL proposal. Test T15 asserts the success block
> contents; the preview-on-`--yes` contract is asserted by T2 (captured
> stdout contains the path + numeric values). Q4 resolution explicitly
> recorded under *Out of Scope* (no double-confirm). **Substantive
> revision negotiated:** T15 added, and the *Out of Scope* additions
> for double-confirm and re-validation were appended rather than
> implicitly dropped.

### Module depth (structural-optimization skill)

**No new public Modules proposed.** `tools/calibrate.py` is one CLI script;
all helpers are private (`_`-prefixed) module-level functions inside that
single file. The deletion test does not apply at the module level — there is
no separate module to delete. False-positive carve-outs reviewed:

- *Observability seam*: N/A — no logging façade introduced.
- *Versioning seam*: N/A — no public API surface for downstream consumers.
- *Security boundary*: N/A — local filesystem write only.
- *Single cold-start entry point*: this IS the cold-start entry point
  (`main()`), which by carve-out is preserved.
- *Contributor-extension contract*: N/A — no base class or `Protocol`
  introduced; v2 calibration framework explicitly out-of-scope.

Inline private helpers (`_read_user_profiles_raw`, `_resolve_target_entry`,
`_build_after_entry`, `_atomic_write_json`, etc.) are testable units of a
single CLI; inlining them into `main` would harm `tests/test_calibrate.py`
readability and exceed `main`'s reasonable function length. They earn their
keep on testability — a recognised structural-optimization carve-out for
test-bearing seams.

**Verdict: N/A — no new Modules; one CLI script with private helpers only.**

### Round 4 — Condition application (2026-05-23)

Applied 4 reviewer conditions (a/b/c/d) verbatim. No architectural change.

---

## Sign-off

### Author sign-off (drafting role — Step 3 termination)
- [ ] Domain expert co-sign  *(required if domain integrity gate is YES; skip if NO — gate is NO, this box is a no-op)*
- [x] Requester sign-off  *(Designer-as-requester; Q1–Q5 resolved in dialog, no FR left unaddressed)*
- [x] TL sign-off  *(drafting author; all 7 termination conditions met — see checklist below)*

**TL sign-off termination checklist:**
1. ✅ FR1–FR14 each appear in at least one Implementation-Plan task or Success-Criteria item (FR1→T1/SC1, FR2→T1/T15/SC6, FR3→T2/SC2, FR4 covered by `--help` text in T1+T10, FR5→T5/T6, FR6→T5+test T9, FR7→T7+T8, FR8→T11+test T11, FR9→T4+test T3, FR10→T3+T9+test T4, FR11→T4+test T2/SC2, FR12→implicit in stdlib-only import surface, FR13→T1+test T1, FR14→T14/SC7. FR15 (success block) added as a derived requirement from Q5 resolution and tested by T15).
2. ✅ Q1–Q5 each resolved in dialog Round 3 with concrete decisions; no question left as "TBD".
3. ✅ Every `FR<n>` from req appears in the Tests table's "Maps to" column.
4. ✅ Success criteria are measurable (exit codes, file contents, runtime bounds, grep targets).
5. ✅ No Data & Interface Contracts section required (domain integrity gate NO); wire-format of change-preview noted inline under *Architecture*.
6. ✅ Non-blocking concerns in Known Risks each carry a predicted-cost line (debug-hours, recovery effort).
7. ✅ Module depth row filled — `N/A — no new Modules; one CLI script with private helpers only` justified against all four carve-outs.

### Independent reviewer sign-off (fresh-context — Step 3.5 termination)
- [x] Independent TL  *(always required; drafting author cannot self-sign here)* — APPROVE (2026-05-23, re-confirmed after applying conditions 1+2; see `## Independent TL Review` below)
- [x] Independent Developer  *(always required)* — APPROVE (2026-05-23, re-confirmed after applying conditions 1+2; see `## Independent Developer Review` below)
- [ ] Independent Researcher  *(required if domain integrity gate is YES; skip if NO)*

---

## Implementation Status
<!-- Populated by #developer at the start of Step 5 Phase A. -->
- [ ] All Implementation Plan tasks completed (every `[ ]` above marked `[x]`)
- [ ] Test suite executed — result: <!-- "N/N tests pass" or paste summary -->
- [ ] No new linter / static-check errors
- Developer note: <!-- one-line summary of what was done and any approved deviations from the plan -->

---

## Post-Implementation Sign-Off
<!-- Step 5 automated loop — no human input needed until Human Final Approval. -->

### TL Review
- [ ] **TL sign-off** — implementation matches design; tests pass; no unintended scope creep; strict-ops pass
- TL review notes: <!-- If issues found, list them here and transition back to #developer. Leave empty when clean. -->

### Domain Expert Review *(required if domain integrity gate is YES; skip if NO)*
- [ ] **Domain expert sign-off** — data contracts, interface schemas, and domain invariants verified against Data & Interface Contracts
- Domain expert review notes: <!-- If issues found, list them here and transition back to #developer. Leave empty when clean. -->

### Human Final Approval
- [ ] **Human approved** for merge / release
- Human notes: <!-- optional directions or conditions -->

---

## Independent TL Review (fresh context, 2026-05-23)

**Verdict:** APPROVE

**Strengths**
- Round 2's read-raw-vs-round-trip-through-`get_profile()` analysis is correct and load-bearing: `_load_json_profiles()` (`vibe_cading/print_settings.py:218-259`) does merge defaults under user overrides, so a round-trip would inflate the user file. Reading raw + mutating one leaf is the only design that satisfies FR9.
- Atomic-write contract via tempfile + `os.replace` plus deepcopy-before-mutate is a clean response to FR10's "no half-migrated state" requirement, and crash injection is explicitly tested (T10).
- Helper-coupling risk to `_is_legacy_flat_entry` / `_migrate_flat_to_nested` is honestly named in *Known Risks*, defended against `Deep-Modules — Dual-Lens` (both lenses fail for a façade today), and guarded by T4 import-at-collection-time.

**Conditions / required edits** (each precise; resolve before Step 5)

1. **FR4 has no explicit Tests-table row.** The TL termination checklist on line 497 claims FR4 is "covered by `--help` text in T1+T10", but Test #1 (line 271) only asserts help text mentions `AxleHoleGauge` and `machine_profiles_user.json` — it does NOT assert the help text contains a concrete `tools/preview.py …` (or equivalent) invocation that re-generates the gauge STEP, which is the operative FR4 obligation ("MUST print a single concrete invocation the user can run to (re-)generate the gauge STEP", req lines 93-96). **Edit:** extend Test #1's assertion to additionally check for a literal `preview.py` substring (or whatever signpost form is chosen) in `--help` output, and add `FR4` to its `Maps to` cell. Cost ≈ 1 LOC in the test; closes the requirement gap that 'Maps to' coverage is supposed to catch.

2. **FR12 has no explicit Tests-table row.** FR12 (offline / no third-party deps beyond the existing `print_settings.py` footprint) is asserted only implicitly by SC8 ("full pytest suite passes") and by code-review of the import block. **Edit:** add one row that asserts `tools/calibrate.py`'s top-level imports are a subset of `{stdlib}` ∪ `{vibe_cading.*}` — trivially scriptable via `ast.parse`. Greppable Maps-to: `FR12`. Cost ≈ 6 LOC.

**Open concerns** (non-blocking; predicted-cost-of-failure stated)

- **T3's `was_legacy` return is consumed by the preview, but the design's data-flow diagram (lines 60-63) shows migration happening before deepcopy.** The implementation order is fine, but if a developer reads T3's contract and reverses deepcopy/migration, a mutated migrated dict could leak back into the loaded `raw` mapping shared with siblings on disk. Predicted cost if wrong: ~30 min debug + a re-run; T3 already implies `deepcopy` in the non-legacy branch and T6/T10 backstop. *Non-blocking — documented for the developer's attention.*
- **T9's `os.replace` atomicity is POSIX-specific.** Dev-container is Debian Linux per `CLAUDE.md`, so this is fine in practice; on Windows it is still atomic in modern Python, but the predicted-cost line is missing for the concurrent-invocation row in *Known Risks* (line 336 already states one debug-hour — adequate). No edit required.
- **FR7's preview must surface migration *and* file-creation conditionals; the wire-format block (lines 129-154) sketches both, but the test matrix has no row that asserts the migration line appears in the preview for the legacy-flat path.** T4 asserts the migrated bytes on disk but not the preview text. Predicted cost if the preview line is silently dropped on the legacy path: a user confirms a migration they did not realise was happening; recoverable from VCS, but a user without VCS on `machine_profiles_user.json` (which is gitignored) loses their old flat entry without warning. Suggest extending T4 to also assert `"migrate"` (case-insensitive) appears in captured stdout. *Non-blocking but cheap to add (1 LOC).*

**Verification log**
- `vibe_cading/print_settings.py:87-92` → `get_default_profile_name()` exists with the documented `VIBE_MACHINE_PROFILE`-then-`fdm_standard` semantics; FR8 import target confirmed.
- `vibe_cading/print_settings.py:138-144` → `_is_legacy_flat_entry` exists, underscored, with the documented heuristic. Importable.
- `vibe_cading/print_settings.py:147-171` → `_migrate_flat_to_nested` exists, underscored, returns a fresh nested dict (does not mutate the input — safe for design's deepcopy contract). Importable.
- `vibe_cading/print_settings.py:218-259` → `_load_json_profiles` performs the defaults-then-user merge claimed in design Round 2; the round-trip-inflates-the-user-file rationale is factually correct.
- `vibe_cading/lego/constants.py:91` → `AXLE_HOLE_TIP_TO_TIP: float = 4.80` exists as a plain float (no `os.getenv` wrapper), matching req §"Known Domain Constraints" lines 218-221 and FR6's "live constant" requirement.
- `vibe_cading/lego/axle_hole_gauge.py:87` → `AxleHoleGauge.__init__` default `diameters: Sequence[float] = (4.70, 4.75, 4.80, 4.85, 4.90, 4.95, 5.00)`; line 94 stores `self.diameters` as a tuple. Design's `AxleHoleGauge().diameters` introspection contract (line 41, T6 prompt text) is satisfied.
- `tools/check_license_headers.py:29` → glob pattern `tools/**/*.py` confirms FR2's CI gate auto-covers the new file with no scope change.
- `vibe_cading/lego/axle_hole_gauge.py:60` → docstring states `slip.radial = (D - 4.80) / 2`, matching FR6's formula. Constant is duplicated as a literal inside the docstring narrative but the actual gauge code does not hardcode 4.80, and the design correctly delegates the live read to `calibrate.py`.

**Re-confirmed 2026-05-23:** conditions (1) and (2) applied; verdict upgraded to APPROVE.

---

## Independent Developer Review (fresh context, 2026-05-23)

**Verdict:** APPROVE

**Strengths**
- Implementation Plan T1–T15 is decomposed at the right granularity for an implementer to execute sequentially without ambiguity — each task names a concrete symbol, file, or assertion. `main()` orchestrates pure helpers; the test harness can drive `argv` deterministically.
- The data-flow diagram + file-layout sketch + change-preview wire-format together resolve every ambiguity I would normally have to ask the Designer about (which dict gets mutated, what the user sees, where atomicity lives). I would not need to escalate to implement T1–T15 as written.
- Cold-start runtime budget is correctly recognised as a CadQuery-import hazard and given a deferred-import strategy (T12) plus a regression test (Test #12). The atomic-write contract (T9) handles the FR11 file-does-not-exist path via the same tempfile + `os.replace` path uniformly.

**Conditions / required edits** (precise; resolve before Step 5 begins)

1. **`tools/check_no_main_blocks.py` claim contradicts T13's test file location.** Requirements §"Known Domain Constraints" line 228-234 correctly notes the no-`__main__`-blocks walker excludes `tools/`, so `tools/calibrate.py`'s `if __name__ == "__main__":` block at line 119 of the design is fine. **However**, T13 places the test file at `tests/test_calibrate.py` — the walker at `tools/check_no_main_blocks.py:77` walks `vibe_cading/` and `parts/` only, so this is also fine for the test file. No design edit needed for the walker rule itself, but the design never confirms that `tests/` is a sanctioned location for a new test file. There is no existing `tests/` directory referenced in the design, and the design does not specify whether a top-level `tests/` already exists or needs creation. **Edit:** add one sentence to T13 stating either "create `tests/` directory if absent" or naming an existing test directory. An implementer who runs `pytest tests/test_calibrate.py` against a missing directory will be uncertain whether to create it or use a different path. Cost: 1 sentence; closes a real "figure out where to put this" blocker.

2. **T13 specifies `monkeypatch.chdir` or a module-level `USER_JSON_PATH` override, but the design's File-layout block (line 94) lists `USER_JSON_PATH` as a module-level constant without specifying that it must be re-readable at call time (not bound at import time).** If `_atomic_write_json` captures `USER_JSON_PATH` as a default argument or closes over it at module-import, `monkeypatch.setattr("tools.calibrate.USER_JSON_PATH", tmp_path / ...)` will not affect functions that have already bound the value. **Edit:** Change T9's signature contract to "takes `path` as a required argument" (it already does per line 234) and add an explicit note in T11 that `main()` reads `USER_JSON_PATH` *at call time* (not via default arg) and passes it down. This makes the test-isolation contract surface-level and testable. Cost: 2 lines of design text; prevents a subtle test-isolation bug.

**Open concerns** (non-blocking; predicted-cost-of-failure stated)

- **FR4 signpost text is not pinned to a concrete invocation in the design.** The design states `--help` mentions `AxleHoleGauge` and the user-file path (Test #1) but never spells out the exact `tools/preview.py vibe_cading.lego.axle_hole_gauge.AxleHoleGauge` (or `build.py` block) string that satisfies FR4's "single concrete invocation" obligation. The Independent TL Review already flagged this for FR4 coverage (line 549). Predicted cost if the implementer guesses wrong: one Designer escalation round (~30 min) or a Step 5 Phase B re-spin when TL re-reviews the actual `--help` output. Recommend pinning the literal command in T1 or T10 alongside the FR4 coverage edit.
- **T7's confirmation accepts `y` / `yes`, rejects "everything else"; bare `Y` (capitalised) is documented as "case-insensitive" — fine — but the design does not list `j`/`ja` or other-locale affirmatives.** This is fine for a single-developer dev-container OSS project; predicted cost of a German-speaker mis-press: zero (they get a non-destructive default-no, hit re-run). No edit needed; flagged for completeness.
- **T9 uses `json.dump(..., sort_keys=False)` to preserve key order, but Python's `json.load` returns an ordinary `dict` whose insertion order reflects parse order. The roundtrip through a `deepcopy` (T3, T4) preserves this — but if `_migrate_flat_to_nested` returns a fresh dict (verified at print_settings.py:158 — it does), the migrated branch will write keys in `{free, slip, press}` order regardless of the legacy file's original key order.** This is a non-issue functionally — the loader reads keys by name — but the design promises "key order preserved" (line 239) which is *only* true on the non-migration path. Predicted cost: zero behavioural impact; one confused future reader of the design. Suggest a one-line clarification in T9: "key order preserved on the no-migration path; on migration, the canonical `free/slip/press` order is written." Non-blocking.

**Verification log**
- `vibe_cading/print_settings.py:87-92` → `get_default_profile_name() -> str` returns `os.getenv("VIBE_MACHINE_PROFILE", "fdm_standard")`. FR8 / Q2 target confirmed; importable without side effects beyond the module-level `load_env_file()` call at line 84.
- `vibe_cading/print_settings.py:138-144` → `_is_legacy_flat_entry(entry: dict) -> bool` exists, underscored, signature exactly as design claims; no `__all__` in the module (confirmed by reading lines 1-280), so `from vibe_cading.print_settings import _is_legacy_flat_entry` is importable. No name mangling (single leading underscore, not double).
- `vibe_cading/print_settings.py:147-171` → `_migrate_flat_to_nested(entry: dict) -> dict` exists, returns a fresh nested dict via dict-literal construction (line 158-171); does NOT mutate input. Safe for the design's deepcopy + immutable-input contract.
- `vibe_cading/print_settings.py:218-259` → `_load_json_profiles()` does merge `machine_profiles.json` (defaults) under `machine_profiles_user.json` (overrides) at the grade level (line 247-253). Design Round 2's "round-trip would inflate the user file" reasoning is factually correct.
- `vibe_cading/lego/constants.py:91` → `AXLE_HOLE_TIP_TO_TIP: float = 4.80` — plain float constant, no `os.getenv` wrapper (deliberately so per docstring lines 80-86: "These are plain constants (NOT env-overridable): they are the geometric nominal, not a printer-tuned value"). FR6 "live constant" target is correct and stable.
- `vibe_cading/lego/axle_hole_gauge.py:85-94` → `AxleHoleGauge.__init__` default `diameters: Sequence[float] = (4.70, 4.75, 4.80, 4.85, 4.90, 4.95, 5.00)`; `self.diameters` stored as `tuple` at line 94. Design's `AxleHoleGauge().diameters` introspection (line 41, T6 prompt text) is satisfied.
- `tools/check_license_headers.py:29` → glob pattern `tools/**/*.py` confirms FR2's CI gate auto-covers `tools/calibrate.py`. No scope change needed; SC6 / T15 will pass once the AGPLv3 header is included per T1.
- `tools/check_no_main_blocks.py:77` → roots are `repo_root / "vibe_cading"` and `repo_root / "parts"`; `tools/` is NOT walked. Confirms req lines 228-234 and unblocks the design's `if __name__ == "__main__":` entry point on line 119.
- Design imports proposed at line 92-94: "imports (stdlib + 3 in-tree symbols)". I count stdlib (`json`, `os`, `argparse`, `copy.deepcopy`, `pathlib.Path`, `sys`) and three in-tree (`get_default_profile_name`, `_is_legacy_flat_entry`, `_migrate_flat_to_nested` from `vibe_cading.print_settings`; `AxleHoleGauge` from `vibe_cading.lego.axle_hole_gauge`; `AXLE_HOLE_TIP_TO_TIP` from `vibe_cading.lego.constants`) — that is technically *five* in-tree symbols, not three, but no third-party deps. FR12 satisfied; minor inaccuracy in the design's own count is cosmetic.

**Re-confirmed 2026-05-23:** conditions (1) and (2) applied; verdict upgraded to APPROVE.

