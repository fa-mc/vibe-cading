# Requirements: Pre-OSS structural design pass — `models/` + adjacent shared infra
<!-- Filename: 2026-05-13-pre-oss-models-structure_req.md (tracked in git under .agents/plans/) -->

## Meta
- **Initiator role**: @pm (escalated from user; PM acting on user's "last chance to finalize design before OSS" directive)
- **Date**: 2026-05-13
- **Domain integrity gate**: NO — structural / public-API design review; no data or domain-model contracts touched

---

## Problem Statement

The project is approaching open-source release. The 2026-05-13 TL deep-modules review of `models/` (chat-only, no artifact) surfaced three deepening candidates plus three parked lower-yield items. User direction (this turn) is to **widen scope**: before any structural patch is implemented, TL produces a comprehensive design pass over the full `models/` public surface (plus the shared infra it imports — `models/cq_utils.py` and `models/print_settings.py`) so the structure OSS users encounter on day one is coherent, well-named, and free of misleading inheritance shells, fragmented naming conventions, and shallow-by-construction abstractions.

This req is **design-only**. Implementation tasks are downstream outputs of the resulting design brief; they will be curated into [INDEX.md](INDEX.md) once TL's phased plan is approved.

## User Story / Motivation

As an open-source contributor encountering vibe-cading for the first time, I need the `models/` class structure — naming, base classes, cutter conventions, package layout, public API surface, constructor ergonomics — to be coherent and self-explanatory so I can contribute new parts without first reverse-engineering the conventions or asking "why does `MetricMachineScrew` inherit from `Screw` but `MetricHexNut.to_cutter()` doesn't match `Nut.to_cutter()`?"

## Functional Requirements

> These describe TL's *deliverable* (the design artifact). They do not prescribe what TL must conclude; only the analytical surface TL must cover.

1. **R1.** TL MUST produce a single comprehensive `2026-05-13-pre-oss-models-structure_design.md` covering all of `models/` plus `models/cq_utils.py` and `models/print_settings.py`.
2. **R2.** Every existing base class — `Screw`, `Nut`, `BaseJoint`, `Gear`, `SlipperGearBase` — MUST be evaluated using the structural-optimization skill's deletion test, applied with BOTH lenses: **maintainer-locality** (do existing internal callers benefit from the base?) AND **contributor-locality** (would an OSS contributor adding a new family member benefit from inheriting it as a documented extension contract?). For each base, the brief records: outcome of each lens, false-positive carve-outs considered (the skill's four canonical + the implicit "contributor-extension contract" shape surfaced during this req's dialog), and a recommended action chosen from FOUR real options: (a) **keep as-is** — accept current state; (b) **repair and keep** — re-align the abstract signatures to match concrete implementations so the contract stops lying; (c) **replace with `typing.Protocol`** — structural typing, no inheritance arrow, easier to evolve while preserving IDE enforcement; (d) **remove entirely** — rely on duck typing + documentation. The brief MUST NOT default to (d); the option must be argued on its merits per base.
3. **R3.** Every cutter surface across the model tree (`to_cutter`, `female`/`male`, `.solid`-property-as-cutter, `cq_utils.WithAllowance`) MUST be surveyed. The brief proposes either (a) a single unified cutter protocol, or (b) a justified explanation per family of why the family stays distinct. Five existing allowance-parameter conventions (`overcut`, `radial_allowance`+`depth_allowance`, `profile`, `overlap`, bespoke kwargs) are addressed explicitly.
4. **R4.** The package layout (`mechanical/`, `lego/`, `xlego/`, `rc/`, `technic_ball_bearing/`) MUST be evaluated for category coherence and OSS readability. The brief recommends harmonization or justifies status quo, naming any specific renames or moves.
5. **R5.** Naming conventions across all public classes, methods, and properties MUST be audited for consistency. The brief flags any misleading name (e.g. `SlipperGearBase` for a class with no abstract methods) and recommends a rename or rationale-to-keep.
6. **R6.** `__init__.py` re-export discipline MUST be audited across `models/` and its subpackages. The brief recommends a uniform public-API policy (which symbols re-export at which level) and justifies it.
7. **R7.** Constructor ergonomics MUST be audited across families: parameter naming, presence/absence of `from_size`-style factory methods, `.solid` property convention, tolerance-profile handling, type-hint completeness. The brief flags inconsistencies and recommends a unified ergonomic shape.
8. **R8.** The shared infra surface — `cq_utils.py` (primitives + curves + `WithAllowance`) and `print_settings.py` (`ToleranceProfile`, `get_profile`) — MUST be evaluated for the same depth / naming / consistency criteria, focused specifically on whether each exposed name is something an OSS user would import and what their experience would be.
9. **R9.** Every recommendation MUST carry a per-recommendation **churn-cost vs benefit** classification (per user's stability policy: "let TL decide per-change"). Suggested classes: `low-churn / high-benefit`, `medium-churn / medium-benefit`, `high-churn / high-benefit`, plus an explicit `parked` bucket for issues TL identifies but defers. This enables fast human triage at Step 4.
10. **R10.** TL MUST propose a phased implementation plan grouping accepted recommendations into PR-sized clusters (e.g. P0 = trivial cleanup, P1 = naming/renames, P2 = cutter unification). Implementation is NOT part of this req — only the plan.
11. **R11.** Every recommendation that overlaps or conflicts with the existing Wave C C1 / Wave C C2 design space MUST be flagged. The brief either subsumes those backlog items, narrows them, or hands them off cleanly with a pointer.
12. **R12.** TL MUST surface backwards-compatibility implications for every recommendation that involves a rename, signature change, or removal. The Step 4 human review uses this to gate which churn lands pre-OSS vs post.

## Non-Functional Constraints

- **One artifact**, not a series of mini-briefs.
- Existing knowledge-base entries — CLAUDE.md, [vibe/INSTRUCTIONS.md](../../vibe/INSTRUCTIONS.md), the Known-Modelling-Pitfalls section, [docs/lego-technic.md](../../docs/lego-technic.md) — MUST NOT be invalidated by recommendations without explicit rationale.
- The TL design dialog MUST follow the `core-agents-design-flow` Step 3 termination contract (every requirement addressed or out-of-scope, every open question resolved, Module-depth table filled per the structural-optimization skill, non-blocking concerns cost-checked).
- The brief itself does not change any source file. Implementation is out of scope.

## Known Domain Constraints

- **License.** All Python files in `models/` carry the AGPLv3 header. Any new file added by recommendations inherits that requirement.
- **CadQuery / OCCT.** Geometric conventions in Known-Modelling-Pitfalls (chord-vs-arc overcut, blind-hole overcut policy, infinite-cutter rule, monotonicity check, single-solid topology assertion) are load-bearing. Recommendations MUST NOT regress these.
- **`build.toml`.** Concrete classes are registered by `module.path.ClassName`. Any rename or move recommendation must include a corresponding `build.toml` update in its implementation plan.
- **Lego Technic invariants.** 8mm stud grid, 4.8mm pin hole, 5.0mm axle tip-to-tip, 7.2mm beam thickness — these are physical-world constants not subject to refactor. Constants module (`models/lego/constants.py`) location and naming may evolve; numeric values do not.
- **Prior TL review (2026-05-13, chat-only).** Three candidates surfaced — collapse `Screw`/`Nut`/`BaseJoint` ABCs, screw `.to_cutter` shallow-wrapper cleanup, unified cutter protocol — plus three parked items in [todo.md](../../todo.md). The umbrella design pass MUST consume that prior review as prior art rather than re-deriving from scratch.
- **Prior structural review (2026-05-08, [tmp/structural-review-2026-05-08.md](../../tmp/structural-review-2026-05-08.md)).** A separate structural review from 5 days prior reached overlapping conclusions on the ABC shells. The umbrella design pass MUST cite where its conclusions agree with or supersede that earlier artifact.
- **Wave C platform coordination.** [tmp/platform-coordination-wave-c.md](../../tmp/platform-coordination-wave-c.md) records the surface communicated to `vibe-cading-platform` for the Wave C C1 / C2 coordination. Any recommendation that changes that surface MUST flag the coordination implication for Admin to route.

## Out of Scope

- **Implementation.** No code in `models/` is modified by this task. Implementation is downstream, triggered by approved phased plan in the design artifact.
- **`tools/` CLI surface** (`preview.py`, `view.py`, `section_slicer.py`, `build.py`, `engine_api/`). Out of scope per user's "models + shared infra it depends on" scope decision. TL MAY flag specific tools issues for follow-up tickets if they materially affect model API usage; it MUST NOT propose structural changes to them in this brief.
- **New model families.** No new fasteners, gears, joints, or RC parts.
- **`docs/` rewrite.** Doc updates flow naturally from accepted renames during implementation; they are not first-class deliverables of this design pass.
- **Wave C C1 / C2 design.** The umbrella brief MAY supersede or narrow those items but does NOT replace their platform-coordination dependency on `vibe-cading-platform#4`.
- **Open-source release timing, license choice, marketing/positioning.** Project-management concerns separate from this structural design pass.

## Open Questions

> These are PM's hand-off questions to TL — surfaced here so TL knows what the user expects design-dialog to resolve.

- [ ] **Contributor-extension lens vs maintainer-locality lens.** The 2026-05-13 PM↔user dialog surfaced that the original deletion-test verdict on `Screw` / `Nut` / `BaseJoint` was applied with maintainer-locality only and missed the contributor-extension argument: an OSS contributor adding `TitaniumWoodScrew(Screw)` gets `@abstractmethod` enforcement, IDE auto-completion, and a documented contract — none of which exist if the base is removed. TL MUST resolve per-base: does the contributor-locality value outweigh the current contract-drift problem? If yes, "repair and keep" or "replace with Protocol" beats "remove." If the structural-optimization skill needs a fifth false-positive carve-out for "contributor-extension contract," that's an Admin-routed instruction-maintenance follow-up — TL flags it, does not implement it.
- [ ] **What unifying concept fits "fastener"?** Separate `Screw` and `Nut` lineages, a shared `Fastener` ancestor with a clear protocol, or pure duck typing? The deletion test should give a verdict; if it doesn't, what is the disambiguating factor?
- [ ] **Is `xlego` a sustainable name for OSS?** It means "extended lego" but newcomers will not know that. Rename, alias, or document?
- [ ] **`print_settings.ToleranceProfile` ergonomics.** Is `from models.print_settings import ToleranceProfile, get_profile` the right shape for an OSS user, or should the surface evolve (e.g. simpler factory, configuration via `.env` only, etc.)?
- [ ] **`.solid` vs `.to_cutter()` vs `.female()` reconciliation.** Pre-stages Wave C C2 but is not blocked on platform coordination for the *design* phase. Should this brief produce a definitive protocol, or only constrain the C2 design space?
- [ ] **`rc/`, `technic_ball_bearing/`, `xlego/` coherence with `mechanical/` and `lego/`.** Are these categorizations sustainable, or do they reflect early experimentation that should reorganize for OSS?
- [ ] **Backwards-compat policy post-OSS.** What deprecation discipline applies after release? (Affects how cheaply renames can ship later if not done now.)

---

## Human Confirmation Checkpoint
- [x] Requirements reviewed and confirmed by human (2026-05-13)
<!-- Confirmed in main-session dialog after R2 was softened to remove the "default to remove" bias on ABCs. Proceeding to Step 3 (TL co-design). -->
