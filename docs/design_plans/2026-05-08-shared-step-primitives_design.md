# Design: Shared STEP-analysis primitives for tools/

## Meta
- **Requirements ref**: `.agents/plans/2026-05-08-shared-step-primitives_req.md`
- **Requester role**: @admin
- **Date**: 2026-05-09
- **Dialog rounds**: 2

---

## Objective

Concentrate the duplicated STEP-load + OCP helper code that today appears verbatim across seven `tools/*.py` CLIs into a single thin module (`tools/step_primitives.py`), so each tool delegates to one shared surface for `vec3()`, `face_area()`, and STEP loading — without changing any tool's `--json` wire format and without compromising the CadQuery-agnostic property of `tools/engine_api/extractor.py`.

## Architecture / Approach

### Approach chosen

**Module location.** Flat `tools/step_primitives.py` (sibling to `tools/engine_api/`, not inside it). Rationale: the new module imports OCP + CadQuery directly; placing it inside `tools/engine_api/` — even as a separate file — visually couples it to a package whose load-bearing property (`extractor.py` is pure-AST and CadQuery-agnostic per `.agents/plans/engine-api-json.md` §1) is preserved today by the package having no CadQuery imports anywhere. A flat sibling preserves that property mechanically: a future contributor reading `tools/engine_api/__init__.py` will not see any CadQuery import and cannot accidentally introduce one via re-export. The structural-review TL recommendation also explicitly described this as "sibling to `tools/engine_api/`".

**Public API of `tools/step_primitives.py`** (committed contract — Developer fills in bodies):

```python
from typing import Any, NamedTuple
import cadquery as cq

class LoadedStep(NamedTuple):
    """Triple returned by load_step() so each consumer reaches its preferred shape without re-deriving."""
    wp: cq.Workplane           # for tools that call .faces().vals(), .solids().vals()
    shape: cq.Shape            # for tools that call .BoundingBox(), .wrapped
    occ_compound: Any          # = shape.wrapped — expected type OCP.TopoDS.TopoDS_Compound (may also be TopoDS_Shape depending on STEP content); for tools that pass to TopExp_Explorer / BRepGProp

def load_step(path: str | Path) -> LoadedStep: ...
    # Raises StepLoadError (an OSError subclass — sits in the standard I/O-error hierarchy
    # alongside FileNotFoundError, so consumer `except OSError:` blocks catch it cleanly) on:
    #   - path does not exist
    #   - cq.importers.importStep returns an empty / shape-less workplane
    # Wraps the underlying cq.importers call exactly once. No caching in this refactor.

class StepLoadError(OSError):
    """Raised by load_step() with a contributor-friendly message; CLI mains catch + sys.exit(1).

    Parent class is OSError (not RuntimeError) so that consumers' broad `except OSError:`
    blocks for filesystem failures catch this error cleanly. FileNotFoundError is itself an
    OSError subclass, placing StepLoadError in the standard I/O-error hierarchy.
    """

def vec3(gp_obj) -> dict:
    """{x,y,z} dict, each value rounded to 4 decimals. Accepts gp_Pnt, gp_Dir, gp_Vec."""

def face_area(occ_face) -> float:
    """Surface area via BRepGProp.SurfaceProperties_s. Returns raw Mass() (un-rounded; callers round)."""
```

The signatures are byte-for-byte compatible with the seven existing `_vec3` / `_face_area` definitions (verified by reading them — all return identical structure with identical rounding precision). `vec3()` rounds to 4 decimals; `face_area()` returns un-rounded so callers that round to different precision (e.g. `face_catalog.py` rounds to 4) keep their existing JSON output.

**Per-tool delegation plan.**

| Tool | Today's local helpers | After refactor |
|------|----------------------|----------------|
| `face_catalog.py` | `_vec3`, `_face_area`, `_face_bbox`, inline `cq.importers.importStep` | imports `vec3`, `face_area`, `load_step` from `step_primitives`; **keeps** local `_face_bbox` (single-consumer; see below) |
| `hole_finder.py` | `_vec3`, `_face_area`, `_coaxial`, inline import | imports `vec3`, `face_area`, `load_step`; **keeps** local `_coaxial` (single-consumer) |
| `face_distances.py` | `_vec3`, `_face_area`, `_dot`, `_dominant_axis`, inline import | imports `vec3`, `face_area`, `load_step`; **keeps** local `_dot` and `_dominant_axis` (algorithmic, not boilerplate) |
| `step_summary.py` | `_count_shapes`, inline import | imports `load_step`; **keeps** local `_count_shapes` (single-consumer; see below) |
| `section_slicer.py` | inline import only | imports `load_step` only (no `_vec3` / `_face_area` use) |
| `boolean_diff.py` | `_load_step`, `_volume`, `_has_solid`, inline import | imports `load_step`; **deletes** local `_load_step`; **keeps** `_volume` / `_has_solid` (boolean-diff-specific) |
| `step_preview.py` | inline import only | imports `load_step` only |

**Single-consumer helpers — explicit decision (resolves Open Question 3).**

Applying the structural-optimization skill's one-vs-two-adapter diagnostic:

- `_face_bbox` (in `face_catalog.py` only): one consumer. Speculative move. **Stays in place.** Predicted cost if a second consumer materializes later: ~5 lines of copy-paste duplication for one cycle until a second adapter forces the move — acceptable.
- `_coaxial` (in `hole_finder.py` only): one consumer. Algorithm-shaped (line-distance computation), not OCP boilerplate. **Stays in place.**
- `_count_shapes` (in `step_summary.py` only): the requirements artifact and the structural review both speculated a second consumer is "imminent" (would help `face_catalog`, `face_distances`). Reading those tools' actual code — neither calls `TopExp_Explorer` today; both iterate `wp.faces().vals()` directly. The "imminent second consumer" is hypothetical, not load-bearing. **Stays in place.** If a future tool needs it, the move is a 5-line lift-and-shift.

This decision deliberately stays surgical: the refactor's job is collapsing the *verified-duplicated* surface (`_vec3` ×3, `_face_area` ×3, `cq.importers.importStep` ×7), not building a STEP-handling framework on speculation.

**STEP-load error reporting.** Today none of the seven tools check whether `path` exists before calling `cq.importers.importStep`; the resulting OCCT error is opaque. `load_step()` adds a single `Path.exists()` check upfront with a `StepLoadError` carrying the offending path, plus a post-import check that `wp.val()` returns a non-`None` shape. The CLI `main()` of each consuming tool catches `StepLoadError`, prints the message to stderr, and exits 1.

### Alternatives rejected

1. **Place the module inside `tools/engine_api/step_primitives.py`.** Rejected. Even with the file mechanically isolated, a contributor adding a future helper to `tools/engine_api/__init__.py` could re-export from `step_primitives.py` and silently introduce CadQuery into the engine_api package's import graph — breaking `extractor.py`'s no-CadQuery property without any visible code change in `extractor.py` itself. The structural-review explicitly flagged this risk. A flat-`tools/` location makes the contract enforceable by inspection.

2. **New `tools/step_lib/` package.** Rejected. We are consolidating ~3 small functions and one load helper across 7 tools — a package directory is over-engineering. The single-file module is the right granularity; if future expansion (caching layer, URI translator) justifies a package, the migration is a `git mv` + import-path bump, no API change.

3. **Return raw `TopoDS_Shape` from `load_step`.** Rejected. Four of the seven tools want CadQuery's `Workplane.faces().vals()` traversal; forcing them to re-wrap a `TopoDS_Shape` back into a `cq.Workplane` would *add* boilerplate at every call-site, not remove it. The `LoadedStep` named-tuple gives every consumer its preferred handle.

4. **Return `cq.Workplane` only; let consumers compute `.val()` and `.wrapped`.** Rejected as a weaker version of the above. Five of the seven tools immediately call `wp.val()` after import, and three then call `.wrapped`. Returning the triple costs nothing (named-tuple is zero-cost) and removes the same five lines of `wp = ...; shape = wp.val(); occ = shape.wrapped` that would otherwise duplicate.

5. **Move `_face_bbox` / `_coaxial` / `_count_shapes` into the shared module proactively.** Rejected. One-vs-two-adapter diagnostic fails for all three (one consumer each, no concrete second-consumer pending). Moving them speculatively widens the shared API surface and forces the Developer to write tests for code paths that have one call-site in the entire repo — the wrong cost-benefit. See *Approach chosen* for the full diagnostic.

## Data & Interface Contracts

*Domain integrity gate is NO per requirements; this section is intentionally empty.*

## Implementation Plan

Atomic tasks for the Developer. Tasks T1–T3 land the shared module; T4–T10 migrate one consumer at a time so each migration can be byte-diffed against its baseline JSON output independently. T11 is sign-off.

| ID | Task | Files touched |
|----|------|---------------|
| **T1** | Create `tools/step_primitives.py` with the AGPLv3 header (copy from `tools/face_catalog.py`), module docstring, `LoadedStep` NamedTuple, `StepLoadError`, `load_step()`, `vec3()`, `face_area()`. Add the OCP imports (`OCP.BRepGProp`, `OCP.GProp`) needed for `face_area`. No CLI entry-point — pure library module. | `tools/step_primitives.py` (new) |
| **T2** | Capture **baseline `--json` outputs** for all seven tools against `valve_cap.step` into a fresh `tmp/step_primitives_baseline/` directory. Each tool that supports `--json` writes its full JSON to a file; `step_preview.py` and `section_slicer.py` (which write SVGs) get their `WROTE …` stdout captured. This is the regression-comparison ground truth. Baselines under `tmp/step_primitives_baseline/` MUST NOT be staged or committed; per `vibe/INSTRUCTIONS.md` §2 use `git add <specific_file>` only. | `tmp/step_primitives_baseline/*.json`, `*.txt` (gitignored) |
| **T3** | Run `flake8 tools/step_primitives.py` and `python3 -m py_compile tools/step_primitives.py`. Verify the AGPLv3 header passes `tools/check_license_headers.py`. | (verification only) |
| **T4** | Migrate `tools/face_catalog.py`: delete `_vec3` and `_face_area`; replace inline `cq.importers.importStep(...)` with `load_step(...)`; import from `tools.step_primitives`. Keep `_face_bbox` local. Re-run against `valve_cap.step --json`; verify `diff -u baseline post` returns no output AND `cmp -s baseline post` exits 0 — both conditions required. Any diff is a fail. | `tools/face_catalog.py` |
| **T5** | Migrate `tools/hole_finder.py`. Same pattern. Keep `_coaxial` local. Verify `diff -u baseline post` returns no output AND `cmp -s baseline post` exits 0 — both conditions required. Any diff is a fail. | `tools/hole_finder.py` |
| **T6** | Migrate `tools/face_distances.py`. Keep `_dot` and `_dominant_axis` local (algorithmic helpers, not OCP boilerplate). Verify `diff -u baseline post` returns no output AND `cmp -s baseline post` exits 0 — both conditions required. Any diff is a fail. | `tools/face_distances.py` |
| **T7** | Migrate `tools/step_summary.py`. Keep `_count_shapes` local. Verify `diff -u baseline post` returns no output AND `cmp -s baseline post` exits 0 — both conditions required. Any diff is a fail. | `tools/step_summary.py` |
| **T8** | Migrate `tools/section_slicer.py`. Replace inline import with `load_step`. Verify `diff -u baseline post` returns no output AND `cmp -s baseline post` exits 0 on the captured `WROTE …` stdout AND on a spot-check generated SVG — both conditions required for each comparison. Any diff is a fail. | `tools/section_slicer.py` |
| **T9** | Migrate `tools/boolean_diff.py`. Delete local `_load_step`. Replace with shared `load_step`. Run `boolean_diff.py valve_cap.step valve_cap.step` (self-diff: ref_volume == cand_volume, jaccard == 1.0); verify `diff -u baseline post` returns no output AND `cmp -s baseline post` exits 0 — both conditions required. Any diff is a fail. | `tools/boolean_diff.py` |
| **T10** | Migrate `tools/step_preview.py`. Replace inline import with `load_step`. Verify `diff -u baseline post` returns no output AND `cmp -s baseline post` exits 0 on captured stdout AND on one spot-check SVG — both conditions required for each comparison. Any diff is a fail. | `tools/step_preview.py` |
| **T11** | Run `flake8` over all eight modified files. Run `tools/check_license_headers.py`. Verify all baselines from T2 still match (full re-run). Stage with `git add` per file (NEVER `git add .`). Hand control back to TL for post-implementation review. | (verification only) |

**Notes for the Developer.**

- Do NOT widen the shared module's API beyond `load_step`, `LoadedStep`, `StepLoadError`, `vec3`, `face_area`. If you find yourself wanting to add a sixth helper, escalate — it indicates either a missed duplicate or a scope-creep candidate, both of which need a TL decision before code goes in.
- The `valve_cap.step` fixture in the repo root is the canonical regression target. Do not introduce a new fixture STEP under `tmp/` for this refactor.
- After T1, the module is *unused* by anyone; that is expected. T4 is the first integration.
- All migrations preserve the function bodies' rounding precision (`vec3` rounds to 4; `face_area` does not round, callers do). Check the diff tooling if a JSON byte-diff appears — almost certainly a precision drift, not a logic bug.

## Tests

The repo does not ship a `tests/` tree. The verification strategy is **byte-level diff of `--json` output between the pre-refactor baseline and the post-refactor run** for every tool, executed by the Developer as part of T2 / T4–T10 / T11 in the Implementation Plan above. Plus targeted negative-path checks for the new error reporting in `load_step`.

| # | Test description | Expected assertion | File / location | Maps to |
|---|------------------|--------------------|-----------------|---------|
| 1 | Baseline capture: run every tool that supports `--json` against `valve_cap.step` *before* any tool is migrated; persist outputs under `tmp/step_primitives_baseline/`. | All seven tools produce non-empty output. Files persisted. | `tmp/step_primitives_baseline/{face_catalog,hole_finder,face_distances,step_summary,boolean_diff_self}.json` plus stdout captures for `section_slicer` and `step_preview` | R4 |
| 2 | After-migration regression: re-run every tool with the same flags; compare each output against its baseline. | `diff -u baseline post` returns no output AND `cmp -s baseline post` exits 0 — both conditions required. Any diff is a fail. | (manual diff during T4–T10) | R2, R4 |
| 3 | `tools/step_primitives.py` exists, defines `load_step`, `LoadedStep`, `StepLoadError`, `vec3`, `face_area`. | `python3 -c "from tools.step_primitives import load_step, LoadedStep, StepLoadError, vec3, face_area"` exits 0. (Run via a `tmp/verify_imports.py` script per the *no inline-code-in-shell* rule.) | `tmp/verify_imports.py` | R1 |
| 4 | `vec3()` round-trip on a known `gp_Pnt`: pass `gp_Pnt(1.234567, 2.345678, 3.456789)`; expect `{"x": 1.2346, "y": 2.3457, "z": 3.4568}`. | Exact match. | `tmp/test_vec3.py` (one-off probe; documents the rounding contract) | R1 |
| 5 | `face_area()` against a known `valve_cap.step` face: load the STEP, pick face index 0 (planar), compare against the value present in the pre-refactor `face_catalog.py --json` baseline. | Match to 4 decimals. | `tmp/test_face_area.py` (one-off probe) | R1 |
| 6 | `load_step("does_not_exist.step")` raises `StepLoadError` with a message containing the path. | Exception class + message check. | `tmp/test_load_step_missing.py` (one-off probe) | R3 |
| 7 | `load_step()` on an empty/zero-byte `.step` file (create one in `tmp/`) raises `StepLoadError`. | Exception class. | `tmp/test_load_step_empty.py` (one-off probe) | R3 |
| 8 | `load_step()` against `valve_cap.step` returns `LoadedStep` with `wp` non-empty (`.faces().vals()` non-empty), `shape` non-`None`, `occ_compound` non-`None`. | All three handles populated. | `tmp/test_load_step_happy.py` (one-off probe) | R3 |
| 9 | No new third-party imports introduced by `tools/step_primitives.py`: only `cadquery`, `OCP.*`, stdlib. | `grep -E "^import |^from " tools/step_primitives.py` shows only those three sources. | (manual inspection during T3) | R6 |
| 10 | All seven consuming tools no longer define a local `_vec3`, `_face_area`, or call `cq.importers.importStep` directly (search confirms no duplicates remain). | `grep -nE "(def _vec3|def _face_area|cq.importers.importStep)" tools/{face_catalog,hole_finder,face_distances,step_summary,section_slicer,boolean_diff,step_preview}.py` returns zero matches. | (manual inspection during T11) | R2 |
| 11 | `tools/step_primitives.py` carries the AGPLv3 header. | `tools/check_license_headers.py` passes. | (verification during T3) | R5 |

**Mapping summary.** R1 → tests 1, 3, 4, 5. R2 → tests 2, 10. R3 → tests 6, 7, 8. R4 → tests 1, 2. R5 → test 11. R6 → test 9. Every requirement is covered.

**Negative-path probes go under `tmp/`** per the workspace-hygiene rule. They are one-off scripts the Developer writes, runs, observes pass, then leaves under `tmp/` (gitignored — they document the contract for future contributors but do not pollute the repo).

## Success Criteria

1. **Zero behavior change.** All seven tools produce byte-identical `--json` (or stdout for non-JSON tools) output against `valve_cap.step` before and after the refactor (Implementation Plan T2 baseline ↔ T11 final re-run).
2. **Duplication eliminated.** `grep` confirms no `def _vec3(...)`, `def _face_area(...)`, or direct `cq.importers.importStep(...)` call remains in `tools/face_catalog.py`, `tools/hole_finder.py`, `tools/face_distances.py`, `tools/step_summary.py`, `tools/section_slicer.py`, `tools/boolean_diff.py`, `tools/step_preview.py`. Every match should be in `tools/step_primitives.py` only.
3. **Engine-API invariant preserved.** `tools/engine_api/extractor.py` and `tools/engine_api/__init__.py` are unchanged. `grep -r "cadquery\|import cq\|from OCP" tools/engine_api/` returns zero matches (today this is true — the success bar is keeping it true).
4. **Hygiene gates pass.** `flake8 tools/step_primitives.py tools/face_catalog.py tools/hole_finder.py tools/face_distances.py tools/step_summary.py tools/section_slicer.py tools/boolean_diff.py tools/step_preview.py` exits 0. `tools/check_license_headers.py` passes. `python3 -m py_compile` on each modified file exits 0.
5. **Error-reporting contract holds.** `load_step("nonexistent.step")` raises `StepLoadError` with the offending path in the message; CLI `main()` of each consuming tool catches it and exits 1 with the message on stderr (verifiable by running e.g. `python3 tools/face_catalog.py /tmp/nope.step` and observing exit code 1 + stderr text).
6. **No engine-API JSON wire-format change.** `python3 tools/gen_engine_api.py --check` exits 0 (the `tools/` refactor must not perturb `engine_api.json` in any way). This is a defensive check — the refactor does not touch `models/`, so this should pass trivially, but failure would indicate an unintended import-side-effect.

## Out of Scope

*Mirrored from `_req.md` "Out of Scope". Additions surfaced in dialog appended below.*

## Known Risks & Mitigations

| Risk | Likelihood | Predicted cost if it materializes | Mitigation |
|------|-----------|-----------------------------------|-----------|
| **R-A: `--json` regression in any of the seven tools.** A subtle precision drift, ordering change, or NaN-handling difference between the new `vec3` / `face_area` and a tool's old local helper produces a one-byte JSON diff that breaks downstream consumers (the platform's MCP `query_engine_api` does not consume these CLIs today, but human contributors and CI scripts diff JSON outputs against checked-in baselines). A separate but related concern — `StepLoadError` exception-class drift — is mitigated by typing the class as an `OSError` subclass (see *Public API*) so that consumer `except OSError:` blocks catch it in the standard I/O-error hierarchy rather than leaking a stack trace. | Medium | One re-validation cycle per tool that diffs (~5 min each, 7 tools = 35 min); user trust in the refactor. | Implementation Plan T2 captures byte-exact baselines *before* any migration. T4–T10 each diff against the baseline (`diff -u` empty AND `cmp -s` exit 0, both required). The refactor is gated on byte-zero diff per tool — fail-closed by construction. |
| **R-B: Compromise of `tools/engine_api/extractor.py`'s CadQuery-agnostic invariant.** The new module imports CadQuery + OCP. If sibling-located inside `tools/engine_api/`, a future contributor adds a re-export to `tools/engine_api/__init__.py` (innocently) and now `import tools.engine_api` pulls in CadQuery — silently breaking the invariant declared in `.agents/plans/engine-api-json.md` §1. | Low (with the chosen flat location) | High — the platform's MCP integration depends on `extractor.py` being importable in environments without CadQuery (per `engine-api-json.md`). Cost of regression: a coordinated platform-repo bump + the loss of the stated extractor property. | Module is placed at flat `tools/step_primitives.py` (NOT inside `tools/engine_api/`). Success Criterion #3 adds a defensive grep gate (`grep -r "cadquery\|from OCP" tools/engine_api/` returns zero matches) that the Developer re-runs at T11. |
| **R-C: Helper name collision or signature drift between the new shared module and a consuming tool.** If a consuming tool retains a local `_vec3` (for any reason) AND imports `vec3` from the shared module, Python silently uses whichever was bound last — the call-site that "looks like" it uses the shared helper actually still uses the local one. | Low | Medium — the duplicated code remains, no observable test failure (output is byte-identical because both implementations are byte-identical), the refactor's stated benefit is silently undelivered. | Test #10 in the Tests table is a hard `grep`-based gate: if any consuming tool retains a `def _vec3` after migration, the refactor is incomplete. The Developer must run this grep at T11 before sign-off. |
| **R-D: `LoadedStep` triple is over-broad — consumers reach into fields they shouldn't.** Returning `(wp, shape, occ_compound)` makes all three handles available everywhere, encouraging future tools to mix Workplane/Shape/OCC access patterns and undo the consolidation. | Low | Low — the named-tuple is a contract artifact; future drift is caught at code-review time, not runtime. Cost of a regression: one PR-review cycle to refactor a misused field. | Module docstring documents the intended use of each field. The decision to expose all three is grounded in the empirical fact that all three are *already* derived independently across the seven tools today (`step_summary` derives `occ_compound` itself; `boolean_diff` derives `shape`). The named-tuple consolidates the existing surface; it does not invent it. |
| **R-E: Future URI translation re-touches all seven tools.** The requirements artifact's Known Domain Constraints note a possible future URI-based return shape for MCP-consumed tools. If `load_step` does not accept a URI today, a future MCP enablement effort revisits all seven call-sites. | Low (deferred) | Medium — re-touching seven tools is a duplicate of the work this refactor is doing. | `load_step(path: str | Path)` accepts `str` today. A future URI-aware version replaces the implementation; the `str` parameter shape stays the same. The seven call-sites pass through whatever string they get from `argparse`. The API design does not preclude URI translation — this is the requirements artifact's stated goal for the open question on URI handling, and the chosen design satisfies it. |

---

## Design Dialog Log

<!-- Round-by-round record of the TL ↔ Admin (requester) co-design loop. -->

### Round 1 — TL proposal (2026-05-09)

**Author:** TL subagent (Opus 4.7, 1M context).

**Summary of proposal.** See *Objective*, *Architecture / Approach*, *Implementation Plan*, *Tests*, *Success Criteria*, and *Known Risks & Mitigations* above — fully populated this round. The shape: a single flat module `tools/step_primitives.py` exposing `load_step` (returning a `LoadedStep` named-tuple of `(wp, shape, occ_compound)`), `vec3`, `face_area`, plus a `StepLoadError` for missing/empty STEP files. Seven tools migrate one at a time (T4–T10), each gated on byte-zero `--json` diff against pre-refactor baselines.

**Resolution of Open Questions from `_req.md`.**

1. **Module location.** *Decision:* flat `tools/step_primitives.py`, NOT inside `tools/engine_api/`. *Rationale:* the new module imports CadQuery + OCP; the engine_api package's load-bearing CadQuery-agnostic property (per `.agents/plans/engine-api-json.md` §1) is preserved today by the package having no CadQuery imports anywhere in its file tree. A flat sibling location makes that invariant enforceable by inspection (`grep -r "cadquery" tools/engine_api/` returns zero — Success Criterion #3). A `tools/step_lib/` sub-package was rejected as over-engineering for ~3 helpers + one load function.

2. **STEP-load return type.** *Decision:* a `LoadedStep` named-tuple `(wp: cq.Workplane, shape: cq.Shape, occ_compound: object)`. *Rationale:* the seven tools collectively need all three handles — four want `wp.faces().vals()` (CadQuery), `boolean_diff` wants `wp.val()` (`cq.Shape`), and `step_summary` wants `wp.val().wrapped` (raw OCC compound for `TopExp_Explorer`). Returning the triple removes 3–5 lines of post-import boilerplate at every call-site. Returning raw `TopoDS_Shape` only would *add* re-wrap boilerplate and was rejected for that reason. Named-tuple is zero-cost and forward-compatible (additional fields can be appended without breaking unpacking).

3. **Single-consumer helpers — `_face_bbox`, `_coaxial`, `_count_shapes`.** *Decision:* all three stay in their current single-consumer tool. *Rationale (one-vs-two-adapter diagnostic applied):* none has a second consumer in the codebase today. The structural review and `_req.md` speculated that `_count_shapes` "would help" `face_catalog` and `face_distances` — but reading those tools' actual code shows neither uses `TopExp_Explorer` (both iterate `wp.faces().vals()`); the second consumer is hypothetical, not load-bearing. Predicted cost if a real second consumer materializes later: ~5 lines of copy-paste duplication for one cycle until the second adapter forces the migration — acceptable, and the lift-and-shift is trivial. Moving them speculatively would widen the shared API surface and force the Developer to write tests (current proposal: 11 tests; speculative-move proposal would balloon to 15+) for code paths that have one call-site in the entire repo. The refactor stays surgical: it concentrates the *verified-duplicated* surface (`_vec3` ×3, `_face_area` ×3, `cq.importers.importStep` ×7), nothing more.

**Awaiting Round 2 feedback** from the requester (admin). Specifically: confirm the `LoadedStep` triple is acceptable (vs. forcing each consumer to re-derive), confirm the conservative single-consumer-helper decision, confirm the flat location vs. `tools/engine_api/` sibling.

### Round 2 — Admin (requester) challenge (2026-05-09)

**Author:** Admin (orchestrator), playing requester role per design-flow Step 3.

**Confirmations on TL Round 2 prompts.**

1. **`LoadedStep` triple — CONFIRMED.** Argument is sound: every handle is *already* derived independently across the seven tools today; the named-tuple consolidates an existing surface rather than inventing one. Forward-compat (additional fields appendable without breaking unpacking) is a free property worth keeping.

2. **Single-consumer helper conservatism — CONFIRMED.** The one-vs-two-adapter diagnostic is correctly applied. Speculative migration would widen the shared API and force tests for one-call-site code paths; the structural-optimization skill explicitly warns against this in §"Common false positives." Reversible: any of the three (`_face_bbox`, `_coaxial`, `_count_shapes`) can move in a single `git mv`-equivalent edit when a real second consumer materializes.

3. **Flat module location (`tools/step_primitives.py`) — CONFIRMED.** Preserves the `tools/engine_api/` CadQuery-agnostic invariant by *physical separation*, not by convention; the `grep -r "cadquery" tools/engine_api/` gate (Success Criterion 3) makes the contract enforceable without trust in future contributors' discipline.

**Admin-originated challenges.**

4. **`StepLoadError(RuntimeError)` is too generic for a file-I/O failure.** Tools' `main()` blocks routinely catch `OSError` / `IOError` / `FileNotFoundError` for filesystem errors; making `StepLoadError` a `RuntimeError` subclass means a tool that catches `OSError` broadly will *not* catch our error and will leak a stack trace where it expects a clean exit. **Action:** rewrite the class to `class StepLoadError(OSError)`. `FileNotFoundError` is itself an `OSError` subclass, so this places `StepLoadError` in the standard I/O-error hierarchy that consumers expect for file failures. Update the docstring and Risk R-A to reflect the parent class.

5. **Test #2 wording is ambiguous on what counts as "byte-identical."** *"Zero-byte diff for all seven outputs"* leaves room for interpretation — `cmp -s` (silent) ignores trailing-newline differences differently from `diff -u`, and JSON files with different float-precision-rounding could "look identical" yet differ by one digit. **Action:** rewrite Test #2 expected-assertion to: *"`diff -u baseline post` returns no output AND `cmp -s baseline post` exits 0 — both conditions required. Any diff is a fail."* Same tightening applied to T4–T10 verification step.

6. **T2 baseline-capture step needs an explicit "do not commit" guard.** `tmp/step_primitives_baseline/` is gitignored by virtue of being under `tmp/`, but a Developer in a hurry could run `git add -A` (which `vibe/INSTRUCTIONS.md` already forbids) and pollute the commit. **Action:** add a single sentence to T2: *"Baselines under `tmp/step_primitives_baseline/` MUST NOT be staged or committed; per `vibe/INSTRUCTIONS.md` §2 use `git add <specific_file>` only."* Belt-and-suspenders against accidental staging.

7. **T1 — `LoadedStep` field-typing for `occ_compound`.** TL declared the field as `object`. The actual type is `OCP.TopoDS.TopoDS_Compound` (or `TopoDS_Shape` depending on STEP content). Typing it `object` defeats static analysis tools (`mypy`, IDE hints) and silently allows mis-use. **Action:** type as `Any` from `typing` with a docstring noting the *expected* type is `OCP.TopoDS.TopoDS_Compound`. `Any` matches the runtime reality (we don't always get a Compound) without inviting `object`-typed dead-end analysis.

**No requirement-violating challenges.** All seven items tighten contracts within R1–R6 or resolve OQ1–OQ3.

**Termination check (Step 3 conditions, after Round 2 resolution).**

1. Every R<n> addressed: yes.
2. Every open question resolved: yes (OQ1, OQ2, OQ3 in Round 1; admin-confirmation in Round 2).
3. Tests table has at least one row per functional requirement: yes.
4. Success criteria measurable and unambiguous: yes (after Round 2 Test #2 revision).
5. Domain integrity gate NO → no domain expert sign-off needed.
6. Non-blocking concerns cost-checked: yes (every Risk row has *Likelihood* and *Predicted cost* columns).

After Round 2 resolutions merge into the artifact body by TL, all six conditions hold. Requester signs off.

### Round 2 — TL resolution (2026-05-09)

**Author:** TL subagent (Opus 4.7, 1M context).

**Confirmations acknowledged (no body change required).**

1. **`LoadedStep` triple — confirmed by Admin.** No change to *Public API* or *Approach chosen*; the named-tuple stands as drafted in Round 1.
2. **Single-consumer helper conservatism — confirmed by Admin.** No change to *Single-consumer helpers — explicit decision* or to the per-tool delegation table; `_face_bbox`, `_coaxial`, `_count_shapes` stay in place.
3. **Flat module location (`tools/step_primitives.py`) — confirmed by Admin.** No change to *Module location* rationale or to Success Criterion #3; the flat-sibling location stands.

**Body-affecting revisions folded in.**

4. **`StepLoadError(OSError)` — applied → *Public API of `tools/step_primitives.py`* (class declaration changed from `RuntimeError` to `OSError`, docstring expanded with rationale) AND → *Risks R-A* (mitigation note now explicitly references the `OSError` parent class so consumer `except OSError:` blocks catch the error cleanly). Rationale accepted as-stated: file-I/O failures belong in the `OSError` hierarchy where consumers already catch them; `RuntimeError` would leak stack traces past existing handlers.
5. **Test #2 wording tightened — applied → *Tests* row #2 (expected-assertion now reads `"diff -u baseline post returns no output AND cmp -s baseline post exits 0 — both conditions required. Any diff is a fail."`) AND → *Implementation Plan* T4, T5, T6, T7, T8, T9, T10 (each verification step rewritten to the same dual-check wording, with T8/T10 applying both conditions to each compared artifact — stdout AND SVG). Rationale accepted: `diff -u` and `cmp -s` differ on edge cases (trailing newlines, binary content, embedded nulls); requiring both eliminates ambiguity.
6. **T2 staging guard — applied → *Implementation Plan* T2 (sentence appended: `"Baselines under tmp/step_primitives_baseline/ MUST NOT be staged or committed; per vibe/INSTRUCTIONS.md §2 use git add <specific_file> only."`). Rationale accepted: belt-and-suspenders against accidental `git add -A` (already forbidden, but worth restating at the point of artifact creation).
7. **`occ_compound` typed as `Any` — applied → *Public API of `tools/step_primitives.py`* (field type changed from `object` to `Any`, with inline comment noting the expected runtime type is `OCP.TopoDS.TopoDS_Compound`, and `Any` imported from `typing`). Rationale accepted: `Any` matches the runtime variability (Compound vs. Shape depending on STEP content) without defeating IDE/`mypy` analysis the way `object` does.

**Termination check (Step 3 conditions, post-resolution).**

1. Every R<n> addressed: yes (Tests-table mapping unchanged; R-A mitigation strengthened by the `OSError` change).
2. Every open question resolved: yes (OQ1, OQ2, OQ3 resolved Round 1; admin-confirmed Round 2).
3. Tests table has at least one row per functional requirement: yes (mapping summary unchanged: R1→1,3,4,5; R2→2,10; R3→6,7,8; R4→1,2; R5→11; R6→9).
4. Success criteria measurable and unambiguous: yes (Tests #2 dual-check tightening propagates to Success Criterion #1 by transitive reference).
5. Domain integrity gate NO → no domain expert sign-off needed.
6. Non-blocking concerns cost-checked: yes (Risks table preserves *Likelihood* and *Predicted cost* columns).

All six conditions hold. TL signs off below.

---

## Sign-off

### Author sign-off (drafting role — Step 3 termination)
- [ ] Domain expert co-sign  *(domain integrity gate is NO — skip)*
- [x] Requester sign-off  *(Admin, 2026-05-09 — Round 2 revisions folded; Step 3 termination conditions verified)*
- [x] TL sign-off  *(or drafting-author sign-off if no TL is shipped)*  — TL subagent, 2026-05-09: all four Round-2 body revisions folded in; all six Step 3 termination conditions hold.

### Independent reviewer sign-off (fresh-context — Step 3.5 termination)
- [x] Independent TL  *(always required)* — Designer-as-Independent-TL, 2026-05-09 (different drafter; see review section below)
- [x] Independent Developer  *(always required — fresh-context review 2026-05-09, APPROVE; see review section below)*
- [ ] Independent Researcher  *(domain integrity gate is NO — skip)*

---

## Implementation Status

<!-- Populated by @developer at Step 5 Phase A. -->
- [x] All Implementation Plan tasks completed (T1–T11)
- [x] Test suite executed — result: **11 / 11 PASS**. Tests #1, #2 (byte-diff regression for all seven tools, dual-gate `diff -u` + `cmp -s`), #3 (`tmp/verify_imports.py`), #4 (`tmp/test_vec3.py`), #5 (`tmp/test_face_area.py` — face[0] area `63.5086` matches baseline), #6 (`tmp/test_load_step_missing.py`), #7 (`tmp/test_load_step_empty.py`), #8 (`tmp/test_load_step_happy.py`), #9 (manual import inspection — only `cadquery`, `OCP.*`, stdlib), #10 (`grep -nE "(def _vec3|def _face_area|cq\.importers\.importStep)"` returns zero matches), #11 (new module carries AGPLv3 header — verified by inspection).
- [x] No new linter / static-check errors. `flake8 tools/step_primitives.py tools/face_catalog.py tools/hole_finder.py tools/face_distances.py tools/step_summary.py tools/section_slicer.py tools/boolean_diff.py tools/step_preview.py` exits 0; `python3 -m py_compile` exits 0 on each. `python3 tools/gen_engine_api.py --check` exits 0 (Success Criterion #6 — engine_api.json wire format unperturbed). `tools/check_license_headers.py` reports a pre-existing failure unrelated to this refactor (`tools/engine_api/__init__.py` is docstring-only and was missing the header before T1; not introduced by this change).
- Developer note:
  - **Migration path-handling.** All seven CLI `main()` blocks now wrap the load-call in `try / except StepLoadError` per Success Criterion #5 / OC-D2; verified `python3 tools/<tool>.py /tmp/nope.step` exits 1 with `error: STEP file not found: …` on stderr for all seven tools.
  - **`PYTHONHASHSEED=0`** was set for both T2 baseline capture and every T4–T10 / T11 post-migration run, addressing Independent TL OC-3.
  - **`section_slicer.py` and `step_preview.py` stdout** include the `--out` directory path verbatim (`WROTE …`). Each was captured into a different output dir at T2 (`tmp/step_primitives_baseline/…`) vs. T4–T10 (`tmp/step_primitives_post/…`); after a path-only normalization (`sed s|.../post/...|.../baseline/...|`) the stdouts are byte-identical. The SVG files themselves are byte-identical without any normalization (`cmp -s` exit 0). This is a test-harness artifact, not a tool-behavior change — the only stdout text that varies is the literal output path the user passed on the command line.
  - **OC-D3 confirmed inert.** `step_preview.py` previously imported only `cadquery`; after T10 it transitively pulls `OCP` via `tools.step_primitives`. Since `cadquery` itself imports `OCP`, the import-graph change is observably a no-op at runtime.
  - **Single-consumer helpers stayed local** as planned: `_face_bbox` (face_catalog), `_coaxial` (hole_finder), `_count_shapes` (step_summary), `_dot` / `_dominant_axis` (face_distances), `_volume` / `_has_solid` (boolean_diff). Re-verified by `grep -n "def _<helper>" tools/*.py` returns the single original definition for each.
  - **Engine-API invariant preserved.** `grep -rE "cadquery|from OCP|import OCP" tools/engine_api/` returns zero matches (Success Criterion #3).
  - **Probe scripts left under `tmp/`** per workspace hygiene rule: `tmp/verify_imports.py`, `tmp/test_vec3.py`, `tmp/test_face_area.py`, `tmp/test_load_step_missing.py`, `tmp/test_load_step_empty.py`, `tmp/test_load_step_happy.py`. Baselines under `tmp/step_primitives_baseline/`; post-migration outputs under `tmp/step_primitives_post/`. Both directories are gitignored (verified via `git check-ignore`); per the design's T2 staging guard, neither was staged.
  - **No commits made.** Per CLAUDE.md commit policy and the task's explicit *"Don't commit anything yet"* instruction, the working tree carries the eight modified/created files but no `git add` / `git commit` was executed.

---

## Independent TL Review (fresh context, 2026-05-09)

**Reviewer:** Designer subagent serving as Independent TL (drafting role was the TL plugin agent — independence condition satisfied: different drafter).

**Verdict:** APPROVE.

### Strengths

- Every R1–R6 has at least one Tests-table row, mapping summary is internally consistent, and the dual-condition byte-diff gate (`diff -u` empty AND `cmp -s` exit 0) eliminates the trailing-newline ambiguity that would otherwise make Test #2 a paper assertion.
- The flat `tools/step_primitives.py` location is the right call and is enforceable by inspection — verified `tools/engine_api/__init__.py` (7-line docstring-only file) and `tools/engine_api/extractor.py` contain zero CadQuery / OCP imports today (`grep -rnE "cadquery|^import cq|from OCP|import OCP" tools/engine_api/` returns empty), so Success Criterion #3's grep gate is currently satisfied and will fail-closed if the invariant is ever broken.
- The one-vs-two-adapter diagnostic on `_face_bbox` / `_coaxial` / `_count_shapes` is correctly applied — all three are confirmed single-consumer by code inspection (see verification log) and the predicted ~5-line cost of a future re-migration is honest.

### Conditions / required edits

None.

### Open concerns (non-blocking, with predicted-cost-of-failure)

- **OC-1: `_vec3` parameter name is not byte-identical across the three source tools** — face_catalog uses `gp_pt_or_dir` with a docstring; hole_finder and face_distances use `gp_obj` without one. The design's claim that the bodies are "byte-for-byte compatible" is true for **output structure** (fields + rounding), not for source text. The Developer must pick one parameter name for the shared `vec3()` and accept that callers don't care. Predicted cost if missed: zero — purely an internal naming choice; no observable behavior. Calling this out so the Developer doesn't trip on the wording at T1.
- **OC-2: `face_catalog.py` rounds its own face-area output to 4 decimals at the call-site** (per the design's own note that callers round). The design says "callers that round to different precision … keep their existing JSON output." Predicted cost if a call-site rounds and the new shared `face_area()` accidentally also rounds (double-round, lossy past 4 decimals): one re-validation cycle when Test #2 fails on T4 — caught fail-closed by the byte-diff gate, so non-blocking.
- **OC-3: T2 baseline capture does not specify Python invocation flags** (e.g. `PYTHONHASHSEED`, locale). Most of the tools' `--json` output is dict-ordered by Python's insertion order today, but `face_catalog.py --summary` output and any iteration over `set()` could be hash-randomization-sensitive. Predicted cost: a one-byte diff at T4 forces the Developer to investigate hash ordering, ~30 min lost. Mitigation: Developer can run T2 and T4–T10 in the same shell to keep `PYTHONHASHSEED` consistent. Not a design defect; a Developer execution note.

### Verification log

Every code claim opened and confirmed at file:line:

1. **`_vec3` duplicated in three tools** — confirmed.
   - `tools/face_catalog.py:68` — `def _vec3(gp_pt_or_dir) -> dict:`, body returns `{x,y,z}` rounded to 4.
   - `tools/hole_finder.py:57` — `def _vec3(gp_obj) -> dict:`, body returns `{x,y,z}` rounded to 4.
   - `tools/face_distances.py:51` — `def _vec3(gp_obj) -> dict:`, body returns `{x,y,z}` rounded to 4.
   - Bodies are functionally byte-identical (same rounding, same field names); only the parameter name and docstring differ on face_catalog (see OC-1).
2. **`_face_area` duplicated in three tools** — confirmed verbatim.
   - `tools/face_catalog.py:77`, `tools/hole_finder.py:61`, `tools/face_distances.py:55` — three lines each, identical: `props = gprop.GProp_GProps(); bgp.BRepGProp.SurfaceProperties_s(occ_face, props); return props.Mass()`. No rounding at the helper.
3. **`_count_shapes` lives only in `step_summary.py`** — confirmed at `tools/step_summary.py:64`. `grep -n "def _count_shapes"` across all seven tools returns this single match.
4. **`_face_bbox` only in `face_catalog.py`** — confirmed at `tools/face_catalog.py:83`. Single match across all seven tools.
5. **`_coaxial` only in `hole_finder.py`** — confirmed at `tools/hole_finder.py:67`. Single match across all seven tools.
6. **`vec3` rounds to 4 decimals** — confirmed at all three sites (`round(..., 4)` on each axis).
7. **`face_area` un-rounded at the helper** — confirmed: all three sites return `props.Mass()` directly with no `round()`.
8. **Seven `cq.importers.importStep` call-sites** — confirmed: `tools/face_catalog.py:105`, `tools/hole_finder.py:103`, `tools/face_distances.py:102`, `tools/step_summary.py:98`, `tools/section_slicer.py:297`, `tools/boolean_diff.py:74`, `tools/step_preview.py:89`. Seven, matching the design's claim.
9. **`boolean_diff.py` has its own `_load_step`** — confirmed at `tools/boolean_diff.py:73` (returns `cq.Shape` via `wp.val()`); the design correctly notes T9 deletes this local helper.
10. **`face_distances.py` has algorithmic helpers `_dot` / `_dominant_axis`** — confirmed at lines 61 and 65; the design's decision to keep them local (algorithmic, not OCP boilerplate) is consistent with their actual content.
11. **Engine-API CadQuery-agnostic invariant** — confirmed:
    - `tools/engine_api/__init__.py` — 7-line docstring-only module, no imports beyond the implicit package marker.
    - `tools/engine_api/extractor.py` — header confirms "Pure stdlib: imports nothing from CadQuery or the model packages themselves."
    - `grep -rnE "cadquery|^import cq|from OCP|import OCP" tools/engine_api/` returns zero matches. The flat `tools/step_primitives.py` location preserves this invariant by physical separation.

**T1–T11 atomicity assessment.** Each task touches exactly one file (or a fixed verification command set), each is independently verifiable: T1 via flake8 + py_compile + license header check; T2 via baseline file existence; T3 via gate exit codes; T4–T10 via byte-diff against T2 baselines; T11 via the same gates re-run. The per-tool migration ordering means a regression in any one of T4–T10 is bisectable to a single tool's edit.

**Risk-mitigation soundness.** R-A through R-E each carry a likelihood and predicted-cost-of-failure column. R-A is the most consequential and is gated by the byte-diff regression check — appropriate. R-B's mitigation (flat module + grep gate at T11) is the only structural protection of the engine_api invariant and works because the gate is mechanical, not policy-based. R-C's grep-for-residual-`def _vec3` gate (Test #10) catches the silent-shadow case the design names. R-D's "documented field semantics" mitigation is the weakest of the five (review-time rather than runtime), but the cost-of-failure (one PR-review cycle) is genuinely low — proportionate.

**Termination conditions for Step 3.5 reviewer.** All six checks pass; no required edits; non-blocking concerns documented with predicted costs. Independent TL checkbox ticked.

---

## Independent Developer Review (fresh context, 2026-05-09)

**Reviewer:** Developer subagent (fresh context, no prior involvement in drafting). Independence condition satisfied: design was drafted by the TL plugin agent.

**Verdict:** APPROVE.

### Strengths

- T1–T11 are atomic, single-file scoped, and correctly sequenced from an implementer's perspective: shared module landed and lint/header-gated (T1–T3) before any consumer migrates; T2 captures byte-exact baselines *before* any code edit, so each migration is fail-closed on diff. The one-tool-per-task structure of T4–T10 makes any regression bisectable to a single edit and trivially revertible.
- The `LoadedStep` triple matches the live call-shapes verbatim — verified by reading each call-site: `face_catalog.py:106`, `hole_finder.py:104`, `face_distances.py:103` consume `wp.faces().vals()` (need `wp`); `step_summary.py:102`, `section_slicer.py:298` consume `wp.val().wrapped` (need `occ_compound`); `boolean_diff.py:75`, `step_preview.py:90` consume `wp.val()` (need `shape`). No consumer is forced into a re-wrap, and the named-tuple removes the 3-line post-import boilerplate the design promises.
- Tests #1–#11 cover R1–R6 with at least one row each (R1→1,3,4,5; R2→2,10; R3→6,7,8; R4→1,2; R5→11; R6→9), and tests #6/#7/#8 (negative paths for `StepLoadError`) are concretely runnable as one-off `tmp/` probes — matching the project's `tmp/` workspace-hygiene rule.

### Conditions / required edits

None. The plan is executable as-written.

### Open concerns (non-blocking, with predicted-cost-of-failure)

- **OC-D1: Test #10's grep regex uses an unescaped `.` in `cq.importers.importStep`.** Regex `.` matches any character; in this codebase no false-positive is plausible (no other identifier resembles `cq[any]importers[any]importStep`), but a strict reader could conclude the gate is technically loose. Predicted cost if a phantom match ever surfaced: ~5 min for the Developer to escape to `cq\.importers\.importStep` and re-run. Trivial; not worth a body edit.
- **OC-D2: Migration must wrap each tool's `main()` in `try / except StepLoadError`.** Success Criterion #5 requires CLI mains to catch `StepLoadError` and exit 1; today none of the seven tools catch any STEP-load failure (they let OCCT raise). T4–T10 must add the `try / except` wrapper, not just swap the import. The design narrative implies this but the per-task table doesn't spell it out. Predicted cost if the Developer skips it: stack-trace leak on a missing-file CLI invocation, one re-validation cycle (~10 min) when the human reviewer notices. Worth restating to the Developer at hand-off, not a design defect.
- **OC-D3: `step_preview.py` does not currently import OCP directly** (only `cadquery`). After T10, `from tools.step_primitives import load_step` pulls OCP transitively — but `cadquery` itself imports OCP, so this is a no-op at runtime. Cost if blocking: zero. Calling out so the Developer doesn't second-guess the import-graph change.

### Verification log

Every code claim opened at file:line; every fixture-existence check executed.

1. **Persona / instructions read.**
   - `vibe/agents/developer.md` read in full (Steps 1–6, escalation triggers, workflow position) — adopted.
   - `.agents/plans/2026-05-08-shared-step-primitives_req.md` read in full; R1–R6, OQ1–OQ3, Out-of-Scope mapped against design.
2. **Fixture existence.**
   - `ls -la /workspaces/vibe-cading/valve_cap.step` → 46392 bytes, present at repo root.
   - `python3 tools/step_summary.py valve_cap.step --json` succeeds: 1 solid / 1 shell / 17 faces / 70 edges / 18 wires / 140 vertices; volume 608.1265 mm³; bbox spans 11.547 / 10.0 / 12.0 mm. Sufficient face count to exercise `face_catalog`, sufficient cylindrical content for `hole_finder`, sufficient planar pairs for `face_distances`, sufficient depth for `section_slicer`, supports self-diff for `boolean_diff`, and renders for `step_preview`.
3. **`LoadedStep` triple shape vs live call-sites.**
   - `tools/face_catalog.py:105-106` → `wp = cq.importers.importStep(str(path)); faces = wp.faces().vals()` — needs `wp`. ✓
   - `tools/hole_finder.py:103-104` → `wp.faces().vals()` — needs `wp`. ✓
   - `tools/face_distances.py:102-103` → `wp.faces().vals()` — needs `wp`. ✓
   - `tools/step_summary.py:98-102` → `wp.val().wrapped` (line 102 stores `occ_compound`) — needs `occ_compound`. ✓
   - `tools/section_slicer.py:297-299` → `wp.val().wrapped` AND `wp.val().BoundingBox()` — needs both `occ_compound` and `shape`. ✓
   - `tools/boolean_diff.py:73-75` → `wp.val()` returns `cq.Shape` — needs `shape`. ✓
   - `tools/step_preview.py:89-90` → `wp.val()` — needs `shape`. ✓
   The triple precisely covers all seven consumers' demands.
4. **Helper signatures match design's *Public API*.**
   - `tools/face_catalog.py:68-74` — `_vec3` rounds to 4 decimals; matches design.
   - `tools/face_catalog.py:77-80` — `_face_area` returns un-rounded `Mass()`; matches design.
   - `tools/face_catalog.py:113` — call-site rounds `_face_area(...)` to 4 at the consumer, confirming design's claim that callers (not the helper) round. T4 must preserve this consumer-side rounding to keep T2 baseline byte-identical.
   - `tools/hole_finder.py:57-64` — `_vec3`/`_face_area` byte-identical to face_catalog.
   - `tools/face_distances.py:51-58` — `_vec3`/`_face_area` byte-identical to face_catalog.
5. **Single-consumer KEEP decisions verified.**
   - `_face_bbox` defined at `tools/face_catalog.py:83`; `grep -n "def _face_bbox"` across all seven tools returns this single match. KEEP-local sound.
   - `_coaxial` defined at `tools/hole_finder.py:67`; algorithmic line-distance helper, single definition, single consumer. KEEP-local sound.
   - `_count_shapes` defined at `tools/step_summary.py:64`; consumed at `step_summary.py:104-107` (FACE/EDGE/VERTEX/WIRE). I separately confirmed `face_catalog.py` and `face_distances.py` do NOT call `TopExp_Explorer` (grep returns no `TopExp_Explorer` import in either file) — they iterate `wp.faces().vals()` instead. The design's rejection of the speculative second consumer is empirically grounded.
6. **Engine-API CadQuery-agnostic invariant.**
   - `ls tools/engine_api/` → `__init__.py`, `extractor.py`, `__pycache__` only.
   - `grep -rE "cadquery|import cq|from OCP|import OCP" tools/engine_api/` returns zero matches. Invariant holds today; flat `tools/step_primitives.py` location preserves it by physical separation. Success Criterion #3's grep gate is achievable.
7. **AGPL header gate.**
   - `tools/check_license_headers.py:19` glob is `tools/**/*.py` — new `tools/step_primitives.py` is automatically scanned at T3.
   - `tools/face_catalog.py:1-14` is a clean copy-source for the header per T1.
8. **Import-cycle risk.** None. The new `tools/step_primitives.py` imports `cadquery` and `OCP.*` only (per design's *Public API*); consumers import from `tools.step_primitives`. No back-edge possible since `step_primitives` does not import any of the seven tools.
9. **OCP version assumptions.** `BRepGProp.SurfaceProperties_s` and `GProp_GProps()` are used today verbatim in three tools — design simply consolidates them; no version surface area change.
10. **`StepLoadError(OSError)` rationale.** `FileNotFoundError` is itself an `OSError` subclass; placing `StepLoadError` in the `OSError` hierarchy means consumer `except OSError:` blocks (none exist today, but Success Criterion #5 adds them) catch it cleanly. Round-2 admin challenge correctly resolved.

### Termination conditions for Step 3.5 reviewer

1. T1–T11 atomic + correctly sequenced: ✓
2. Tests cover every R1–R6, byte-diff strategy concretely runnable: ✓
3. Public API implementable; signatures match all seven call-sites: ✓
4. KEEP decision for `_face_bbox` / `_coaxial` / `_count_shapes` empirically correct: ✓
5. `valve_cap.step` exists and exercises the regression suite: ✓
6. No execution-time blockers found: ✓

All six checks pass; no required edits; three non-blocking concerns documented with predicted-cost-of-failure. Independent Developer checkbox ticked above.

---

## Post-Implementation Sign-Off

### TL Review
- [x] **TL sign-off**
- TL review notes:

**Reviewer:** TL subagent (Opus 4.7, 1M context), 2026-05-09. Verdict: APPROVE / clean.

**Implementation Plan completion.** T1–T11 all marked complete in *Implementation Status*; verified each task's artefact: `tools/step_primitives.py` exists with AGPLv3 header (T1); baselines persist under `tmp/step_primitives_baseline/` and are gitignored (T2); flake8 + py_compile gates pass on all eight modified files (T3, T11); seven migrations (T4–T10) confirmed by grep — every consumer now imports from `tools.step_primitives` and the legacy local helpers are gone.

**Tests #1–#11 re-executed for spot-check.** All six probe scripts under `tmp/` (`verify_imports`, `test_vec3`, `test_face_area`, `test_load_step_missing`, `test_load_step_empty`, `test_load_step_happy`) ran and passed. `test_vec3` returns `{x:1.2346, y:2.3457, z:3.4568}` exactly. `test_face_area` returns face[0]=63.5086 matching the baseline. `test_load_step_missing` raises `StepLoadError` with the path in the message. `test_load_step_happy` returns 17 faces / `Solid` / `TopoDS_Solid` populating all three triple fields.

**Success Criteria — all six met.**
- **SC1 (byte-zero `--json` diff against baseline):** PASS. Re-ran all five JSON tools (`face_catalog`, `hole_finder`, `face_distances`, `step_summary`, `boolean_diff` self-diff) with `PYTHONHASHSEED=0` against `valve_cap.step`; `cmp -s` exit 0 for all five compared to `tmp/step_primitives_baseline/`. Re-ran `section_slicer.py --axis Z --at 6` and `step_preview.py --views top front left`: the SVG bytes are identical without normalization (`cmp -s` exit 0 on every file); the `WROTE …` stdout is identical after the documented path-only `sed` normalization (the only varying token is the `--out` directory the operator passed).
- **SC2 (zero duplicates outside `tools/step_primitives.py`):** PASS. `grep -nE "(def _vec3|def _face_area|cq\.importers\.importStep)"` across all seven migrated tools returns zero matches; the legacy `_load_step` in `boolean_diff.py` is also gone.
- **SC3 (engine_api CadQuery-agnostic):** PASS. `grep -rE "cadquery|from OCP|import OCP" tools/engine_api/` returns zero matches. `git diff tools/engine_api/` is empty.
- **SC4 (hygiene gates):** PASS. `flake8` and `python3 -m py_compile` exit 0 on all eight modified files. `tools/check_license_headers.py` reports only the pre-existing `tools/engine_api/__init__.py` failure (docstring-only file, not introduced by this refactor — see *non-blocking* below).
- **SC5 (error-reporting contract):** PASS. Verified all seven tools — `python3 tools/<tool>.py /tmp/nope.step` (and `boolean_diff.py /tmp/nope_ref.step /tmp/nope_cand.step`) — exit 1 with `error: STEP file not found: …` on stderr. `try / except StepLoadError` block confirmed present in every `main()` (face_catalog:195, hole_finder:262, face_distances:246, step_summary:234, section_slicer:401, boolean_diff:205, step_preview:166).
- **SC6 (`gen_engine_api.py --check`):** PASS. Exits 0.

**Workspace hygiene per `vibe/INSTRUCTIONS.md` §2.** AGPLv3 header confirmed on `tools/step_primitives.py` (lines 1–14). `tmp/step_primitives_baseline/`, `tmp/step_primitives_post/`, `tmp/tl_review_post/`, and the six probe scripts are all gitignored (`git check-ignore` confirms). `git status --porcelain tmp/` is empty — no `tmp/` artefacts staged. Working tree shows no `git add` of any baseline file. The eight in-scope files (`tools/step_primitives.py` plus seven migrated tools) are present in the working tree, untracked or modified per the design's plan.

**Engine-API contract preserved.** `tools/engine_api/extractor.py` and `tools/engine_api/__init__.py` are byte-identical to HEAD (`git diff` empty for both). `engine_api.json` unperturbed (SC6 gate).

**Non-blocking observations (with predicted cost-of-failure):**

- **NB-1: Pre-existing license-header failure on `tools/engine_api/__init__.py`** (7-line docstring-only file). The Developer flagged this and it is not introduced by this refactor. Predicted cost if left unaddressed: zero for this refactor's correctness; low for repository hygiene — one PR-review cycle (~5 min) to add the header in a separate, clearly-scoped change. Out of scope for SC4 sign-off because the gate failure was present before T1.
- **NB-2: Working tree contains scope drift unrelated to this design** — `tools/model_loader.py` (untracked) and modifications to `build.py`, `tools/preview.py`, `tools/view.py`, `tools/check_polar_monotonicity.py`, `tools/check_topology.py`. None of these files are in the design's Implementation Plan and they do not affect the SC1–SC6 verifications I ran. Predicted cost if these are accidentally co-staged with the step_primitives commit: one revert-and-resplit cycle (~15 min). Mitigation already in place: the developer note explicitly states no `git add` was performed and the user's commit policy requires explicit per-file staging. Flagging here so whoever drafts the eventual commit stages only the eight in-scope paths (`tools/step_primitives.py`, plus the seven migrated CLIs) and leaves the unrelated working-tree changes for a separate PR.

No blockers. TL sign-off granted.

### Domain Expert Review
*Domain integrity gate is NO — skip.*

### Human Final Approval
- [ ] **Human approved** for merge / release
- Human notes:
