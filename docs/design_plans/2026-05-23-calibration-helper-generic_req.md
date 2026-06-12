# Requirements: `tools/calibrate.py` — generic multi-knob print-tolerance calibration helper (Brief #2)
<!-- Filename: 2026-05-23-calibration-helper-generic_req.md  (tracked in git under .agents/plans/) -->

## Meta
- **Initiator role**: @designer (PM-spawned 2026-05-23 — Brief #2 of the calibration-helper re-scope; built on the just-merged Brief #1 print-profile foundation, PR #8 merge commit `dc877a7`)
- **Date**: 2026-05-23
- **Domain integrity gate**: **YES**
  - Rationale: this brief writes calibrated tolerance values into
    `print_profiles_user.json` that propagate via `get_profile()` to
    *every* downstream model class — Lego adapters, RC mounts, generic
    screws, nuts, bearings, joints, standoffs, hinges. A wrong
    calibration math (e.g. the M3-clearance-hole gauge writes the
    derived value into the wrong knob, or applies the wrong nominal,
    or mis-resolves the gauge-to-grade mapping) silently mis-applies
    tolerances **library-wide** — every printed part is wrong on the
    next print cycle, recoverable only after a physical fit-test fails.
    The blast radius is identical to Brief #1's domain-integrity-gate
    rationale; the harm vector (write-back, not read-side merge) is
    different but symmetric. The design-flow therefore requires a
    fresh-context Designer co-sign at Step 3 and Step 5 Phase C per the
    design-flow integrity-gate rule.

---

## Problem Statement

Brief #1 (PR #8, merged 2026-05-23) shipped the data-contract foundation:
files renamed to `print_profiles*.json`, env var renamed to
`VIBE_PRINT_PROFILE`, user-key convention `<machine>__<material>[__<brand>]`
documented, and the loader now performs a **field-level deep-merge** so
a user can override a single tolerance leaf
(`{"fdm_standard": {"slip": {"radial": 0.11}}}`) and inherit every
sibling field from the shipped grade. The README's *Print Tolerances &
Calibration* section was rewritten to document the new contract and
forward-points at *"a single-knob calibration CLI that writes the value
into `print_profiles_user.json` for you is on the roadmap."*

The roadmap is now this brief. The remaining gap is a user-facing one:

1. **The calibration procedure is documented but unautomated.** A user
   must print a gauge, judge fit by hand, hand-compute the radial value
   from a nominal, and hand-edit JSON keyed under their
   `<machine>__<material>[__<brand>]` profile name. The schema is now
   forgiving (field-level merge means one leaf override is sufficient
   on disk) but the *workflow* of getting that one leaf right is still
   five manual steps per knob.
2. **The existing calibration thread targeted Lego axle holes only.**
   `AxleHoleGauge` calibrates `slip.radial` from the *Lego axle*
   nominal (4.80 mm) — a delicate-fit signal useful to power users, but
   irrelevant to a contributor who builds RC mounts, screw-bolted
   plates, or bearing pockets with no Lego parts in sight. The Lego
   gauge as the *only* calibration entry point is a niche-default;
   most-models calibration needs gauges anchored to **generic
   mechanical primitives** (M3 screw clearance hole, M3 nut press
   pocket) that align with what most downstream cutters actually
   consume.
3. **Calibration is per-machine + per-filament reality.** The
   foundation's `<machine>__<material>__<brand>` key convention codifies
   this — the helper has to honour it. A user with a Bambu P1S + PLA
   Overture profile + a Bambu P1S + PETG profile needs to calibrate
   each independently, each writing under its own profile key, without
   clobbering the other. Today, a single mistyped key (`bambo_p1s`)
   silently creates a typo'd profile entry that the loader never reads
   (it falls back to `fdm_standard` with the new
   unknown-profile warning); the helper must make the active-profile
   resolution and the write-back target visible to the user *before*
   the write.
4. **Print-cycle economy matters.** Each calibration print is ~30–60
   minutes of printer time per gauge. The standing
   *fewer-calibration-knobs* anchor (auto-memory:
   [feedback_fewer_calibration_knobs.md](/root/.claude/projects/-workspaces-vibe-cading/memory/feedback_fewer_calibration_knobs.md))
   says: minimise values a user must measure/set; ship defaults for
   forgiving fits, calibrate only fussy ones. The user's *"no more
   than 5 models needed, fewer is better"* anchors this numerically:
   v1's gauge inventory MUST land at **≤ 5 print models total**, with
   2 default + 3 opt-in being the recommended split.

Brief #2 turns the foundation's read-side contract into a write-side
ergonomics workflow: a single CLI command that walks the user through
calibrating the **most-consumed** tolerance knobs against **generic
mechanical gauges** that are not Lego-specific, writes the results into
the user's per-machine + per-filament profile, and respects both the
field-level merge contract (don't clobber sibling fields) and the
fewer-knobs anchor (don't add a prompt for a value that ships with a
forgiving default).

## User Story / Motivation

As a **new vibe-cading contributor who has just printed one or two
calibration gauges on a new printer + filament combination**, I need
**a single CLI command that asks me which gauge feature fit best for
each knob it calibrates and writes the resulting tolerance values into
the right `<machine>__<material>[__<brand>]` profile entry in
`print_profiles_user.json` for me**, so that **I can dial in my
printer's most-consumed clearance knobs without learning the
profile-JSON schema, the field-level merge semantics, the gauge-to-knob
mapping, or the per-knob radial-derivation math by hand — and so that
every downstream model class (RC mounts, Lego adapters, screw-bolted
plates, bearing pockets) inherits the calibrated values on the next
`get_profile()` call without me touching another file**.

Secondary persona: a **returning contributor recalibrating for a new
filament or printer** needs the same command to (a) target a specific
named profile (`--profile bambu_p1s__petg_polymaker`), (b) create the
entry if it does not yet exist, and (c) update only the calibrated
leaves under field-level merge — never clobbering sibling fields or
unrelated profile entries.

Tertiary persona: a **Lego-Technic-focused user who needs the delicate
axle-slip-fit calibration** (the existing `AxleHoleGauge` thread)
needs an opt-in path to use that gauge for the `slip.radial` knob
instead of (or in addition to) the generic default gauge.

## Functional Requirements

<!-- Numbered, unambiguous, testable. Use "MUST" or "MUST NOT" language. -->

### A. Repository surface

1. The repository **MUST** contain a new executable Python script at
   `tools/calibrate.py`, runnable as `python3 tools/calibrate.py` from
   the repository root.

2. `tools/calibrate.py` **MUST** carry the AGPLv3 header at the top of
   the file, identical in wording to the header in any current
   `vibe_cading/**/*.py` file. The CI license-header gate
   (`tools/check_license_headers.py`) already enforces this on
   `tools/**/*.py`; no scope change is required.

3. The tool's `--help` output **MUST** describe (a) the v1 scope (which
   knobs it calibrates and which gauges it uses), (b) the prerequisite
   (the user must print the gauge(s) themselves before running this
   tool — auto-print is out of scope), (c) the file it modifies
   (`print_profiles_user.json`), (d) the per-profile targeting
   mechanism (active-profile resolution + `--profile <name>` override),
   and (e) at least one concrete invocation example that re-generates a
   gauge STEP (e.g. via `tools/preview.py` or an exported STEP path
   under `tmp/`).

### B. Knob scope (the load-bearing v1 decision)

4. v1 **MUST** calibrate at minimum the following tolerance knobs:
   - `free.radial` — the **most-consumed** knob in the library
     (consumed by every class in `vibe_cading/mechanical/holes.py`,
     every screw `to_cutter()`, every nut captive-pocket cutter,
     standoffs, hinges, RC `freespin_hex_hub` bearing seats).
   - `press.radial` — consumed by bearing outer-pocket cutters in
     `vibe_cading/mechanical/bearings.py` and (potentially, see
     Open Question Q6) by nut press-fit pockets if the design phase
     introduces a press-pocket variant.

5. v1 **MUST** support `slip.radial` calibration as an **opt-in**
   knob (consumed by Lego `TechnicAxleHole`, magnets, and the bearing
   shaft-slip cutter). The opt-in mechanism (CLI flag, sub-subcommand,
   or interactive selection) is Open Question Q1; the requirement here
   is that the user can reach the slip-radial calibration without
   editing source code.

6. v1 **MUST NOT** prompt the user for `slip.axial`, `slip.slot`,
   `free.axial`, `free.slot`, or `press.axial` calibration. These
   knobs ship with forgiving defaults on `fdm_standard` (e.g.
   `slip.slot = 0.10` mm per Brief #1 §8 pinned tuple) that the
   foundation's field-level merge preserves on a user's single-leaf
   override. The standing *fewer-calibration-knobs* anchor forbids
   prompting for default-shipped values without a separate
   requirements pass per knob.

### C. Gauge model inventory

7. v1's total gauge model count — counted as **distinct printable
   models the user must print**, NOT as test samples within one
   gauge — **MUST** land at **≤ 5 models total**, split as:
   - **2 default gauges** (always run when the user invokes the tool
     with no opt-ins): one for `free.radial`, one for `press.radial`.
   - **Up to 3 opt-in gauges** (run only when the user explicitly
     selects them): the existing `AxleHoleGauge` for `slip.radial`
     (Lego-axle delicate-fit signal), and at most two future
     additions deferred to v2 (see *Out of Scope*).

8. The default `free.radial` gauge **MUST** be anchored to the **M3
   machine-screw clearance hole** nominal (3.2 mm per
   `vibe_cading/mechanical/screws/metric.py` line 23,
   `MetricMachineScrew.DIMENSIONS["M3"]["clearance"]`). This nominal
   is the diameter the M3-clearance-hole cutter reads at the call site
   `CounterboreHole(shaft_diameter=3.2)` then inflates by
   `free.radial`. The gauge sweeps **hole diameters** around the
   3.2 mm centre such that the user can read off the smallest hole
   that accepts a real M3 screw shank with a firm-but-free slip
   without rotational binding.

9. The default `press.radial` gauge **MUST** be anchored to one of
   two candidate nominals — **Open Question Q6 (Designer
   recommendation: M3 nut across-flats 5.5 mm)** — and the resolution
   is load-bearing for the knob-to-gauge mapping. The two candidates:
   - (a) **M3 nut across-flats** (5.5 mm per
     `vibe_cading/mechanical/nuts/metric.py` line 28,
     `MetricHexNut.DIMENSIONS["M3"]["width_flats"]`). Gauge sweeps
     hexagonal pocket widths around 5.5 mm; user identifies the
     smallest pocket that accepts the nut as a press-fit. *Caveat:*
     `MetricHexNut.to_cutter()` (line 57–69) currently reads
     `profile.free.radial` for the captive-pocket inflation, NOT
     `press.radial`. Selecting this gauge requires either (i) a
     small targeted change to `MetricHexNut.to_cutter` (or to a new
     "press pocket" variant) so its allowance reads `press.radial`,
     OR (ii) calibrating the M3-nut gauge against `free.radial` (a
     second sample for the same knob the M3-screw gauge calibrates,
     which is wasteful), OR (iii) deferring nut calibration to v2
     and using a different press-fit gauge here.
   - (b) **Bearing outer-pocket** (e.g. MR85 8 mm OD) — matches what
     the existing `ToleranceGauge` Row 2 already exercises with
     `prof.press.radial` (verified in
     `vibe_cading/mechanical/tolerance_gauge.py:94–105`); the gauge
     can be a stripped-down single-row variant of `ToleranceGauge`.
     No source change required; honest mapping to `press.radial`.

10. The opt-in `slip.radial` gauge **MUST** be the existing
    `vibe_cading.lego.axle_hole_gauge.AxleHoleGauge` (no new gauge
    class). The user selects it via the opt-in mechanism (Q1); the
    helper's calibration math is the same `slip.radial = (D − AXLE_HOLE_TIP_TO_TIP) / 2`
    formula already documented in the gauge's class docstring (line
    60), reading `AXLE_HOLE_TIP_TO_TIP` live from
    `vibe_cading/lego/constants.py` (no hardcoded 4.80).

11. The helper **MUST** read each gauge's default-sweep tuple off
    the gauge class itself (e.g. `MThreeClearanceGauge().diameters`,
    `MThreeNutPocketGauge().widths`, `AxleHoleGauge().diameters`) —
    it **MUST NOT** hardcode the sweep values. A future sweep-range
    adjustment in a gauge class must propagate without a helper
    edit. (Mirrors the SUPERSEDED brief's FR-derived constraint at
    `.agents/plans/2026-05-23-calibrate-helper_req.md:110`.)

12. The new gauge model classes themselves (the M3-screw-clearance
    gauge, and the press-fit gauge per Q6 resolution) **MAY** be
    implemented either inside this brief or as separate sub-briefs.
    Open Question Q7. The brief's Functional Requirements assume the
    gauge classes exist by the time the helper ships; the
    Implementation Plan in the design phase decides the sequencing.

### D. Cross-model propagation contract (the load-bearing user-facing claim)

13. Every tolerance value the helper writes into
    `print_profiles_user.json` **MUST** propagate to every downstream
    model class that consumes `vibe_cading.print_settings.get_profile()`
    on the **next** `get_profile()` call — no module reload required,
    no model-class re-import required, no source edit required. This
    is the load-bearing user-facing claim of the helper
    (*"calibrate once, all models inherit"*) and the foundation's
    field-level merge contract is the data-contract enabler. The
    helper **MUST** state this contract explicitly in its `--help`
    text and in its post-write success block.

14. The helper **MUST** target the same `ToleranceProfile` /
    `FitGrade` / `slip` / `free` / `press` / `radial` / `axial` /
    `slot` field set the foundation defines — no new fields, no
    renamed fields, no schema extension. (Mirrors Brief #1 §"Known
    Domain Constraints" and §"Out of Scope": the field set is
    invariant.)

### E. Per-machine + per-filament workflow

15. The helper **MUST** consume
    `vibe_cading.print_settings.get_default_profile_name()` to
    resolve the **active** profile — the same resolution chain the
    rest of the library uses (`VIBE_PRINT_PROFILE` env var first,
    then `VIBE_MACHINE_PROFILE` legacy with the foundation's
    one-shot deprecation warning, then `fdm_standard` fallback).
    The helper **MUST NOT** re-implement this resolution.

16. The helper **MUST** accept an optional `--profile <name>` flag
    that overrides the active profile resolution and targets a
    specific named profile (e.g.
    `--profile bambu_p1s__petg_polymaker`). When set, the helper
    operates on that profile entry exclusively; the resolution
    chain in FR15 is bypassed for the duration of the run. (Mirrors
    Q2 resolution in the SUPERSEDED brief.)

17. The helper **MUST** print the resolved target profile name to
    stdout **before** prompting for any user input or making any
    write, so the user can abort by Ctrl-C if it is wrong. (Mirrors
    SUPERSEDED FR8.)

18. If the resolved target profile name does **not** yet exist in
    `print_profiles_user.json` (the typical case for a fresh
    `<machine>__<material>__<brand>` calibration on a freshly-set-up
    filament), the helper **MUST** create the entry, populated only
    with the calibrated leaves of this run — no inherited defaults
    injected, since the foundation's field-level merge will fill the
    siblings at read time. The creation of a new profile entry
    **MUST** be surfaced explicitly in the change preview (FR21)
    so the user sees it before confirming.

19. If `print_profiles_user.json` itself does not yet exist (a
    fresh-checkout user), the helper **MUST** create it, containing
    only the target profile entry per FR18. (Mirrors SUPERSEDED
    FR11.)

20. When the resolved target profile name exists but does not match
    any shipped fallback (`fdm_standard`, `resin_precise`, `cnc`)
    and is being **created** for the first time by this run, the
    helper **MUST** prompt the user once to confirm the target key
    name and the recommended `<machine>__<material>[__<brand>]`
    convention. The confirmation prompt's default **MUST** be the
    resolved key as-is; the prompt exists specifically to catch
    typo'd `VIBE_PRINT_PROFILE` keys (`bambo_p1s` ≠ `bambu_p1s`)
    before a write creates a typo'd entry. The exact prompt-vs-flag
    shape for non-interactive runs is Open Question Q5.

### F. Persistence, atomic safety, and field-level merge contract

21. The helper **MUST** show the user a *change preview* of every
    JSON change it intends to write **before** writing, including:
    (a) the target file path with a `(will be CREATED)` annotation
    when the file does not yet exist; (b) the target profile key with
    a `(will be CREATED)` annotation when the profile entry does not
    yet exist; (c) for each calibrated knob: the grade, the field,
    the before-value (with `(inherited from print_profiles.json)`
    annotation when the user file does not currently override it),
    the after-value, the derivation (input dimension, nominal, and
    formula). Format is plain text per the SUPERSEDED design's
    wire-format pattern; nothing parses it programmatically.

22. The helper **MUST** require explicit confirmation before writing
    (interactive `y/N` prompt with default-no, or a non-interactive
    `--yes` flag — see Open Question Q5). On default-no or any
    non-`y`/`yes` response the helper **MUST** exit without
    modifying any file. (Mirrors SUPERSEDED FR7.)

23. The helper **MUST** write `print_profiles_user.json` atomically
    via tempfile + `os.replace` so an interrupted run cannot leave a
    partial / corrupt JSON on disk. If the existing file fails to
    parse, the helper **MUST** abort with a clear error rather than
    overwriting it. (Mirrors SUPERSEDED FR-NFC "Filesystem safety";
    SUPERSEDED design T9.)

24. The helper's write **MUST** be a **field-level merge** against
    the existing user file: only the calibrated leaves under
    `<profile>.<grade>.<field>` are touched; every other leaf in
    the target profile, every other grade in the target profile,
    and every other top-level profile in the file **MUST** remain
    byte-identical. The write **MUST NOT** restate any sibling
    field, **MUST NOT** inject inherited defaults, and **MUST NOT**
    re-serialise any unrelated profile entry. (This is the
    write-side mirror of Brief #1's read-side
    `_deep_merge_profiles` contract — the user file stays as
    *"diffs from defaults"*, never morphing into *"full snapshot of
    resolved values"*.)

25. The helper **MUST** handle the legacy-flat → nested schema
    migration transparently. If the target profile in the existing
    `print_profiles_user.json` is in the legacy flat schema (carries
    `slip_fit` / `free_fit` / `press_fit` / `z_clearance` keys), the
    helper **MUST** migrate it to the nested schema *as part of the
    write*, reusing the foundation's `_migrate_flat_to_nested`
    helper — and **MUST** declare this migration in the change
    preview (FR21) so the user sees it before confirming. (Mirrors
    SUPERSEDED FR10.)

### G. Sequencing and one-shot UX

26. v1 **MUST** ship at least one of: (a) a **sequence mode** where
    the user invokes `tools/calibrate.py` with no arguments and the
    tool walks every default-knob calibration in sequence (print
    one, measure, enter; print next, measure, enter; …), OR (b)
    **per-knob subcommands** where the user invokes
    `tools/calibrate.py free` / `press` / `slip` / `all` to
    calibrate one knob at a time. The exact UX shape is Open
    Question Q2 — the requirements-level call is: at minimum, the
    default no-args invocation **MUST** be usable by a new
    contributor without reading the source, and **MUST** complete
    in a single confirmation-and-write cycle per knob (no surprise
    multi-knob bundled writes without a per-knob preview).

27. Within one sequence run, the helper **MUST** persist each knob's
    calibrated value atomically as that knob's confirmation
    completes — the user **MUST NOT** be required to complete the
    full sequence to land any single knob's calibration. A user who
    Ctrl-Cs between gauges 1 and 2 keeps gauge 1's value on disk.
    (See Open Question Q4 for the alternative atomic-session
    semantic; this is the recommended default.)

28. Per-knob runs (whether invoked individually or as the next step
    of a sequence) **MUST** be independent: calibrating
    `free.radial` **MUST NOT** require the user to have calibrated
    `press.radial` first, or vice versa.

### H. Discoverability and offline operation

29. The helper **MUST** be discoverable from the README's *Print
    Tolerances & Calibration* section. As part of this task's
    implementation phase, that section **MUST** be updated to
    replace the current forward-pointer
    (*"a single-knob calibration CLI ... is on the roadmap"*) with
    a live reference to `python3 tools/calibrate.py`, including
    the no-args invocation as the recommended entry point.

30. The helper **MUST** operate entirely offline — no network calls,
    no package installs, no third-party pip dependencies beyond what
    the consumed in-tree modules
    (`vibe_cading.print_settings`, gauge classes) already import.
    Matches the project's no-`python-dotenv`-style discipline.
    (Mirrors SUPERSEDED FR12.)

## Non-Functional Constraints

- **Print-cycle economy (the 5-model cap is the numeric form of the
  fewer-knobs anchor).** Total v1 gauge model count ≤ 5 distinct
  printable models. Each gauge model packs its sweep into one
  printable part — the gauge's *internal* sweep count is a design
  call per gauge, but the user prints **one part per model**, not
  one part per sweep value.

- **Interaction shape.** The helper runs in a terminal against a
  human reader, not as a build-pipeline step. It is acceptable —
  and expected — for it to block on `input()` prompts; it **MUST
  NOT** launch a viewer, open a file in an editor, or require
  curses/TUI support. A one-shot non-interactive form (with all
  inputs supplied via flags) is also acceptable but is Open
  Question Q5.

- **Filesystem safety.** Per FR23, every write is atomic
  (tempfile + `os.replace`). Per FR24, every write is field-level
  merge. An interrupted run **MUST NOT** leave a corrupt JSON on
  disk, and **MUST NOT** silently clobber unrelated profile
  entries or sibling fields.

- **Field-level merge invariant on write.** The write-side and
  read-side merge contracts **MUST** be symmetric: the helper
  writes only the leaves it calibrated, and the foundation's
  `_deep_merge_profiles` fills the siblings on the next
  `get_profile()` call. The Implementation Plan **MUST** include
  a test that asserts a calibrated write against a multi-profile,
  multi-grade existing user file leaves every non-target leaf
  byte-identical on disk.

- **Style.** The helper is read by first-time contributors as
  documentation-by-example for the print-settings system.
  Variable names are descriptive; every prompt explains *what* it
  is asking and *why* (which knob it is calibrating, which
  downstream classes consume it, what the gauge nominal is).
  The script **MUST** demonstrate the library's documented
  pattern — no schema shortcuts, no direct dict mutation that
  bypasses `print_settings.py` helpers where those helpers
  exist.

- **Runtime budget.** The helper's `--help` path (parse args,
  render help text, exit) **MUST** complete in under ~2 seconds
  on the dev-container baseline — i.e. it must not trigger a
  full CadQuery import-cascade for `--help` alone. CadQuery
  imports for gauge introspection are acceptable on the prompt
  path but **MUST** be deferred until first prompt entry.
  (Mirrors SUPERSEDED FR-NFC "Runtime budget" + T12.)

- **Per-knob session atomicity.** Per FR27, each knob's
  confirmation lands a single atomic write. A multi-knob
  sequence is *not* one big atomic write — it is a sequence of
  per-knob atomic writes. (Open Question Q4 challenges this
  default; if the design phase reverses it, the constraint
  flips accordingly.)

## Known Domain Constraints

- **Profile-schema and merge mechanics are owned by
  `vibe_cading/print_settings.py`** (the just-merged Brief #1
  foundation). The helper **MUST** read/write through the
  foundation's helpers — `get_default_profile_name`,
  `_is_legacy_flat_entry`, `_migrate_flat_to_nested`, and any
  newly-public surface the design phase introduces. The
  helper **MUST NOT** re-implement the merge, the migration,
  or the resolution chain. (The SUPERSEDED design's R1
  resolution — direct-import of `_`-prefixed helpers with a
  module-docstring callout — carries forward as a candidate
  approach; the design phase may revisit it now that a second
  consumer materialises and the dual-lens deletion test
  reads differently.)

- **`AXLE_HOLE_TIP_TO_TIP` is the real-Lego nominal** (4.80 mm;
  `vibe_cading/lego/constants.py` line 91, plain float, no
  `os.getenv` wrapper). The opt-in slip-radial calibration math
  derives `slip.radial = (D - AXLE_HOLE_TIP_TO_TIP) / 2` and
  reads the constant live. (Mirrors SUPERSEDED FR6.)

- **`MetricMachineScrew.DIMENSIONS["M3"]["clearance"] = 3.2`
  mm** (`vibe_cading/mechanical/screws/metric.py` line 23). This
  is the nominal the M3-screw-clearance default gauge sweeps
  around, and the nominal the `free.radial` derivation reads
  from. The helper **MUST** read it live from the DIMENSIONS
  dict (not hardcode 3.2).

- **`MetricHexNut.DIMENSIONS["M3"]["width_flats"] = 5.5` mm**
  (`vibe_cading/mechanical/nuts/metric.py` line 28). If the
  design phase resolves Q6 toward the M3-nut gauge, this is the
  nominal the gauge sweeps around. The helper **MUST** read it
  live (not hardcode 5.5).

- **Knob-to-consumer mapping (verified by repo-wide grep
  2026-05-24)**:
  - `free.radial` → every class in
    `vibe_cading/mechanical/holes.py`, all screw `to_cutter()`,
    `MetricHexNut.to_cutter` (captive pocket),
    `MetricSquareNut.to_cutter`, `MetricTNut.to_cutter` (×2),
    `Standoff.to_cutter`, `Hinge.to_cutter`, RC
    `FreespinHexHub.bearing_seat_diameter`.
  - `free.axial` → counterbore head depth, captive-nut pocket
    depth, RC `FreespinHexHub.bearing_seat_height`.
  - `slip.radial` → `TechnicAxleHole`, `Magnet.to_cutter`
    (×2 sites), `Bearing.shaft_cutter`.
  - `slip.axial` → `Magnet.to_cutter` (×2 sites).
  - `slip.slot` → `TechnicAxleHole` narrow-slot allowance.
  - `press.radial` → `Bearing.outer_pocket` (only consumer in
    the current tree).
  This mapping is load-bearing for FR8 / FR9 / Q6 — the gauge
  the helper offers for a knob **MUST** be the gauge that
  isolates the geometry the knob's downstream consumers
  actually read.

- **No-`__main__`-blocks rule does NOT apply to `tools/`** —
  only `vibe_cading/**` and `parts/**` are walked by
  `tools/check_no_main_blocks.py`. A
  `tools/calibrate.py if __name__ == "__main__":` entry point
  is permitted and expected. (Mirrors SUPERSEDED §"Known
  Domain Constraints".)

- **The 2026-05-23
  [feedback_fewer_calibration_knobs.md](/root/.claude/projects/-workspaces-vibe-cading/memory/feedback_fewer_calibration_knobs.md)
  auto-memory anchor is the standing user preference**:
  minimise values a user must measure/set; ship defaults for
  forgiving fits, calibrate only fussy ones. The 5-model cap
  in FR7 is the numeric instantiation of this anchor for this
  brief. Every Open Question that proposes adding a knob or a
  gauge is evaluated against this anchor.

## Out of Scope

<!-- Explicitly state what this task does NOT cover to prevent scope creep. -->

- **The opt-in Lego axle gauge implementation.** Already exists
  as `vibe_cading.lego.axle_hole_gauge.AxleHoleGauge` (Stage 1
  brief, Amendment 2 — `4.70 … 5.00` mm sweep, `4.80 mm`
  nominal). The helper **consumes** this class; it does not
  re-implement or modify it.

- **Cross-hole arm-slot calibration (`slip.slot`).** Brief #1's
  `fdm_standard.slip.slot = 0.10` mm pinned default
  (Brief #1 §8 T9b shipped-profile pin) is the conservative
  floor and ships forgiving. The `AxleCrossHoleGauge` exists
  (Stage 2b) and remains available as a manual calibration
  path; v1 of this helper does NOT prompt for it. Per the
  fewer-knobs anchor, ship a default rather than calibrate.

- **`*.axial` knobs (`slip.axial`, `free.axial`, `press.axial`).**
  All ship with forgiving defaults on `fdm_standard` (per the
  Brief #1 §8 T9b pinned tuples) that field-level merge
  preserves. Counterbore depths and pocket depths are coarse
  enough on FDM that calibration discriminates poorly. Defer
  to v2; ship defaults.

- **`slot` knobs on grades other than `slip` (`free.slot`,
  `press.slot`).** Ship `0.0` per the Brief #1 §8 pin; no
  consumer reads them today. No calibration entry point in v1.

- **Net-new gauge classes beyond what FR7's "default 2 + opt-in
  up-to-3" inventory requires.** Specifically out-of-scope: a
  pin-hole gauge (Technic pin friction-fit, a different
  per-radial-knob calibration), a bearing-press gauge beyond
  what Q6 resolution permits, a magnet-press gauge, a
  threaded-insert taper gauge, an axial counterbore-depth
  gauge. Each is a legitimate v2 brief, none is v1 scope.

- **Auto-measurement.** No webcam, no camera-based fit
  detection, no USB-caliper integration. The user judges fit
  by hand (the same procedure the existing gauge docstrings
  document). (Mirrors SUPERSEDED §"Out of Scope".)

- **Auto-print dispatch.** No slicer invocation, no
  printer-API call, no STEP-to-G-code pipeline. The helper
  signposts the print step and trusts the user.

- **Stage 2c production-corner calibration** — deferred per
  the Stage-2b brief; not a v1 calibration knob and may never
  need one.

- **Build-pipeline integration.** The helper **MUST NOT** be
  registered in `build.toml` (it is a CLI utility, not a
  deliverable). It also **MUST NOT** become a dependency of
  `python build.py` or CI; it is a user-invoked one-off.

- **A pluggable calibration-registry framework.** A "register a
  new gauge against a knob" extensibility surface is a tempting
  v2 architecture but is explicitly **NOT** v1 — the SUPERSEDED
  brief already flagged this, and the same out-of-scope
  rationale carries forward: ship one helper end-to-end with
  the documented gauges; revisit registry-vs-direct-import when
  a sixth gauge materialises.

- **The `ToleranceProfile` / `FitGrade` dataclass rename.**
  Explicitly out-of-scope per Brief #1 §Out of Scope. The
  field set and class names are invariant under v1.

- **GUI / TUI / curses anything.** Out of scope per FR §G and
  Non-Functional Constraints §"Interaction shape".

- **Changing existing model-class signatures or
  `to_cutter()` knob-reads.** If Q6 resolution requires a
  small targeted change to `MetricHexNut.to_cutter()` (e.g.
  to read `press.radial` for a press-pocket variant), that
  change is scoped to whatever sub-brief Q7 resolves to —
  not to the helper itself. The helper is a write-side CLI;
  it does not refactor consumers.

## Open Questions

<!-- Unresolved questions the TL-led design dialog (Step 3) must answer before sign-off. -->

- [ ] **Q1 — Opt-in mechanism for the `slip.radial` Lego-axle
  gauge.** Options: (a) a `--gauge axle` flag (or
  `--slip-gauge axle`) on the main command; (b) a sub-subcommand
  (`tools/calibrate.py slip --use axle`); (c) an interactive
  picker that prompts when the user reaches the `slip` knob's
  calibration step ("Use M3-screw / axle / skip?"); (d) leave the
  Lego axle gauge entirely out of the helper and ship only the
  generic gauges in v1 (users who want the delicate-fit axle
  signal continue to use the existing manual procedure
  documented in `AxleHoleGauge`'s docstring). Designer
  recommendation: (a) for the default invocation, with (c)
  layered on if Q2 resolves toward sequence mode and the slip
  step is reached interactively. Reject (d) — the user
  explicitly named Lego-axle calibration as the delicate-fit
  use-case in the reframe.

- [ ] **Q2 — Sequence vs. per-knob subcommand UX shape.** Three
  candidates: (a) **single command, walks everything in
  sequence** — `tools/calibrate.py` with no args prints gauge 1
  instructions, prompts, writes, then gauge 2 instructions,
  prompts, writes, with explicit per-knob confirmation
  preview each time; (b) **per-knob subcommands** —
  `tools/calibrate.py free`, `tools/calibrate.py press`,
  `tools/calibrate.py slip`, `tools/calibrate.py all`
  (where `all` is sequence mode); (c) **hybrid** — single
  command with optional positional `[knob]` arg
  (`tools/calibrate.py [free|press|slip|all]`, defaulting to
  `all`). Designer recommendation: (c) — minimises CLI surface
  while keeping per-knob targeting flat. The choice
  fundamentally shapes `--help` text, the change preview, and
  the test matrix; cannot be deferred.

- [ ] **Q3 — Custom-sweep handling.** Each gauge is parametric;
  a power user may have printed a non-default sweep tuple.
  Options: (a) helper accepts only the *default* sweep values
  and rejects others with a clear error listing valid choices;
  (b) helper accepts any numeric input in a sane range
  (e.g. `[1.0, 10.0]` mm) and trusts the user; (c) helper
  prompts for the swept range up front. Designer recommendation:
  (a) — matches the documented workflow and the
  SUPERSEDED brief's resolution; rejects (b)+(c) on the
  fewer-prompts anchor. If a power-user need surfaces, v2.

- [ ] **Q4 — Per-knob atomic write vs full-session atomic
  write.** FR27 defaults to per-knob (each confirmation lands
  one atomic write; Ctrl-C between knobs keeps prior knobs
  persisted). The alternative is full-session atomicity (no
  write happens until the user confirms the *whole* sequence
  of calibrated values; Ctrl-C between knobs discards everything).
  Per-knob is the documented filesystem-safety pattern from the
  SUPERSEDED design (T10 crash-injection test); full-session
  matches the "one print, one calibration cycle" mental model
  but invents a different atomicity semantic. Designer
  recommendation: per-knob (FR27 as written). Full-session is a
  surprise foot-gun for the case "I calibrated free and then
  realised I measured wrong on press — let me re-run just
  press" — under per-knob, `free` is already persisted; under
  full-session it never was.

- [ ] **Q5 — Interactive vs one-shot invocation shape.** Should
  the helper also expose a one-shot non-interactive form
  (e.g.
  `python3 tools/calibrate.py free --diameter 3.30 --yes
  --profile bambu_p1s__pla_overture`) for users who already
  know their measured value, or is interactive-only
  sufficient? One-shot unlocks CI smoke-testing of the write
  path and is ~5 LOC of arg-parsing per knob; interactive-only
  ships faster. Designer recommendation: support one-shot
  per-knob (matches SUPERSEDED Q3 resolution), but require
  `--profile <name>` to be explicit on any non-interactive
  invocation that creates a *new* profile entry (so a CI run
  cannot silently mis-resolve the active profile and create a
  typo'd entry).

- [ ] **Q6 — Press-fit gauge geometry (the knob-to-gauge
  alignment).** The user reframe named "M3 nut for press fit"
  as the default. The repo-grep above (Known Domain
  Constraints §"Knob-to-consumer mapping") shows that
  `MetricHexNut.to_cutter()` currently reads
  `profile.free.radial`, NOT `press.radial`. Three resolutions:
  (a) **M3 nut gauge, write to `press.radial`, accept that the
  nut cutter does not yet read this knob** — the gauge calibrates
  the value that the nut *should* read (matching the user's
  mental model), and a separate sub-brief later changes
  `MetricHexNut.to_cutter` (or introduces a press-pocket variant)
  to actually read it; until then, the calibrated value applies
  only to bearing outer-pockets in practice. (b) **M3 nut gauge,
  write to `free.radial`, accept that this is a second sample
  for the knob the M3-screw gauge already calibrated** — schema-
  honest but wasteful; one of the two default gauges becomes a
  cross-check rather than a distinct calibration. (c)
  **Bearing outer-pocket gauge** (single-row variant of the
  existing `ToleranceGauge` Row 2) **as the press default** —
  the M3 nut is dropped from v1's default set entirely; press
  calibration anchors to the only current `press.radial`
  consumer. The user's nut framing is honoured as a v2 follow-up
  once `MetricHexNut.to_cutter` is updated. Designer
  recommendation: **(a) with the targeted
  `MetricHexNut.to_cutter` change folded into Q7's scoping
  decision.** Rationale: the user's mental-model ("M3 nut for
  press fit") is the right user-facing framing; the schema
  drift is a small targeted refactor (~5 LOC), not a v2-scale
  conversation; calibrating against the bearing-pocket gauge
  ships an honest-but-niche default that does not match what
  most contributors would expect from "press fit." TL pushes
  back on this if the refactor is structurally larger than
  estimated.

- [ ] **Q7 — Are the net-new gauge classes (M3 screw clearance
  gauge, and the press-fit gauge per Q6 resolution)
  implementation deliverables in THIS brief, or do they spin
  off as separate sub-briefs?** Options: (a) all-in-one — the
  helper, the gauge classes, the README update, and any
  targeted `MetricHexNut.to_cutter` change land in one PR;
  (b) gauge classes first (separate sub-briefs per gauge),
  then the helper in a follow-up PR consuming them;
  (c) helper-skeleton first against placeholder gauge stubs,
  then gauge classes filled in. Designer recommendation:
  (a) for the M3-screw gauge (small enough to land alongside
  the helper) + (b) for the Q6-resolved press gauge IF Q6
  resolves to a path that requires the
  `MetricHexNut.to_cutter` refactor (the refactor is a
  domain-integrity-touching change that earns its own
  sub-brief). TL has the architecture call here; the
  fewer-PRs path is cleaner if the refactor is genuinely
  small.

- [ ] **Q8 — Output verbosity / next-steps in the success
  block.** On successful per-knob write, what does the helper
  print? Minimum: the path written, the calibrated leaf
  (`<profile>.<grade>.<field>`), the before-value, the
  after-value. Recommended addition: a one-line "next" pointer
  ("calibrate `press` next: `tools/calibrate.py press`" or
  "you're done; verify by printing a real part using the new
  tolerance"). Designer recommendation: minimum + the next-knob
  pointer in sequence mode, minimum-only in per-knob mode.
  (Mirrors SUPERSEDED Q5 resolution.)

- [ ] **Q9 — Visual contract deliverable scope.** This brief
  produces a CLI helper, not a CAD model class — by the
  *Visual Contract Deliverable* rule in `vibe/INSTRUCTIONS.md`,
  CLI / tooling tasks are explicitly carve-out exempt. But the
  brief's Q7 may pull in net-new gauge model classes (the
  M3-screw clearance gauge, possibly an M3-nut or bearing
  press gauge) that ARE CAD models with visible geometry.
  Designer recommendation: the *helper itself* takes the
  carve-out exemption; *each new gauge class* introduced as a
  side-effect of Q7 generates its own iso_ne SVG per the rule.
  TL confirms the per-gauge SVG-generation falls inside this
  brief's design phase or splits into Q7's sub-briefs.

---

## Human Confirmation Checkpoint
- [x] Requirements reviewed and confirmed by human _(2026-05-24, PM-relayed; Q1–Q7 deferred to TL+Designer Step-3 co-design)_
<!-- Do not proceed to design until this box is checked. -->
