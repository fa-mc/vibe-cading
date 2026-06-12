# Requirements: Shared model-class loader for tools/

## Meta
- **Initiator role**: @admin
- **Date**: 2026-05-08
- **Domain integrity gate**: NO — pure tooling refactor; no model geometry, no data/model contracts, no engine-api JSON wire format affected.

---

## Problem Statement

Five CLI tools (`build.py`, `tools/preview.py`, `tools/view.py`, `tools/check_topology.py`, `tools/check_polar_monotonicity.py`) each independently re-implement the same Module: split `module.path.ClassName` on the last dot, `importlib.import_module`, `getattr` for the class, instantiate with kwargs from `--params key=value` (parsed identically), pull `.solid`. The shared logic is ~30 lines per tool, with subtle drift between sites. `_parse_params` exists in three near-identical copies (`view.py`, `preview.py`, plus an inline copy in `build.py`'s tomllib path). Three of the tools also add `models/` to `sys.path` independently. Surfaced as Candidate 3 of the structural review at `tmp/structural-review-2026-05-08.md`.

## User Story / Motivation

As a contributor adding a new CLI tool that operates on a CadQuery model class, I need a single Module that handles dotted-path → instance → `.solid` resolution and `--params` parsing, so I don't copy-paste 30 lines from a neighboring tool and inherit its drift.

## Functional Requirements

1. The repo MUST expose a single Module under `tools/` (e.g. `tools/model_loader.py` or `tools/engine_api/loader.py`) that handles: (a) parsing `module.path.ClassName` to a Python class, (b) parsing `--params key=value` strings into a kwargs dict, (c) instantiating the class with those kwargs, (d) returning the resulting object plus its `.solid` accessor result if present.
2. `build.py`, `tools/preview.py`, `tools/view.py`, `tools/check_topology.py`, `tools/check_polar_monotonicity.py` MUST delegate their class-loading and parameter-parsing logic to that Module. No duplicated implementations remain.
3. The Module's behavior MUST preserve every existing tool's CLI surface: same `--params` syntax, same dotted-path syntax, same exit-code semantics on "class not found" / "instance has no `.solid`" / "params don't match constructor".
4. The Module MUST NOT import CadQuery or `ocp_vscode` at module load time — `import_module` of a model class triggers CadQuery indirectly, which is acceptable, but the loader Module itself must be CadQuery-agnostic so it remains testable in isolation.
5. The repo MUST run all five tools end-to-end against at least one representative model class (e.g. `models.lego.technic_axle.TechnicAxle`) before sign-off and confirm no behavior change. `python build.py` MUST still produce identical STEP files for `build.toml` entries (byte-identical or volume-identical via `boolean_diff`).
6. The shared Module MUST carry the AGPLv3 header per project rule.

## Non-Functional Constraints

- Pre-existing `tools/engine_api/` package layout suggests `tools/engine_api/loader.py` as a natural home; the design dialog decides between that and a flat `tools/model_loader.py`. Either way, the Module is internal to `tools/` and is NOT part of the engine class catalog walked by `gen_engine_api.py`.
- No new third-party pip dependencies. Standard library only.
- The Module MUST be importable without `models/` already on `sys.path` — it adds the path itself if needed (currently three tools do this independently).

## Known Domain Constraints

- The `.solid` accessor convention is encoded in `engine_api.json`'s `result_accessor` field (per `.agents/plans/engine-api-json.md`). The loader must return `.solid` for the standard case but tolerate classes without `.solid` (e.g. assemblies that expose `assemble()` per `tools/view.py`'s `--assembly` mode). The design dialog decides the exact API shape.
- `tools/view.py` has an `--assembly` mode that calls top-level `assemble()` instead of class instantiation. The loader Module either covers this case or `view.py` retains the assembly path while delegating the class-instantiation path.
- `build.py` reads kwargs from `build.toml` (TOML), not from `--params`. The loader's parameter-parsing API must accept already-parsed dicts, not just CLI strings.

## Out of Scope

- Changes to `engine_api.json` schema or to `tools/engine_api/extractor.py`. The loader is consumed by the CLI tools, not by the extractor.
- Candidate 4 (`__main__` viewer blocks). That refactor builds on top of this one but is sequenced as Wave B per the TL recommendation.
- Adding new CLI features. This is a pure consolidation.
- Performance optimization. The loader's runtime cost is negligible vs. CadQuery model build time.

## Open Questions

- [ ] Module location: `tools/model_loader.py` (flat) vs. `tools/engine_api/loader.py` (under engine_api package)? Argument for engine_api: the loader's job IS resolving the engine class catalog, so it sits naturally there. Argument against: `engine_api/` is currently AST-only and CadQuery-agnostic; the loader does real imports and therefore has different deploy-time properties.
- [ ] Does the loader also handle `--assembly` mode (top-level `assemble()` calls), or does `view.py` retain that path?
- [ ] Error mode: when `.solid` is absent, raise vs. return `None` vs. return the instance? Each of the five tools handles this differently today; the design dialog standardizes.

---

## Human Confirmation Checkpoint
- [x] Requirements reviewed and confirmed by human  *(2026-05-09: human delegated Step 3 co-design to admin+tl, implicitly confirming the Step 2 artifact)*
