# Requirements: Shared STEP-analysis primitives for tools/

## Meta
- **Initiator role**: @admin
- **Date**: 2026-05-08
- **Domain integrity gate**: NO — pure tooling refactor; no model geometry, no data/model contracts, no engine-api JSON wire format affected.

---

## Problem Statement

Seven STEP-analysis CLI tools (`tools/face_catalog.py`, `tools/hole_finder.py`, `tools/face_distances.py`, `tools/step_summary.py`, `tools/section_slicer.py`, `tools/boolean_diff.py`, `tools/step_preview.py`) each independently import the same OCP namespaces (`OCP.BRepAdaptor`, `OCP.BRepGProp`, `OCP.GeomAbs`, `OCP.GProp`, `OCP.TopAbs`, `OCP.TopExp`) and re-define the same tiny helpers. `_vec3` appears in three tools verbatim; `_face_area` in three tools verbatim; `_count_shapes` would help two more tools but lives only in `step_summary.py`. None of the tools share a STEP-load Adapter that handles file existence, empty-shape error reporting, or future URI-based input translation. Surfaced as Candidate 5 of the structural review at `tmp/structural-review-2026-05-08.md`.

## User Story / Motivation

As a contributor adding a new STEP-analysis tool (e.g. a future "diff a STEP file against a model class" tool), I need shared primitives for STEP loading, face iteration, vector/area extraction, so I don't copy-paste 50 lines of OCP boilerplate from a neighboring tool and inherit its API drift.

## Functional Requirements

1. The repo MUST expose a single Module under `tools/` (e.g. `tools/step_primitives.py` or `tools/engine_api/step_primitives.py`) containing the shared STEP-analysis helpers: at minimum `vec3()`, `face_area()`, `count_shapes()`, plus a STEP-load function with consistent error reporting on missing/empty files.
2. `tools/face_catalog.py`, `tools/hole_finder.py`, `tools/face_distances.py`, `tools/step_summary.py`, `tools/section_slicer.py`, `tools/boolean_diff.py`, `tools/step_preview.py` MUST delegate to the shared Module for the consolidated helpers. No duplicated implementations remain.
3. The Module's STEP-load function MUST handle: (a) file-not-found → clear error message and non-zero exit, (b) file-exists-but-empty/unreadable → clear error message and non-zero exit, (c) success → returns the loaded shape(s) in a uniform type the tools agree on.
4. The repo MUST run all seven tools end-to-end against at least one representative reference STEP file (e.g. `valve_cap.step` already in the repo root, or a fixture STEP under `tmp/`) before sign-off and confirm no behavior change. JSON output (`--json` mode) MUST be field-by-field identical pre-/post-refactor.
5. The shared Module MUST carry the AGPLv3 header per project rule.
6. The Module MUST NOT introduce a CadQuery / OCP dependency where one isn't already present — the consuming tools all import OCP today, so this is essentially extracting their existing surface.

## Non-Functional Constraints

- No new third-party pip dependencies. OCP and CadQuery already pulled in by the consuming tools.
- The Module MUST be a thin wrapper: the goal is concentrating duplicate helpers, not adding a heavy abstraction layer over OCP.
- The Module's API MUST be stable enough that future tools (URI-aware, caching, etc.) can extend it without breaking the seven existing call-sites.

## Known Domain Constraints

- A possible future requirement is a URI-based return shape for tools consumed over MCP. The shared STEP-load function should be designed so a future URI translator can plug in without re-touching all seven tools — but the URI logic itself is OUT of scope for this refactor (nothing consumes these CLIs over MCP today).
- `tools/engine_api/extractor.py` is pure-AST and CadQuery-agnostic per `.agents/plans/engine-api-json.md` §1. The new STEP-primitives Module is the OPPOSITE — it imports OCP and CadQuery directly. Sibling location under `tools/engine_api/` is acceptable only if the extractor's no-CadQuery property is preserved (different files; clear separation).

## Out of Scope

- Changes to `engine_api.json` or to `tools/engine_api/extractor.py`.
- Changes to the `--json` output schema of any of the seven tools. JSON wire format is preserved exactly.
- Performance optimization (caching of expensive STEP loads is interesting future work but not this refactor).
- Adding new analysis primitives beyond the duplicate-extraction set.
- URI-based input translation. Captured in the Open Questions to ensure the API design doesn't preclude it, but the implementation is deferred.

## Open Questions

- [ ] Module location: flat `tools/step_primitives.py` vs. `tools/engine_api/step_primitives.py` vs. a new `tools/step_lib/` package? The design dialog decides; the engine_api package is a viable home only if the extractor's CadQuery-agnostic property is provably preserved (separate file, no shared imports).
- [ ] STEP-load return type: raw `TopoDS_Shape` (OCP-native) vs. CadQuery `Workplane` vs. a project-specific wrapper? Today the seven tools mix all three. The dialog standardizes — likely on `TopoDS_Shape` since that matches the OCP-native helpers, with CadQuery wrappers built per-tool as needed.
- [ ] Should `_face_bbox`, `_coaxial`, and `_count_shapes` (currently each in only one tool) move to the shared Module on speculation, or stay until a second consumer materializes (per the skill's one-adapter-vs-two-adapters diagnostic)?

---

## Human Confirmation Checkpoint
- [x] Requirements reviewed and confirmed by human  *(2026-05-09: human delegated Step 3 co-design to admin+tl, implicitly confirming the Step 2 artifact)*
