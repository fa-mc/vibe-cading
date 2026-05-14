# Plans Index

Single-glance backlog view maintained by PM. Source of truth for plan status across sessions.

## Schema

| Column | Meaning |
|---|---|
| Task | Short human-readable title |
| Plan file | Relative path under `.agents/plans/` |
| Status | `proposed` / `designed` / `in-flight` / `blocked` / `done` / `archived` |
| Owner role | Role currently responsible, or `—` if unassigned |
| Blocker | Short note if blocked; `—` otherwise |
| Last update | YYYY-MM-DD of last status change |

## Backlog

| Task | Plan file | Status | Owner role | Blocker | Last update |
|---|---|---|---|---|---|
| FDM tolerance gauge | [fdm-tolerance-gauge.md](fdm-tolerance-gauge.md) | done | — | — | 2026-04-02 |
| Fastener drive sockets | [fastener_drives.md](fastener_drives.md) | done | — | — | 2026-05-08 |
| Snap-fit cantilever hooks | [snap-fit-hooks.md](snap-fit-hooks.md) | done | — | — | 2026-05-08 |
| Structured `engine_api.json` (RFC #2) | [engine-api-json.md](engine-api-json.md) | done | — | — | 2026-05-08 |
| Establish CI baseline | [2026-05-08-ci-baseline_design.md](2026-05-08-ci-baseline_design.md) | done | — (PR #5 rebase-merged, commits 81680d5 + 4d5fd9f) | — | 2026-05-08 |
| Wave A C3 — shared model-class loader | [2026-05-08-shared-model-loader_design.md](2026-05-08-shared-model-loader_design.md) | done | — (commit ee060d8) | — | 2026-05-09 |
| Wave A C5 — shared STEP-analysis primitives | [2026-05-08-shared-step-primitives_design.md](2026-05-08-shared-step-primitives_design.md) | done | — (commit 4bb4989) | — | 2026-05-09 |
| Wave B C4 — `__main__` block sweep + `tools/view.py --demo` | [2026-05-09-main-block-sweep_design.md](2026-05-09-main-block-sweep_design.md) | done | — (commit 774a010) | — | 2026-05-09 |
| Wave C C1 — Cutter↔ToleranceProfile glue + `get_screw_allowances` | _(no design artifact yet)_ | blocked | — | platform coordination filed: vibe-cading-platform#4 | 2026-05-09 |
| Wave C C2 — Unified Cutter Interface | _(no design artifact yet)_ | blocked | — | platform coordination filed: vibe-cading-platform#4 (major schema bump) | 2026-05-09 |
| Structural review — deep-modules pass on `models/` | _(chat-only — see Notes)_ | done | — | — | 2026-05-13 |
| Pre-OSS structural design pass — `models/` + shared infra | [2026-05-13-pre-oss-models-structure_design.md](2026-05-13-pre-oss-models-structure_design.md) | designed | Step 4 — awaiting human final approval | — | 2026-05-14 |
| ↪ Collapse pass-through ABC shells (`Screw` / `Nut` / `BaseJoint`) | subsumed by umbrella above | proposed | — | will re-curate after umbrella design completes | 2026-05-13 |
| ↪ Screw `.to_cutter()` shallow-wrapper cleanup | subsumed by umbrella above | proposed | — | will re-curate after umbrella design completes | 2026-05-13 |

## Notes

- `snap-fit-hooks.md` brief specified `models/mechanical/snap_fit.py`; actual implementation lives at [models/mechanical/joints/snap_fit.py](../../models/mechanical/joints/snap_fit.py) (joints submodule). Brief path is outdated, not a defect.
- **2026-05-09 TL deep-modules review of `models/`** — surfaced three deepening candidates. Two are tracked above as standalone `proposed` rows; the third (unified cutter protocol) overlaps with **Wave C C2** and pre-stages its design rationale: cutters today are 7 distinct shapes (`to_cutter` / `female` / `.solid` property) with five different allowance-parameter conventions (`overcut`, `radial_allowance`+`depth_allowance`, `profile`, `overlap`, bespoke kwargs). Whoever picks up C2 should treat the cutter survey in this review as load-bearing prior art rather than re-surveying. Lower-yield items (rename `SlipperGearBase` → `SlipperGearAssembly`, harmonize `models/mechanical/__init__.py` re-exports, audit `cq_utils.tapered_arm_profile` / `archimedean_spiral_arc` for second-adapter justification) are parked in [todo.md](../../todo.md).
