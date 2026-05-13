# Session backlog / parking lot

Short-lived items, ideas, and parked refactors that surfaced during a session
but are not actively being driven. Curated by PM. Promote to
[`.agents/plans/INDEX.md`](.agents/plans/INDEX.md) when an item earns a
design slot.

## Admin follow-ups

- **Upstream proposal: fifth false-positive carve-out for `core-agents:structural-optimization`.** The skill's deletion test currently has four canonical carve-outs (observability / versioning / security-boundary / cold-start-orientation). The 2026-05-13 PM↔user dialog on this project surfaced a legitimate fifth shape: **contributor-extension contract** — a class with no maintainer-side polymorphism that still earns its keep because external OSS contributors inherit / implement it for IDE auto-completion, `@abstractmethod` enforcement, or documented protocol shape. Project-local enforcement is in place (see `vibe/INSTRUCTIONS.md` → Code Quality & Open-Source Standards → Deep-Modules Dual-Lens Rule). Upstream path: route through `bump-review` skill once the next core-agents release window opens, or open a PR / issue against `fa-mc/core-agents` directly. Owner: Admin (human contributor, given the project does not ship a tracked Admin persona).

## Parked refactors — from 2026-05-09 TL deep-modules review

- **Rename `SlipperGearBase` → `SlipperGearAssembly`** ([models/xlego/slipper_gear/directional/base.py](models/xlego/slipper_gear/directional/base.py)). The class has no abstract methods and no extension hooks; the `Base` suffix misleads readers into expecting an inheritance pattern that does not exist. Naming nit, not structural depth.
- **Harmonize `models/mechanical/__init__.py` re-exports**. Currently exports `ClearanceHole`/`CounterboreHole`/`TeardropHole` only — not screws, nuts, joints, or gears, even though those subpackages re-export at their own level. Either re-export all top-level domain types from `models.mechanical` or remove the partial set so the public-API boundary is consistent.
- **Audit `cq_utils.tapered_arm_profile` / `archimedean_spiral_arc` for second-adapter justification**. Both are used by `slipper_gear` only today — single-adapter speculative seam under the deep-modules diagnostic. If no second consumer materializes, fold them back into the slipper-gear module.
