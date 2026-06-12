# Requirements: `tools/calibrate.py` — guided print-tolerance calibration helper

> ⚠️ **SUPERSEDED 2026-05-23 at Step-4 design gate.** Scope rejected by human:
> v1 was hard-anchored to a single knob (`slip.radial`) and a single
> Lego-specific gauge (`AxleHoleGauge`), but the real goal is a generic
> per-machine + per-filament calibration helper that covers most models
> (defaults: M3 screw hole for slip, M3 nut for press; Lego axle as opt-in
> for delicate fits), and the work overlaps with two foundation-level TODOs
> (`machine_profiles → print_profiles` rename + field-level merge in the
> loader). Re-scoped into two new briefs:
>
> - `.agents/plans/2026-05-23-print-profile-foundation_req.md` (foundation: rename + key convention + field-level merge)
> - `.agents/plans/2026-05-23-calibration-helper-generic_req.md` (usage: generic gauges + multi-knob helper, built on the foundation)
>
> This artifact and its sibling `_design.md` are retained as prior-art —
> TL's atomic-write + migration mechanics carry forward conceptually, but
> the FRs and Implementation Plan are NOT load-bearing for the new briefs.

<!-- Filename: 2026-05-23-calibrate-helper_req.md  (tracked in git under .agents/plans/) -->

## Meta
- **Initiator role**: @designer (PM-spawned per user direction 2026-05-23 — *"drive tools/calibrate.py — guided calibration helper, include designer and tl for req and design"*)
- **Date**: 2026-05-23
- **Domain integrity gate**: NO

> Rationale for NO: this task adds a new CLI tool under `tools/` that *reads* an
> existing model class (`AxleHoleGauge`) and *writes* a documented JSON schema
> (`machine_profiles_user.json`, schema owned by `vibe_cading/print_settings.py`).
> It introduces no new CAD geometry contract, no new tolerance-profile field, no
> change to any model class's public API, and no change to the
> `ToleranceProfile` / `FitGrade` data shape. It is a *workflow ergonomics*
> deliverable on an already-stable data contract.

---

## Problem Statement

The project just finished a three-stage axle-hole calibration thread
(`.agents/plans/2026-05-20-...`, `-21-...`, `-22-...`). The resulting
calibration *mechanism* is sound — print a gauge, pick the variant that fits,
record the value in `machine_profiles_user.json` — but the *user-facing flow*
is entirely undocumented procedure scattered across three design briefs, an
`AxleHoleGauge` docstring, and `docs/lego-technic.md`. Today a user must:

1. Know that `AxleHoleGauge` exists and is the right entry point.
2. Find and run the right `python3 tools/preview.py …` (or `build.py` block)
   to produce a STEP they can print.
3. Print the gauge, visually pick the smallest hole that accepts a real Lego
   axle.
4. Hand-compute `slip.radial = (D − 4.80) / 2` from the chosen diameter.
5. Hand-edit `machine_profiles_user.json` — knowing the nested-schema shape,
   knowing not to clobber other grades, knowing which printer-profile key to
   target, knowing that legacy-flat entries must be migrated first.

Steps 4 and 5 are the friction points: they require the user to internalise
schema details (nested vs legacy flat, dict-merge semantics, the `radial`
formula) that the `print_settings.py` loader already understands. A guided
helper that performs steps 4 and 5 on the user's behalf — and signposts
steps 1–3 — converts the calibration thread's *output* into a *workflow* a
new OSS contributor can complete in one session without reading three design
briefs first.

This becomes a release-readiness concern at OSS publication time: the
pre-OSS checklist in [todo.md](../../todo.md) requires a getting-started
flow that walks a new contributor from clone to first useful output. Print
calibration is a one-time setup gate for every realistic downstream use of
the library (every printed Technic adapter passes through the axle-hole or
pin-hole fit). A user who hits a too-tight hole on their first print and
cannot find the calibration procedure will not stay.

## User Story / Motivation

As a **new vibe-cading user who has just printed a calibration gauge**,
I need **a single CLI command that asks me which gauge hole fit best and
writes the resulting tolerance value into `machine_profiles_user.json` for
me**, so that **I can dial in my printer's slip-fit tolerance without
learning the profile-JSON schema, the legacy-flat → nested migration, or
the `radial = (D − 4.80) / 2` formula by hand**.

Secondary persona: a **returning contributor recalibrating for a new
filament or printer** needs the same command to update an existing
`machine_profiles_user.json` entry without clobbering unrelated grades or
profiles.

## Functional Requirements

1. The repository **MUST** contain a new executable Python script at
   `tools/calibrate.py`, runnable as `python3 tools/calibrate.py` from the
   repository root.

2. `tools/calibrate.py` **MUST** carry the AGPLv3 header at the top of the
   file, identical in wording to the header in any current
   `vibe_cading/**/*.py` file. The CI license-header gate
   (`tools/check_license_headers.py`) already enforces this on
   `tools/**/*.py`; no scope change is required.

3. The tool **MUST** walk the user through the axle-hole **tip-to-tip
   (round-hole) slip-fit calibration** as its v1 scope — the calibration
   the existing `AxleHoleGauge` class is designed to produce. The
   user-visible outcome of one successful run is a `slip.radial` value
   written into the active printer profile inside
   `machine_profiles_user.json`. (See *Out of Scope* for the explicit list
   of other calibrations deferred to v2.)

4. The tool **MUST** signpost the print step but **MUST NOT** attempt to
   automate it. A successful flow assumes the user has *already* printed
   `AxleHoleGauge` on the target printer + material; the tool's job
   starts at the visual fit-test, not before. The tool **MUST** print a
   single concrete invocation the user can run to (re-)generate the
   gauge STEP if they have not yet printed one (e.g. by referencing
   `tools/preview.py` or an exported STEP path under `tmp/`) and exit
   non-destructively.

5. The tool **MUST** prompt the user for the **modelled diameter** of the
   smallest gauge hole that accepted the axle with a firm-but-free slip
   (one of `AxleHoleGauge`'s labelled values — currently `4.70 … 5.00`
   in 0.05 mm steps). Accepted input forms include the bare diameter
   (`4.95`) and the engraved label (`"4.95"`); the tool **MUST** reject
   any value outside the actual swept range with a helpful error message
   that lists the valid choices.

6. The tool **MUST** compute `slip.radial = (D − AXLE_HOLE_TIP_TO_TIP) / 2`
   using the live `AXLE_HOLE_TIP_TO_TIP` constant from
   `vibe_cading/lego/constants.py` — it **MUST NOT** hardcode `4.80`, so
   a future nominal change in `constants.py` propagates automatically.

7. The tool **MUST** show the user a *preview* of the JSON change it
   intends to write (target file path, target profile key, target grade,
   before/after `slip.radial` values, any required legacy-flat →
   nested migration) and **MUST** require explicit confirmation
   (interactive `y/N` prompt or an equivalent `--yes` non-interactive
   flag — see Open Question Q3) before writing. The default answer to
   the confirmation prompt **MUST** be "no" — the tool is destructive on
   confirm, non-destructive on default.

8. The tool **MUST** target the **active** machine profile — the one
   `vibe_cading.print_settings.get_default_profile_name()` resolves to
   (i.e. `VIBE_MACHINE_PROFILE` or the `fdm_standard` fallback) — so the
   value the user just calibrated is the value the rest of the library
   will read on the next `get_profile()` call. The tool **MUST** print
   the resolved active profile name before prompting, so the user can
   abort if it is wrong.

9. The tool **MUST NOT** clobber unrelated content in
   `machine_profiles_user.json`. Specifically: other profile keys
   (sibling printers), other fit grades (`free`, `press`) of the target
   profile, and other fields of the target grade (`axial`, `slot`) **MUST**
   be preserved verbatim. The write **MUST** be a structural merge into
   the existing JSON tree, not a wholesale rewrite.

10. The tool **MUST** handle the legacy-flat → nested schema migration
    transparently. If the target profile in `machine_profiles_user.json`
    is in the legacy flat schema (carries `slip_fit` / `free_fit` /
    `press_fit` / `z_clearance` keys), the tool **MUST** migrate it to
    the nested schema *as part of the write*, using the same migration
    that `vibe_cading.print_settings._migrate_flat_to_nested` already
    performs — and **MUST** declare this migration in the change preview
    (FR7) so the user sees it before confirming.

11. If `machine_profiles_user.json` does not exist, the tool **MUST**
    create it, containing only the target profile, in the nested schema,
    populated with the calibrated `slip.radial` plus any other grades
    inherited from the active profile's currently-resolved values.
    Creating the file **MUST** also be surfaced in the change preview
    (FR7).

12. The tool **MUST** operate entirely offline — no network calls, no
    package installs, no third-party pip dependencies beyond what
    `vibe_cading/print_settings.py` itself already imports (i.e.
    standard library + CadQuery's existing footprint). This matches the
    project's no-`python-dotenv`-style discipline.

13. The tool's `--help` output **MUST** describe the v1 scope (axle-hole
    tip-to-tip slip calibration), the prerequisite (a printed
    `AxleHoleGauge`), and the file it modifies
    (`machine_profiles_user.json`). It **MUST** name the gauge class
    explicitly so a `--help` reader can find the upstream artifact.

14. The tool **MUST** be discoverable from the README's getting-started
    flow. As part of this task's implementation phase, `README.md`
    **MUST** be updated to reference `python3 tools/calibrate.py` from
    the "Print Tolerances & Calibration" section added in the Stage-1
    Amendment-2 implementation pass. This is the v1 surface that closes
    the loop between "you have a printer" and "the library knows your
    tolerances."

## Non-Functional Constraints

- **Single-knob scope discipline.** Per the user's recorded standing
  preference ([core memory: "fewer-calibration-knobs"](../../memory/feedback_fewer_calibration_knobs.md)
  / the Stage-2b Amendment), v1 calibrates exactly one value (`slip.radial`
  on the active profile). The tool **MUST NOT** prompt for `axial`,
  `slot`, `free`, `press`, or any other knob that ships with a forgiving
  default. Each additional prompt is a regression on this principle and
  must be earned by a separate requirements pass.
- **Interaction shape.** The tool runs in a terminal against a human
  reader, not as a build-pipeline step. It is acceptable — and
  expected — for it to block on `input()` prompts; it **MUST NOT**
  launch a viewer, open a file in an editor, or require curses/TUI
  support. (Whether to *also* expose a one-shot non-interactive
  invocation is Open Question Q3.)
- **Filesystem safety.** The tool **MUST** write
  `machine_profiles_user.json` atomically (write to a tempfile, then
  rename) so an interrupted run cannot leave a partial / corrupt JSON
  on disk. If the existing file fails to parse, the tool **MUST**
  abort with a clear error rather than overwriting it.
- **Style.** The script is read by first-time contributors as
  documentation-by-example for the print-settings system. Variable
  names are descriptive; every prompt explains *what* it is asking and
  *why*. The script **MUST** demonstrate the library's documented
  pattern — no schema shortcuts, no direct dict mutation that bypasses
  `print_settings.py` helpers where those helpers exist.
- **Runtime budget.** The tool's no-print-path (just resolve the active
  profile, render the change preview, prompt) **MUST** complete in
  under ~2 seconds on the dev-container baseline — i.e. it must not
  trigger a full CadQuery import-cascade unless strictly required for
  the calibration math.

## Known Domain Constraints

- **Profile schema is owned by `vibe_cading/print_settings.py`** — see
  the module docstring (lines 16–73) for the canonical nested-schema
  shape, the legacy-flat schema, and the in-memory migration. Any
  reading / writing of `machine_profiles_user.json` **MUST** go through
  the helpers in that module (`_is_legacy_flat_entry`,
  `_migrate_flat_to_nested`, `_fitgrade_from_dict`,
  `_profile_from_nested`) rather than re-implementing them. If a helper
  is currently `_`-prefixed and the tool needs it as a public surface,
  promoting it (or wrapping it) is a TL call for the design phase.
- **Active profile resolution lives in
  `get_default_profile_name()`** — `VIBE_MACHINE_PROFILE` env var, then
  `fdm_standard` fallback. The tool MUST consume this function, not
  re-implement the resolution.
- **`AXLE_HOLE_TIP_TO_TIP` is the real-Lego nominal** (4.80 mm; Stage-1
  Amendment 2). It is a plain `float` constant — no `os.getenv` wrapper
  — and the calibration formula derives `slip.radial` *from* it. The
  tool MUST NOT shift the nominal.
- **`AxleHoleGauge`'s default sweep is `(4.70, 4.75, 4.80, 4.85, 4.90,
  4.95, 5.00)`** (Stage-1 brief Amendment 2026-05-20). The tool MUST
  read the actual default `diameters` tuple off the class — not
  hardcode it — so a future sweep adjustment propagates without a tool
  edit. (A user who printed a non-default sweep is an Open Question —
  see Q1.)
- **No-`__main__`-blocks rule does NOT apply to `tools/`** — only
  `vibe_cading/**` and `parts/**` are walked by
  `tools/check_no_main_blocks.py` (per
  `.agents/plans/2026-05-15-examples-directory_req.md` Known Domain
  Constraints, verified line 76–77). A `tools/calibrate.py`
  `if __name__ == "__main__":` entry point is therefore permitted and
  expected.

## Out of Scope

- **Cross-hole arm-slot calibration (`slip.slot`).** The Stage-2b
  Amendment ships `slip.slot = 0.10` as a conservative default on
  `fdm_standard` precisely so the user does not need to calibrate it.
  Adding a `slot` prompt would violate the *fewer knobs* anchor on day
  one. If a future bug report shows the shipped default is wrong for a
  class of printers, calibrating `slot` becomes a v2 requirement;
  until then it stays a default-only knob.
- **Other tolerance fields.** `axial` (counterbore depth), `free`-grade
  radial (loose clearance), `press`-grade radial (press fit), and every
  non-axle-hole consumer (`PIN_HOLE_PRINTED`, bearings, magnets) are
  out of scope. The v1 tool calibrates one value. Multi-value calibration
  is a v2 design conversation, not a v1 scope creep.
- **Auto-measurement.** No webcam, no camera-based fit detection, no
  USB-caliper integration. The user judges fit by hand (the procedure
  in `AxleHoleGauge`'s docstring and `docs/lego-technic.md`).
- **Auto-print dispatch.** No slicer invocation, no printer-API call,
  no STEP-to-G-code pipeline. The tool signposts the print step and
  trusts the user.
- **Stage 2c production-corner calibration** — deferred per the
  Stage-2b brief; not a v1 calibration knob and may never need one.
- **Build-pipeline integration.** The tool **MUST NOT** be registered
  in `build.toml` (it is a CLI utility, not a deliverable). It also
  **MUST NOT** become a dependency of `python build.py` or CI; it is a
  user-invoked one-off.
- **Project-wide calibration framework.** A pluggable
  "calibration registry" that other gauge classes can register into is
  a tempting v2 architecture but is **NOT** a v1 requirement. v1 ships
  one calibration (axle-hole tip-to-tip) end-to-end; the design phase
  may sketch the v2 shape but **MUST NOT** build it.

## Open Questions

<!-- Unresolved questions the TL-led design dialog (Step 3) must answer before sign-off. -->

- [ ] **Q1 — Custom-sweep handling.** `AxleHoleGauge` is parametric; a
  power user may have printed a non-default `diameters` tuple. Three
  paths: (a) the tool only accepts the *default* tuple's values and
  documents this in `--help` — simplest, covers the documented
  workflow, rejects a power-user's print with a clear error; (b) the
  tool accepts any value in `[3.0, 7.0]` and trusts the user to enter
  what they actually measured — most flexible, no rejection on a valid
  custom print; (c) the tool prompts for the swept range up front,
  validates against it — most defensive, adds a prompt that violates
  the "fewer knobs" anchor for default-sweep users. Recommend (a) for
  v1 (matches the documented procedure); design-phase confirms.

- [ ] **Q2 — Multi-profile environments.** A user who keeps multiple
  printer profiles in `machine_profiles_user.json` (e.g. `bambu_p1s`
  and `prusa_mk4`) may want to calibrate one without setting
  `VIBE_MACHINE_PROFILE` first. Should v1: (a) calibrate only the
  active profile (FR8 as written, simplest); (b) accept an optional
  `--profile <name>` override flag that targets a specific entry;
  (c) prompt the user to pick from the existing profile keys when more
  than one is present? Recommend (a)+(b): default to active, allow
  explicit override; reject (c) on the "fewer prompts" principle.

- [ ] **Q3 — Interactive vs one-shot invocation shape.** FR7 mandates a
  confirmation prompt; FR5 / FR8 mandate other prompts. Should the tool
  also expose a one-shot non-interactive form (e.g.
  `python3 tools/calibrate.py --diameter 4.95 --yes`) for users who
  already know their measured value, or is interactive-only sufficient
  for v1? One-shot adds ~5 lines of arg-parsing and one CI-friendly
  invocation; interactive-only ships faster. Note this is a
  requirements-level UX call (do users want a non-interactive form?),
  not an architecture call (which arg-parsing library) — the latter is
  TL's.

- [ ] **Q4 — Stale-confirmation guard.** Should the tool require the
  user to type the diameter twice (or type "yes" rather than "y") on
  the confirmation prompt, on the grounds that
  `machine_profiles_user.json` edits propagate silently to every
  subsequent build? Default-no confirmation (FR7) already guards
  against accidental enter-key; a stronger guard buys defence-in-depth
  at the cost of an extra friction point on a single-knob tool.

- [ ] **Q5 — Output verbosity / next-steps.** On successful write, what
  should the tool print? Minimum: the path written and the new
  `slip.radial` value. Maximum: also re-run `AxleHoleGauge`'s
  recommended verification (the user re-inserts the axle into the
  *same* gauge hole after profile change — but the gauge was printed
  with the *old* profile, so re-running it makes no sense; the real
  verification is the next real-part print). Recommend: a short
  block — path, before/after value, the suggested next step ("print
  a real Technic adapter and confirm fit").

---

## Human Confirmation Checkpoint
- [x] Requirements reviewed and confirmed by human _(2026-05-23, PM-relayed; Q1–Q5 deferred to TL+Designer Step-3 co-design)_
<!-- Do not proceed to design until this box is checked. -->
