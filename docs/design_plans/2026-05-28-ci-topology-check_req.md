# Requirements: CI Topology Check (wire `tools/check_topology.py` into `ci.yml`)
<!-- Filename: 2026-05-28-ci-topology-check_req.md  (tracked under .agents/plans/) -->

## Meta
- **Initiator role**: @designer (per @admin direction in 2026-05-29 session)
- **Date**: 2026-05-28 (slug); authored 2026-05-29
- **Domain integrity gate**: **NO** — workflow scaffolding only. No
  geometry, tolerance, fit-grade, or model code is touched. The change
  adds one (or one+overrides) CI step that invokes an existing tool
  against existing model classes.
- **Recommended path**: **Path C — direct PR, no separate `_design.md`.**
  Justification: single workflow step (plus a small allowlist data
  structure), no new code module, failure mode is "CI step false-positives
  or false-negatives" which the local sweep already de-risks (see
  §Pre-Flight Sweep below). The design dimension that *would* warrant a
  full `_design.md` — "what to do about the three legitimate multi-body
  classes" — is resolved up-front in this req (FR3 + the allowlist data).
  Escalates to a full `_design.md` only if the human gate rejects the
  proposed allowlist shape.

---

## Problem Statement

The repo ships [`tools/check_topology.py`](../../tools/check_topology.py)
— a CadQuery validator that loads a model class (or STEP file) and
fails (exit 1) if the resulting geometry contains more disconnected
solid bodies than expected. The tool is referenced as a **mandatory
guard** in the project's *Topological Validation (Floating Bodies)*
known-pitfall in [`vibe/INSTRUCTIONS.md`](../../vibe/INSTRUCTIONS.md):

> The Developer must ensure that the final produced geometry consists
> of a single contiguous solid. Add a programmatic check at the end of
> parts that should produce a single object: `assert len(result.solids().vals()) == 1, …`.

…and is cited in the design-brief template's validation-commands
section. But **no workflow currently invokes it.** A model that
regresses into a floating-artifact state — a chord-vs-arc ring, a
failed boolean union, an incomplete cut leaving a wafer — ships
through CI green so long as `python build.py` itself doesn't raise.
The `assert` in individual `_build()` methods catches some cases at
class-instantiation time (and `build.py` does run every registered
class), but assert coverage is non-uniform across the codebase, and
new contributors writing a class without the assert get no CI signal.

This task is the final remaining bullet of the *GitHub Actions CI —
release-readiness pass* item in [`todo.md`](../../todo.md) line 15.
Closing it is a release blocker for OSS publication.

## User Story / Motivation

As an OSS contributor opening a PR that adds a new model class or
modifies an existing one, I need CI to fail loudly if my geometry
contains floating solids (artifact wafers, un-merged unions,
disconnected bodies) so that I do not have to remember to run
`tools/check_topology.py` locally for every change, and so that a
reviewer who skips local verification still gets honest signal
before merge.

## Pre-Flight Sweep (informational — established by Designer)

Before drafting FRs the Designer ran `tools/check_topology.py` against
**every** model registered in `build.toml` (15 entries).  Results:

| Status | Count | Notes |
|---|---|---|
| `[PASS]` (n = 1 solid, `--ignore 0`) | 12 | Default expectation holds. |
| `[FAIL]` (legitimately multi-body) | 2 | `ServoMountAssembly` (n = 2), `SlipperGearSteep` (n = 6). |
| Tool error (no exit-0/1 verdict) | 1 | `PrintInPlaceHinge` — `.solid` returns a `cq.Compound`; tool crashes with `AttributeError: 'Compound' object has no attribute 'vals'` at `tools/check_topology.py:86`. |

The two legitimate failures are pre-arranged print plates / assemblies
exposed via the project's *Multi-Part Assemblies* mechanism documented
in [`CLAUDE.md`](../../CLAUDE.md) / [`vibe/INSTRUCTIONS.md`](../../vibe/INSTRUCTIONS.md).
Both compose multiple `.solid` instances into one combined
`cq.Workplane` for slicer convenience.  Their per-part body counts are
intentional and stable.

`PrintInPlaceHinge` is a third shape: a print-in-place hinge whose
`solid` property does `cq.Assembly().add(leaf_a).add(leaf_b).toCompound()`
and returns a `cq.Compound` directly (not a `cq.Workplane`).  The tool's
`workplane.solids().vals()` chain assumes a `Workplane`.  This is a
**tool gap** the CI wiring will surface; see Q1 below.

The full sweep script + raw output is in
[`tmp/topology_sweep.sh`](../../tmp/topology_sweep.sh) (git-ignored
working artefact); the script is one-line idempotent (`bash
tmp/topology_sweep.sh`) for future re-runs.

## Functional Requirements

1. **FR1 — New `Topology check` step in `ci.yml`.**  Add one step to the
   existing `check` job in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
   that invokes `tools/check_topology.py` against every model class
   registered in `build.toml`.  The step MUST live **after** the
   `Build smoke (python build.py)` step (which is the existing
   end-of-pipeline CadQuery-runtime gate), so the topology check
   benefits from the same `pip install -r requirements-ci.txt` and
   Python 3.11 setup that `build.py` already needs.
2. **FR2 — Target set = `build.toml` entries.**  The CI step MUST
   iterate the `[[build]]` entries in `build.toml` as the canonical
   target list.  Rationale: `build.toml` is the project's existing
   single source of truth for "models that ship"; using it
   automatically picks up new entries without a second registration
   file, and matches the failure mode the user actually cares about
   (a model that ends up in `output/` should have honest topology).
   Models *not* in `build.toml` (cutters, internal helpers,
   experimental scratch under `experiments/` that isn't registered)
   are out of scope for this task.
3. **FR3 — Per-target expected-body-count allowlist.**  The CI step
   MUST support a per-target override of the default `--ignore 0`
   posture, keyed by the **fully-qualified model class path** (the
   `model` field of each `[[build]]` entry).  Target set today
   (driven by the Pre-Flight Sweep above):

   | Class | `--ignore` value | Why |
   |---|---|---|
   | `vibe_cading.lego_adapters.servos.sg90.servo_mount.ServoMountAssembly` | `1` (expect 2 bodies) | Pre-arranged print plate composing `ServoMountBase` + `ServoMountClamp` via `cq.Workplane().add().add()`. |
   | `experiments.slipper_gear.directional.steep.SlipperGearSteep` | `5` (expect 6 bodies) | R&D slipper-gear assembly composing plate + ring + 4 spring parts via `cq.Assembly().toCompound()`. |
   | `vibe_cading.mechanical.hinge.PrintInPlaceHinge` | *(see Q1 — tool gap)* | `.solid` returns `cq.Compound`, not `cq.Workplane`; tool crashes before `--ignore` can apply. |
   | *(all 12 others)* | `0` (default — single contiguous solid) | Standard contract. |

   Every entry on the allowlist MUST carry an inline comment
   explaining *why* the override exists (so a future contributor
   removing the assembly doesn't silently leave a stale override).
4. **FR4 — Allowlist lives in the workflow, not a separate file.**
   The override map MUST be defined inline in `ci.yml` (e.g. as a
   small bash associative array or a YAML matrix-include block,
   whichever the implementer judges most readable).  Rationale:
   the override set is small (today, 2 entries that resolve cleanly
   plus 1 deferred), tightly coupled to the workflow's own
   per-target invocation logic, and rarely changes.  A separate
   `topology_overrides.toml` file would be over-engineering for the
   current scale; promote to a separate file only if the allowlist
   grows past ~5 entries.
5. **FR5 — Step fails closed on any unhandled exit code.**  If the
   tool exits with any code other than `0`, the step MUST fail the
   workflow.  A tool crash (exit ≠ 0, no `[PASS]` / `[FAIL]` line)
   MUST be surfaced as a CI failure, not swallowed — the tool gap
   surfaced by `PrintInPlaceHinge` (see Q1) is itself a signal that
   needs maintainer attention, not silent skipping.
6. **FR6 — Step output is human-readable on failure.**  On a topology
   failure for any target, the step MUST print the target's
   fully-qualified class path immediately before the tool's own
   `[FAIL]` block, so a reviewer scrolling CI logs can identify
   which model regressed without correlating offsets.  The tool's
   built-in `Breakdown by Volume` listing is sufficient detail.
7. **FR7 — No `--export` in CI.**  The CI invocation MUST NOT pass
   `--export`.  The flag writes residual STEP files to `tmp/` for
   local triage; in CI those files are discarded with the runner
   and uploading them as artefacts is out of scope for v1 (revisit
   if a real CI failure ever needs post-hoc inspection).
8. **FR8 — Local-developer parity: document the invocation.**  The
   developer MUST also append a one-paragraph note to either
   `README.md` §CI Gates or `CONTRIBUTING.md` §6 (whichever
   currently lists the existing CI gates — the developer chooses
   based on which file better surfaces it to contributors) that
   names the new Topology check step and points to
   `tools/check_topology.py` for local reproduction.  Rationale: a
   contributor whose PR fails the new gate needs a one-liner on how
   to reproduce it locally; without the docs touch, the failure
   message in CI is the only discoverable path.

## Non-Functional Constraints

- **Runtime budget.**  The new step MUST add no more than ~60 s to
  CI wall-clock on a clean GitHub-hosted runner.  The 15 model
  classes already get instantiated once by `python build.py`; the
  topology step instantiates each a second time.  Empirically the
  full local sweep ran in well under 2 minutes; CI parity is
  expected.  If the implementer measures >120 s, escalate as a
  blocker (likely root cause: re-running `python build.py`'s
  expensive geometry per target — mitigation would be a one-shot
  Python harness that imports once and validates many, deferred
  until needed).
- **CadQuery already installed.**  The new step adds no new pip
  dependencies — `requirements-ci.txt` already provides CadQuery
  for the existing `python build.py` smoke step.
- **No `build.toml` schema change.**  This task does NOT add a
  `topology_expected_bodies` field to the per-entry TOML.  Per FR4
  the allowlist lives in `ci.yml` only.  Promoting to a TOML-level
  declaration is a deferred refinement gated on real demand (more
  than a handful of overrides).
- **Existing CI steps untouched.**  `flake8`, `py_compile`,
  `check_no_main_blocks.py`, `ocp_vscode` greps, pytest, and
  `python build.py` MUST run unchanged.  The new step is purely
  additive.
- **Workflow placement: same `check` job.**  The new step joins the
  existing `check` job rather than spawning a separate job.  A
  separate job would force a redundant `actions/checkout` +
  `actions/setup-python` + `pip install` cycle (~30 s pre-amble for
  a ~60 s payload), tripling cold-start cost.  Same-job parallelism
  is not available within a single job, but the topology step
  depends on a working CadQuery install which the existing
  `python build.py` step already validates — running them
  serially in the same job is the right shape.

## Known Domain Constraints

- **Multi-part assemblies are a documented project pattern.**  See
  [`CLAUDE.md`](../../CLAUDE.md) §Multi-Part Assemblies: distinct
  physical parts get their own classes with their own `.solid`;
  a wrapper class composes them.  `ServoMountAssembly` and
  `SlipperGearSteep` are intentional applications of that pattern,
  not regressions to refactor away.
- **`PrintInPlaceHinge` uses `cq.Compound`.**  The
  `cq.Assembly().toCompound()` return value violates an
  unstated assumption baked into `tools/check_topology.py` (that
  every target either is a `cq.Workplane` or has a
  `.solid` that is a `cq.Workplane`).  This is a tool gap that
  the wiring exposes; resolution path is Q1.
- **`assert len(part.solids().vals()) == 1` in `_build()` methods
  is the per-class guard.**  Several library classes already carry
  this assertion (e.g. `ServoMountBase._build`, `ServoMountClamp._build`).
  The CI step is the **uniform** safety net behind those scattered
  per-class asserts; it does not replace them.

## Out of Scope

*Explicit anti-scope — DO NOT include in this PR:*

- **No refactor of `PrintInPlaceHinge`.**  Per Q1 below, the path
  options range from "fix the tool to accept `Compound`" to
  "refactor the class to expose `.solid` as a `Workplane`".  Whichever
  path the human gate picks, it lands in this PR for the specific
  tool-or-class fix needed to unblock the CI step — but **no broader
  cleanup** of other Assembly-returning classes (there are none today
  that ship via `build.toml` other than this one, but treat the rule
  as forward-looking).
- **No `topology_expected_bodies` TOML field.**  Deferred until the
  allowlist grows past ~5 overrides.
- **No coverage of unregistered classes.**  Cutters
  (`TechnicAxleHole`, `TechnicPinHole`, `CounterboreHole`, etc.) and
  internal helpers are out of scope.  They are designed to be cutter
  geometry, not standalone shipped parts.
- **No upload of `--export`ed STEP residuals as CI artefacts.**  v2 if
  ever needed.
- **No `engine-api.yml` change.**  Different workflow, different
  purpose.
- **No CI badge addition to `README.md`.**  Tracked as a separate
  bullet in [`todo.md`](../../todo.md) line 15 ("add a CI status
  badge to `README.md` once first post-publication green-build
  lands") — independent of this PR.
- **No `tmp/topology_sweep.sh` promotion to `tools/`.**  The sweep
  script is a Designer working artefact; the CI step is the
  production form.  Deleting `tmp/topology_sweep.sh` is at the
  developer's discretion post-merge.

## Open Questions

*For human-Admin resolution before the developer starts.  Designer
recommendations are noted inline.*

- [ ] **Q1 — `PrintInPlaceHinge` tool gap: fix the tool, fix the
      class, or exclude from the CI sweep?**  Today the tool crashes
      with `AttributeError: 'Compound' object has no attribute 'vals'`
      because `cq.Compound.solids()` returns a list, not a
      `cq.Workplane` selector chain.  Three options:

      **(a) Fix the tool.**  Add a `Compound`-aware branch in
      `tools/check_topology.py:load_target` that wraps a `Compound`
      in `cq.Workplane(obj=compound)` (or extracts `compound.Solids()`
      directly).  Cost: ~5–10 LOC in the tool plus a small unit test
      under `tests/tools/`.  Benefit: every future
      `cq.Assembly().toCompound()`-returning class works
      automatically; the tool stops carrying a hidden assumption.
      **(b) Fix the class.**  Refactor `PrintInPlaceHinge.solid` to
      return `cq.Workplane(obj=comp.toCompound())` instead of the bare
      `Compound`, restoring the implicit project convention that
      `.solid` is always a `Workplane`.  Cost: 1-line code change in
      `vibe_cading/mechanical/hinge.py` plus verifying it doesn't
      regress the engine-api wire contract or anyone consuming
      `hinge.solid`.  Benefit: keeps the tool simple; honors the
      convention every other model class already follows.
      **(c) Exclude from the CI sweep with an explanatory comment.**
      Skip `PrintInPlaceHinge` in the FR4 allowlist with a TODO
      pointing at this Q1.  Cost: zero immediate work, but leaves a
      known-unwatched model in `build.toml` indefinitely.
      *Designer recommends:* **(b) — fix the class.**  Rationale:
      every other shipped model uses `.solid → cq.Workplane`; this
      class is the lone exception, and the deviation was almost
      certainly unintentional.  A one-line wrap restores the
      convention, keeps the tool small and honest about its
      contract, and lets the FR3 allowlist entry resolve cleanly to
      `--ignore 2` (a hinge expects three solids: leaf_a + leaf_b +
      the knuckle bridge — to be confirmed empirically post-wrap).
      Option (a) is acceptable as a fallback if the human gate
      prefers tool generality, but the engine-api wire-contract
      verification adds a small extra step relative to (b).
- [ ] **Q2 — Should the workflow step iterate `build.toml` at
      runtime, or hardcode the model list in the workflow YAML?**
      Two implementation shapes:

      **(a) Runtime iteration.**  The step shells out to a small
      Python one-liner (e.g. `python -c "import tomllib; …"`) to
      enumerate `[[build]]` entries, then loops a bash `for` over
      the resulting list, applying the FR3 allowlist as it goes.
      Cost: ~10 lines of bash + Python in the workflow.  Benefit:
      new `build.toml` entries are picked up automatically; the
      workflow stays in sync with no manual edit.
      **(b) Hardcoded list in the workflow.**  The workflow YAML
      lists every target by FQ class path, with per-target
      `--ignore` inline.  Cost: every new `build.toml` entry
      requires a parallel `ci.yml` edit, enforced only by the new
      gate's absence-of-coverage being silent.
      *Designer recommends:* **(a) — runtime iteration.**  Keeps
      `build.toml` as the single source of truth (matching the
      rationale in FR2) and prevents a class of bug where a
      contributor adds to `build.toml` but forgets to update
      `ci.yml`.  The cost delta is small (~10 lines).
- [ ] **Q3 — How granular should the per-target failure log be?**
      FR6 mandates printing the FQ class path before each `[FAIL]`
      block.  Stretch options if the developer judges them worth the
      extra ~10 lines:

      **(a) FR6 only** — minimal: class path + tool's own output.
      **(b) FR6 + a final summary line** — at end of step, print
      `X / Y targets passed, Z failed`.
      **(c) FR6 + per-target green log** — print `✓ {class_path}`
      on every pass too (verbose but symmetric).
      *Designer recommends:* **(b) — FR6 + summary line.**  Minor
      developer-experience win on green runs (a glanceable "15/15
      passed"); avoids the per-pass noise of (c).  Implementer is
      free to skip if it adds >5 LOC.
- [ ] **Q4 — Does the step name need a `(may be slow)` qualifier or
      similar?**  The new step is the slowest in the `check` job
      (every other step is sub-30 s; this one is the second
      CadQuery-runtime gate).  Worth flagging in the step name
      (`name: Topology check (CadQuery — slow)`) so contributors
      watching CI logs know which step is the wall-clock dominator?
      *Designer recommends:* **no qualifier.**  The existing
      `Build smoke (python build.py)` step already carries the
      "slow" reputation; a parallel qualifier on the topology step
      is noise.  Keep the name terse: `name: Topology check`.

## Pre-Implementation Verification (mandatory for developer)

Before committing the workflow edit, the developer MUST:

1. **Re-run the local sweep** (`bash tmp/topology_sweep.sh` or
   equivalent ad-hoc loop) against every `build.toml` entry with the
   FR3 allowlist applied locally to confirm every target either
   `[PASS]`es or matches its declared `--ignore` value.  Capture the
   output in the PR description.
2. **If Q1 resolves to (b) — fix the class** — verify the
   `engine_api.json` regen produces no unexpected drift beyond the
   `.solid`-return-type docstring delta (if any).  The engine-api
   workflow's `--check` gate will catch a regression here; pre-empt
   it locally.
3. **Run `python build.py` end-to-end locally** to confirm the
   class-fix or tool-fix from Q1 doesn't regress the build smoke
   step.

If any target fails `[PASS]` under its declared `--ignore` value
post-fix, escalate as a blocker — do NOT paper over with a larger
`--ignore`.  A failure here means a real topology regression in
shipped geometry, which is a different (and higher-priority) class of
problem than the CI wiring this PR addresses.

---

## Touchpoint Inventory (informational — confirmed by repo grep + sweep)

| # | File | Nature of change |
|---|---|---|
| 1 | `.github/workflows/ci.yml` | Add `Topology check` step at end of `check` job; inline allowlist per FR3. |
| 2 | `vibe_cading/mechanical/hinge.py` | *(conditional on Q1 = b)* — one-line `.solid` wrap to return `cq.Workplane`. |
| 3 | `tools/check_topology.py` | *(conditional on Q1 = a)* — `Compound`-aware branch in `load_target`. |
| 4 | `tests/tools/test_check_topology.py` | *(conditional on Q1 = a — new file)* — unit test for the `Compound` branch. |
| 5 | `engine_api.json` | *(conditional on Q1 = b)* — regen if hinge `.solid` docstring changes. |
| 6 | `README.md` *or* `CONTRIBUTING.md` | FR8 — one-paragraph CI Gates note. |
| 7 | `todo.md` | Strike the "wire `tools/check_topology.py` into `ci.yml`" sub-bullet from line 15. |

---

## Human Confirmation Checkpoint
- [x] Requirements reviewed and confirmed by human — **approved 2026-05-29**.
  - **Q1 → (b)** fix the class: `PrintInPlaceHinge.solid` wraps its
    `cq.Compound` return as `cq.Workplane(obj=…)`.
  - **Q2 → (a)** runtime iteration of `build.toml` in the workflow step.
  - **Q3 → (b)** FR6 + final summary line (`X / Y targets passed, Z failed`).
  - **Q4 → no qualifier** on the step name (keep `name: Topology check`).
  - **Path C confirmed** — direct PR, no separate `_design.md`.
<!-- Approval relayed by PM 2026-05-29; developer cleared to execute Path C. -->

---

## Implementation Outcome

**Date:** 2026-05-29 · **Branch:** `ci-topology-check` · **PR:** _(URL added once `gh pr create` returns)_

### Deliverables
- **`.github/workflows/ci.yml`** — new `Topology check` step appended to the
  `check` job after `Build smoke (python build.py)`.  Iterates `build.toml`
  at runtime via inline `python3 -c "import tomllib; …"` one-liner (Q2=a);
  applies FR3 allowlist via a bash associative array (FR4); prints
  `::: <fq.class.path> (--ignore N)` before each invocation (FR6); emits
  final `X / Y targets passed, Z failed` summary line (Q3=b); fails closed
  on any non-zero exit (FR5); no `--export` (FR7); step name is bare
  `Topology check` (Q4 — no qualifier).
- **`vibe_cading/mechanical/hinge.py`** — `PrintInPlaceHinge.solid`
  refactored per Q1=b: wraps `cq.Assembly().toCompound()` in
  `cq.Workplane(obj=…)` to honor the project-wide `.solid → cq.Workplane`
  convention.  Expanded docstring documents the wrap and the downstream
  tooling that depended on it.
- **`CONTRIBUTING.md` §8** — appended item 8 to the CI Gates list (FR8
  destination chosen: CONTRIBUTING; README has no §CI Gates section, only
  CONTRIBUTING does).  Names the new step, points contributors at
  `tools/check_topology.py` for local reproduction, calls out the three
  allowlisted classes.
- **`todo.md`** — struck the "wire `tools/check_topology.py` into `ci.yml`"
  sub-bullet from the *GitHub Actions CI — release-readiness pass* item.
- **`tmp/topology_sweep_with_allowlist.sh`** — local-reproduction helper
  (gitignored under `tmp/`).  Mirror of the CI step's allowlist + loop
  shape; one-line idempotent runner (`bash tmp/topology_sweep_with_allowlist.sh`).
  Supersedes the older `tmp/topology_sweep.sh` (deleted — no allowlist).

### Deviations from FR1–FR8

- **FR3 allowlist value for `PrintInPlaceHinge` resolved empirically to
  `--ignore 1` (expect 2 bodies), NOT `--ignore 2` as the Designer guessed
  in Q1's recommendation note.**  The Designer's hypothesis was
  "leaf_a + leaf_b + the knuckle bridge → 3 solids".  Under the actual
  `build.toml` params (`knuckle_count=3` left at default since `build.toml`
  doesn't pass it), the bridge knuckle composes into `leaf_a` via the
  existing `knuckles_solid` union — so the final compound is 2 bodies
  (leaf_a-with-bridge + leaf_b), not 3.  Verified by running the tool
  post-wrap with `--ignore 0` (fails reporting 2 bodies), then with
  `--ignore 1` (passes).  This is the empirical confirmation the Designer
  flagged ("to be confirmed empirically post-wrap") and is in scope — not
  a scope expansion.

No other deviations from FR1–FR8.

### Pre-Implementation Verification — captured outputs

1. **Local sweep against every `build.toml` entry with FR3 allowlist
   applied** — `bash tmp/topology_sweep_with_allowlist.sh` →
   `15 / 15 targets passed, 0 failed` (exit 0).  All three allowlisted
   classes confirm their expected body count: `ServoMountAssembly` → 2,
   `SlipperGearSteep` → 6, `PrintInPlaceHinge` → 2 (post-wrap).  The 12
   default-contract classes all `[PASS]` at `--ignore 0` (single
   contiguous solid).
2. **engine-api drift assessment** — `python3 tools/gen_engine_api.py
   --check` exits 0 (silent success).  The `.solid` docstring expansion
   does NOT affect `engine_api.json`: the extractor uses
   `ast.get_docstring(node)` against the class node, not the property
   docstring; `result_accessor` remains `".solid"`.  No regen commit
   needed.
3. **Build smoke regression** — `python3 build.py` builds all 15 STEPs
   successfully, including `mechanical/hinge_print_in_place.step`.  The
   one-line wrap is a pure type-conversion; `cq.exporters.export` accepts
   both `cq.Workplane` and `cq.Compound`, so build.py was already
   tolerant.
4. **Test regression** — `python3 -m pytest tests/ -v` → 289 passed,
   2 xfailed, 9 warnings (warnings are upstream `ezdxf` / `pyparsing`
   deprecations + the existing `PETG` profile fallback warning from
   `MotorMountPlate`'s `build.toml` entry).  No new failures.

### Blockers
None.
