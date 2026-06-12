# Requirements: Sweep `__main__` viewer blocks from `models/` and deepen `tools/view.py`

## Meta
- **Initiator role**: @admin
- **Date**: 2026-05-09
- **Domain integrity gate**: NO — pure tooling / contributor-ergonomic refactor; no model geometry change, no engine-api wire format affected.

---

## Problem Statement

`vibe/INSTRUCTIONS.md` and `CLAUDE.md` both ban `ocp_vscode` imports and `if __name__ == "__main__":` viewer blocks in model files, and direct contributors to `tools/view.py`. Despite that, **40 of 55** model files in `models/**` carry such blocks (verified `grep -rlE 'if __name__ == "__main__"' models/ | wc -l → 40`). The blocks encode genuinely useful contributor demonstrations — single-class views (`show(obj.solid)`), multi-instance comparisons with named labels and colors (`show(s1, s2, s3, names=[…])`), and solid+cutter overlays (`show(joint.male(), joint.female())`) — that `tools/view.py` does not currently absorb. Three model files (`models/mechanical/joints/snap_fit.py`, `models/mechanical/joints/dovetail.py`, `models/mechanical/hinge.py`) carry `try: from .base import X / except ImportError: from base import X` import fallbacks whose only purpose is supporting direct script execution (which the policy forbids). Surfaced as Candidate 4 of the structural review at `tmp/structural-review-2026-05-08.md`. Wave A's `tools/model_loader.py` (commit `ee060d8`) is the natural foundation for the `tools/view.py` deepening — Wave B builds on it.

## User Story / Motivation

As a contributor authoring a new CadQuery model, I need a way to express *"show this class's solid (or its `to_cutter()` output) with optional labels / colors / multi-config side-by-side"* without writing a per-class `__main__` block — so the canonical viewer entry point stays `tools/view.py` and the `ocp_vscode` runtime dependency stays out of the engine package's import graph.

## Functional Requirements

1. `tools/view.py` MUST gain a structured way for a model class to declare multiple labeled demonstration shapes (solid, optional `to_cutter()` output, multi-instance side-by-side comparisons) such that `python3 tools/view.py <ModuleClass> --demo` (or equivalent invocation — exact CLI shape decided in Phase 3) renders the class's intended demonstration without executing any code in `models/**`.
2. Every `if __name__ == "__main__":` block in `models/**` MUST be deleted. After the refactor, `grep -rlE 'if __name__ == "__main__"' models/` MUST return zero matches.
3. Every `try: from .base import X / except ImportError: from base import X` import fallback in `models/**` (verified to exist in `snap_fit.py`, `dovetail.py`) MUST be normalized to the relative-import-only form (`from .base import X`). The `hinge.py` file's `try / except ImportError: pass` block lives inside its `__main__` and is removed by R2.
4. After the refactor, `grep -rlE 'from ocp_vscode' models/ tools/` MUST find `ocp_vscode` only in `tools/view.py`. No `models/**` file may import `ocp_vscode`, even transitively at module load time.
5. CI MUST enforce R2: a static check (extend `tools/check_license_headers.py` to also flag `__main__` blocks under `models/`, OR a new `tools/check_no_main_blocks.py`, OR an entry in the existing flake8 baseline) MUST exit non-zero if any `if __name__ == "__main__":` line appears in `models/**`. Decision deferred to Phase 3.
6. `python build.py` MUST produce STEP files identical to pre-Wave-B output (per the same tiered cmp + boolean_diff Jaccard ≥ 0.9999 + volume Δ < 0.01 % gate Wave A established). Sweeping `__main__` blocks must NOT alter any class's `.solid` accessor, `.to_cutter()` output, or `__init__` defaults.
7. The new file (if a separate CI check is created) MUST carry the AGPLv3 header per project rule.

## Non-Functional Constraints

- No new third-party pip dependencies.
- The demonstration-shape declaration MUST be lightweight (a single method or function per class; not a new ABC, not a new package). The structural-optimization skill's one-vs-two-adapter diagnostic applies — don't invent a Demo framework with one consumer.
- The deepened `tools/view.py` MUST continue to support its existing modes: single-class `<ModuleClass>` invocation (today's `view_single`), multi-class side-by-side (today's `view_multiple` / explicit `--export STEP` path), and `--assembly` for `assemble()`-style modules.
- The sweep MUST NOT touch any class's public constructor signature or `.solid` accessor — those are part of the engine-api JSON wire contract per `.agents/plans/engine-api-json.md`.

## Known Domain Constraints

- The 40 affected model files span every package: `models/mechanical/{screws,nuts,joints,gears,enclosures,inserts,bearings,magnets,standoffs,hinge,trailer_hitch_cover}`, `models/lego/{technic_axle,cutters/}`, `models/rc/servo/`, `models/xlego/{servos,slipper_gear}`. Sweep cannot be scoped to one package.
- Some `__main__` blocks reference helper variables / classes that exist only at runtime (e.g. `models/mechanical/joints/snap_fit.py` constructs a `cq.Workplane().box(...)` then cuts the female cavity into it for the demo). The demonstration encoding MUST be expressive enough to absorb these patterns, OR the contributor MUST be willing to lose that specific demo (Phase 3 decides per-file if any).
- `tools/view.py` already supports an `--assembly` mode that calls a module-level `assemble() → list[(solid, name, color)]`. The proposed `--demo` mode is shape-similar but class-scoped instead of module-scoped — Phase 3 decides whether to unify the two or keep them parallel.
- Wave A's `tools/model_loader.py` provides `instantiate(dotted, params)` and `resolve_solid(instance, missing=...)` — Wave B's deepened `tools/view.py` should reuse these (no duplicate loader logic).

## Out of Scope

- Refactoring or unifying any model class's public API (Candidate 2 of the structural review).
- Cutter-ABC unification (Candidate 2 — high engine-api wire-format risk; explicitly Wave C).
- Tolerance/profile glue refactor (Candidate 1 — Wave C, separate platform-coordination story).
- Model class deletions, additions, or renames.
- Changes to `models/**` constructor parameters, `.solid` accessor, or `to_cutter()` signatures.
- Engine-api JSON schema changes — `engine_api.json` MUST be byte-identical pre/post Wave B.
- `models/cq_utils.py` and `models/print_settings.py` `try / except ImportError` blocks — those serve real purposes (optional dotenv parsing, lazy imports), not direct-execution path-juggling. Out of scope.
- Changes to existing `--assembly` modules in `models/xlego/servos/` (those use the established `assemble()` pattern correctly).

## Open Questions

- [ ] **Demo encoding shape.** Three candidate approaches:
  - **(A) CLI-only**: extend `tools/view.py` with multi-`--params` and `--with-cutter` flags; the demo lives in the CLI invocation, not the class. Pro: zero per-class code change beyond block deletion. Con: complex demos (snap_fit's cut-female-into-block pattern) can't be expressed in CLI flags.
  - **(B) Class-scoped method**: each class that wants a demo defines `def demo(cls) -> list[tuple[Solid, str, color]]` (or similar). `tools/view.py --demo` invokes it. Pro: complex demos are expressible in Python; matches `assemble()` pattern. Con: 40 classes potentially gain a new method (though classes with trivial demos can opt out).
  - **(C) Module-level function**: each module that wants a demo defines a top-level `demo() → list[tuple[…]]`. Same shape as `--assembly`. Pro: unifies with existing assemble pattern. Con: same 40-file-edit cost.
- [ ] **CI enforcement mechanism.** Extend `tools/check_license_headers.py` (already package-aware, scans `models/`)? Add a new `tools/check_no_main_blocks.py`? Or add a flake8/pylint rule? Phase 3 decides.
- [ ] **Per-class demo scope.** Of the 40 files, how many genuinely need a preserved demo vs how many can be deleted entirely (the demo was a one-off contributor sanity check)? Phase 3 decides; the sweep can be selective.
- [ ] **Renderer back-end.** `ocp_vscode.show()` writes to the OCP CAD viewer (port 3939). Should `--demo` also support an SVG-export mode (so the CI machine can render demos without needing `ocp_vscode` running)? Or is interactive-only acceptable for demos?

---

## Human Confirmation Checkpoint
- [x] Requirements reviewed and confirmed by human  *(2026-05-09: human authorized continuous Wave B execution; "don't stop unless you need me to make a critical decision")*
