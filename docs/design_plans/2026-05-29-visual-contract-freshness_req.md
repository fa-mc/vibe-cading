# Requirements: Visual-contract SVG freshness CI check
<!-- Filename: 2026-05-29-visual-contract-freshness_req.md  (tracked under .agents/plans/) -->

## Meta
- **Initiator role**: @designer (per human-Admin direction in 2026-05-29 session)
- **Date**: 2026-05-29
- **Domain integrity gate**: **NO** — workflow / tooling scaffolding only. No
  geometry, tolerance, fit-grade, axis convention, or model code is touched.
  The change adds a manifest, a check tool, and one CI step that invokes
  `tools/preview.py`'s existing code path against existing model classes.

---

## Problem Statement

The project's *Visual Contract Deliverable* rule (`vibe/INSTRUCTIONS.md`)
requires every design artifact that ships a new CAD model class — or changes
visible geometry — to co-locate a git-tracked `_design_*.svg` preview that
serves as the *visual contract*. The invariant the contract relies on is
**`committed == regenerable`**: the committed SVG must reproduce byte-for-byte
when its source class is re-rendered through `tools/preview.py`. But nothing
in the workflow *enforces* that invariant after the initial Step-5 Phase-A
generation. When a model class is later refactored, no step re-runs the SVG
regeneration, so the committed contract silently drifts from the model code
and the visual contract becomes a lie.

This was proven in practice by [PR #17](https://github.com/fa-mc/vibe-cading/pull/17):
regenerating the contracts revealed **7 of 9** tracked design SVGs had drifted
from current model code (the beam pin-hole-radius refactor and the axle-gauge
engraved `text()` labels were both absent from the committed contracts despite
being live in the model). Drift escaped every prior review because no
mechanical gate ever compares committed-vs-regenerable. Closing this gap is a
release-readiness item for OSS publication.

## User Story / Motivation

As an OSS contributor who refactors an existing model class (or whose change
alters any visible geometry), I need CI to fail loudly when a committed
`_design_*.svg` visual contract no longer reproduces from its source class, so
that I am forced to refresh the contract in the same PR — rather than letting
the contract rot silently and mislead the next contributor who trusts it as
the source-of-truth picture of the model.

## Empirical Foundation (established by RCA — `tmp/svg-freshness-rca.md`)

The following facts are **proven** (probe run 2026-05-29, this dev container)
and are fixed inputs to the requirements — the developer must not re-derive
them:

1. **CadQuery interpreter.** CadQuery lives on `python3.11` here (3.11.x +
   cadquery 2.7.0), the *same* interpreter CI uses via `requirements-ci.txt`.
   Default `python3` is 3.13 with **no** cadquery. The check tool must run
   under the CadQuery interpreter (in CI, after the build-smoke step).
2. **Byte-exact regenerate-and-compare is viable.** All 9 tracked
   `_design_*.svg` regenerate **byte-identical** today via
   `tools/preview.py <Class> --views <view> [--params …]` after preview.py's
   existing 3 dp `_round_svg_coords` pass. Verified with `cmp` (exit 0 on
   every file). OCCT projection is deterministic here once coords are rounded
   to 3 dp.
3. **The mtime-lint alternative is REJECTED.** Git does not preserve mtimes;
   a fresh `actions/checkout` assigns files checkout-order mtimes, so
   "SVG older than its source `.py`" is meaningless on a clean CI clone. It
   only works as a weak local-only convenience.
4. **Filenames do NOT encode class / params / view.** The exact mapping lives
   only in prose scattered across design briefs. A machine-readable manifest is
   required. The confirmed 9-row mapping:

   | Committed SVG (`.agents/plans/`) | Class | Params | View |
   |---|---|---|---|
   | `2026-05-15-lego-technic-beam_design_iso_ne.svg` | `vibe_cading.lego.technic_beam.LegoTechnicBeam` | `length_in_studs=5` | `iso_ne` |
   | `2026-05-15-lego-technic-beam_design_top.svg` | (same) | `length_in_studs=5` | `top` |
   | `2026-05-15-lego-technic-beam_design_front.svg` | (same) | `length_in_studs=5` | `front` |
   | `2026-05-20-axle-hole-tip-to-tip-gauge_design_iso_ne.svg` | `vibe_cading.lego.axle_hole_gauge.AxleHoleGauge` | *(defaults)* | `iso_ne` |
   | `2026-05-20-axle-hole-tip-to-tip-gauge_design_top.svg` | (same) | *(defaults)* | `top` |
   | `2026-05-21-axle-cross-hole-gauge_design_iso_ne.svg` | `vibe_cading.lego.axle_cross_hole_gauge.AxleCrossHoleGauge` | *(defaults)* | `iso_ne` |
   | `2026-05-21-axle-cross-hole-gauge_design_top.svg` | (same) | *(defaults)* | `top` |
   | `2026-05-23-calibration-helper-generic_design_m3_clearance_iso_ne.svg` | `vibe_cading.mechanical.calibration.m3_clearance_gauge.MThreeClearanceGauge` | *(defaults)* | `iso_ne` |
   | `2026-05-23-calibration-helper-generic_design_m3_nut_pocket_iso_ne.svg` | `vibe_cading.mechanical.calibration.m3_nut_pocket_gauge.MThreeNutPocketGauge` | *(defaults)* | `iso_ne` |

   **`LegoTechnicBeam.length_in_studs` is a REQUIRED positional arg with no
   default** — so a filename-only or default-only scheme cannot regenerate the
   three beam contracts. The manifest **MUST** carry params.

## User (human-Admin) Decisions — fixed inputs

These were decided before this requirements artifact and are NOT open
questions:

- **D1 — Approach = CI regenerate-and-compare** (path (a)), not mtime lint.
- **D2 — Coverage gate = YES.** The check MUST also fail when a tracked
  `.agents/plans/*_design_*.svg` exists but is NOT registered in the manifest,
  so the manifest cannot silently rot as new design SVGs are added.
- **D3 — Manifest format = DEFERRED to @tl + @designer advice.** This is the
  one open architectural question and is carried in the design artifact's
  Architecture section as a recommended option *pending TL co-sign*. (See the
  design's Open Questions; the requirements do not pre-decide it.)

## Functional Requirements

1. **FR1 — Machine-readable visual-contract manifest.** The project MUST gain a
   single machine-readable manifest that maps each committed
   `.agents/plans/*_design_*.svg` to the exact `(class, params, view)` tuple
   that regenerates it. The manifest MUST carry params (FR-driven by the
   `LegoTechnicBeam.length_in_studs` required-arg fact above). At creation the
   manifest MUST register all **9** SVGs in the table above. The concrete
   *format* of the manifest (dedicated `visual_contracts.toml` vs. extending
   `build.toml` vs. design-brief front-matter) is resolved in the design
   artifact pending TL co-sign — see design Open Questions.

2. **FR2 — `tools/check_visual_contract_freshness.py` regenerate-and-compare.**
   A new tool MUST exist that, for each manifest entry, regenerates the SVG
   through the **same code path `tools/preview.py` uses** — i.e. by importing
   and calling `tools.preview.export_previews(...)` (or the equivalent
   loader-backed render) into a temporary directory — and **byte-compares** the
   regenerated bytes against the committed file. The tool MUST exit non-zero if
   any committed SVG differs from its regeneration. The tool MUST NOT duplicate
   the model-loader logic (`tools/model_loader.py`) nor the `_round_svg_coords`
   / `_fix_svg_viewport` post-processing — it reuses `tools/preview.py`'s
   public `export_previews()` so the rendering pipeline is provably identical to
   the one that produced the committed contracts.

3. **FR3 — Coverage gate (per D2).** The tool MUST enumerate every tracked
   `.agents/plans/*_design_*.svg` and fail (non-zero exit) if any such file is
   NOT registered in the manifest. This prevents the manifest from silently
   rotting as new design SVGs land. Conversely, a manifest entry pointing at a
   **non-existent** committed SVG MUST also fail (a manifest row whose target
   file is missing is equally a rot signal).

4. **FR4 — Filename indirection handled correctly.** `export_previews()` names
   its output `<ClassName>_<view>.svg`, which does **not** match the committed
   `<date>-<slug>_design[_<label>]_<view>.svg` names (e.g. the calibration
   gauges render as `MThreeClearanceGauge_iso_ne.svg` but commit as
   `2026-05-23-calibration-helper-generic_design_m3_clearance_iso_ne.svg`). The
   tool MUST resolve this indirection: regenerate into a temp dir, then
   byte-compare the regenerated `<ClassName>_<view>.svg` against the committed
   path named by the manifest's `svg` field. The committed path in the manifest
   is the source of truth for *where* the contract lives; the class+view drive
   *what* gets rendered.

5. **FR5 — `--update` regenerate-all mode.** The tool MUST provide a
   `--update` (regenerate-all) mode that re-renders every manifest entry and
   overwrites the committed SVG in place, so a contributor who *legitimately*
   changed geometry can refresh all contracts with one command instead of
   re-running `tools/preview.py` nine times and hand-copying files. In
   `--update` mode the tool does NOT fail on diff — it writes the new bytes and
   reports which files changed. The default (no `--update`) mode is the
   read-only check used by CI.

6. **FR6 — New CI step in `ci.yml`.** A new step MUST be added to the existing
   `check` job in `.github/workflows/ci.yml` that runs the check tool. The step
   MUST live **after** the `Build smoke (python build.py)` step (so CadQuery is
   already installed and validated), mirroring the placement and style of the
   existing `Topology check` step (which is the closest precedent — see the
   2026-05-28 CI-topology-check PR). The step MUST fail the workflow on any
   non-zero exit from the tool.

7. **FR7 — Human-readable failure output.** On a drift failure the tool MUST
   print, for each mismatching contract, the committed SVG path and the exact
   regenerate command a contributor can run locally to refresh it (i.e. the
   `--update` invocation, or the equivalent `tools/preview.py` line). On a
   coverage-gate failure it MUST name the unregistered SVG (or the missing
   target). A reviewer scrolling CI logs must be able to identify *which*
   contract drifted and *how to fix it* without correlating offsets.

8. **FR8 — AGPLv3 header + lint-clean.** `tools/check_visual_contract_freshness.py`
   is a new file under `tools/`, so it MUST carry the AGPLv3 header (copy the
   exact text from an existing `tools/` file) and pass `flake8 .` and
   `py_compile` (both already run earlier in the same CI job).

9. **FR9 — Close the TODO item.** `TODO.md` lines 106–116 (the
   "Visual-contract SVG freshness" backlog entry, raised 2026-05-29) MUST be
   marked resolved, citing the PR. (This commit qualifies for the project's
   TODO direct-push carve-out, but that is the developer's procedural concern —
   it is listed here only as a deliverable.)

## Non-Functional Constraints

- **Runtime budget.** The new step renders 9 SVGs (today). Each render is a
  single-class OCCT projection — empirically sub-second to a few seconds each.
  The step MUST add no more than ~60 s to CI wall-clock on a clean
  GitHub-hosted runner. If the developer measures >120 s, escalate as a blocker
  (likely cause: re-instantiating expensive geometry per view rather than once
  per class — mitigation is rendering all views of a class in one
  `export_previews` call, which the tool should already do).
- **No new pip dependencies.** `requirements-ci.txt` already provides CadQuery
  for the build-smoke step. The check tool MUST use only that + the standard
  library (`tomllib` is stdlib on 3.11). No new third-party dependency.
- **Reuse, do not duplicate.** Per `vibe/INSTRUCTIONS.md` §Utility Reuse and
  §2D-sketching-adjacent reuse norms, the tool MUST import the existing
  `tools.preview.export_previews` and `tools.model_loader` rather than
  re-implementing the loader, the param parser, the viewport fix, or the
  coordinate-rounding pass. Duplicating `_round_svg_coords` would create a
  second source of truth that could itself drift.
- **Existing CI steps untouched.** `flake8`, `py_compile`,
  `check_no_main_blocks.py`, `ocp_vscode` greps, pytest, `python build.py`, and
  the `Topology check` step MUST run unchanged. The new step is purely
  additive and runs last (or after build-smoke / topology — placement detail in
  the design).
- **Determinism dependency is acknowledged, not mitigated here.** The check
  rests on OCCT projection being deterministic for a fixed cadquery/OCCT
  version (proven true today). A future cadquery/OCCT bump *could* change
  tessellation and break byte-equality across the board. That is the **correct**
  behavior — it would force a contract refresh via `--update` in the same PR
  that bumps the dependency. No tolerance-compare fallback is in scope (see
  Out of Scope).

## Known Domain Constraints

- **`export_previews()` output naming is `<ClassName>_<view>.svg`.** This is
  fixed in `tools/preview.py` and is not changed by this task. The manifest +
  the check tool absorb the filename indirection (FR4); preview.py's public API
  is not modified.
- **`LegoTechnicBeam.length_in_studs` has no default.** Any scheme that cannot
  carry per-entry params is unworkable for the beam contracts (proven).
- **The 3 dp coordinate rounding (`_round_svg_coords`, PR #17) is what makes
  byte-equality stable.** The check MUST run *the same* post-processing, which
  is automatically true if it calls `export_previews()` (it applies the pass
  internally). The check tool MUST NOT bypass `export_previews()` and call
  `cq.exporters.export` directly — that would skip the rounding pass and produce
  spurious full-precision mismatches.
- **All current tracked design SVGs match `*_design_*.svg`.** Confirmed by glob
  — there are no design-artifact SVGs outside that pattern. The coverage gate's
  enumeration glob (`*_design_*.svg` under `.agents/plans/`) is therefore both
  necessary and sufficient for the current tree.

## Out of Scope

*Explicit anti-scope — DO NOT include in this PR:*

- **No tolerance / fuzzy SVG compare.** Byte-exact works today (proven) and is
  the simplest, strongest signal. A perceptual or tolerance-based comparator is
  explicitly deferred; if a future OCCT bump makes byte-equality unstable, the
  decision will be revisited then (the answer is more likely "pin OCCT + refresh
  via `--update`" than "fuzzy-compare").
- **No mtime lint.** Rejected per RCA (D1). Not even as a local convenience —
  shipping a second, weaker check would be confusing.
- **No `build.toml` geometry change, no model code change.** The 9 source
  classes are not touched. If the developer finds a class that *won't*
  regenerate byte-identically (it should — all 9 are proven), that is a blocker
  to escalate, not a model edit to make under this task.
- **No new model class, no visible-geometry change → no new design preview SVG
  for THIS task.** This task is a documented **carve-out** from the Visual
  Contract SVG rule itself: the deliverable is tooling + CI, not a CAD model.
  (Stated explicitly in the design.)
- **No promotion of the manifest to a richer registry** (e.g. embedding
  expected dimensions, hashes, or multi-view bundling beyond the
  one-row-per-SVG shape) beyond what FR1 requires. Keep the manifest minimal.
- **No `engine-api.yml` change, no README CI badge.** Different workflow /
  separate backlog items.
- **No retroactive refresh of the 9 SVGs.** They are already byte-identical to
  their regeneration (PR #17 just refreshed them). The check will pass on the
  first run; no `--update` sweep is needed at landing time. (If, by the time
  this lands, any source class drifted again, the developer runs `--update`
  once and commits — but that is expected to be a no-op.)

## Open Questions

*The single substantive open question is the manifest format. Per D3 it is
carried into the **design** artifact (Architecture + Open Questions) with a
Designer recommendation pending TL co-sign, rather than pre-decided here. The
questions below are the design-dialog seeds.*

- [ ] **Q1 — Manifest format.** Dedicated top-level `visual_contracts.toml`
  (parallel to `build.toml`) vs. extend `build.toml` with `[[visual_contract]]`
  entries vs. front-matter / parsed block inside each design brief.
  *Designer recommendation (justification in the design): dedicated
  `visual_contracts.toml`.* Pending TL co-sign.
- [ ] **Q2 — CI step ordering relative to `Topology check`.** Both are
  post-build-smoke CadQuery-runtime steps. Does the freshness check run before
  or after the topology check? *Designer recommendation: after `Topology
  check` (it is the newest / least load-bearing gate; ordering is cosmetic
  since the job runs steps serially and any failure fails the job).* Trivial;
  developer's discretion.
- [ ] **Q3 — Does `--update` belong in v1, or is the bare `tools/preview.py`
  re-run + manual copy acceptable?** *Designer recommendation: include
  `--update` in v1 (FR5)* — the 9-file hand-copy with filename indirection (FR4)
  is exactly the error-prone manual step that caused contracts to drift in the
  first place; a one-command refresh removes that friction. Recommend, not
  over-build — `--update` is a thin loop over the same render path, ~15 LOC.

---

## Human Confirmation Checkpoint
- [ ] Requirements reviewed and confirmed by human
<!-- Do not proceed past the human design gate until this box is checked.
     The manifest-format question (Q1) is the key item the human + TL must
     co-sign before the developer starts. -->
