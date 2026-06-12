# Requirements: `examples/` directory for OSS publication

<!-- Filename: 2026-05-15-examples-directory_req.md  (tracked in git under .agents/plans/) -->

## Meta
- **Initiator role**: @designer (continuing from PM-confirmed Discovery pass)
- **Date**: 2026-05-15
- **Domain integrity gate**: NO
- **FR13 re-pinned 2026-05-17** after `LegoTechnicBeam` class landed
  (see `.agents/plans/2026-05-15-lego-technic-beam_design.md` Phase D
  approval). FR2 bullet 1, FR13, and Q1 promotion note updated to
  consume the real first-party class; constants-composition workaround
  retired. Domain-integrity gate re-confirmed NO (consuming an existing
  class instead of constants does not change data-contract scope).

> Rationale for NO: this task introduces a new top-level `examples/`
> directory containing thin demonstration scripts that consume the existing
> public API of `vibe_cading/`. It does not alter any core data contract,
> class hierarchy, coordinate convention, tolerance profile schema, or
> `build.toml` shape. It carves out a new (small) scope exception in two
> existing rules — the no-`__main__`-blocks lint scope and the AGPLv3 header
> scope — but neither rule changes semantically; only the path globs they
> enumerate widen. The condition-1 fix (correcting the enforced-vs-voluntary
> AGPLv3 scope) and the condition-2/3 promotions (FR13 pinning the Lego
> beam to the first-party `LegoTechnicBeam` class; FR14 pinning snap-fit's two-file
> output) tighten v1 contract surface without crossing into
> domain-contract territory — they constrain example-script behaviour, not
> library API shape. Gate remains NO post-fix.

---

## Problem Statement

The `examples/` directory is listed as a release-blocker on the pre-OSS
publication checklist in [todo.md](../../todo.md) and is referenced
implicitly by [README.md](../../README.md) line 5 ("It also features
practical examples demonstrating how to use these primitives…"). Today the
directory does not exist. A new contributor cloning the repo can only learn
the library's public surface by reading model classes inside
`vibe_cading/` or running `tools/view.py` against names they have no way to
discover. There is no end-to-end, self-contained, agent-free entry point
that demonstrates how the library's primitives compose into a usable part.

This blocks v1 publication on two fronts: the README's getting-started
anchor has no concrete target to link to, and the first-impression bar for
a CadQuery / OSS-CAD reader landing on the GitHub page is unmet.

## User Story / Motivation

As a **new OSS contributor or evaluator** cloning `vibe-cading` for the
first time, I need **a small set of self-contained Python scripts under
`examples/` that I can run with `python3 examples/<name>.py` against a
vanilla CadQuery install**, so that **I can see the library's primitives
compose into real, exportable geometry within minutes of cloning, without
having to set up Claude Code, the dev container, or any agent host first**.

Secondary persona: a **returning contributor** scanning the repo for the
canonical usage pattern of a primitive (screw cutter, gear factory, snap
fit, Lego adapter) needs a copy-pasteable, minimal reference that is
guaranteed to run.

## Functional Requirements

<!-- Numbered, unambiguous, testable. Use "MUST" or "MUST NOT" language. -->

1. The repository **MUST** contain a new top-level `examples/` directory
   tracked in git, distinct from `vibe_cading/`, `parts/`, `experiments/`,
   and `tools/`.

2. The `examples/` directory **MUST** contain exactly four scripts in v1,
   each one demonstrating a different facet of the library's public API:
   - `examples/lego_technic_beam.py` — instantiate the first-party
     `LegoTechnicBeam` class from `vibe_cading/lego/technic_beam.py`
     with a concrete `length_in_studs` value, read its `.solid`, and
     export the result. Showcases the canonical Lego Technic beam
     primitive (stud-grid-aligned body with through pin holes,
     counterbores, and lead-in chamfers). See FR13 for the v1 contract.
   - `examples/screw_cutter.py` — instantiate a metric machine screw from
     `vibe_cading/mechanical/screws/metric.py`, build a small host block,
     and apply the screw's `.to_cutter()` to subtract a clearance pocket +
     head recess. Showcases the unified `CutterProtocol` contract.
   - `examples/gear_from_iso.py` — build a spur gear via
     `SpurGear.from_iso(...)` (the concrete-subclass factory in
     `vibe_cading/mechanical/gears/base.py` line 357; calling
     `Gear.from_iso` directly raises `TypeError` because `Gear` is
     abstract — see `base.py:367–370`). Export the result. Showcases
     the gear factory + ISO-parametric construction.
   - `examples/snap_fit_hook.py` — build a cantilever snap-fit hook
     from `vibe_cading/mechanical/joints/snap_fit.py` via
     `CantileverSnapFit(...).male(...)`, cut its `.to_cutter(...)`
     cavity into a host block, and export both the male hook and the
     mating host (two STEP files — see FR14). Showcases the
     male/`to_cutter` joint API contract (`CutterProtocol`).

3. Each example script **MUST** be runnable via the literal invocation
   `python3 examples/<name>.py` from the repository root, against a
   vanilla CadQuery install (no environment variables, no command-line
   arguments, no agent-host setup, no dev-container assumption).

4. Each example script **MUST** carry an `if __name__ == "__main__":`
   block as its execution entry point. This is the inverted contract
   relative to `vibe_cading/**` and `parts/**` (which forbid main blocks
   per `tools/check_no_main_blocks.py`); the no-main-blocks CI rule
   therefore **MUST NOT** widen its walked roots to include `examples/`.

5. Each example script **MUST** write its build outputs to
   `examples/build/<example_name>/` (creating the directory tree if
   absent). At minimum each script **MUST** produce one STEP file per
   distinct solid it builds; preview SVGs are encouraged but not
   mandatory in v1.

6. The `examples/build/` directory **MUST** be added to the repository's
   top-level `.gitignore` so example output never enters git history.

7. Each example script **MUST** print, on successful completion, the
   absolute path of every file it wrote (one path per line, prefixed by
   a short label such as `"STEP:"` or `"SVG:"`). This satisfies the
   "print where it wrote its STEP/SVG" requirement from the pre-OSS
   checklist and gives the reader a copy-pasteable path for viewer
   inspection.

8. Each example script **MUST** carry the AGPLv3 header at the top of
   the file, identical in wording to the header in any current
   `vibe_cading/**/*.py` file. The license-header CI check
   (`tools/check_license_headers.py`) **MUST** widen its glob set to
   include `examples/*.py` so this is enforced automatically.

9. Each example script **MUST** be self-contained: it imports only from
   the Python standard library, `cadquery`, and `vibe_cading.*`. It
   **MUST NOT** import from `parts.*`, `experiments.*`, `tools.*`, or
   any third-party package outside CadQuery's own dependencies.

10. Each example script **MUST** open with a module-level docstring
    (immediately after the AGPLv3 header) that states in 2–6 lines:
    (a) which primitive the example demonstrates, (b) the literal
    `python3 examples/<name>.py` invocation, and (c) what files the
    script writes and where. This is the script's own help text — no
    `argparse`, no `--help` flag required.

11. `README.md` **MUST** be updated, as part of this task's
    implementation phase, to add a "Getting started — examples" subsection
    (or equivalent anchor) under the existing Dev Setup / Models area
    that lists the four example scripts with one-line descriptions and
    the literal run command. The anchor target is the getting-started
    flow described in the pre-OSS checklist line 12 of
    [todo.md](../../todo.md).

12. The example scripts **MUST NOT** be registered in `build.toml`. They
    are demonstration entry points, not tracked deliverables of the
    build pipeline; their outputs land in `examples/build/` and are
    git-ignored, not in the canonical `build/` tree.

13. **Lego beam example v1 contract.** `examples/lego_technic_beam.py`
    **MUST** import the `LegoTechnicBeam` class from
    `vibe_cading.lego.technic_beam` and instantiate it with a concrete
    `length_in_studs` value (suggested: `5` — modest size that shows
    multiple holes clearly in a preview). The script **MUST** read the
    instance's `.solid` property, export it to a STEP file at
    `examples/build/lego_technic_beam/lego_technic_beam.step` per FR5
    + FR14, and (per FR7) print the absolute path of every file it
    writes. It **MUST NOT** re-implement the beam from constants +
    raw CadQuery primitives, and **MUST NOT** be silently renamed away
    from `lego_technic_beam.py`. Showcases the canonical first-party
    Lego Technic beam class as the v1 demonstration surface.
    (Originally promoted from Q1 as a constants-composition workaround
    when no beam class existed; re-pinned 2026-05-17 after
    `LegoTechnicBeam` landed — see Meta block.)

14. **Snap-fit example output convention.** `examples/snap_fit_hook.py`
    **MUST** emit two STEP files into `examples/build/snap_fit_hook/`:
    `hook.step` (the male `CantileverSnapFit` body via `.male(...)`)
    and `host.step` (the host block with the `.to_cutter(...)` cavity
    subtracted). The two-file convention is required so the reader can
    open both in a viewer and see which solid is the cutter target.
    Each of the other three examples (FR2 bullets 1–3) emits one STEP
    file named `<example_name>.step` inside its
    `examples/build/<example_name>/` subdirectory. (Promoted from
    former Q3; tightens FR5.)

## Non-Functional Constraints

- **Vanilla CadQuery install assumption.** The scripts run on whatever
  CadQuery version is pinned by the dev container today. They **MUST NOT**
  rely on `ocp_vscode`, `python-dotenv`, `pytest`, or any other dependency
  not already required to import `vibe_cading.*`.
- **Runtime budget.** Each script should complete in under ~10 seconds on
  the dev-container baseline (the heaviest realistic case is the gear
  example; if that exceeds the budget, the design phase may reduce its
  default tooth count). No script may launch a viewer process, open a
  network socket, or block on user input.
- **File-size budget.** Each example script is a teaching artifact:
  target ≤ 80 lines of executable Python (excluding the AGPLv3 header
  and module docstring), with no inline class definitions. If a script
  exceeds 120 lines, that is a signal the example is doing too much and
  should be split or simplified — the design phase will decide.
- **Style.** Examples are read by first-time contributors. Variable names
  are descriptive (no single-letter locals except loop indices); every
  non-obvious dimension carries an inline comment naming its source
  (`# 8 mm Lego stud pitch`, `# M3 nominal × 1.5 ` `head_height`).
  Examples **MUST** demonstrate the library's normal usage pattern — no
  workarounds, no "magic number" shortcuts that contradict the project's
  Code Quality & Open-Source Standards.
- **CI runtime impact.** Adding `examples/*.py` to the license-header
  CI glob and to a future smoke-run (if introduced) must add no more
  than a handful of seconds to CI wall time on the existing GitHub
  Actions runner.

## Known Domain Constraints

- **No-`__main__`-blocks rule is currently scoped to `vibe_cading/**` and
  `parts/**`** (per [CLAUDE.md](../../CLAUDE.md) "OCP Viewer — Dedicated
  Entry Point" and the literal roots list in
  [tools/check_no_main_blocks.py](../../tools/check_no_main_blocks.py)
  lines 76–77). The script's docstring already records that
  `experiments/` is intentionally exempt; `examples/` joins the exempt
  set on the same rationale (intentional execution entry points,
  outside the model-class surface).
- **AGPLv3 header rule is enforced by CI on `vibe_cading/**/*.py` and
  `tools/**/*.py`** (per
  [tools/check_license_headers.py](../../tools/check_license_headers.py)
  line 24); `parts/` is intentionally *not* walked by the gate (see the
  same file lines 8–11) and carries the header by convention only.
  [vibe/INSTRUCTIONS.md](../../vibe/INSTRUCTIONS.md) → Licensing & Open
  Source lists `parts/` alongside `vibe_cading/` and `tools/` as a
  voluntary scope; the *enforced* CI scope is the load-bearing surface
  for FR8. `examples/` is a new scope addition to that enforced set.
- **Stud-grid alignment** (8 mm pitch) — the Lego Technic beam example
  must obey this. Constants live in `vibe_cading/lego/constants.py`.
- **Tolerance profiles** — the screw-cutter example demonstrates the
  `profile=...` pattern via `vibe_cading.print_settings.get_profile(...)`.
  It **MUST NOT** hardcode a numeric clearance.
- **Zero-datum origin convention** — examples that build composite
  assemblies (the snap-fit-into-host case) must respect the project's
  zero-datum rule: the host block's mating face sits at Z=0, the snap
  hook extrudes into +Z, the cutter projects into -Z.
- **Cutter overcut discipline** — the snap-fit example must demonstrate,
  not contradict, the "Infinite Cutter Overcuts" rule from
  [CLAUDE.md](../../CLAUDE.md). The example is a teaching surface for
  this rule, not a workaround for it.

## Out of Scope

<!-- Explicitly state what this task does NOT cover to prevent scope creep. -->

- **Tolerance-sweep example.** A fifth example demonstrating
  `vibe_cading.print_settings` profile sweep / gauge generation was
  considered during Discovery and explicitly deferred. The four scripts
  above are the v1 release set.
- **Assembly-module example.** The `assemble()` module-level pattern
  (e.g. `vibe_cading.lego_adapters.servos.sg90.servo_mount`) is documented
  in `CLAUDE.md` and surfaced by `tools/view.py --assembly`; reproducing
  it under `examples/` is deferred until a real second consumer needs it.
- **Pytest coverage of examples.** Adding `tests/test_examples.py` to CI
  to actually execute each example as part of the pytest job is out of
  scope for this requirements pass. If smoke-running examples in CI is
  desired, it is a follow-up task (the existing `python build.py` job
  covers the underlying primitives' regression-prevention).
- **`tools/view.py` integration changes.** The examples deliberately use
  raw CadQuery export (`cq.exporters.export(...)`) rather than routing
  through `tools/view.py`, because their value proposition is "runs with
  vanilla CadQuery, no project tooling required." Cross-promoting
  `tools/view.py` belongs in the README, not in the example bodies.
- **Non-OSS / Claude-Code-specific demonstrations.** The `vibe/agents/`
  workflow, slash commands, and design-brief flow are documented in
  `docs/agentic-workflow.md` and surfaced by the README. They are not
  reproduced as `examples/`.
- **README authoring beyond the getting-started anchor.** Functional
  Requirement 11 inserts a single subsection that lists and runs the
  examples. A wider README release-readiness audit is its own backlog
  item on the pre-OSS checklist and is out of scope here.

## Open Questions

<!-- Unresolved questions the TL-requester design dialog must answer before sign-off. -->

- [x] **Q1 — Lego beam primitive selection.** *FULLY RESOLVED —
  `LegoTechnicBeam` landed 2026-05-17
  (see `.agents/plans/2026-05-15-lego-technic-beam_design.md` Phase D
  approval); FR13 now consumes the real first-party class from
  `vibe_cading/lego/technic_beam.py`.* (Previously promoted to FR13
  on 2026-05-15 as a constants-composition workaround because no beam
  class existed; re-pinned to the real class on 2026-05-17.)

- [ ] **Q2 — Gear factory entry point.** Does the current
  `vibe_cading/mechanical/gears/` surface expose a `Gear.from_iso(...)`
  classmethod, or is the canonical factory at a different name (e.g.
  `SpurGear(module=..., teeth=...)` or a `from_iso_module` helper)? The
  Discovery shortlist named the script `examples/gear_from_iso.py`; the
  design phase confirms the exact import path and class/method name
  against the current code, and updates the example body accordingly.

- [x] **Q3 — Build-output filename convention.** *Promoted to FR14.*
  Snap-fit emits two files (`hook.step` + `host.step`); the other
  three examples emit one `<example_name>.step` each.

- [ ] **Q4 — SVG preview generation in v1.** Functional Requirement 5
  marks SVGs as "encouraged but not mandatory." The design phase
  decides whether to ship SVGs with v1 (which means the examples must
  invoke a 2D projection helper, adding a few lines per script and
  pulling more of CadQuery's projection API into the teaching surface)
  or defer SVGs entirely to a follow-up (keeps each script tight and
  on-message: "here's the library, here's a STEP file").

- [ ] **Q5 — Cross-platform path printing.** Functional Requirement 7
  mandates printing absolute paths. On Windows the contributor will see
  back-slashed paths; this is fine for `pathlib.Path` formatting but
  worth a one-line decision: print via `str(path.resolve())` (native
  separators) or via `path.resolve().as_posix()` (forward slashes
  everywhere). Design-phase call; consistency across all four scripts
  is the only hard constraint.

*(Former Q6 — license-header CI glob patch shape — moved to "Notes
for the Developer" below; it is an implementation-phase decision, not
a design-phase gate.)*

---

## Notes for the Developer

- **License-header CI glob widening (former Q6).** FR8 requires
  `tools/check_license_headers.py` to enforce the AGPLv3 header on
  `examples/*.py`. The patch shape (adding a single new glob entry to
  the tuple at line 24 vs. lifting the tuple into a named module-level
  constant) is left to the developer's judgement; either is
  acceptable. If the developer chooses the constant refactor, the
  module docstring at lines 1–15 should be updated in the same patch
  so the documented scope stays in sync with the enforced scope.

---

## Human Confirmation Checkpoint
- [x] Requirements reviewed and confirmed by human (2026-05-17, PM-relayed from user "Approve" after FR13 re-pin to landed `LegoTechnicBeam` class)
<!-- Do not proceed to design until this box is checked. -->

---

## Independent Designer Review (fresh context, 2026-05-15)

- **Verdict:** `APPROVE-WITH-CONDITIONS`

- **Strengths**
  - Coverage of the seed bullet is complete and traceable: greenfield
    (FR1), vanilla-CadQuery runnability (FR3 + NFC "Vanilla CadQuery
    install assumption"), output-path printing (FR7), README
    cross-reference (FR11), and all four candidates from the seed
    (FR2).
  - The inverted main-block contract (FR4) is correctly identified as
    a *scope decision*, not a rule rewrite — the artifact pins the CI
    tool's path globs as the load-bearing surface, matching the
    project's "Rule Placement" discipline.
  - Out-of-Scope items are each anchored to a real follow-up
    (tolerance sweep, assembly module, pytest smoke, view.py
    integration); none read as work-avoidance.

- **Conditions / required edits** (single-pass)
  1. **Fix the AGPLv3-scope claim in "Known Domain Constraints".** The
     artifact states the header rule is scoped to `vibe_cading/`,
     `parts/`, `tools/`. The CI gate
     (`tools/check_license_headers.py` lines 24, 8–11) walks
     `vibe_cading/**/*.py` and `tools/**/*.py` only — `parts/` is
     explicitly **not** walked. Correct the bullet to the actual
     enforced scope (`vibe_cading/` + `tools/`); `parts/` is unenforced
     by convention. FR8 itself is unaffected.
  2. **Lift Q1 (Lego beam primitive) out of Open Questions and into
     Functional Requirements as a v1-contract decision, OR rename FR2
     bullet 1 to a name that matches an extant primitive.** No
     `LegoTechnicBeam` class exists today — the README Models table
     lists only `TechnicAxle`, `TechnicAxleHole`,
     `TechnicAxleToBearingSleeve`. Whether the example builds a beam
     from `lego/constants.py` primitives or swaps to a different
     existing class **materially changes what the v1 example
     demonstrates** (constants-module surface vs. existing class
     surface) — that is a requirements-phase call, not a
     design-phase one.
  3. **Tighten FR2's gear example name against the actual API.**
     `Gear.from_iso(...)` on the abstract base raises `TypeError`;
     the working call is `SpurGear.from_iso(...)`
     (`vibe_cading/mechanical/gears/base.py:357–370`). FR2 should
     either name `SpurGear.from_iso` directly or generalize to
     "a concrete gear subclass's `from_iso` factory"; Q2 can then
     close to a pure naming-of-the-script question.

- **Open concerns** (non-blocking)
  - **Q3 (filename convention) reads as a smuggled requirement.**
    Whether snap-fit emits one file or two (`hook.step` +
    `host.step`) changes FR5's contract surface. Predicted
    cost-of-failure if deferred: the developer ships a single-file
    convention, the reader can't tell which solid is the cutter
    target, README copy gets re-written. Low cost (one re-edit), but
    worth pinning before the design phase opens.
  - **Q4 (SVG in v1)** is correctly design-phase — FR5 already lets
    SVG be optional. Predicted cost if mishandled: a script grows
    past the 120-line NFC budget and gets split unnecessarily.
  - **Q6 (license-header glob shape)** is genuinely
    implementation-phase, not design — consider moving it out of
    Open Questions into a "Notes for the Developer" footnote so it
    doesn't gate design sign-off.

- **Verification log**
  - `tools/check_no_main_blocks.py:77` — `roots = [repo_root /
    "vibe_cading", repo_root / "parts"]` ✓ confirms FR4 and the
    Known-Domain-Constraints citation of lines 76–77.
  - `tools/check_license_headers.py:24` — pattern tuple is
    `("vibe_cading/**/*.py", "tools/**/*.py")` ✗ contradicts the
    artifact's claim that `parts/` is in scope; condition 1 above.
  - `examples/` directory presence — `ls` returns "No such file or
    directory" ✓ confirms "Today the directory does not exist".
  - `vibe_cading/mechanical/screws/metric.py:28, :132` — `class
    MetricMachineScrew` with `def to_cutter(self, profile=None, fit:
    str = "clearance")` ✓ confirms FR2 screw bullet.
  - `vibe_cading/mechanical/joints/snap_fit.py:22, :72, :98` —
    `class CantileverSnapFit` with `.male(...)`, `.to_cutter(...)`
    ✓ confirms FR2 snap-fit bullet (note: artifact says
    `.female(...)`; the actual method is `.to_cutter(...)` — a
    naming nuance, not a contract gap, but worth aligning with FR2
    wording).
  - `vibe_cading/mechanical/gears/base.py:357` — `Gear.from_iso`
    requires a concrete subclass; ✗ contradicts FR2's literal
    `Gear.from_iso(...)` invocation. Condition 3 above.
  - `vibe_cading/lego/` listing — contains `constants.py`,
    `technic_axle.py`, `cutters/`, `gears/`. No beam class. ✗
    confirms Q1 is unresolved and elevates it to condition 2.
  - `README.md:5` ✓ confirms the "practical examples demonstrating
    how to use these primitives" reference cited in Problem
    Statement.
  - `.gitignore:37` — `build/` is git-ignored at root; ✓ FR6's
    addition of `examples/build/` is consistent with the existing
    pattern.
  - `vibe_cading/print_settings.py:253` — `def get_profile(name:
    str | None = None) -> ToleranceProfile` ✓ confirms the
    Known-Domain-Constraints tolerance-profile claim.

### Re-confirmation (2026-05-15)

- **Verdict:** `APPROVE`

- **Conditions resolved:**
  1. ✓ AGPLv3-scope claim corrected. "Known Domain Constraints"
     (lines 213–221) now states the enforced CI scope is
     `vibe_cading/**/*.py` and `tools/**/*.py`, with `parts/` called
     out as intentionally not walked (voluntary by convention).
     Matches `tools/check_license_headers.py:24` (pattern tuple
     `("vibe_cading/**/*.py", "tools/**/*.py")`) and lines 8–11 of
     that file's docstring.
  2. ✓ Lego beam Q1 promoted to FR13 (lines 151–162) as a
     constants-module + raw-CadQuery v1 contract; FR2 bullet 1
     (lines 66–75) rewritten to match, with an explicit `No
     first-party LegoTechnicBeam class exists in v1 — see FR13`
     note. Q1 in Open Questions (line 271) is closed with the
     promotion pointer.
  3. ✓ Gear factory tightened. FR2 bullet 3 (lines 80–85) now names
     `SpurGear.from_iso(...)` directly and cites
     `vibe_cading/mechanical/gears/base.py:357` with the `Gear`-is-
     abstract caveat. Verified against base.py:357–370.

- **Open concerns addressed:**
  - Q3 (filename convention) promoted to FR14 (lines 164–173),
    pinning two-file output (`hook.step` + `host.step`) for
    snap-fit and `<example_name>.step` for the other three.
  - Q4 (SVG in v1) remains correctly design-phase under FR5.
  - Former Q6 moved to "Notes for the Developer" (lines 309–318),
    no longer gating design sign-off.
  - Snap-fit `.female(...)` vs `.to_cutter(...)` naming nuance
    resolved: FR2 bullet 4 (line 88) and FR14 (line 167) both use
    `.to_cutter(...)`. Verified against
    `vibe_cading/mechanical/joints/snap_fit.py:98`.

- **Verification log delta (this pass):**
  - `tools/check_license_headers.py:24` — pattern tuple
    `("vibe_cading/**/*.py", "tools/**/*.py")`; lines 8–11
    docstring affirms `parts/` is intentionally NOT walked. ✓
    condition 1 resolved.
  - `vibe_cading/mechanical/gears/base.py:357–370` — `@classmethod
    def from_iso(cls, …) -> "Gear"`; docstring at 369–371 states
    "`cls` must be a concrete subclass (e.g.
    `SpurGear.from_iso(...)`); calling `Gear.from_iso` directly
    raises `TypeError`". ✓ condition 3 resolved.
  - `vibe_cading/mechanical/joints/snap_fit.py:22, :72, :98` —
    `class CantileverSnapFit`, `def male(self, overlap: float =
    1.0)`, `def to_cutter(self, profile: ToleranceProfile | None =
    None)`. ✓ FR2 bullet 4 + FR14 names match real API.
  - `vibe_cading/mechanical/screws/metric.py:132` — `def
    to_cutter(self, profile=None, fit: str = "clearance")`. ✓
    FR2 bullet 2 unchanged and still accurate.
  - Domain-integrity-gate rationale (lines 16–22) updated to
    reflect the FR13/FR14 promotions; still NO. Accurate — no
    library API contract is altered.

### FR13 re-pin re-confirmation (2026-05-17)

- **Verdict:** `APPROVE`
- **FR13 coverage:**
  - (a) Imports `LegoTechnicBeam` from `vibe_cading.lego.technic_beam`
    ✓ — class exists at `vibe_cading/lego/technic_beam.py:74`.
  - (b) Public surface match ✓ — constructor `__init__(self,
    length_in_studs: int)` at `technic_beam.py:107`; `.solid`
    property at `:214`; `demo()` classmethod at `:219` (matches
    `tools/view.py --demo` signature contract).
  - (c) MUST/MUST-NOT wording (FR13 lines 153–167) is unambiguous
    and individually testable (import path, constructor arg,
    `.solid` read, STEP path, re-implementation prohibition,
    filename prohibition).
- **FR2 bullet 1:** ✓ names `LegoTechnicBeam` from
  `vibe_cading/lego/technic_beam.py` (lines 72–77).
- **Q1:** ✓ marked `[x]` FULLY RESOLVED with reference to
  `.agents/plans/2026-05-15-lego-technic-beam_design.md` Phase D
  approval and 2026-05-17 landing date (lines 276–282).
- **Meta block:** ✓ one-line re-pin note at lines 9–14, dated
  2026-05-17, cites sibling design path.
- **Human Confirmation Checkpoint:** ✓ still `[ ]` unchecked
  (line 332) — fresh gate preserved.
- **Domain integrity gate:** ✓ still NO with unchanged rationale
  (line 8, lines 16–28); re-pin consumes an existing class
  instead of constants — no data-contract scope change.
- **Coherence sweep:** ✓ no stale leaks. Grep for
  "constants-composition", "raw CadQuery primitives", "without a
  Beam class", "since no Beam class exists" returns 4 hits — all
  in legitimate historical/negative-framing contexts: Meta re-pin
  note (line 12), FR13 MUST NOT clause (line 162), FR13 historical
  parenthetical (line 165), Q1 RESOLVED historical parenthetical
  (line 281). Original Independent Designer Review section
  unmodified.
- **Verification log delta:**
  - `vibe_cading/lego/technic_beam.py:74` — `class LegoTechnicBeam`
    exists and is importable under the path FR13 names. ✓
  - `vibe_cading/lego/technic_beam.py:107` — `def __init__(self,
    length_in_studs: int) -> None`; accepts the concrete arg FR13
    suggests (`5`). ✓
  - `vibe_cading/lego/technic_beam.py:214–217` — `@property def
    solid(self) -> cq.Workplane` returns the built body. ✓
  - `vibe_cading/lego/technic_beam.py:219–231` — `@classmethod def
    demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]`
    matches the project's `demo()` signature contract. ✓ (FR13
    does not require the example to invoke `demo()`, but its
    presence confirms the class is `tools/view.py --demo`-ready,
    consistent with the v1 demonstration-surface framing.)
