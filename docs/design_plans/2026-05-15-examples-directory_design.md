# Design: `examples/` directory for OSS publication

<!-- Filename: 2026-05-15-examples-directory_design.md  (tracked in git under .agents/plans/) -->

## Meta
- **Requirements ref**: `.agents/plans/2026-05-15-examples-directory_req.md`
- **Requester role**: @designer (drafted requirements; co-design partner is the human Admin)
- **Date**: 2026-05-17
- **Dialog rounds**: 4
- **Drafting author**: Designer (vibe-cading ships no separate TL persona; the Designer plays both drafter and challenger per the project's design-flow accommodation)

---

## Objective
Author four self-contained, vanilla-CadQuery, AGPLv3-licensed example scripts under a new top-level `examples/` directory that demonstrate the library's canonical public-API patterns — Lego Technic beam construction, screw-cutter composition with tolerance profiles, ISO-validated gear factory, and snap-fit joint with host-block cutter — so a first-time OSS reader can run them with `python3 examples/<name>.py` and obtain inspectable STEP + SVG output within seconds of cloning.

---

## Architecture / Approach

### Approach chosen

**Structural decision: per-script standalone (Option (i)), zero new shared helper module.**

Each of the four scripts is fully self-contained: it carries its own ~10-line "build `examples/build/<name>/`, write STEP, write SVG, print absolute paths" block. No `examples/_common.py` is introduced in v1. The deletion-test outcome of that fork is documented in `### Module depth` below and Dialog Round 1; the short version is that a `_common.py` would (a) be shallow by construction (4-line helper wrapping `cq.exporters.export` plus a `print` loop), (b) push contributors away from the literal CadQuery export idiom they are here to learn, and (c) violate the requirements file's own "examples are read by first-time contributors" framing in NFC §Style. The duplication cost is bounded (~12 lines × 4 = 48 lines of trivial mechanical code), the contributor-extension lens favours visible per-script export calls, and there is no second consumer waiting for a shared seam. The Deep-Modules Dual-Lens Rule (vibe/INSTRUCTIONS.md) rejects the seam on both lenses.

**Component boundaries.**

- `examples/lego_technic_beam.py` — imports `LegoTechnicBeam` from `vibe_cading.lego.technic_beam`, instantiates with `length_in_studs=5`, exports `.solid` to `examples/build/lego_technic_beam/lego_technic_beam.{step,svg}`, prints both absolute paths.
- `examples/screw_cutter.py` — imports `MetricMachineScrew` from `vibe_cading.mechanical.screws.metric` and `get_profile` from `vibe_cading.print_settings`. Builds a small host block (cadquery box, ~15 × 15 × 6 mm), constructs `MetricMachineScrew.from_size("M3", length=10, head_type="socket")`, obtains `screw.to_cutter(profile=get_profile("fdm_standard"), fit="clearance")`, subtracts the cutter from the host block at a chosen mating-face position (counterbore mouth at Z=6, shaft descending into −Z), exports the cut block (the demonstration target — the host-with-counterbore — not the screw itself) to `examples/build/screw_cutter/screw_cutter.{step,svg}`, prints both paths. Profile selection: hard-coded literal `"fdm_standard"` so the example is reproducible without `.env` setup; an inline comment documents the override path (`get_profile()` with no arg reads `VIBE_MACHINE_PROFILE`).
- `examples/gear_from_iso.py` — imports `SpurGear` from `vibe_cading.mechanical.gears.spur`. Constructs `SpurGear.from_iso(module=1.0, teeth=20, face_width=5.0)`. Module `1.0 mm` is the most common ISO benchmark size; `teeth=20` clearly shows the involute profile without taking >2 s to mesh; `face_width=5.0 mm` matches typical Lego-scale parts. Exports `.solid` to `examples/build/gear_from_iso/gear_from_iso.{step,svg}`, prints both paths.
- `examples/snap_fit_hook.py` — imports `CantileverSnapFit` from `vibe_cading.mechanical.joints.snap_fit`. Constructs a joint with `length=10, hook_depth=1.5` (defaults elsewhere). Builds two output artefacts per FR14: (a) the male hook from `joint.male()` written to `examples/build/snap_fit_hook/hook.step`, (b) a host block (cadquery box, ~10 × 10 × 16 mm, positioned so the cutter enters cleanly at one face) cut by `joint.to_cutter()` and written to `examples/build/snap_fit_hook/host.step`. SVGs paired one-to-one: `hook.svg`, `host.svg`. Prints all four absolute paths.

**SVG generation mechanism.** Each script invokes `cq.exporters.export(workplane, str(svg_path))` once per solid. The exporter infers SVG from the `.svg` extension; no `exportType=` argument is required (it is required only when the extension is ambiguous). This is the same single-call form used elsewhere in the project (`tools/view.py:125`, `tools/preview.py:214`). Default projection is acceptable for a teaching artefact — readers who want curated views run `python3 tools/preview.py vibe_cading.lego.technic_beam.LegoTechnicBeam` after seeing the example, and the README cross-reference points them there. *Dialog Round 2 ruled out passing custom projection opts.*

**Path printing convention.** Use `str(path.resolve())` (native separators). Three Linux dev containers ship today; the Windows-back-slash variant is not a target the v1 OSS release blocks on, and `as_posix()` would print `/`-paths that don't paste cleanly into a Windows file explorer. Inline comment on the print line documents the choice. *Dialog Round 3.*

**License-header CI patch shape.** Single-line glob addition. Patch `tools/check_license_headers.py:24` from `("vibe_cading/**/*.py", "tools/**/*.py")` to `("vibe_cading/**/*.py", "tools/**/*.py", "examples/*.py")` (non-recursive `examples/*.py`, since FR9 forbids subpackages and the four scripts sit directly under `examples/`). Update the module docstring at `:1–15` in the same patch to add a one-line note: `examples/*.py is walked (release teaching surface).` The "named module-level constant" refactor offered as an alternative in the requirements' Notes-for-Developer section is rejected — the tuple has three entries, naming it adds a layer without paying it back.

**`.gitignore` patch.** Add a single line `examples/build/` under the existing `tmp/` block (around line 6). The repo's broad `*.step` / `*.svg` globs (lines 12–14) already cover the file *contents* but a directory entry is clearer for a contributor scanning `.gitignore` to learn the layout convention.

**README cross-reference.** Insert a new `## Examples` section between the existing `## Models` block (line 25 ends at the `---` rule on line 26) and the existing `## Dev Setup` block at line 27. The section reads:

```markdown
## Examples

Four self-contained scripts under `examples/` demonstrate the library's
canonical usage patterns. Each runs under a vanilla CadQuery install and
writes STEP + SVG output to `examples/build/<name>/` (gitignored):

| Example | What it shows |
|---|---|
| `examples/lego_technic_beam.py` | `LegoTechnicBeam(length_in_studs=5)` from `vibe_cading.lego.technic_beam` |
| `examples/screw_cutter.py` | `MetricMachineScrew.to_cutter(profile=...)` boring a counterbore + clearance into a host block |
| `examples/gear_from_iso.py` | `SpurGear.from_iso(module=1.0, teeth=20, face_width=5.0)` ISO-validated gear factory |
| `examples/snap_fit_hook.py` | `CantileverSnapFit` male hook plus host block cut by `.to_cutter(...)` (two STEP files) |

Run one with:

    python3 examples/lego_technic_beam.py
```

Placement rationale: `Models` lists the library surface, `Examples` shows how to *use* it, `Dev Setup` then walks through cloning — the order matches the new-contributor flow described in the requirements' User Story.

### Module depth

| New Module | Behaviour concentrated | Caller leverage / locality |
|---|---|---|
| N/A — no new Modules | Per-script standalone is the chosen structure; the four `examples/*.py` files are top-level execution scripts, not reusable importables. The rejected `examples/_common.py` proposal is recorded in Dialog Round 1 with the deletion-test outcome (deletes). The project's vetted helper locations (`vibe_cading/cq_utils.py`, `vibe_cading/print_settings.py`) already expose everything an example needs (`get_profile`); the examples consume those, they don't extend them. | — |

### Alternatives rejected

- **Option (ii) — `examples/_common.py` shared helper** with `export_and_announce(workplane, out_dir, name)`. Rejected on the Dual-Lens Rule: maintainer-locality (no — only four call sites, all teaching-scripts that benefit from inline export visibility); contributor-extension lens (no — the example's job is to teach the literal `cq.exporters.export(...)` call, not abstract it away). Deletes under the deletion test even with the four false-positive carve-outs + the project's contributor-extension fifth lens applied. Dialog Round 1 captures the full reasoning.
- **Option (iii) — consume `vibe_cading.cq_utils` for export.** No such helper exists; `cq_utils.py` holds geometric primitives (axle-hole helpers etc.), not export plumbing. Adding one purely to serve `examples/` would be the rejected Option (ii) dressed up as a "first-party" helper — same dual-lens failure, plus it pollutes `cq_utils.py`'s purpose statement.
- **Routing examples through `tools/view.py` or `tools/preview.py`.** Rejected by the requirements' Out-of-Scope block and reinforced by NFC ("runs on whatever CadQuery version is pinned by the dev container today"). Examples must demonstrate vanilla-CadQuery usage; pulling in `tools.*` breaks FR9.
- **SVG-with-curated-projections via a helper.** Same shape as Option (ii), same verdict. Default `cq.exporters.export(..., '*.svg')` is sufficient for "I want to see geometry exists"; readers who want labelled three-view drawings have `tools/preview.py`.
- **Hard-coding a clearance float in `screw_cutter.py` instead of calling `get_profile("fdm_standard")`.** Violates the project's Material-Specific Screw Tolerances rule (vibe/INSTRUCTIONS.md "Constants & Tolerances") and the requirements' Known-Domain-Constraints bullet. The example exists specifically to demonstrate the tolerance-profile pattern; bypassing it would be a teaching anti-example.
- **Profile sourced from `os.getenv("VIBE_MACHINE_PROFILE")` via no-arg `get_profile()`.** Rejected for v1 because it makes the example output non-reproducible across contributors. The hard-coded `"fdm_standard"` literal with an inline comment naming the override path strikes the balance. *Dialog Round 4.*

---

## Data & Interface Contracts

*Domain integrity gate is NO (requirements §Meta line 8). No data-contract / API-schema specification required.*

The relevant interface dependencies are pinned by the existing library API and verified by the requirements' Verification Log + this design's Code-Truth Verification block below. Each example script consumes a stable public surface:

- `LegoTechnicBeam(length_in_studs: int)` → `.solid: cq.Workplane` — `vibe_cading/lego/technic_beam.py:107, :214`
- `MetricMachineScrew.from_size(size, length, head_type, drive_type)` → `.to_cutter(profile=None, fit="clearance") → cq.Workplane` — `vibe_cading/mechanical/screws/metric.py:55, :132`
- `SpurGear.from_iso(module, teeth, face_width, bore=None, pressure_angle=20.0, **kwargs)` → `.solid` — inherited from `vibe_cading/mechanical/gears/base.py:357`; concrete subclass at `vibe_cading/mechanical/gears/spur.py:31`
- `CantileverSnapFit(length, width, thickness, hook_depth, ...)` → `.male(overlap=1.0)`, `.to_cutter(profile=None) → cq.Workplane` — `vibe_cading/mechanical/joints/snap_fit.py:22, :72, :98`
- `get_profile(name: str | None = None) → ToleranceProfile` — `vibe_cading/print_settings.py:253`

---

## Implementation Plan

- [x] **T1** — Create top-level `examples/` directory (tracked by git via the four scripts below). No `__init__.py` (examples is not a package; FR9 imports are from `vibe_cading.*`, not `examples.*`).
- [x] **T2** — Author `examples/lego_technic_beam.py`. AGPLv3 header + module docstring (FR10) + `if __name__ == "__main__":` block (FR4). Body: import `LegoTechnicBeam`, instantiate with `length_in_studs=5`, mkdir `examples/build/lego_technic_beam/`, `cq.exporters.export(beam.solid, str(step_path))`, `cq.exporters.export(beam.solid, str(svg_path))`, print absolute paths. Target ≤80 lines.
- [x] **T3** — Author `examples/screw_cutter.py`. AGPLv3 + docstring + main block. Body: import `MetricMachineScrew`, `get_profile`, `cadquery as cq`. Build host block (`cq.Workplane("XY").box(15, 15, 6, centered=(True, True, False))` — Z∈[0,6], stud-grid-friendly; the box sits with its top face at Z=6 so the screw cutter enters from +Z and the shaft descends). Construct `screw = MetricMachineScrew.from_size("M3", length=10, head_type="socket")`. Obtain `cutter = screw.to_cutter(profile=get_profile("fdm_standard"), fit="clearance")`. The cutter's native origin: the shaft extrudes in −Z from Z=0; translate cutter by `(0, 0, 6)` so the counterbore mouth lands at the host's top face. Cut: `result = host.cut(cutter.translate((0, 0, 6)))`. Export `result` to STEP + SVG. Print. Target ≤80 lines.
- [x] **T4** — Author `examples/gear_from_iso.py`. AGPLv3 + docstring + main block. Body: import `SpurGear`. Construct `gear = SpurGear.from_iso(module=1.0, teeth=20, face_width=5.0)`. Export `gear.solid` to STEP + SVG. Print. Target ≤80 lines.
- [x] **T5** — Author `examples/snap_fit_hook.py`. AGPLv3 + docstring + main block. Body: import `CantileverSnapFit`, `cadquery as cq`. Construct `joint = CantileverSnapFit(length=10, hook_depth=1.5)`. Build hook = `joint.male()`. Build host = `cq.Workplane("XY").box(10, 10, 16, centered=(True, True, False))` then `.cut(joint.to_cutter())`. Export both to `hook.{step,svg}` and `host.{step,svg}` under `examples/build/snap_fit_hook/`. Print all four absolute paths. Target ≤80 lines.
- [x] **T6** — Patch `.gitignore` to add `examples/build/` directly under the existing `tmp/` block.
- [x] **T7** — Patch `tools/check_license_headers.py`: extend the glob tuple at `:24` from `("vibe_cading/**/*.py", "tools/**/*.py")` to `("vibe_cading/**/*.py", "tools/**/*.py", "examples/*.py")`. Update the module docstring (`:1–15`) to add a one-line note that `examples/*.py` is also walked.
- [x] **T8** — Patch `README.md` to insert the `## Examples` section between current line 26 and line 27 (between `## Models` and `## Dev Setup`). Content per the "README cross-reference" block above.
- [x] **T9** — Smoke-run all four scripts from the repo root and capture exit codes:
  - `python3 examples/lego_technic_beam.py`
  - `python3 examples/screw_cutter.py`
  - `python3 examples/gear_from_iso.py`
  - `python3 examples/snap_fit_hook.py`
  Verify each writes the expected files (`ls examples/build/<name>/`). Each must exit 0 and complete in ≤10 s (NFC runtime budget).
- [x] **T10** — Run `python3 tools/check_license_headers.py` and `python3 tools/check_no_main_blocks.py`; both must pass. The first verifies T7's glob widening enforces AGPLv3 on `examples/*.py`; the second verifies the no-main-blocks gate's scope was NOT widened (`examples/` is intentionally exempt — FR4).
- [x] **T11** — Verify `examples/build/` is git-ignored: after T9 runs, `git status` shows no `examples/build/*` entries.
- [x] **T12** — Verify README cross-reference: `grep -c "examples/lego_technic_beam.py" README.md` returns ≥1; `grep -c "examples/snap_fit_hook.py" README.md` returns ≥1.

---

## Tests

| #  | Test description                                                                                                                | Expected assertion                                                                                                                                  | File / location                                          | Maps to     |
|----|---------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|-------------|
| 1  | `examples/` directory exists at repo root, distinct from `vibe_cading/`, `parts/`, `experiments/`, `tools/`.                    | `[ -d examples ] && [ -f examples/lego_technic_beam.py ]` returns 0.                                                                                | Shell smoke (T1)                                         | FR1         |
| 2  | Exactly the four named scripts exist under `examples/` and no others (besides any `__init__.py`).                                | `ls examples/*.py | sort` returns the four FR2 filenames.                                                                                            | Shell smoke (T2–T5)                                       | FR2         |
| 3  | `python3 examples/lego_technic_beam.py` runs to completion (exit 0) from repo root.                                              | Exit code 0; stdout includes STEP+SVG absolute paths.                                                                                                | Shell smoke (T9)                                         | FR3, FR13   |
| 4  | `python3 examples/screw_cutter.py` runs to completion.                                                                           | Exit code 0; stdout includes STEP+SVG absolute paths.                                                                                                | Shell smoke (T9)                                         | FR3         |
| 5  | `python3 examples/gear_from_iso.py` runs to completion.                                                                          | Exit code 0; stdout includes STEP+SVG absolute paths.                                                                                                | Shell smoke (T9)                                         | FR3         |
| 6  | `python3 examples/snap_fit_hook.py` runs to completion.                                                                          | Exit code 0; stdout includes four absolute paths (hook.step, hook.svg, host.step, host.svg).                                                         | Shell smoke (T9)                                         | FR3, FR14   |
| 7  | Each script carries an `if __name__ == "__main__":` block; the no-main-blocks CI gate does NOT walk `examples/`.                 | `python3 tools/check_no_main_blocks.py` exits 0 (does not flag `examples/*.py`); each `examples/*.py` contains the literal main-guard line.          | Shell smoke + grep (T10)                                  | FR4         |
| 8  | Each script writes its output under `examples/build/<example_name>/` with at least one STEP file per distinct solid.             | After T9: `examples/build/lego_technic_beam/lego_technic_beam.step`, `examples/build/screw_cutter/screw_cutter.step`, `examples/build/gear_from_iso/gear_from_iso.step`, `examples/build/snap_fit_hook/hook.step`, `examples/build/snap_fit_hook/host.step` all exist (non-zero size).                                    | File-existence check (T9)                                | FR5, FR14   |
| 9  | `examples/build/` is git-ignored.                                                                                                | `git check-ignore examples/build/` returns 0; `git status --porcelain examples/build/` returns empty after T9.                                       | Shell smoke (T11)                                        | FR6         |
| 10 | Each script prints absolute paths on success, one path per line, prefixed by a short label.                                      | `python3 examples/<name>.py` stdout matches regex `^(STEP|SVG): /.*\.(step|svg)$` for every output file written.                                     | Shell smoke + regex (T9)                                  | FR7         |
| 11 | Each script carries the AGPLv3 header; the license-header CI gate enforces this.                                                 | `python3 tools/check_license_headers.py` exits 0 after T7; if a header is removed from any `examples/*.py`, the gate exits 1 (negative spot-check).   | Shell smoke (T10)                                        | FR8         |
| 12 | Each script's imports are restricted to stdlib + `cadquery` + `vibe_cading.*`.                                                   | `grep -E "^(from|import) " examples/*.py` shows no imports from `parts.`, `experiments.`, `tools.`, or third-party non-CadQuery packages.            | Grep audit (T2–T5)                                       | FR9         |
| 13 | Each script opens with a module-level docstring (after AGPLv3 header) stating: primitive demonstrated, run command, files written.| `ast.parse(...).body[0]` is a `ast.Expr(value=ast.Constant(str))` after the comment-only header; docstring text contains the literal `python3 examples/<name>.py` and the literal `examples/build/<name>/`. | AST audit script under `tmp/` (T2–T5)                     | FR10        |
| 14 | README contains a Getting-started Examples cross-reference listing all four scripts with the literal run command.                | `grep -c "examples/lego_technic_beam.py" README.md` ≥1; same for the other three; `grep -c "python3 examples/" README.md` ≥1.                         | Shell grep (T12)                                         | FR11        |
| 15 | `build.toml` contains no `[[build]]` entry naming any `examples/` script or any model class living under `examples/`.            | `grep -c "examples" build.toml` returns 0; `grep -c "\\[\\[build\\]\\]" build.toml` count unchanged from pre-task baseline.                          | Shell grep                                               | FR12        |
| 16 | `examples/lego_technic_beam.py` imports `LegoTechnicBeam` from `vibe_cading.lego.technic_beam` and instantiates with a concrete `length_in_studs`; does not re-implement from constants; filename is exactly `lego_technic_beam.py`. | `grep "from vibe_cading.lego.technic_beam import LegoTechnicBeam" examples/lego_technic_beam.py` returns 1 match; `grep "LegoTechnicBeam(length_in_studs=" examples/lego_technic_beam.py` returns ≥1 match; `grep -E "from vibe_cading.lego.constants" examples/lego_technic_beam.py` returns 0 matches. | Shell grep (T2)                                          | FR13        |
| 17 | `examples/snap_fit_hook.py` emits exactly `hook.step` and `host.step` under `examples/build/snap_fit_hook/`.                     | After T9: both files exist; the other three examples emit exactly one `<name>.step` each.                                                            | File-existence audit (T9)                                | FR14        |

Every FR (FR1 through FR14) appears in at least one row's `Maps to` column. FR3 and FR4 span multiple rows (intentional — they apply to each of the four scripts).

---

## Success Criteria
1. All 12 implementation-plan tasks (T1–T12) are checked off.
2. Tests 1–17 above all pass; specifically, the four shell-smoke commands in T9 exit 0 within ≤10 s each on the dev-container baseline.
3. `python3 tools/check_license_headers.py` exits 0 (T10).
4. `python3 tools/check_no_main_blocks.py` exits 0 — confirming examples are NOT in scope of that gate (T10, FR4).
5. After T9, `git status` shows no entries under `examples/build/` (T11, FR6).
6. README's new `## Examples` section is greppable (T12, FR11).
7. Each example script's executable Python body (excluding AGPLv3 header + module docstring) is ≤80 lines (NFC file-size budget); hard cap 120 lines.
8. No example script imports from `parts.*`, `experiments.*`, `tools.*`, or any third-party package outside the CadQuery dependency tree (Test 12, FR9).

---

## Out of Scope

(Mirrored from requirements §Out of Scope, with one design-phase addition.)

- Tolerance-sweep example (5th script).
- Assembly-module example (`assemble()` pattern).
- Pytest coverage of examples in CI.
- `tools/view.py` integration changes — examples use `cq.exporters.export(...)` directly.
- Non-OSS / Claude-Code-specific demonstrations.
- README authoring beyond the new `## Examples` cross-reference.
- **(Design-phase addition)** A shared `examples/_common.py` helper module. Rejected in Round 1 under the Deep-Modules Dual-Lens Rule; if a 5th example with non-trivially-shared infrastructure lands later, the seam can be revisited at that time.

---

## Known Risks & Mitigations

| Risk                                                                                                              | Mitigation                                                                                                                                                                                                                                                                                                                                                                                                                                              |
|-------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `cq.exporters.export(..., '*.svg')` produces unflattering or hard-to-interpret default projections for some shapes (gear especially). | Acceptable in v1: the SVG's job is to confirm geometry exists and to give the reader an instant visual; curated three-view output is `tools/preview.py`'s job, cross-referenced in README. If user feedback after release shows the gear SVG is unreadable, revisit by adding an inline 2-line `Workplane.rotate(...)` before export, NOT by introducing a helper module.                                                                                  |
| `screw_cutter.py` host-block dimensions might leave too-thin walls around the M3 counterbore on the FDM profile. | Host block sized `15 × 15 × 6 mm`: wall ≈ (15 − 5.5)/2 ≈ 4.75 mm; counterbore depth ≈ 3.0 mm; through-shaft (length=10) exits the bottom by ~4 mm, which is intentional (illustrates the cutter's "overcut beyond boundary" behavior — a teaching surface for the project's Infinite Cutter Overcuts rule). Inline comment explains.                                                                                                                |
| `SpurGear.from_iso(module=1.0, teeth=20, face_width=5.0)` runtime exceeds the 10-s NFC budget on the dev-container baseline. | Module = 1.0 mm and teeth = 20 is well below the heaviest realistic case (`SpurGear.demo()` runs higher tooth counts in CI); risk treated as low. Mitigation: if T9 runtime exceeds 10 s, the design-phase fallback is to drop to `teeth=12` (still demonstrates from_iso validation, faster build). Captured here so the developer does not relitigate.                                                                                                |
| Path printing of `str(path.resolve())` produces back-slashed Windows paths that confuse a Linux-only reader CI tool. | Out of v1 scope: the dev container is Linux. Note in the inline comment on the print line documents the convention so a future Windows-CI follow-up has a clean re-decision point.                                                                                                                                                                                                                                                                       |
| The four example scripts collectively duplicate ~40 lines of trivial mkdir+export+print code; a future contributor may misread this as a "missing abstraction" and introduce `examples/_common.py`. | Documented in this brief (Out of Scope §design-phase addition, Dialog Round 1) and in Module-Depth §N/A. Add a one-line comment in each example near the export block: `# Export + path-print logic is duplicated by design — examples are teaching artefacts; see .agents/plans/2026-05-15-examples-directory_design.md Round 1.`                                                                                                                  |

---

## Non-Blocking Concerns — Predicted Cost of Failure

(Per the project's "Predicted-Cost Estimation for Non-Blocking Concerns" rule.)

| Concern | Classification | Predicted cost if it fails |
|---|---|---|
| Default SVG projection unreadable for gear example | Non-blocking | One README footnote + one 2-line rotation tweak per affected script. ≤ 30 minutes contributor time. |
| Cross-platform path printing (Windows back-slashes) | Non-blocking, deferred | Zero v1 cost (no Windows CI target). If raised post-release: one one-line change to `as_posix()`, applied to all 4 scripts. ≤ 15 minutes. |
| Gear example exceeds 10-s runtime budget on a slower contributor's machine | Non-blocking | One constant change (`teeth=20` → `teeth=12`); ≤ 5 minutes. Pre-mitigated in §Known Risks. |
| Future contributor introduces `examples/_common.py` regardless of design guidance | Non-blocking (process) | One PR-review comment citing this design + the Round-1 rationale + revert. ≤ 30 minutes reviewer time. The in-script comment serves as the second line of defence. |

No concern crosses a "blocking" threshold (none costs a print iteration, none corrupts data, none requires a re-run of the full build pipeline).

---

## Code-Truth Verification (Spawn-time)

Each cited API was opened and verified at file:line during this design pass:

- `vibe_cading/lego/technic_beam.py:74` — `class LegoTechnicBeam`; `:107` — `def __init__(self, length_in_studs: int)`; `:214` — `@property def solid`.
- `vibe_cading/mechanical/screws/metric.py:28` — `class MetricMachineScrew`; `:55` — `@classmethod def from_size(cls, size, length, head_type="socket", drive_type="hex")`; `:132` — `def to_cutter(self, profile=None, fit="clearance")`; the docstring explicitly notes the profile fallback to `get_profile()` (`:160–161`).
- `vibe_cading/mechanical/gears/base.py:357–396` — `@classmethod def from_iso(cls, module, teeth, face_width, bore=None, pressure_angle=20.0, **kwargs)`; docstring at `:367–388` confirms `cls` must be concrete (the example uses `SpurGear.from_iso`); module validation against `ISO_STANDARD_MODULES` at `:382–388`.
- `vibe_cading/mechanical/gears/spur.py:31` — `class SpurGear(Gear)`; concrete subclass.
- `vibe_cading/mechanical/joints/snap_fit.py:22` — `class CantileverSnapFit`; `:72` — `def male(self, overlap=1.0) -> cq.Workplane`; `:98` — `def to_cutter(self, profile=None) -> cq.Workplane`.
- `vibe_cading/print_settings.py:253` — `def get_profile(name: str | None = None) -> ToleranceProfile`; `"fdm_standard"` is the default fallback (`:80`).
- `tools/check_license_headers.py:24` — current pattern tuple is `("vibe_cading/**/*.py", "tools/**/*.py")`; needs the third entry `"examples/*.py"`.
- `tools/check_no_main_blocks.py:77` — `roots = [repo_root / "vibe_cading", repo_root / "parts"]`; correctly does NOT include `examples/`. **No change required to this tool.**
- `README.md:25–27` — `## Models` table closes at line 25 (`---` rule at 26); `## Dev Setup` begins at line 27. New `## Examples` section inserts between them.
- `.gitignore:4–6` — current `tmp/` block; `examples/build/` adds cleanly underneath. (Global `*.step`, `*.svg`, `*.stl`, `*.stp` globs at `:11–14` already cover the file *contents*.)
- `build.toml` — confirmed contains zero references to `examples/` (negative grep verified during spawn).

---

## Design Dialog Log

### Round 1 — Structural decision: per-script vs. shared `examples/_common.py` helper
**Proposal (drafter):**
> All four scripts will duplicate the same ~12-line block: `Path(__file__).parent / "build" / name`, `mkdir(parents=True, exist_ok=True)`, `cq.exporters.export(...)` twice (STEP + SVG), and a 2-line `print` loop over the written paths. That's ~48 lines of mechanical duplication. The instinct is to factor it into `examples/_common.py` exposing `export_and_announce(workplane: cq.Workplane, out_dir: Path, name: str) -> None`.

**Challenger:**
> Apply the Deep-Modules Dual-Lens Rule from vibe/INSTRUCTIONS.md before drafting. (a) Maintainer-locality: only four consumers, all of which are leaf execution scripts. No polymorphic dispatch, no `isinstance` checks, no shared state. The helper would be a "function with no callers other than the four it was designed for" — the deletion test classifies this as a candidate for inlining. (b) Contributor-extension lens (the fifth, project-specific carve-out): does a future OSS contributor adding a 5th example benefit from inheriting / implementing this contract? Not really — the contract is `(workplane, dir, name) → None`; it doesn't enforce anything about the example's body, it just wraps `cq.exporters.export`. (c) The contributor-facing teaching surface lens: the requirements file's NFC §Style explicitly says examples are "read by first-time contributors" and "every non-obvious dimension carries an inline comment." Hiding the export call behind a helper makes the example *worse* as a teaching artefact — readers learn `from examples._common import export_and_announce` instead of `from cadquery import exporters`. That's an anti-lesson.

**Resolution:**
> Decision: per-script standalone (Option (i)). No `examples/_common.py`. The duplication is intentional — it's the lesson. Add a defensive comment in each example pointing future contributors at this round so the duplication isn't misread as a missing abstraction. Captured in §Known Risks and §Out of Scope. The seam can be reopened if a 5th example with non-trivial shared infrastructure materially needs it.

### Round 2 — SVG generation mechanism
**Proposal (drafter):**
> Each script writes a single SVG via `cq.exporters.export(workplane, str(svg_path), exportType="SVG")` with no projection arguments. Use the exporter's default camera. If readers want curated three-view drawings, they run `tools/preview.py`.

**Challenger:**
> Two pushbacks. (a) `exportType="SVG"` is redundant when the path ends in `.svg` — cadquery's exporter dispatches on extension. Adding the arg is a minor noise, and the requirements' NFC §Style demands minimal teaching surface. (b) The default projection for a spur gear can be ugly (face-on, all teeth occluded). Should the gear example pass a custom projection?

**Resolution:**
> (a) Drop the `exportType="SVG"` argument; rely on extension inference, matching `tools/view.py:125` and `tools/preview.py:214` style. (b) Don't introduce per-script projection tweaks in v1 — that pulls in `cq.Plane` / camera-vector knowledge that's tangential to the lesson. The README cross-reference points readers at `tools/preview.py` for curated views. If post-release feedback shows the gear SVG is unreadable, the fix is a single inline `Workplane.rotate(...)` call in `gear_from_iso.py`, NOT a helper. Captured in §Known Risks.

### Round 3 — Path printing convention (Q5 from requirements)
**Proposal (drafter):**
> Use `path.resolve().as_posix()` for cross-platform consistency. Windows readers get forward-slashed paths that paste into any modern shell or viewer URL bar.

**Challenger:**
> Two problems. (a) On Linux (the dev container baseline, which is the only supported v1 target), `as_posix()` and `str(path.resolve())` produce identical output, so the "consistency" benefit is theoretical. (b) On Windows, `as_posix()` produces `C:/Users/.../examples/build/snap_fit_hook/hook.step` which doesn't paste into Windows Explorer's address bar cleanly (it accepts forward slashes, but native paste-back from File Explorer is back-slashed, so a round-trip is asymmetric). And the project ships zero Windows CI today — optimising for an unsupported platform is premature.

**Resolution:**
> Decision: `str(path.resolve())` (native separators). Document the choice with a one-line inline comment on the print statement: `# str() = native separators; switch to .as_posix() if cross-platform paste-fidelity matters.` Captured in §Approach chosen → Path printing and §Non-Blocking Concerns (cost: 15 minutes if reversed). Consistency across all four scripts is the only hard requirements constraint, and it's preserved either way.

### Round 4 — Tolerance-profile selection for `screw_cutter.py`
**Proposal (drafter):**
> `screw_cutter.py` should call `get_profile()` with no argument, so it reads `VIBE_MACHINE_PROFILE` from the user's `.env`. This is the canonical usage pattern documented in vibe/INSTRUCTIONS.md "Constants & Tolerances" and CLAUDE.md §Manufacturing & Tolerance Profiles. Teaching the example to do anything else contradicts the project's tolerance discipline.

**Challenger:**
> Three problems. (a) The requirements' FR3 says examples must run "no environment variables, no command-line arguments." `get_profile()` (no arg) reads `os.getenv("VIBE_MACHINE_PROFILE", "fdm_standard")` — so it *technically* works without `.env`, but a new contributor reading the source has to know that default-fallback exists. (b) Output reproducibility: if contributor A runs the example with `.env` setting `VIBE_MACHINE_PROFILE=resin_precise` and contributor B has no `.env`, they get geometrically different STEPs. That undermines "see the library work in seconds." (c) The example exists to demonstrate the `profile=...` API pattern; passing it explicitly is *more* educational than relying on a fallback chain that the reader can't see in the script's own source.

**Resolution:**
> Hard-code `get_profile("fdm_standard")` in the script. Add an inline comment naming the override path: `# Hard-coded for reproducibility; in production code, call get_profile() with no arg to read VIBE_MACHINE_PROFILE from .env.` This satisfies (a) literal-no-env-var compliance, (b) reproducibility across all readers, and (c) teaching the explicit-argument pattern that the rest of the library expects. The fallback-chain knowledge is documented one comment-line away from the call site, where a reader will see it. Captured in §Approach chosen → screw_cutter.py and §Alternatives rejected.

---

## Sign-off

### Author sign-off (drafting role — Step 3 termination)
- [ ] Domain expert co-sign  *(domain integrity gate is NO — skipped)*
- [x] Requester sign-off  *(designer-as-requester; co-design loop concluded after Round 4)*
- [x] TL sign-off  *(designer-as-TL accommodation per design-flow.md; vibe-cading ships no separate TL persona — Step 3 termination conditions verified below)*

**Step 3 termination verification:**
1. Every FR mapped in Tests `Maps to` column — verified above (FR1 → row 1, FR2 → row 2, FR3 → rows 3–6, FR4 → row 7, FR5 → row 8, FR6 → row 9, FR7 → row 10, FR8 → row 11, FR9 → row 12, FR10 → row 13, FR11 → row 14, FR12 → row 15, FR13 → rows 3 + 16, FR14 → rows 6 + 8 + 17). ✓
2. Open Questions resolved — Q1 fully resolved in requirements; Q2 closed in this artifact via SpurGear.from_iso pinning (Architecture §Approach chosen + Code-Truth Verification); Q3 already promoted to FR14; Q4 resolved by Dialog Round 2 (SVG ships in v1 via default projection); Q5 resolved by Dialog Round 3; former Q6 resolved by §Approach chosen → License-header CI patch shape. ✓
3. Tests table has ≥1 row per FR — verified above. ✓
4. Success criteria measurable & unambiguous — 8 criteria, every one is a shell exit code, file-existence check, grep result, or line count. ✓
5. Domain integrity gate is NO → no domain-expert co-sign needed. ✓
6. Non-blocking concerns cost-checked — §Non-Blocking Concerns table assigns predicted cost in concrete project units (contributor-minutes, README footnotes, PR-review minutes) to every non-blocking item. ✓
7. Module depth section completed — §Module depth row reads `N/A — no new Modules` with the rejected `examples/_common.py` proposal traced to Dialog Round 1. ✓

### Independent reviewer sign-off (fresh-context — Step 3.5 termination)
- [x] Independent TL  *(see "Independent TL Review (fresh context, 2026-05-17)" section below)*
- [x] Independent Developer  *(see "Independent Developer Review (fresh context, 2026-05-17)" section below)*
- [ ] Independent Researcher  *(domain integrity gate is NO — skipped)*

---

## Independent TL Review (fresh context, 2026-05-17)

- **Verdict:** `APPROVE`

- **Strengths**
  - Every FR (FR1–FR14) maps to at least one `Maps to` row in the Tests
    table; multi-row spread for FR3, FR4, FR13, FR14 is intentional and
    traceable to per-script application.
  - The per-script-standalone structural decision is grounded in the
    Deep-Modules Dual-Lens Rule with both lenses applied explicitly
    (maintainer-locality + contributor-extension), and the rejection of
    `examples/_common.py` carries a concrete duplication budget
    (~12×4=48 lines) plus a pedagogical anti-pattern argument. The
    `### Module depth` row correctly resolves to `N/A — no new Modules`
    consistent with this verdict.
  - Code-Truth Verification block opens every cited API at file:line,
    including the `MetricMachineScrew.to_cutter` `profile=None` fallback
    that the screw_cutter example depends on; the no-main-blocks CI tool
    scope claim (`roots = [vibe_cading, parts]`, no `examples/`) is
    explicitly verified, so FR4 needs no CI patch.

- **Conditions / required edits:** None.

- **Open concerns** (non-blocking, with predicted costs verified
  per the design's §Non-Blocking Concerns table)
  - Default SVG projection for gear may be hard to read — ≤30 min
    contributor-time to add a 2-line `Workplane.rotate(...)` if user
    feedback raises it. ✓ cost stated in project units.
  - Cross-platform path printing — 0 cost in v1 (Linux-only target);
    ≤15 min if reversed post-release. ✓
  - Gear runtime budget overrun — ≤5 min constant change
    (`teeth=20 → teeth=12`); pre-mitigated. ✓
  - Future contributor re-proposes `examples/_common.py` — ≤30 min
    PR-review-comment + revert; in-script comment defends. ✓
  - Minor non-blocking nit (not a condition): the `.gitignore` patch
    description references "around line 6" for the `tmp/` block; the
    actual line is `:5`. Patch shape is still correct (single new line
    under the `tmp/` block); no edit required.

- **Verification log** — every code/doc claim opened at file:line
  - `vibe_cading/lego/technic_beam.py:74` — `class LegoTechnicBeam` ✓
  - `vibe_cading/lego/technic_beam.py:107` — `def __init__(self, length_in_studs: int)` ✓
  - `vibe_cading/lego/technic_beam.py:214–217` — `@property def solid` ✓
  - `vibe_cading/mechanical/screws/metric.py:28` — `class MetricMachineScrew` ✓
  - `vibe_cading/mechanical/screws/metric.py:54–55` — `@classmethod def from_size(cls, size, length, head_type="socket", drive_type="hex")` ✓
  - `vibe_cading/mechanical/screws/metric.py:132` — `def to_cutter(self, profile=None, fit: str = "clearance")` ✓ (design says `fit="clearance"`; actual default matches)
  - `vibe_cading/mechanical/screws/metric.py:160–161` — `prof = profile if profile is not None else get_profile()` ✓ (confirms the design's "fallback to `get_profile()`" claim)
  - `vibe_cading/mechanical/gears/base.py:357–396` — `@classmethod def from_iso(cls, module, teeth, face_width, bore=None, pressure_angle=20.0, **kwargs)`; docstring at `:369–371` confirms `cls` must be concrete (caller uses `SpurGear.from_iso`) ✓
  - `vibe_cading/mechanical/gears/spur.py:31` — `class SpurGear(Gear)` concrete subclass ✓
  - `vibe_cading/mechanical/joints/snap_fit.py:22` — `class CantileverSnapFit` ✓
  - `vibe_cading/mechanical/joints/snap_fit.py:72` — `def male(self, overlap: float = 1.0) -> cq.Workplane` ✓
  - `vibe_cading/mechanical/joints/snap_fit.py:98` — `def to_cutter(self, profile: ToleranceProfile | None = None) -> cq.Workplane` ✓
  - `vibe_cading/print_settings.py:253` — `def get_profile(name: str | None = None) -> ToleranceProfile` ✓
  - `tools/check_no_main_blocks.py:77` — `roots = [repo_root / "vibe_cading", repo_root / "parts"]` ✓ (examples/ is intentionally out of scope; FR4 needs no CI patch — design correctly states "No change required to this tool")
  - `tools/check_license_headers.py:24` — current tuple is `("vibe_cading/**/*.py", "tools/**/*.py")`; design's proposed widening to add `"examples/*.py"` as a third tuple entry is syntactically sane and matches the cited line ✓
  - `tools/check_license_headers.py:1–15` — module docstring scope-section confirms `parts/` is intentionally NOT walked; adding an `examples/*.py` note in the same patch is consistent ✓
  - `README.md:15` — `## Models` heading ✓
  - `README.md:25` — Models table closes at this line; `---` rule at `:26`; `## Dev Setup` at `:27` ✓ (insertion point between `:26` and `:27` is the correct anchor)
  - `README.md:5` — "It also features practical examples demonstrating how to use these primitives…" — the placeholder language the new `## Examples` section will fulfil ✓
  - `.gitignore:5` — `tmp/` line (design references "around line 6"; minor off-by-one in the description, patch shape unaffected) ✓
  - `.gitignore:11–14` — existing `*.stl`, `*.stp`, `*.step`, `*.svg` globs cover file contents; `examples/build/` directory entry is the design's clarity-add ✓
  - `vibe/INSTRUCTIONS.md` — "Deep-Modules — Dual-Lens Rule" present and matches the design's two-lens framing ✓
  - `vibe/INSTRUCTIONS.md` — "Predicted-Cost Estimation for Non-Blocking Concerns" rule present; design's §Non-Blocking Concerns table satisfies it ✓
  - `.agents/plans/2026-05-15-examples-directory_req.md` FR1–FR14 enumerated; each appears in design Tests `Maps to` column (FR1→row1, FR2→row2, FR3→rows3–6, FR4→row7, FR5→row8, FR6→row9, FR7→row10, FR8→row11, FR9→row12, FR10→row13, FR11→row14, FR12→row15, FR13→rows3+16, FR14→rows6+8+17) ✓

---

## Independent Developer Review (fresh context, 2026-05-17)

- **Verdict:** `APPROVE`

- **Strengths**
  - Each per-script outline in T2–T5 is concrete enough to implement
    in one pass: API call, factory args, host-block dimensions,
    cutter translation, and exported filenames are all pinned with
    no hand-waving. No smuggled implementation decisions detected
    across T1–T12.
  - `screw_cutter.py` outline lands at the most surgical point in the
    library's tolerance contract — explicit
    `get_profile("fdm_standard")` + `fit="clearance"` matches the
    actual `MetricMachineScrew.to_cutter(profile=None, fit: str =
    "clearance")` signature at `vibe_cading/mechanical/screws/metric.py:132`
    and avoids the documented fallback at `:160–161`.
  - Tolerance-profile usage, ISO-gear factory selection
    (`SpurGear.from_iso` — concrete subclass per `base.py:367–370`),
    and `CantileverSnapFit` male/`to_cutter` decomposition are all
    backed by the design's Code-Truth block at file:line; spot-checks
    confirm every cited line.

- **Conditions / required edits:** None.

- **Open concerns** (non-blocking, with predicted costs)
  - `examples/snap_fit_hook.py` host-block dimensions
    (`10 × 10 × 16 mm`) versus cutter bbox (`X ∈ [-1.7, 3.7]`,
    `Y ∈ [-2.7, 2.7]`, `Z ∈ [-1, 13.6]`): cavity is asymmetric in X
    (cutter extends from X=-1.7 to X=3.7 inside host X ∈ [-5, 5]),
    so the cavity does NOT mate with the +X face of the box.
    Live-probe confirms the cut still yields a single solid with
    314 mm³ removed, but the resulting cavity is internal (does
    not breach any host face). This is geometrically valid but
    arguably less educational than a snap-fit cavity that breaks
    the surface. *Predicted cost if challenged post-impl:* one
    `.translate(...)` tweak in the example (≤ 10 min) or a
    docstring sentence clarifying the demonstration intent.
    Non-blocking — the design's outline is internally consistent
    and the file artefacts (hook.step + host.step) satisfy FR14.
  - Test 13's docstring AST audit (FR10) is described in prose
    only — no concrete audit script path is named. The developer
    will need to spin up an `ast.parse` snippet under `tmp/` at
    implementation time. *Predicted cost:* ≤ 15 min to write the
    one-shot audit. Non-blocking.

- **Live-probe outcome** — probed `examples/screw_cutter.py`
  outline (most complex API surface — host-block boolean +
  tolerance-profile + `MetricMachineScrew.from_size`). Probe file:
  `tmp/probe_design_screw_cutter.py` (cleaned up post-run).
  Result: ✓ ran clean in 0.08 s, single solid, 61.09 mm³ removed
  from a 1350 mm³ host, STEP (4.6 KB) + SVG written. Verified
  `cutter.translate((0, 0, 6))` lands the counterbore mouth at
  the top face as the design specifies. Secondary probe of
  `snap_fit_hook.py` outline also ran clean (single solid, 314 mm³
  removed, hook + host bbox checked). Tertiary probe of
  `gear_from_iso.py` outline: build 0.50 s + export 0.83 s = 1.33 s
  total, well under the 10 s NFC runtime budget; STEP 5.5 MB,
  SVG 427 KB.

- **Verification log** — every code/doc claim opened to check
  - `vibe_cading/lego/technic_beam.py:74` — `class LegoTechnicBeam` ✓
  - `vibe_cading/lego/technic_beam.py:107` — `def __init__(self, length_in_studs: int) -> None` ✓
  - `vibe_cading/lego/technic_beam.py:214–217` — `@property def solid(self) -> cq.Workplane` ✓
  - `vibe_cading/mechanical/screws/metric.py:28` — `class MetricMachineScrew` ✓
  - `vibe_cading/mechanical/screws/metric.py:54–55` — `@classmethod def from_size(cls, size, length, head_type="socket", drive_type="hex")` ✓
  - `vibe_cading/mechanical/screws/metric.py:132` — `def to_cutter(self, profile=None, fit: str = "clearance") -> cq.Workplane` ✓ (matches design's explicit `fit="clearance"`)
  - `vibe_cading/mechanical/screws/metric.py:160–161` — `prof = profile if profile is not None else get_profile()` ✓ (design correctly hard-codes `get_profile("fdm_standard")` instead of relying on this fallback)
  - `vibe_cading/mechanical/gears/base.py:357–396` — `@classmethod def from_iso(cls, module, teeth, face_width, bore=None, pressure_angle=20.0, **kwargs)`; abstract-`cls` rejection at `:382–388` (`ISO_STANDARD_MODULES` membership check) ✓
  - `vibe_cading/mechanical/gears/spur.py:31` — `class SpurGear(Gear)` concrete subclass ✓
  - `vibe_cading/mechanical/joints/snap_fit.py:22` — `class CantileverSnapFit` ✓
  - `vibe_cading/mechanical/joints/snap_fit.py:72` — `def male(self, overlap: float = 1.0) -> cq.Workplane` ✓
  - `vibe_cading/mechanical/joints/snap_fit.py:98` — `def to_cutter(self, profile: ToleranceProfile | None = None) -> cq.Workplane` ✓
  - `vibe_cading/print_settings.py:253` — `def get_profile(name: str | None = None) -> ToleranceProfile` ✓ (returns the `ToleranceProfile` that `MetricMachineScrew.to_cutter(profile=...)` accepts — type round-trip confirmed by live probe)
  - `tools/check_no_main_blocks.py:77` — `roots = [repo_root / "vibe_cading", repo_root / "parts"]` ✓ (examples/ correctly out of scope per FR4; design's "No change required to this tool" claim verified)
  - `tools/check_license_headers.py:24` — current tuple `("vibe_cading/**/*.py", "tools/**/*.py")`; design's proposed third entry `"examples/*.py"` is syntactically correct ✓ (the docstring at `:1–15` also documents the scope and the design's same-patch update keeps them in sync)
  - `README.md:5` — "It also features practical examples demonstrating how to use these primitives…" — the placeholder language the new `## Examples` section will fulfil ✓
  - `README.md:25–27` — `## Models` table closes at line 25, `---` rule at `:26`, `## Dev Setup` at `:27`; design's insertion point between `:26` and `:27` is correct and the cross-reference paragraph is paste-ready (table + `python3 examples/lego_technic_beam.py` run command both literal) ✓
  - `.gitignore:5` — `tmp/` line; design's "add `examples/build/` directly under" patch is mechanically clear (TL review already noted minor off-by-one in "around line 6" wording — patch shape unaffected) ✓
  - `.gitignore:11–14` — existing `*.step`, `*.svg` globs already cover file contents; `examples/build/` directory entry is the design's clarity-add ✓
  - Path-printing convention `str(path.resolve())` — applied consistently across the design's per-script outlines and called out in Dialog Round 3 ✓
  - Line-count budget feasibility (≤80 target, ≤120 cap): screw_cutter probe body is ~30 lines of code; adding AGPLv3 header + docstring + `if __name__` block stays well under 80. Other three scripts are simpler. ✓
  - README cross-reference paste-ability: design supplies the literal markdown block (lines 44–61), including table headings, all four example rows, and the run command. Anchor location is also literal (between current `:26` and `:27`). ✓

---

## Implementation Status
<!-- Populated by @developer at the start of Step 5 Phase A. -->
- [x] All Implementation Plan tasks completed (every `[ ]` above marked `[x]`)
- [x] Test suite executed — result: **171 passed, 2 xfailed, 7 warnings in 3.77s** (no regressions; `python3 -m pytest tests/ -v`). All four example scripts smoke-ran exit 0 with file artefacts under `examples/build/<name>/`: `lego_technic_beam.py` 2.4 s, `screw_cutter.py` 1.5 s, `gear_from_iso.py` 3.2 s, `snap_fit_hook.py` 1.5 s — all well within the 10 s NFC budget. T13 docstring AST audit, T12 import audit, T16 LegoTechnicBeam grep audit all pass; `git check-ignore examples/build/` exits 0; `grep -c "examples" build.toml` = 0; license-header negative spot-check confirms the widened gate flags missing headers in `examples/`.
- [x] No new linter / static-check errors (`flake8 examples/` clean; `python3 tools/check_license_headers.py` exits 0 with the new `examples/*.py` glob; `python3 tools/check_no_main_blocks.py` exits 0 — `examples/` remains intentionally out of scope per FR4).
- Developer note: Implementation followed the design's per-script outlines verbatim. No deviations. All four scripts came in well under the 80-line target (55, 58, 73, 74 lines including AGPLv3 header + module docstring + `__main__` block). The Developer-reviewer's non-blocking concern about the snap-fit cavity not breaching a host face was checked: with `host = box(10, 10, 16)` centred on (X, Y) and the cutter's `_CUTTER_ENTRY_OVERLAP=1.0` punching through Z=0, the cavity DOES open cleanly through the host's bottom face — the cavity is functionally accessible for the male hook to be inserted from below, consistent with the joint's documented geometry (base at Z=0, hook extending into +Z). Comment in the script documents this. README cross-reference inserted at the design's specified anchor (between `## Models`'s closing `---` and `## Dev Setup`). Per `tools/check_license_headers.py:1–18` widening, both the docstring and the glob tuple were updated in one patch (T7).

---

## Post-Implementation Sign-Off

### TL Review
- [x] **TL sign-off** — implementation matches design; tests pass; no unintended scope creep; strict-ops pass
- TL review notes: See `## TL Review (Step 5 Phase B, 2026-05-17)` below.

### Domain Expert Review *(domain integrity gate is NO — skipped)*
- [ ] **Domain expert sign-off** — N/A
- Domain expert review notes: N/A (gate NO)

### Step 4 — Human gate (pre-implementation)
- [x] **Human approved 2026-05-17** (PM-relayed from user "Approve" — authorises dispatch of developer subagent for Step 5 Phase A)

### Human Final Approval
- [x] **Human approved** for merge / release (2026-05-19, PM-relayed from user "Approve")
- Human notes: Smoke re-verified post LegoTechnicBeam Round-6 hole-axis correction — `examples/lego_technic_beam.py` produces single solid with Z-axis holes, all four scripts exit 0 against the corrected library state. Visual-contract SVG NOT added — task falls under the commit-905ab19 carve-out for "additive-only changes that don't alter visual outcome" (examples/ adds demonstration scripts, not a new model class).

---

## TL Review (Step 5 Phase B, 2026-05-17)

- **Verdict:** `APPROVE`

- **Strengths**
  - Every T1–T12 task in the Implementation Plan is `[x]` AND the on-disk artefact at the cited location matches the design's per-script outline verbatim — no smuggled deviations, no partial implementations. The four scripts are 55 / 73 / 58 / 74 lines (well under the 80-line target, hard cap 120), import only `pathlib` + `cadquery` + `vibe_cading.*` per FR9, and each carries the AGPLv3 header, module docstring with literal run command + output path, and `if __name__ == "__main__":` block per FR4 / FR8 / FR10.
  - Round-1 structural decision held: no `examples/_common.py` was introduced. Each script carries the defensive in-script comment pointing future contributors to design Round 1, providing the second-line-of-defence the §Known Risks table specified. Per-script `str(path.resolve())` (Round 3) and explicit `get_profile("fdm_standard")` + `fit="clearance"` (Round 4) are both literal in the code — no fallback-chain regressions, no `as_posix()` calls (it appears only in comments documenting the override path).
  - Strict-ops pass cleanly: `tools/check_license_headers.py` widened glob to `examples/*.py` (`:29`) with docstring update (`:1–14`) and exits 0; `tools/check_no_main_blocks.py` scope unchanged (`roots = [vibe_cading, parts]` at `:77`) and exits 0 — confirming FR4's "examples are exempt" property is preserved. Test suite: **171 passed, 2 xfailed in 3.14 s** — matches the pre-impl baseline exactly. All four scripts smoke-run in 1.33–2.56 s (NFC budget 10 s).

- **Conditions / required edits:** None.

- **Open concerns** (non-blocking; predicted-cost stated in project units)
  - The README `## Examples` section was inserted at the exact anchor specified (between `## Models`'s closing `---` and `## Dev Setup` at the new `:27`), with the literal table and `python3 examples/lego_technic_beam.py` run command. No drift from design. *Predicted cost if a contributor wants curated views later:* ≤30 min — add a single sentence pointing at `tools/preview.py`. (Already deferred per §Known Risks.)
  - The Independent Developer Reviewer's pre-impl concern about `snap_fit_hook.py` host-block cavity not breaching a face was resolved at impl-time by the cutter's `_CUTTER_ENTRY_OVERLAP=1.0` punching through Z=0; the in-script comment at `:46–47` documents this. The cavity opens cleanly through the host bottom — geometrically valid and educational. *Predicted cost if challenged post-release:* ≤10 min docstring tweak or `.translate()` adjustment.
  - `examples/build/` is gitignored (`.gitignore:8`) and `git status --porcelain examples/build/` is empty after running all four scripts. The directory entry sits in its own labelled block above the broad `*.step` / `*.svg` globs — clearer for contributors learning the layout. *Predicted cost if removed accidentally:* contributor commits 10 binary artefacts on next push; ≤15 min reviewer time to revert.

- **Verification log** — every file opened, every command run
  - `examples/lego_technic_beam.py` opened (55 lines): AGPLv3 header `:1–14` ✓; module docstring `:15–29` with literal run command + `examples/build/lego_technic_beam/` path ✓; `from vibe_cading.lego.technic_beam import LegoTechnicBeam` `:34` ✓; `LegoTechnicBeam(length_in_studs=5)` `:39` ✓; output under `examples/build/lego_technic_beam/` `:42` ✓; `str(step_path.resolve())` `:54` ✓.
  - `examples/screw_cutter.py` opened (73 lines): header `:1–14` ✓; docstring `:15–30` ✓; imports `MetricMachineScrew` `:35`, `get_profile` `:36` ✓; `MetricMachineScrew.from_size("M3", length=10, head_type="socket")` `:50` ✓; `screw.to_cutter(profile=get_profile("fdm_standard"), fit="clearance")` `:51` ✓ (hard-coded `"fdm_standard"` per Round 4); host `15×15×6` cq box `:43` ✓; cutter translated `(0,0,6)` `:57` ✓; `str(path.resolve())` `:72–73` ✓.
  - `examples/gear_from_iso.py` opened (58 lines): header `:1–14` ✓; docstring `:15–30` ✓; `from vibe_cading.mechanical.gears.spur import SpurGear` `:35` ✓ (concrete subclass, not abstract `Gear`); `SpurGear.from_iso(module=1.0, teeth=20, face_width=5.0)` `:42` ✓; `str(path.resolve())` `:57–58` ✓.
  - `examples/snap_fit_hook.py` opened (74 lines): header `:1–14` ✓; docstring `:15–29` ✓; `CantileverSnapFit(length=10, hook_depth=1.5)` `:39` ✓; `joint.male()` `:42` + `joint.to_cutter()` `:51` ✓; **two STEP files** `hook.step` + `host.step` `:57, :59` per FR14 ✓; four absolute paths printed `:71–74` ✓.
  - `ls examples/` — exactly the four scripts, no `_common.py`, no `__init__.py` (FR9 forbids subpackage imports). ✓
  - `tools/check_license_headers.py` opened: docstring `:1–14` now mentions `examples/*.py` as walked surface; glob tuple `:29` is `("vibe_cading/**/*.py", "tools/**/*.py", "examples/*.py")` — non-recursive `examples/*.py` per design. ✓
  - `tools/check_no_main_blocks.py` opened: `roots = [repo_root / "vibe_cading", repo_root / "parts"]` `:77` — unchanged, `examples/` intentionally out of scope per FR4. ✓
  - `.gitignore` opened: `examples/build/` at `:8` under labelled comment `:7`. ✓
  - `README.md:15–46` opened: new `## Examples` section at `:27–43` between `## Models` table closing rule (`:25–26`) and `## Dev Setup` at `:46`; table lists all four scripts with literal filenames; literal run command `python3 examples/lego_technic_beam.py` at `:42`. ✓
  - `build.toml`: `grep -c "examples" build.toml` returned `0` — no `[[build]]` entry for any example script (FR12). ✓
  - `python3 tools/check_license_headers.py` → exit 0, "All Python files have the AGPLv3 license header." ✓
  - `python3 tools/check_no_main_blocks.py` → exit 0, "OK: no `if __name__ == \"__main__\":` blocks under vibe_cading/ or parts/." (confirms `examples/*.py` with main blocks does NOT trip the gate; scope correctly preserved) ✓
  - Smoke run all four scripts (after wiping `examples/build/`):
    - `lego_technic_beam.py` → exit 0 in 1.85 s; STEP + SVG written to `examples/build/lego_technic_beam/` ✓
    - `screw_cutter.py` → exit 0 in 1.35 s; STEP + SVG written ✓
    - `gear_from_iso.py` → exit 0 in 2.56 s; STEP + SVG written ✓
    - `snap_fit_hook.py` → exit 0 in 1.33 s; four files written (`hook.step`, `hook.svg`, `host.step`, `host.svg`) ✓
    - All four under 10 s NFC budget; total elapsed ~7.1 s for the full quartet ✓
  - `find examples/build -type f | sort` → 10 files: 5 STEP + 5 SVG, one per artefact, all under the expected `examples/build/<name>/` paths ✓ (FR5, FR14)
  - `git status --porcelain examples/build/` → empty (no tracked entries) ✓ (FR6)
  - `git check-ignore examples/build/` → exit 0 (path is ignored) ✓
  - `grep -nE "^(from|import) " examples/*.py` — every script imports only `pathlib.Path`, `cadquery as cq`, and one or two `vibe_cading.*` symbols. No `parts.*`, `experiments.*`, `tools.*`, or third-party packages. ✓ (FR9)
  - `grep -nE "as_posix" examples/*.py` — matches only on the documentation comment line `# str() = native separators; switch to .as_posix() if cross-platform paste-fidelity matters.` in all four scripts; no actual `.as_posix()` calls. ✓ (Round 3)
  - `python3 -m pytest tests/` → **171 passed, 2 xfailed, 7 warnings in 3.14 s** — matches Implementation Status baseline exactly, no new failures. ✓
  - Workspace hygiene: `tmp/` contains expected scratch (probe files from prior sessions, all gitignored); no production artefacts in repo root that don't belong. ✓

