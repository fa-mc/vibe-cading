# Design: Pre-OSS structural design pass — `models/` + adjacent shared infra
<!-- Filename: 2026-05-13-pre-oss-models-structure_design.md (tracked in git under .agents/plans/) -->

## Meta
- **Requirements ref**: [2026-05-13-pre-oss-models-structure_req.md](2026-05-13-pre-oss-models-structure_req.md)
- **Requester role**: User (acting as Admin / domain expert; PM-curated the req)
- **Date**: 2026-05-13
- **Dialog rounds**: 7 (Round 1 methodology / Round 2 per-base verdicts / Round 3 package partition / Round 4 cutter unification / Round 5 naming + ergonomics / Round 6 shared infra / Round 7 synthesis)

---

## Objective

Produce a comprehensive structural recommendation for `models/` + `models/cq_utils.py` + `models/print_settings.py`, classifying every per-base / per-cutter / per-package / per-name finding by churn-cost vs benefit, so the user can triage which structural changes land pre-OSS-release versus which defer.

## Architecture / Approach

### Approach chosen — Two-Lens Deletion-Test Methodology (project-ratified)

Round 1 of this dialog ratified the methodology as project policy. The rule is now codified at **[vibe/INSTRUCTIONS.md:117](../../vibe/INSTRUCTIONS.md#L117) — Deep-Modules Dual-Lens Rule**, which adds two important refinements over my initial proposal:

1. **Verdict preference ordering on drift.** When an abstract contract has drifted from concrete implementations, *prefer `repair` or `replace-with-Protocol` over `remove`*. The justification: "lying contracts mislead contributors; honest contracts onboard them." A drifted contract is fixable; the existence of drift is a poor reason to delete the abstraction entirely.
2. **Project-wide bias toward contributor-locality.** "Contributor onboarding is a first-class structural concern, not a postscript." This affects every round of the brief, not just bases — cutter naming, package layout, constructor ergonomics, `__init__.py` discipline all get reweighted toward contributor experience.

The Admin-routed follow-up to propose the fifth false-positive carve-out (contributor-extension contract) upstream to `core-agents` is recorded in [todo.md](../../todo.md) under "Admin follow-ups."

**Diagnostic procedure for every existing Module evaluated in this brief:**

1. **Maintainer-locality deletion test.** Imagine deleting the Module. Where does complexity reappear in the *existing* codebase — call sites, polymorphism, internal collaborators? Evidence required: grep for `isinstance` checks, type annotations naming the Module, call sites holding polymorphic references.

2. **Contributor-locality deletion test.** Imagine an OSS contributor adding a new family member six months after release. With the Module: what mechanical enforcement does inheritance / Protocol membership / convention give them? Without it: what failure mode is likely (silent contract drift, missing methods caught only at runtime, divergent ergonomics)? Evidence required: walk the contributor flow concretely — what does their IDE show, what does their test failure look like.

3. **Synthesis verdict.** Per-Module, choose ONE of:
   - **`keep`** — both lenses pass; current state is correct.
   - **`repair`** — at least one lens fails *because the current implementation lies* (signature drift, misleading name, dead enforcement). Fix the lie; keep the structure.
   - **`replace-with-Protocol`** — contributor-locality passes (contract is real); maintainer-locality passes; but `ABC + @abstractmethod` is the wrong *form* (no shared implementation, inheritance arrow adds reading cost without payoff). `typing.Protocol` (PEP 544 structural typing) preserves IDE enforcement and contract documentation without the inheritance arrow.
   - **`remove`** — both lenses fail. The Module concentrates nothing the codebase or contributors need.

4. **False-positive carve-outs** (per structural-optimization skill): observability seam / versioning seam / security-boundary seam / single-cold-start-entry-point seam. **Plus an additional shape surfaced by this design dialog: contributor-extension-contract** — a Module that earns its keep by orienting *future contributors* who add new family members. (TL will flag this as a potential fifth canonical carve-out for Admin-routed skill-evolution follow-up; this brief does NOT itself amend the skill.)

5. **Effort-vs-benefit classification** (per req R9, refined Round 5 follow-up): every recommended change is tagged with implementation-effort-only labels (no "user churn" axis since no external users exist):
   - `LE/HB` — low effort, high benefit (no-brainer cleanup)
   - `ME/MB` — medium effort, medium benefit (judgment call)
   - `HE/HB` — high effort, high benefit (large rewrite, but worth doing — was previously labeled `HC/HB` "high churn, high benefit")
   - `parked` — TL identified the issue but recommends deferring; reason noted

6. **Backwards-compatibility surfacing** (per req R12): ~~every recommendation that involves a rename, signature change, or removal records what would break for a hypothetical existing user.~~ **SUPERSEDED by Round 5 follow-up:** user confirmed "no external users at the moment, no need to consider churning." R12 becomes documentation-only — list what changes structurally, but no need to gate land-now-vs-defer based on hypothetical breakage. Churn classification simplifies from "user pain" to **implementation effort only**.

### Gear deepening proposal *(Round 2 closure)*

User direction in Round 2: "current version is probably not deep enough — lay foundation so contributors can build on top." The existing `Gear` base validates parameters and exposes derived radii, but every concrete subclass (`SpurGear`, `HelicalGear`, `RackGear`) re-implements involute-tooth math, bore-subtraction, and tooth-array generation independently. That's duplication, not depth. A contributor adding a new gear family (`BevelGear`, `WormGear`, `InternalRingGear`) today must re-derive the involute curve from scratch.

**Proposed deepenings (numbered for reference):**

1. **`_involute_tooth_profile_2d() -> list[tuple[float, float]]`** — shared involute-flank generator. Concrete subclasses consume the same canonical curve instead of each re-deriving it. Removes the largest geometry-math duplication in the gears subtree.
2. **`_gear_blank_with_teeth_2d() -> cq.Workplane`** — shared full-toothed 2D cross-section sketch. `SpurGear.solid` becomes `extrude(face_width)`; `HelicalGear.solid` becomes a swept extrude with helix angle; `RackGear` re-uses the involute primitives but unrolls them linearly. Subclasses no longer build the tooth array — they only specify the extrusion / sweep path.
3. **`bore_cutter(profile: ToleranceProfile) -> cq.Workplane | None`** — shared bore-subtraction tool keyed off `self.bore`. Currently each subclass handles bore cutting ad-hoc; centralize.
4. **`mesh_with(other: "Gear", phase: float = 0.0) -> tuple[cq.Workplane, cq.Workplane]`** — public method returning both gears positioned at correct center distance with teeth phase-aligned. Replaces `center_distance_to(other)` (which is just a number, dormant in callers) with the actionable visualization / assembly form.
5. **Composable `Bore` types** — `RoundBore(diameter)`, `HexBore(across_flats)`, `DBore(diameter, flat_offset)`, `KeyedBore(diameter, keyway_width, keyway_depth)`. `Gear.__init__(bore: Bore | float | None = None)` — pass either a number (interpreted as round bore radius for backward-compat) or a typed bore object. Mixin pattern that any gear consumes.
6. **`Gear.from_iso(module, teeth, ...)`** — classmethod factory that validates `module` against ISO standard series (`0.5, 0.8, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0`). Convenience for OSS users who don't know which modules are "standard."

**Optional parameters deferred** (can land post-OSS without restructure): `backlash: float = 0.0` (radial flank clearance), `profile_shift: float = 0.0` (addendum modification — needed for low-tooth-count gears without undercut). Tracked as known follow-ups in todo.md after design lands.

**Backwards-compat:** existing `SpurGear`, `HelicalGear`, `RackGear` public APIs (`__init__`, `.solid`) are preserved. Internal `_build_*` methods rewrite to delegate into the new shared primitives. No call site at user level changes. Churn classification: `HC/HB` — high churn (every gear subclass body rewritten), high benefit (foundation for arbitrary new gear types).

### Module depth *(per new Module proposed)*

| Module | Behaviour concentrated | Caller leverage & locality |
|---|---|---|
| `ScrewProtocol`, `NutProtocol`, `JointProtocol` (PEP 544) | Documented contract surface for each fastener / joint family — method signatures, return types, semantic invariants. No implementation; structural typing only. | OSS contributors writing `class TitaniumScrew:` get IDE autocomplete + `isinstance(x, ScrewProtocol)` checks for any code that wants to dispatch on family. Locality: every contract lives at one file (`models/mechanical/screws/protocol.py` etc.); concrete classes don't carry an inheritance arrow. |
| `Gear._involute_tooth_profile_2d` (deepening) | Canonical involute-curve generation; the math single contributor would otherwise re-derive per gear type. | New gear-type contributor (`BevelGear`) inherits `Gear` and consumes the curve — they implement only the unique twist (sweep/loft path), not the math. Locality: math lives in one file; bugs in tooth curve fixed once. |
| `Gear._gear_blank_with_teeth_2d` (deepening) | Full 2D toothed cross-section. | Subclasses only specify the extrusion / sweep path. Three current gear types lose 100+ lines of duplicated array-generation code; new types start with a tested foundation. |
| `Gear.bore_cutter(profile)` (deepening) | Bore-subtraction tool, tolerance-aware. | Concrete gears stop hand-coding bore cuts. Locality: bore clearance / overcut convention lives at one method, not five. |
| `Gear.mesh_with(other, phase=0.0)` (deepening) | Two-gear positioning at correct center distance with phase-aligned teeth. | OSS contributor previewing a gearbox calls `g1.mesh_with(g2)` — gets both solids positioned for `tools/view.py` directly. Locality: meshing-positioning logic lives in one method; visualizations / assemblies stop re-deriving it. |
| `RoundBore`, `HexBore`, `DBore`, `KeyedBore` (new composable types) | Bore-shape variations as typed objects. | OSS contributor passes `Gear(bore=HexBore(across_flats=5.0))` instead of hand-cutting a hex pocket post-hoc. Locality: bore taxonomy concentrated; mixable with any gear type. |
| `SlipperGearAssembly` (renamed from `SlipperGearBase`) | Assembly logic for ring + plate + spring with alignment offsets. (Behaviour unchanged from current `SlipperGearBase`; the deepening is in the *name* honestly communicating "assembly", not "base class to extend.") | Contributors reading the file understand the class isn't a base they extend; they instantiate or compose. |

### Alternatives rejected

- **`Gear.solid` left as the only contract; no shared geometric primitives.** Rejected — duplication across `SpurGear` / `HelicalGear` is real and growing; contributors adding new gear types would re-derive the involute curve. Round 2 user direction was explicit: "lay foundation so people can build on top."
- **Move `Gear` base to `Protocol` route alongside Screw / Nut / Joint.** Rejected — `Gear` has substantial shared *implementation* (validation, derived radii, will gain involute primitives). Protocol provides contract-only typing; ABC provides contract + shared methods. Use the right tool. `Gear` stays an ABC because it carries shared code; Screw / Nut / Joint go Protocol because they don't.
- **Backlash + profile_shift as Round 2 deliverables.** Rejected — both are parametric additions that can land post-OSS without restructure. Defer to keep this brief focused on structural pre-OSS finalization.

### Package layout & partition *(Round 3)*

User confirmed **Option B**: `models/applications/` subdir under existing tree. Single import root preserved; OSS contributors browsing `models/` see generic primitives first, project-specific end-products in a clearly-labeled subtree.

**File-by-file disposition** *(populated from user direction in Round 3 + TL inference)*:

| Current path | Disposition | New path | Rationale |
|---|---|---|---|
| `models/mechanical/trailer_hitch_cover.py` | **DELETE** | — | User: "remove this entirely." Also drop any `build.toml` entry. |
| `models/rc/hex_wheel_hub.py` | **RENAME + KEEP as RC-generic primitive** | `models/rc/freespin_hex_hub.py` | User confirmed `freespin_hex_hub` — the free-spinning aspect (vs. fixed-to-shaft driven wheel) is what makes this part distinct. |
| `models/xlego/` (whole subtree) | **RENAME** | `models/lego_adapters/` | User confirmed `lego_adapters/`. Flagged non-blocking concern: term sounds narrower than the actual function (could include connectors, mounts, bridges). Defensible interpretation — "adapter" in mechanical engineering is broad enough to encompass connectors. Revisit if a clearly non-adapter family materializes. |
| `models/xlego/axle_to_pin_bore_adapter.py` | **KEEP as adapter** | `models/lego_adapters/axle_to_pin_bore_adapter.py` | Generic xlego adapter primitive. |
| `models/xlego/motors/mount_plate.py` | **MOVE to applications** | `parts/arrma_vorteks_223s/motor_mount_plate.py` | User: this is the "Arrma motor plate" — vehicle-specific end-product. Co-locate with `esc_mount.py` (same vehicle). |
| `models/xlego/servos/sg90/servo_mount.py`, `servo_mount_half.py` | **KEEP as generic adapter** | `models/lego_adapters/servos/sg90_mount.py`, `sg90_mount_half.py` | User confirmed generic — SG90-to-Lego mount, not vehicle-specific. Goes into the renamed adapter layer. |
| `models/xlego/servos/{cam_utils,shaft,shaft_body,shaft_crown,shaft_with_saver}.py` | **KEEP as SG90 working assembly in library** *(2026-05-14 correction)* | `vibe_cading/lego_adapters/servos/{...}.py` | These are part of the SG90 servo replacement-shaft + mount assembly. Dependency-graph verification confirmed slipper_gear does NOT import any of these files. The drafting-TL initially mis-classified them as slipper-gear-coupled; user (in Round 7.5 dialog) corrected. STAY in library. |
| `models/xlego/slipper_gear/*` | **MOVE to experiments** (Option 2) | `experiments/slipper_gear/` | User chose Option 2 — preserve R&D in repo for personal future iteration; not part of OSS library. `build.toml` does NOT register experiments. |
| `cq_utils.tapered_arm_profile`, `cq_utils.archimedean_spiral_arc` | **MOVE to experiments** (single-adapter rule) | `experiments/slipper_gear/curves.py` (or similar) | Both helpers exist only to serve slipper_gear. Moving them with their only caller resolves the single-adapter speculative-seam flag from `todo.md`. `cq_utils.py` becomes leaner; the OSS library stops exposing curve generators with no documented use case. |
| `models/technic_ball_bearing/axle_sleeve.py` | **GENERICIZE + MOVE** | `models/lego_adapters/technic_axle_to_bearing_sleeve.py` *(proposed)* | User: "We can make it generic. The purpose is to adapt the lego technic axle (cross shaped) through ball bearings (ID >= 5mm)." Belongs in the adapter layer alongside other Lego↔non-Lego bridges. Drop the standalone `technic_ball_bearing/` directory once moved. |
| `models/rc/vorteks_223s/esc_mount.py` | **MOVE to applications** | `parts/arrma_vorteks_223s/esc_mount.py` | Vehicle-specific end-product. Drop the `rc/vorteks_223s/` directory once moved. |
| `models/rc/servo/sg90.py` | **KEEP** | `models/rc/servo/sg90.py` | Standard hobby servo (SG90 is industry-standard). Stays in library as a wrapper for a commercial part. |
| `models/rc/__init__.py` | **REVIEW** | — | After moves, `rc/` contains only generic-RC primitives (`idler_hex_hub.py`, `servo/sg90.py`). Re-export discipline reviewed in Round 5. |
| `models/lego/*` | **KEEP as-is** | unchanged | Pure-Lego primitives (constants, axle, gear_28t, technic cutters). No moves. |
| `models/mechanical/*` (minus `trailer_hitch_cover.py`) | **KEEP as-is** | unchanged | Generic parametric mechanical primitives. No moves. |

### Slipper gear disposition

User: "I was experimenting with two designs, but they were not good enough."

**Three options:**

1. **Remove entirely.** Delete `models/xlego/slipper_gear/`, `models/xlego/servos/{cam_utils,shaft,shaft_body,shaft_crown,shaft_with_saver}.py`, and the corresponding `cq_utils.tapered_arm_profile` / `cq_utils.archimedean_spiral_arc` helpers (which exist only to serve slipper_gear). Cleanest OSS release; nothing experimental ships.

2. **Move to an `experiments/` top-level folder** (outside `models/`). Preserves the R&D for the user's own future iteration but explicitly marks it as not-shipped-as-library. OSS release ignores it; OSS contributors don't see it as a model they could subclass.

3. **Salvage the parametric primitives, drop the assembly.** Extract `SlipperRing` (ramp-cam math), `SlipperSpring` (tapered-arm 2D profile), and `SlipperPlate` if they're independently useful as parametric primitives. Move them to `models/applications/slipper_gear_experiment/` or to a generic location if the user wants them as library primitives. Delete the assembly orchestration layer (`SlipperGearBase` → `SlipperGearAssembly` rename moot if the assembly is removed).

**TL recommendation: Option 1 (remove entirely).** Reasoning:
- "Not good enough" is the cleanest signal; pre-OSS is the right moment to drop failed experiments rather than carry them as embarrassing artifacts.
- The `cq_utils` helpers (`tapered_arm_profile`, `archimedean_spiral_arc`) were already flagged in `todo.md` as single-adapter speculative seams. Removing slipper_gear removes the single adapter and resolves the helper question simultaneously.
- An `experiments/` folder is a "I'll fix this later" trap; pre-OSS is when the housekeeping is cheapest.
- If the user later wants to retry slipper-gear from scratch, `git log` preserves the prior attempt — it's not lost.

**Option 2 is defensible** if the user wants to keep iterating personally without re-checking out old commits.

**Option 3 is only worth doing** if `SlipperRing`'s ramp-cam math is genuinely reusable for some other future part the user has in mind — which is speculative second-adapter justification, the exact pattern the deep-modules diagnostic flags as a false seam.

## Data & Interface Contracts

_Domain integrity gate is NO. Section retained for any Module-protocol contracts that the cutter-unification analysis introduces (Round 3+)._

## Implementation Plan

Eight phases. Each phase = one PR-sized cluster. Each is independently verifiable. Effort labels are implementation-effort-only per Round 5 follow-up (no external users = no churn-cost axis).

### Phase 0 — Skeleton scaffolding *(LE/HB; ~1.5 hr)*
- [ ] **T0.1** — Create `experiments/` top-level directory with `experiments/.gitkeep`.
- [ ] **T0.2** — Create `parts/` top-level directory with `parts/__init__.py` (empty namespace marker so `parts.*` module paths resolve).
- [ ] **T0.3** — Create `parts/arrma_vorteks_223s/__init__.py`.
- [ ] **T0.4** — Create `.env.example` at workspace root documenting all supported env vars (`VIBE_MACHINE_PROFILE`, `PIN_HOLE_PRINTED`, `DEFAULT_CORNER_RADIUS`, `DEFAULT_LEAD_IN`, `GH_TOKEN`).
- [ ] **T0.5** — Scaffold `tests/` directory: create `tests/__init__.py`, `tests/conftest.py` (empty initial stub), and `pytest.ini` at workspace root (or `[tool.pytest.ini_options]` block in a follow-up). Test files referenced by T4 / T5 / T6 / T13 / T15 live under `tests/` and import from `vibe_cading.*` and `parts.*`.
- [ ] **T0.6** — Add a `pytest` job step to `.github/workflows/ci.yml` (the actual file edit happens in Phase 1 T1.16 along with the path renames; T0.6 is the design-time decision to include pytest in CI).
- [ ] **T0.7** — Confirm Python version constraint (`>=3.10` for `typing.Protocol` / structural-typing maturity). Record in `pytest.ini` or wherever the project tracks runtime version.
- [ ] **T0.8** — Snapshot pre-refactor build outputs: `cp -r output/ tmp/pre-refactor-output/` (per Developer-reviewer live verification: actual build target directory is `output/`, not `build/`). This snapshot becomes the reference for T2 volume-diff comparisons. Do this BEFORE Phase 1 begins.

### Phase 1 — Package rename + file moves + import updates *(ME/HB; ~3 hr)*
Single atomic commit. Pure file-relocation + import-path-update. No semantic changes. **No `pyproject.toml`** — see Round 3 follow-up §"Decision history."

**1A — Top-level package rename (`models/` → `vibe_cading/`):**
- [ ] **T1.1** — `git mv models vibe_cading` to preserve history.
- [ ] **T1.2** — Global find-and-replace `from models.` → `from vibe_cading.` and `import models.` → `import vibe_cading.` across every `.py` under `vibe_cading/`, `tools/`, `tests/`, root scripts (`build.py`), and any TOML/Markdown/YAML referencing these import paths.
- [ ] **T1.3** — Update `build.toml` library entries from `models.…` → `vibe_cading.…`.

**1B — Within-package partitions and renames:**
- [ ] **T1.4** — Delete `vibe_cading/mechanical/trailer_hitch_cover.py`. (Note: not registered in `build.toml` per reviewer verification — no build.toml edit needed for this task.)
- [ ] **T1.5** — Rename `vibe_cading/rc/hex_wheel_hub.py` → `vibe_cading/rc/freespin_hex_hub.py`. Rename the class `HexWheelHub` → `FreespinHexHub` (final). Update `build.toml`.
- [ ] **T1.6** — Rename subtree `vibe_cading/xlego/` → `vibe_cading/lego_adapters/`. Update every `from vibe_cading.xlego...` import — including within the subtree, in `tools/`, in tests, in `build.toml`.
- [ ] **T1.7** — Move + genericize `vibe_cading/technic_ball_bearing/axle_sleeve.py` → `vibe_cading/lego_adapters/technic_axle_to_bearing_sleeve.py`. Update class name + parameter naming for the generic ID ≥ 5 mm framing. Drop empty `vibe_cading/technic_ball_bearing/` directory.

**1C — Project-specific to top-level `parts/`:**
- [ ] **T1.8** — Move `vibe_cading/lego_adapters/motors/mount_plate.py` → `parts/arrma_vorteks_223s/motor_mount_plate.py`. Drop empty `vibe_cading/lego_adapters/motors/` directory.
- [ ] **T1.9** — Move `vibe_cading/rc/vorteks_223s/esc_mount.py` → `parts/arrma_vorteks_223s/esc_mount.py`. Drop empty `vibe_cading/rc/vorteks_223s/` directory.

**1D — Experiments out:**
- [ ] **T1.10** — Move ONLY `vibe_cading/lego_adapters/slipper_gear/` → `experiments/slipper_gear/`. The SG90 shaft files (`cam_utils.py`, `shaft.py`, `shaft_body.py`, `shaft_crown.py`, `shaft_with_saver.py`) STAY in `vibe_cading/lego_adapters/servos/` (corrected from earlier draft per 2026-05-14 dialog — they are part of a working SG90 assembly, NOT slipper-gear-coupled).
- [ ] **T1.11** — Move `vibe_cading.cq_utils.tapered_arm_profile` + `archimedean_spiral_arc` + `fillet_z_edges` definitions → `experiments/slipper_gear/curves.py`. Remove from `cq_utils.py`. Update the moved slipper-gear callers (specifically `slipper_spring.py`) to import from `experiments.slipper_gear.curves`.

**1E — build.toml + tools-side import resolution:**
- [ ] **T1.12** — Update `build.toml` entries: library classes use `vibe_cading.…` paths; project-specific classes use `parts.arrma_vorteks_223s.…` paths.
- [ ] **T1.13** — Audit and update every tool/script hardcoding `models/` paths. Per Developer-reviewer enumeration, at minimum: `build.py`, `tools/check_no_main_blocks.py`, `tools/check_license_headers.py`, `tools/gen_engine_api.py`, `tools/model_loader.py`, `tools/view.py`, `tools/preview.py`, `tools/boolean_diff.py`, `tools/engine_api/extractor.py`, `tools/step_preview.py`. Replace literal `models/` path references with `vibe_cading/`. For module-resolution (`importlib.import_module(...)`), ensure both `vibe_cading.*` and `parts.*` namespaces resolve.
- [ ] **T1.16** — Update `.github/workflows/ci.yml`: 4 hardcoded `models/` path references (per Developer-reviewer survey) → `vibe_cading/`. Add the pytest job step deferred from T0.6.
- [ ] **T1.14** — Run `python build.py`; verify all STEP files regenerate (both library classes under `vibe_cading/` and project-specific under `parts/`).
- [ ] **T1.15** — Smoke test import paths (no pip install required — workspace root on `sys.path`): `python -c "from vibe_cading.mechanical.screws import MetricMachineScrew; print(MetricMachineScrew)"` and `python -c "from parts.arrma_vorteks_223s.esc_mount import EscMount; print(EscMount)"` (adjust class names if needed).

### Phase 2 — cq_utils cleanup *(LE/HB; ~1 hr)*
- [ ] **T2.1** — Remove `cq_utils.WithAllowance` (replaced by profile-aware cutters in Phase 4).
- [ ] **T2.2** — Remove `cq_utils.countersunk_hole`; migrate 3 SG90-mount call sites to `CounterboreHole(head_type="cone").to_cutter()`.
- [ ] **T2.3** — Remove `cq_utils.fillet_z_edges` (moved to experiments with `slipper_spring.py` in Phase 1).
- [ ] **T2.4** — Move `cq_utils.orient_to_neg_x` + `cq_utils.orient_to_pos_x` → `vibe_cading/lego_adapters/_wall_helpers.py` (private module, underscored). Update the 4 call sites in `servo_mount.py` + `servo_mount_half.py`.
- [ ] **T2.5** — Create `vibe_cading/_env.py` private module containing the shared `.env` parser. Replace duplicated parsers in `vibe_cading/print_settings.py` and `vibe_cading/lego/constants.py` with imports.
- [ ] **T2.6** — Rename `SlipperGearBase` → `SlipperGearAssembly` if the class is still in-tree (it's not after Phase 1's move to experiments/, so this task is moot — skip).

### Phase 3 — ToleranceProfile 2D restructure *(ME/HB; ~3 hr)*
- [ ] **T3.1** — Define `FitGrade` dataclass + restructure `ToleranceProfile` to nested form in `vibe_cading/print_settings.py`.
- [ ] **T3.2** — Migrate `machine_profiles.json` to nested schema (free/slip/press × radial/axial).
- [ ] **T3.3** — Migrate `machine_profiles_user.json.example` (and the user's own `machine_profiles_user.json` if present locally — flagged as a private migration the user does).
- [ ] **T3.4** — Update every call site that reads `profile.free_fit`, `profile.z_clearance`, etc. → `profile.free.radial`, `profile.free.axial`. Affected files: `vibe_cading/mechanical/holes.py` (7 classes per reviewer verification — not 4), `vibe_cading/mechanical/screws/*` (5 classes), `vibe_cading/mechanical/nuts/*`, `vibe_cading/mechanical/inserts.py`, `vibe_cading/mechanical/standoffs.py`, more.
- [ ] **T3.5** — Run `python build.py`; verify volume parity with pre-restructure reference (volume delta < 0.1% per class).

### Phase 4 — CutterProtocol introduction *(ME/HB; ~3 hr)*
- [ ] **T4.1** — Define `CutterProtocol` (PEP 544) in `vibe_cading/mechanical/protocols.py`.
- [ ] **T4.2** — Migrate every `holes.py` class: signature `to_cutter(overcut=100.0)` → `to_cutter(profile=None)`. Overcut bakes in per through-vs-blind class semantics (per-class policy, no kwarg).
- [ ] **T4.3** — Rename `BaseJoint.female()` → `Joint.to_cutter(profile=None)` (Protocol-route name; concrete class drops the `Base` prefix per Round 2). Update concrete `DovetailJoint` and `CantileverSnapFit`.
- [ ] **T4.4** — Add `.solid` property to `DovetailJoint` and `CantileverSnapFit` (returns `.male(overlap=0.0)`).
- [ ] **T4.5** — Add `.to_cutter(profile=None)` method to `TechnicPinHole` and `TechnicAxleHole`. Keep `.solid` as an alias (calls `.to_cutter(get_profile())`).
- [ ] **T4.6** — Migrate `HeatSetInsert.to_cutter(through_hole, clearance_d)` → constructor-time `through_hole` + `clearance_d`, call-time `to_cutter(profile=None)`. (Reviewer-verified actual class name; not "InsertFastener" as earlier draft said.)
- [ ] **T4.8** — Migrate `Sg90Servo.to_cutter` (in `rc/servo/sg90.py`) to the `to_cutter(profile=None)` signature per `CutterProtocol`.
- [ ] **T4.9** — Migrate both `ventilation.py` cutter classes (`VentilationPattern` overloads) to the `to_cutter(profile=None)` signature.
- [ ] **T4.10** — Migrate the `FastenerDrive` ABC subtree (`drives.py`: `HexDrive`, `SlottedDrive`, `PhillipsDrive`, `TorxDrive`) from the older `cutter()` method name to `to_cutter(profile=None)`. This is a same-name-different-signature drift the original cutter survey missed; updating these aligns the drive cutters with `CutterProtocol`. Update all call sites that invoke `.cutter` on drive instances.
- [ ] **T4.7** — Migrate `Standoff.to_cutter(radial_allowance, depth_allowance)` → `to_cutter(profile=None)`.

### Phase 5 — Screw/Nut/Joint Protocol conversion *(ME/HB; ~3 hr)*
- [ ] **T5.1** — Define `ScrewProtocol`, `NutProtocol`, `JointProtocol` (PEP 544) in `vibe_cading/mechanical/{screws,nuts,joints}/protocol.py` (one Protocol per family).
- [ ] **T5.2** — Delete `vibe_cading/mechanical/screws/base.py`, `vibe_cading/mechanical/nuts/base.py`, `vibe_cading/mechanical/joints/base.py`.
- [ ] **T5.3** — Drop the parent-class arrow on every concrete `Screw` / `Nut` / `Joint` subclass; remove `from .base import …` lines.
- [ ] **T5.4** — Migrate every screw `to_cutter(mode, ...)` signature → `to_cutter(profile=None, fit="clearance")` per Round 4 Q3 resolution. Drop the legacy-override `ToleranceProfile` construction bridge in `metric.py` and siblings.
- [ ] **T5.5** — Migrate every nut `to_cutter(...)` signature → `to_cutter(profile=None)`. `TNut` keeps `to_captive_slot` as a nut-specific extension.
- [ ] **T5.6** — Update `__init__.py` files in `screws/`, `nuts/`, `joints/` to re-export the new Protocol names; drop the old `Screw` / `Nut` / `BaseJoint` re-exports.
- [ ] **T5.7** — Update `docs/screws.md` heading "Screw Base Class and Standard Fasteners" → "Screws and Standard Fasteners" (per req R8 / Round 1 carryover).
- [ ] **T5.8** — Extend `tools/engine_api/extractor.py::_is_discoverable` (line ~266-303) to filter out `typing.Protocol`-derived classes, mirroring the existing ABC-exclusion logic. Otherwise `ScrewProtocol` / `NutProtocol` / `JointProtocol` / `CutterProtocol` would leak into the wire JSON contract.

### Phase 6 — Gear deepening *(HE/HB; ~6 hr)*
**Inheritance reality check (per TL-reviewer verification, 2026-05-14):** `HelicalGear` inherits from `SpurGear` (NOT directly from `Gear`); `RackGear` does NOT inherit from `Gear` at all. So shared primitives become `@classmethod` helpers that ANY caller (inheriting or not) can invoke as `Gear.involute_tooth_profile_2d(module=…, teeth=…, pressure_angle=…)`. No re-parenting of `RackGear` required.

- [ ] **T6.1** — Add `Gear.involute_tooth_profile_2d(module, teeth, pressure_angle)` as a `@classmethod` returning 2D involute-flank curve. Static-helper shape so non-inheriting callers (`RackGear`) can use it.
- [ ] **T6.2** — Add `Gear.gear_blank_with_teeth_2d(module, teeth, pressure_angle)` `@classmethod` returning the full toothed cross-section sketch.
- [ ] **T6.3** — Add `Gear.bore_cutter(bore, profile)` `@classmethod` shared method (takes bore spec as parameter rather than reading `self.bore`).
- [ ] **T6.4** — Add `Gear.mesh_with(self, other, phase=0.0)` instance method returning `(self_solid, other_solid)` at correct center distance with teeth phase-aligned.
- [ ] **T6.5** — Define composable `Bore` types in `vibe_cading/mechanical/gears/bore.py`: `RoundBore`, `HexBore`, `DBore`, `KeyedBore`.
- [ ] **T6.6** — Refactor `SpurGear.solid` to consume `Gear.gear_blank_with_teeth_2d(...)` + extrude.
- [ ] **T6.7** — `HelicalGear` inherits from `SpurGear` — verify it continues to work; the helix path is its only unique twist beyond `SpurGear`'s consumption of the shared blank.
- [ ] **T6.8** — Refactor `RackGear.solid` to consume `Gear.involute_tooth_profile_2d(...)` as a `@classmethod` call + linearize. No inheritance relationship needed.
- [ ] **T6.9** — Add `Gear.from_iso(module, teeth, ...)` classmethod with ISO standard module validation (`[0.5, 0.8, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]`).
- [ ] **T6.10** — Run `tools/check_polar_monotonicity.py` against `Gear.involute_tooth_profile_2d` and `Gear.gear_blank_with_teeth_2d` invoked with fixed reference inputs (`module=1.0, teeth=20, pressure_angle=20.0`). The check tool currently constructs zero-arg instances per its existing invocation contract — extend the tool to accept a parameter pack, OR pre-bind the classmethods via a wrapper script under `tmp/`. Reconcile with the tool's actual interface during implementation.
- [ ] **T6.11** — Run `python build.py`; verify volume parity with pre-refactor reference per gear class.

### Phase 7 — Final consistency sweep *(LE/MB; ~2 hr)*
- [ ] **T7.1** — Update `__init__.py` files across `vibe_cading/` per the two-level discipline: leaf packages re-export public types; mid-level (`vibe_cading/mechanical/__init__.py`) re-export nothing; top-level (`vibe_cading/__init__.py`) stays empty.
- [ ] **T7.2** — Constructor parameter naming sweep: `dia` → `diameter`, ad-hoc names harmonized per Round 5.4.
- [ ] **T7.3** — Type-hint coverage audit on public constructors; fill gaps.
- [ ] **T7.4** — Update doc surface for renames:
  - `docs/lego-technic.md` and any other `docs/*.md` referencing old class names / import paths.
  - `docs/screws.md` — heading rename (per T5.7) and remove / re-explain the `get_screw_allowances` reference (the helper does not exist in the new design; `ToleranceProfile` carries everything).
  - **`vibe/INSTRUCTIONS.md`** — per Developer-reviewer survey, ~8 lines reference `models/` (including the line-117 Deep-Modules Dual-Lens Rule that this design itself cites). Update every `models/…` reference to `vibe_cading/…`.
  - `CLAUDE.md` and `vibe/INSTRUCTIONS.md` Knowledge-Base sections — verify no other `models/` references remain.
  - `tmp/structural-review-2026-05-08.md` and `tmp/platform-coordination-wave-c.md` are historical artifacts — DO NOT mutate; rationale rests on the timestamp.

### Phase dependency graph
```
0 → 1 → 2 → 3 → 4 → 5
                \     ⤷ 7
                 → 6 ─┘
```
Phases 0–4 are strictly sequential. Phase 5 and Phase 6 can land in parallel after Phase 4 completes; Phase 7 waits for both.

## Tests

Per req termination condition #3: every functional requirement R1–R12 maps to at least one test row. Tests are mostly integration tests against the existing `build.py` / `tools/preview.py` / `tools/view.py` / `tools/engine_api` surface; new unit tests added only where the Protocol structural-typing assertions cannot be expressed through integration.

| # | Test description | Expected assertion | Maps to | File / location |
|---|---|---|---|---|
| T1 | Run `python build.py` on the post-refactor tree | All STEP files in `build.toml` regenerate successfully (no exceptions, no missing classes) | R1, R3, R4, R6, R7, R8 | `python build.py` invoked in CI |
| T2 | Volume diff per registered class against pre-refactor reference | Volume delta < 0.1% per class | R3, R7 | `tools/boolean_diff.py <pre-step> <module.Class> --align-bbox` per class |
| T3 | Engine API extraction succeeds post-refactor | All concrete classes appear in wire JSON; no `*Protocol` types leak; `__init__.py` re-export changes don't regress the contract | R2, R6 | `python -m tools.engine_api` |
| T4 | Protocol structural typing | `isinstance(MetricMachineScrew(...), CutterProtocol)` returns True; same for `ScrewProtocol`, `NutProtocol`, `JointProtocol`, plus hole / insert / standoff classes against `CutterProtocol` | R2, R3 | new unit test at `tests/test_protocols.py` |
| T5 | `ToleranceProfile` 2D schema loads | All canonical profiles in `machine_profiles.json` parse into nested form; user override merges; default fallback works when JSON broken | R8 | new unit test at `tests/test_tolerance_profile.py` |
| T6 | Import smoke test for every concrete class | `from vibe_cading.mechanical.screws import MetricMachineScrew`, `from vibe_cading.lego_adapters.servos.sg90 import …`, `from parts.arrma_vorteks_223s import …` etc. all resolve | R2, R4, R5, R6 | new unit test at `tests/test_imports.py` |
| T7 | `tools/preview.py <Class>` runs for every concrete class | Three SVGs emit per class to `tmp/preview/` with no exceptions | R5, R7 | bash script iterating registered build.toml classes |
| T8 | `tools/view.py <Class> --demo` runs for every class with a `demo()` classmethod | Subprocess exits 0; tessellation completes | R5 | bash script iterating classes |
| T9 | `tools/view.py --assembly <module>` runs for assembly modules | Subprocess exits 0 | R4 | bash for the surviving assembly modules in the new layout |
| T10 | Lint pass | `flake8` clean on all changed files | R-NF (non-functional) | CI |
| T11 | Main-block sweep CI check | `tools/check_no_main_blocks.py` passes — no `if __name__ == "__main__"` blocks in any `models/**.py` file | R-NF | CI |
| T12 | Polar monotonicity for shared gear methods | `tools/check_polar_monotonicity.py` passes for `Gear.gear_blank_with_teeth_2d` and `Gear.involute_tooth_profile_2d` (both `@classmethod` per the corrected Phase 6 — no leading underscore) invoked with fixed reference inputs (`module=1.0, teeth=20, pressure_angle=20.0`) | R2 (Gear deepening) | New CI step or invoked manually; may need a `tmp/` wrapper to pre-bind classmethod args per T6.10 |
| T13 | Cutter contract — overcut policy | For every class implementing `CutterProtocol`, the returned cutter extends at least 1 mm past every entry face. (Spot-check via bounding box assertion in a probe.) | R3 | `tests/test_cutter_overcut.py` |
| T14 | Backwards-compat documentation pass | R12 documentation-only deliverable: every rename / signature change is listed in the design artifact's "Implementation Plan" section with old → new mapping. | R12 | This design artifact, §Implementation Plan |
| T15 | Meta-requirement presence audit | R9 effort-vs-benefit master table populated with at least 1 row per Phase 0–7 task cluster; R10 phased implementation plan present with dependency graph; R11 Wave C reconciliation section present with C1 / C2 explicit subsumption note. | R9, R10, R11 | Manual grep against this design artifact: `grep -c '\| R-' …_design.md` ≥ 29; `grep -E '### Phase [0-7]'` returns 8 matches; `grep -c 'Wave C reconciliation'` ≥ 1. |

## Success Criteria

Implementation is considered complete when ALL of:

1. **Build parity.** `python build.py` regenerates every STEP file registered in `build.toml`. Volume delta < 0.1% per class against the pre-refactor reference (geometry not regressed).
2. **Engine API contract.** `python -m tools.engine_api` extraction succeeds; every concrete class in the new layout appears in the wire JSON; no `*Protocol` types leak; no removed-base-class references remain.
3. **Preview pipeline.** `tools/preview.py <Class>` runs for every registered class, emitting three SVGs per class. No exceptions.
4. **View pipeline.** `tools/view.py <Class>`, `--demo` for classes with `demo()`, and `--assembly` for assembly modules all run without exception.
5. **Imports.** Every documented import path in `docs/screws.md` and any other doc resolves. Smoke test (T6) green.
6. **Structural typing.** Every concrete class satisfies its corresponding Protocol (`ScrewProtocol`, `NutProtocol`, `JointProtocol`, `CutterProtocol` as applicable) under `isinstance()`. Test T4 green.
7. **Tolerance profile.** `ToleranceProfile` loads from nested-schema JSON; user override merges correctly; default fallback works. Test T5 green.
8. **Lint clean.** `flake8` passes on all changed files. `tools/check_no_main_blocks.py` passes. `tools/check_polar_monotonicity.py` passes for shared gear methods. Tests T10, T11, T12 green.
9. **Cutter overcut.** Every `CutterProtocol`-implementing class returns a cutter that extends past every entry face (test T13).
10. **Documentation.** `docs/screws.md` heading updated; any other doc referencing old class names or paths updated. `.env.example` exists.
11. **No dead code.** No file moved to `experiments/` is imported from inside `vibe_cading/` or `parts/`. No `from models.…` or `from vibe_cading.xlego.…` import remains anywhere. No `cq_utils.WithAllowance` / `cq_utils.countersunk_hole` / `cq_utils.fillet_z_edges` / `cq_utils.orient_to_*` import remains.
12. **Importable from workspace root.** `python -c "from vibe_cading.mechanical.screws import MetricMachineScrew"` and `python -c "from parts.arrma_vorteks_223s.esc_mount import EscMount"` both resolve when run from the repo root. (No `pip install` step in this brief — packaging deferred per Round 3 follow-up Option 3.)

## Out of Scope

Inherited from req — see [§Out of Scope of the req artifact](2026-05-13-pre-oss-models-structure_req.md).

Additions surfaced during dialog: _(populated as the dialog proceeds)_.

## Known Risks & Mitigations

| Risk | Predicted cost if unmitigated | Mitigation |
|------|---|---|
| `typing.Protocol` structural typing misses runtime contract violations that `ABC + @abstractmethod` would catch | Silent attribute errors at first call site instead of explicit `TypeError` at instantiation | T4 unit test verifies Protocol membership via `isinstance` for every concrete class; CI runs `mypy` / `pyright` if available — catches structural mismatches statically before runtime. |
| `ToleranceProfile` JSON schema break leaves the maintainer's local `machine_profiles_user.json` unreadable | One-time hand migration of a single local file | Migration helper script under `tmp/migrate_profile_json.py` converts old flat schema → new nested schema. Run once at Phase 3. |
| Gear deepening introduces subtle geometric regressions (involute math, tooth-array generation) | Print-time discovery of wrong tooth shape; one re-print cycle per affected gear | T2 (volume diff per gear class) catches gross geometric regression. T12 (`tools/check_polar_monotonicity.py`) catches polygonal back-tracking in the 2D sketch path. Manual `tools/preview.py` SVG inspection for at least one gear per type. |
| Subtree moves (`xlego` → `lego_adapters`, `slipper_gear` → `experiments`) leave dangling imports | CI break; OSS user `ImportError` on first install | Phase 1 is single atomic commit including all import-path updates. T6 import smoke test exercises every documented entry point. CI runs `python build.py` on the post-move tree. |
| Phase 5 (Protocol conversion) drops the `Screw` / `Nut` / `BaseJoint` ABC names, breaking any downstream Wave C platform consumer that imported them | Platform-side breakage at `vibe-cading-platform#4`'s next attempt | TL flag at the §Wave C reconciliation section below: route to Admin pre-implementation. Concrete Protocol names (`ScrewProtocol`, etc.) communicated as the replacement. |
| `cq_utils.WithAllowance` removal breaks any out-of-tree caller (none confirmed) | Silent `AttributeError` for any forgotten in-tree caller | Phase 2 grep sweep confirms no remaining `WithAllowance` references in `models/` and `tools/` before merge. |
| Gear `mesh_with` rotation math: phase alignment between two gears at correct center distance is non-trivial; the naive `pitch_radius` ratio isn't sufficient for arbitrary gear pair | Visualization shows visibly mis-meshed teeth; not a build-time failure but undermines T9 success criterion | Phase 6 sub-task in `T6.4`: implement `mesh_with` with explicit tooth-phase computation; validate visually via `tools/view.py` on two known-good gear pairs before declaring complete. |
| Phase 1 global `models.` → `vibe_cading.` rewrite misses a callsite (e.g. in a `tmp/` probe, a Markdown doc, or a string-literal `importlib` argument) | `ImportError` at first downstream use; CI catches most via build/preview/view smoke tests | `git grep -n 'from models\.' && git grep -n 'import models'` MUST return empty after Phase 1's find-and-replace. Add a CI check (one-line bash) asserting both greps are empty so the regression cannot reappear. |

## Wave C reconciliation *(req R11)*

The pre-existing backlog items **Wave C C1** (Cutter↔ToleranceProfile glue + `get_screw_allowances`) and **Wave C C2** (Unified Cutter Interface) are listed in [INDEX.md](INDEX.md) as `blocked` on platform coordination at `vibe-cading-platform#4`. This brief's Round 4 (CutterProtocol) and Round 5 (ToleranceProfile 2D restructure) **subsume both items**:

- **Wave C C1** subsumed: every cutter now takes `profile: ToleranceProfile | None = None` at call time; `get_screw_allowances` is unnecessary because the profile carries everything. The original `vibe-cading-platform#4` concern was "every cutter gains an optional `material: str = "PLA"`" — the Protocol approach generalizes this beyond `material` to a full `ToleranceProfile` parameter, which is strictly more expressive. Platform consumers who would have called `get_screw_allowances("PLA")` now call `get_profile("fdm_standard")` (or pass a custom `ToleranceProfile` literal).
- **Wave C C2** subsumed: `CutterProtocol` (PEP 544) is the unified cutter interface. The original C2 design space — settle on one method name, one parameter convention, one overcut policy — is fully resolved by this brief's Round 4 decisions.

**Platform coordination action item (route to Admin).** The original Wave C briefs sent the platform team the abstract ABC signatures (`Screw.to_cutter(mode, radial_allowance, head_recess_depth)`, etc. — see [tmp/platform-coordination-wave-c.md](../../tmp/platform-coordination-wave-c.md)). This brief's Round 5 Phase 5 removes those ABCs entirely; the replacement is structural-typing Protocols whose names (`ScrewProtocol`, `NutProtocol`, `JointProtocol`, `CutterProtocol`) and signatures should be communicated to the platform team if their downstream LLM prompts reasoned against the original ABC contracts. **Whether they did so is a question Admin must route to the platform team.** This is the only Wave C platform-coordination action surviving this brief.

After implementation lands:
- PM updates [INDEX.md](INDEX.md) to mark Wave C C1 and C2 as `done — subsumed by 2026-05-13-pre-oss-models-structure_design.md` rather than as independent in-flight tasks.
- The `vibe-cading-platform#4` external dependency is *no longer blocking* this project's pre-OSS structural work; remaining platform-side action (if any) is post-merge cleanup.

## Effort-vs-benefit master table *(req R9)*

| # | Recommendation | Effort | Benefit | Phase |
|---|---|---|---|---|
| R-1 | Replace `Screw`/`Nut`/`BaseJoint` ABCs with `ScrewProtocol`/`NutProtocol`/`JointProtocol` (PEP 544) | ME | HB | 5 |
| R-2 | Keep `Gear` ABC; add 6 deepenings (involute math, tooth array, bore cutter, mesh_with, composable Bores, from_iso) | HE | HB | 6 |
| R-3 | Rename `SlipperGearBase` → `SlipperGearAssembly` (moot; class moves to experiments) | n/a | n/a | n/a |
| R-4 | Delete `mechanical/trailer_hitch_cover.py` | LE | LB | 1 |
| R-5 | Rename `hex_wheel_hub` → `freespin_hex_hub` | LE | MB | 1 |
| R-6 | Rename `xlego/` → `lego_adapters/` (subtree move + import updates) | ME | HB | 1 |
| R-6b | Rename top-level package `models/` → `vibe_cading/` (no `pyproject.toml`, no PyPI per Option 3) | ME | HB | 1 |
| R-7 | Move Arrma-specific parts to top-level `parts/arrma_vorteks_223s/` (sibling to `vibe_cading/`) | LE | HB | 1 |
| R-8 | Move slipper-gear + supporting servo-shaft files to `experiments/` | ME | HB | 1 |
| R-9 | Move `cq_utils.tapered_arm_profile` + `archimedean_spiral_arc` to `experiments/` | LE | HB | 1 |
| R-10 | Genericize + move `technic_ball_bearing/axle_sleeve.py` to `lego_adapters/` | LE | HB | 1 |
| R-11 | Define `CutterProtocol` (PEP 544) | LE | HB | 4 |
| R-12 | Migrate `holes.py` to `to_cutter(profile=None)` | LE | HB | 4 |
| R-13 | Rename `Joint.female()` → `Joint.to_cutter(profile=None)` | LE | HB | 4 |
| R-14 | Add `.solid` property to joints | LE | MB | 4 |
| R-15 | Add `.to_cutter()` method to lego cutters (alias of `.solid`) | LE | HB | 4 |
| R-16 | Deprecate / remove `cq_utils.WithAllowance` | LE | HB | 2 |
| R-17 | Remove `cq_utils.countersunk_hole`; migrate to `CounterboreHole` | LE | HB | 2 |
| R-18 | Move `cq_utils.orient_to_*` to `lego_adapters/_wall_helpers.py` | LE | HB | 2 |
| R-19 | Remove `cq_utils.fillet_z_edges` | LE | HB | 2 |
| R-20 | `ToleranceProfile` 2D restructure (`FitGrade(radial, axial)` × {free, slip, press}) | ME | HB | 3 |
| R-21 | `machine_profiles.json` schema migration | LE | HB | 3 |
| R-22 | Constructor parameter naming sweep (`diameter`, `length`/`depth`/`height` per axis) | ME | MB | 7 |
| R-23 | `__init__.py` two-level discipline | LE | MB | 7 |
| R-24 | Centralize `.env` parser in `models/_env.py` | LE | MB | 2 |
| R-25 | Create `.env.example` | LE | HB | 0 |
| R-26 | Migrate screw `to_cutter(mode, ...)` → `to_cutter(profile=None, fit="clearance")` (call-site fit) | ME | HB | 5 |
| R-27 | Migrate nut / insert / standoff `to_cutter(...)` → `to_cutter(profile=None)` | ME | HB | 5 |
| R-28 | Delete `models/mechanical/screws/base.py`, `nuts/base.py`, `joints/base.py` | LE | HB | 5 |
| R-29 | Update `docs/screws.md` heading | LE | HB | 5 |

Total: 29 recommendations across 8 phases. No `parked` items — every surfaced concern has a verdict or an explicit deferral.

---

## Design Dialog Log

### Round 1 — Methodological framework

**TL proposal:**

> Apply a **two-lens deletion test** (maintainer-locality + contributor-locality) to every existing Module evaluated in this brief, then choose ONE of four verdicts per Module: `keep` / `repair` / `replace-with-Protocol` / `remove`. Use four canonical false-positive carve-outs plus a fifth surfaced by the 2026-05-13 PM↔user dialog (contributor-extension-contract). Classify every recommendation by churn-vs-benefit and surface backwards-compat impact even though pre-OSS users do not yet exist.
>
> Rationale: a single-lens (maintainer-only) analysis is what produced the original "remove all bases" verdict that the user correctly challenged. The two-lens framework forces both perspectives into every Module-level decision and gives the user a triage-friendly verdict vocabulary.

**Requester challenge / contribution:**

> Codified the methodology as a project-wide rule in [vibe/INSTRUCTIONS.md:117](../../vibe/INSTRUCTIONS.md#L117) ("Deep-Modules — Dual-Lens Rule"). Added two refinements over TL's initial proposal: (a) verdict-preference ordering on drift — `repair` or `replace-with-Protocol` are preferred over `remove`; (b) project-wide bias toward contributor-locality with the framing "contributor onboarding is a first-class structural concern, not a postscript." Recorded an Admin follow-up in [todo.md](../../todo.md) to propose the fifth false-positive carve-out upstream to `core-agents`. Implicit rejections: TL's three pushback questions (third lens, Protocol availability, docstring-only verdict) are all answered by the codified rule.

**Resolution:**

> Methodology accepted as project policy. The substantive revision negotiated this round: verdict-preference ordering on drift was NOT in TL's original proposal; the user added it. This is a material constraint on Round 2 (per-base verdicts) and Round 3 (cutter unification). TL's framework section in this artifact now cites the rule rather than restating it. Round 1 closed.

### Round 2 — Per-base verdicts

**TL proposal:**

> Applying the now-ratified two-lens methodology to all five existing bases in scope. Summary table; full justification in §"Architecture / Approach → Per-base verdicts" below.
>
> | Base | Maintainer lens | Contributor lens | Drift? | Verdict | Churn |
> |---|---|---|---|---|---|
> | [`Screw`](../../models/mechanical/screws/base.py) | shallow (zero polymorphic callers) | deep when honest | YES — `to_cutter(mode, radial_allowance, head_recess_depth)` vs concrete `(mode, profile=None)` | **`repair`** OR **`replace-with-Protocol`** — choice deferred to Round 3 (cutter unification) | depends on Round 3 |
> | [`Nut`](../../models/mechanical/nuts/base.py) | shallow | deep when honest | YES (partial — `TNut` matches; `MetricHexNut`/`MetricSquareNut` drift to `(profile)`) + extra method (`to_captive_slot`) | **`repair`** OR **`replace-with-Protocol`** — choice deferred to Round 3 | depends on Round 3 |
> | [`BaseJoint`](../../models/mechanical/joints/base.py) | shallow | **deep, no drift** — concrete `male(overlap)`/`female(overlap)` match abstract exactly | NO | **`keep` with rename** → drop "Base" prefix: `BaseJoint` → `Joint`. OR **`replace-with-Protocol`** as `JointProtocol`. | LH/MB |
> | [`Gear`](../../models/mechanical/gears/base.py) | **deep** (shared `__init__` with parameter validation + derived radii + `center_distance_to(other)`) | deep | NO | **`keep`** unchanged. Only base that wins both lenses unambiguously today. | none |
> | [`SlipperGearBase`](../../models/xlego/slipper_gear/directional/base.py) | mixed — class contains real assembly logic (ring/plate/spring composition) but has **zero abstract methods**; subclasses just supply different `__init__` presets | **shallow as a "base"** — name implies extension contract that doesn't exist; subclasses are parameter presets, not extensions | naming/semantic | **`repair`** via rename → `SlipperGearAssembly` (per [todo.md](../../todo.md) parked item). Keep subclass structure — named variants beat factory-string lookup on contributor-locality. | LH/MB |
>
> **Cross-cutting decision blocked here:** for Screw / Nut / BaseJoint specifically, the meta-choice between `repair` (keep `ABC + @abstractmethod`, fix the signature) vs `replace-with-Protocol` (use PEP 544 `typing.Protocol`, drop the inheritance arrow). Two real options:
>
> - **(A) ABC route.** Inheritance arrow stays explicit. `MetricMachineScrew(Screw)` reads as "is-a Screw" — IDE hover-doc shows the protocol; `@abstractmethod` enforces method presence. Familiar to Python users from any decade.
> - **(B) Protocol route.** No inheritance arrow on concrete classes (`class MetricMachineScrew:` — no parent). The protocol is named `ScrewProtocol` or similar; concrete classes "implement" it by signature shape (PEP 544 structural typing). Modern Python idiom. IDE still flags missing methods when type-annotated. More flexible (no `super().__init__()` required, no metaclass conflicts).
>
> Pure deep-modules view is agnostic — both make the contract honest. The choice is *aesthetic + ergonomic*. My recommendation: **(B) Protocol** — for an OSS project where contributors will read the code, the absence of an inheritance arrow + an explicit `*Protocol` suffix communicates "contract, no shared implementation" more directly than the ABC route, which can mislead contributors into looking for shared helpers. But it's a 60/40 preference; reasonable to disagree.
>
> **Specific renames recommended this round** (separable from the ABC/Protocol decision):
> - `BaseJoint` → `Joint` (or `JointProtocol` under route B). The "Base" prefix is convention-clutter — `class CantileverSnapFit(Joint):` reads cleaner.
> - `SlipperGearBase` → `SlipperGearAssembly`. The class is the assembly; subclasses are presets.

**Requester challenge / contribution:**

> 1. **Protocol route** confirmed for Screw / Nut / BaseJoint contracts.
> 2. **`BaseJoint` → `Joint`** rename approved.
> 3. **`SlipperGearBase` → `SlipperGearAssembly`** rename approved.
> 4. **Gear: deepen, don't just keep.** Current version is probably not deep enough — lay foundation so contributors can build on top.
> 5. **NEW concern:** "Some models (like the Arrma motor plate, or some lego / xlego stuff) are not generic or universal. We need to address these." → opens a partitioning question between generic-library content and project-specific end-products. Bumped to Round 3.

**Resolution:**

> Round 2 verdicts locked as follows:
> - **Screw / Nut / `BaseJoint`** → `replace-with-Protocol` (route B). Concrete classes lose their inheritance arrow; new `*Protocol` types (`ScrewProtocol`, `NutProtocol`, `JointProtocol`) capture the contract via PEP 544 structural typing. `BaseJoint` rename is subsumed by Protocol route — the new name is `JointProtocol`.
> - **`Gear`** → `keep` AND **deepen**. See §"Architecture / Approach → Gear deepening proposal" below for concrete deepening directions.
> - **`SlipperGearBase` → `SlipperGearAssembly`** rename approved. Subclass structure preserved (named variants beat factory-string lookup for contributor-locality).
>
> Specific-vs-generic partition concern routed to Round 3 (was originally Round 4 in the planned sequence; reordered because the partition affects what's in-scope for subsequent rounds, especially the cutter unification round).

### Round 3 — Specific-vs-generic partition

**TL proposal:**

> User flagged that "some models are not generic or universal" — concrete examples: Arrma Vorteks 223S ESC mount, `xlego/motors/mount_plate.py` (the "Arrma motor plate"), and likely several `xlego/servos/sg90/*` files. The current `models/` tree mixes three categories without marking them, which is a contributor-locality problem: a newcomer reading the tree can't tell which classes are reusable primitives vs. which are one-off end-products.
>
> **Three categories visible in the tree:**
>
> | Category | What it is | Examples |
> |---|---|---|
> | **Generic library** | Parametric primitives that any contributor / downstream project would use unchanged | `models/mechanical/screws/*`, `models/mechanical/nuts/*`, `models/mechanical/gears/*`, `models/mechanical/holes.py`, `models/lego/{constants,technic_axle,cutters/*}`, `models/cq_utils.py`, `models/print_settings.py` |
> | **Standard-part wrappers** | Specific commercial parts with a parametric body — widely used in their category, not Arrma-specific | `models/rc/servo/sg90.py` (SG90 servo body — industry-standard hobby servo), `models/lego/gears/gear_28t.py` (THE Lego 28t gear), `models/technic_ball_bearing/axle_sleeve.py` (Lego-axle-to-ball-bearing adapter) |
> | **Project-specific end-products** | Designed for a particular vehicle / use-case; not parametric for other applications | `models/rc/vorteks_223s/esc_mount.py` (Arrma Vorteks 223S only), `models/xlego/motors/mount_plate.py` (Arrma motor plate per user), `models/xlego/servos/sg90/*` (specific SG90 mounts), `models/xlego/slipper_gear/*` (specific slipper-gear design), `models/mechanical/trailer_hitch_cover.py` (looks specific — needs confirmation) |
>
> **Proposed partition strategy:** introduce a clear top-level separation between **library** (parametric primitives + standard parts) and **applications** (project-specific end-products). Three layout options to consider:
>
> **Option A — Flat sibling directories:**
> ```
> models/             ← library (generic + standard parts) — what OSS contributors reuse
> applications/       ← project-specific end-products — what THIS user built using the library
> ```
> Tightest separation. OSS contributors get `pip install vibe-cading` and import from `models.*` only. `applications/` is the maintainer's portfolio — visible in the repo, not exported as a package.
>
> **Option B — Subdirectory under `models/`:**
> ```
> models/
>   mechanical/...           ← generic library
>   lego/...                 ← generic library
>   applications/            ← project-specific end-products
>     arrma_vorteks_223s/...
>     custom_slipper_gear/...
> ```
> Single import root preserved (`from models.applications.arrma_vorteks_223s import ...`). Easier to refactor in steps. Slightly weaker separation — newcomers might not realize `models/applications/` is "the maintainer's parts" vs "more library content."
>
> **Option C — Library-vs-parts naming inversion:**
> ```
> vibe_cading/           ← renamed library namespace
>   primitives/...    ← generic parts (screws, nuts, gears, etc.)
>   lego/...
>   rc/sg90.py        ← standard-part wrappers
> parts/              ← maintainer's project-specific end-products
>   vorteks_223s/
>   slipper_gear/
> ```
> Boldest restructure. Renames the library namespace for a cleaner OSS pitch. HC/HB churn — every existing import in `build.toml` + tests + docs changes. Pre-OSS is the cheap moment.
>
> **My recommendation: Option B** — single import root, separable PR, low friction. Option A is cleaner long-term but requires a build-tool change (`pip install` semantics). Option C is the OSS-ideal end-state but the churn isn't justified vs B's pragmatism *unless* you have specific OSS-positioning reasons to rename the namespace.
>
> **Confirmation questions about specific files:**
>
> - `models/mechanical/trailer_hitch_cover.py` — is this an Arrma / specific-vehicle part, or a generic trailer-hitch parametric primitive? (Filename suggests specific.)
> - `models/rc/hex_wheel_hub.py` — RC-specific generic adapter, or specific-to-one-vehicle?
> - `models/xlego/axle_to_pin_bore_adapter.py` — generic xlego utility? (Filename suggests generic.)
> - `models/technic_ball_bearing/axle_sleeve.py` — generic adapter for Lego-axle-to-bearing? Or specific bearing size?
> - `models/xlego/slipper_gear/*` — entire subtree project-specific? Or does the user want SOME of it (`SlipperRing` parametric math, `SlipperSpring` archetype) to remain library content?

**Requester challenge / contribution:**

> 1. **Option B** confirmed.
> 2. `mechanical/trailer_hitch_cover.py` → remove entirely.
> 3. `rc/hex_wheel_hub.py` → RC-specific generic; bad naming. Clarified: free-spinning hex hub for non-driving (idler) wheels of a 2WD RC; hub rotates around the shaft via ball bearing (vs. fixed-to-shaft like driven wheels).
> 4. `xlego` → adapter layer that joins non-lego RC parts with Lego.
> 5. `technic_ball_bearing/axle_sleeve.py` → make generic; purpose is to adapt the Lego Technic (cross-shaped) axle through ball bearings with ID ≥ 5 mm.
> 6. `xlego/slipper_gear/*` → user asked for TL advice ("two designs, neither good enough").

**Resolution:**

> All four sub-decisions resolved by user in follow-up:
> - **Xlego rename → `lego_adapters/`** confirmed.
> - **Hex-wheel-hub rename → `freespin_hex_hub.py`** confirmed.
> - **Slipper-gear fate → Option 2** (move to `experiments/` top-level outside the package).
> - **SG90 servo mount → generic** — goes to `lego_adapters/servos/`.
>
> Round 3 (first close) accepted Option B (`models/applications/` nested).
> Round 3 **REOPENED on 2026-05-14** when user asked whether the "no-churn" follow-up had been applied to earlier rounds (it had not been fully applied to Round 3). User then chose **pip-installable target** → **Option C** wins on the no-churn lens. Final close below.

### Round 3 follow-up (2026-05-14) — Namespace rename, NO pip-install (Option 3)

**Decision history:**
1. Original Round 3 close picked Option B (`models/applications/` nested) on a churn-cost argument.
2. Round 5 follow-up retired the churn argument ("no external users at the moment").
3. User probed whether earlier rounds had been re-evaluated under the no-churn lens; TL surfaced Round 3 Option B-vs-C as the place the churn argument biased the choice.
4. User initially picked **pip-installable** (Option C).
5. User then asked @admin whether pip-installability was justified at all, given the primary use case (AI-agent-driven CAD via `vibe/agents/`) requires a repo clone regardless.
6. **Admin diagnosed Option C as a single-adapter speculative seam** under this project's own deep-modules discipline — one hypothetical platform consumer doesn't justify HE effort + ongoing PyPI maintenance.
7. **User picked Option 3:** rename `models/` → `vibe_cading/` for OSS-clarity benefit; NO `pyproject.toml`; NO PyPI distribution. Pip-installability becomes a future single-PR addition when a real second consumer is committed.

**Package name:** `vibe_cading` (exact transliteration of project name `vibe-cading`).

**Final layout (Option 3 — rename, no pip):**

```
vibe-cading/                     ← repo root (unchanged folder name)
├── vibe_cading/                    ← Python package (RENAMED from models/); NOT pip-distributed
│   ├── __init__.py
│   ├── mechanical/              ← unchanged (domain axis; not renamed to primitives/)
│   │   ├── screws/
│   │   ├── nuts/
│   │   ├── joints/
│   │   ├── gears/
│   │   ├── holes.py
│   │   ├── enclosures/
│   │   ├── inserts.py
│   │   ├── standoffs.py
│   │   ├── magnets.py
│   │   ├── bearings.py
│   │   ├── hinge.py
│   │   ├── tolerance_gauge.py
│   │   └── protocols.py        ← NEW (CutterProtocol)
│   ├── lego/                    ← pure Lego primitives
│   ├── lego_adapters/           ← Lego ↔ non-Lego adapter layer (renamed from xlego/)
│   │   ├── _wall_helpers.py     ← private (orient_to_*)
│   │   ├── axle_to_pin_bore_adapter.py
│   │   ├── technic_axle_to_bearing_sleeve.py
│   │   └── servos/
│   │       └── sg90/
│   │           ├── servo_mount.py
│   │           └── servo_mount_half.py
│   ├── rc/                      ← RC primitives + standard-part wrappers
│   │   ├── freespin_hex_hub.py  ← renamed from hex_wheel_hub.py
│   │   └── servo/
│   │       └── sg90.py
│   ├── cq_utils.py
│   ├── print_settings.py
│   └── _env.py                  ← NEW (shared .env parser, private)
├── parts/                       ← TOP-LEVEL SIBLING; project-specific portfolio
│   └── arrma_vorteks_223s/
│       ├── __init__.py
│       ├── motor_mount_plate.py
│       └── esc_mount.py
├── experiments/                 ← R&D
│   └── slipper_gear/
│       ├── directional/
│       ├── servo_shaft/         ← consolidated cam_utils / shaft / shaft_body / etc.
│       └── curves.py            ← consolidated tapered_arm_profile + archimedean_spiral_arc
├── tools/                       ← unchanged location; imports update vibe_cading
├── tests/
├── docs/
├── build.toml                   ← entries updated to vibe_cading.* and parts.*
├── machine_profiles.json
├── .env.example                 ← NEW
└── ...
```

NO `pyproject.toml`. Distribution = repo clone. Users run scripts from the workspace root; `python -c "from vibe_cading.mechanical.screws import …"` works because the workspace root is on `sys.path` (current invocation pattern). When a real second pip consumer materializes, a single future PR adds `pyproject.toml` + ships to PyPI.

**Implications:**

1. **Every import `from models.X import Y` becomes `from vibe_cading.X import Y`.** Pervasive but mechanical.
2. **`build.toml` entries shift** — library classes use `vibe_cading.mechanical.…`; `parts/` classes use `parts.arrma_vorteks_223s.…`. The build system + tools must recognize both roots.
3. **Tools update** — `tools/preview.py`, `tools/view.py`, etc. that hardcode `from models.…` patterns or do `module.ClassName` resolution must support both `vibe_cading.…` and `parts.…` namespaces.
4. **OSS pitch surface improves** — a contributor's first import reads `from vibe_cading.mechanical.screws import MetricMachineScrew`, which says exactly what it is. No generic `models` prefix.
5. **No PyPI maintenance.** No version-number management, no dependency-declaration drift, no `package-data` configuration. The renamed namespace is structurally pip-ready; ship to PyPI later if and when a second real consumer is committed.

**Resolution (Round 3, final):**

> Layout: Option 3 — rename `models/` → `vibe_cading/`, top-level sibling `parts/` for project-specific end-products, top-level `experiments/`. `mechanical/` retained as the domain category name. **NO `pyproject.toml`. NO PyPI distribution.**
>
> Round 3 closed (final). Effort impact: Phase 1 is ME (every-file import rewrite + tools-aware module resolution); the HE pip-installable phase reverts. No semantic change to any class; pure renaming + relocation.
>
> **Distribution-mode note (2026-05-14 dialog out-of-scope but recorded for posterity):** Distribution = **git clone only**. The primary use case (AI-agent-driven CAD via `vibe/agents/`, slash commands, `.agents/` plans) requires the full repo regardless. Library-mode pip distribution was considered (Option C) and rejected as a single-adapter speculative seam — one hypothetical platform consumer doesn't justify the packaging + maintenance cost. Pip-installability is captured in [todo.md](../../todo.md) as a deferred future task gated on a real second consumer.

### Round 4 — Cutter protocol unification *(R3 / OQ4 / Wave C C2 reconciliation)*

**TL proposal:**

> The codebase has 7+ cutter-emitting surfaces with 5 different parameter conventions (`overcut` / `radial_allowance+depth_allowance` / `profile` / `overlap` / bespoke kwargs) and 3 different method names (`.to_cutter()` / `.female()` / `.solid`-property-as-cutter). For OSS users this is the largest single source of friction — "how do I get a cutter from X?" has a different answer per family. Pre-OSS is the moment to converge.
>
> **Proposed unified contract — `CutterProtocol`** (PEP 544, structural typing, no inheritance arrow):
>
> ```python
> class CutterProtocol(Protocol):
>     def to_cutter(self, profile: ToleranceProfile | None = None) -> cq.Workplane:
>         """Return a workplane suitable for boolean subtraction.
>
>         The returned workplane MUST include infinite-overcut on entry faces
>         per the project's Known-Modelling-Pitfalls rule (coincident faces are
>         a known OCCT boolean failure mode). Callers do not specify overcut.
>
>         If profile is None, get_profile() is used (env / .env fallback).
>         """
> ```
>
> **Cross-family migration table:**
>
> | Family | Current state | Proposed state |
> |---|---|---|
> | `mechanical/holes.py` (`ClearanceHole`, `CounterboreHole`, `TeardropHole`, `CaptiveNutPocket`) | `to_cutter(overcut=100.0)`; profile in `__init__` | `to_cutter(profile=None)`; overcut bakes-in internally. `profile` parameter shifts from constructor-only to call-site overridable (constructor still accepts `profile` as default). **Reference shape** — already closest to canonical. |
> | `mechanical/screws/*.py` | `to_cutter(mode, profile=None)` — drifted from base | `to_cutter(profile=None)` only. `mode` (clearance/tap/interference) moves into the **screw constructor** as `fit: str = "clearance"`. Cutter call site stops varying mode per call. |
> | `mechanical/nuts/*.py` | drifted: some `(profile)`, `TNut` keeps `(radial_allowance, depth_allowance)` | `to_cutter(profile=None)`. `TNut` migrates to profile-based interface. The extra `Nut.to_captive_slot(slot_length, ...)` survives but is NOT part of CutterProtocol — it's a Nut-specific extension. |
> | `mechanical/joints/*.py` | `female(overlap=1.0)` + `male(overlap)` | **Rename `.female()` → `.to_cutter(profile=None)`**. `.male()` stays as joint-specific positive-side accessor (not part of CutterProtocol; it's the *opposite* of a cutter). `overlap` semantics fold into profile-driven defaults; explicit `overlap` kwarg deprecated. |
> | `mechanical/inserts.py` `InsertFastener` | `to_cutter(through_hole=False, clearance_d=3.2)` | `to_cutter(profile=None)`. `through_hole` and `clearance_d` move into constructor (per-instance configuration, not per-call variation). |
> | `mechanical/standoffs.py` `Standoff` | `to_cutter(radial_allowance, depth_allowance)` | `to_cutter(profile=None)`. Allowances derive from profile. |
> | `lego/cutters/*.py` (`TechnicPinHole`, `TechnicAxleHole`) | `.solid` property IS the cutter; no `.to_cutter()` method | **Add `to_cutter(profile=None)` method**; `.solid` remains as an alias (back-compat within the codebase; deprecate in a follow-up). Internally `.solid` calls `.to_cutter(get_profile())`. |
> | `cq_utils.WithAllowance` | Generic shell-offset wrapper | **Deprecate.** Replaced by the canonical CutterProtocol implementations which take their own profile. Removed if no remaining call sites. |
> | `rc/servo/sg90.py` `Sg90Servo` | Has its own `to_cutter` method (cutter for the servo body cavity in a host part) | Migrate to `to_cutter(profile=None)` per CutterProtocol. (Added 2026-05-14 per TL-reviewer condition TL-1.) |
> | `mechanical/enclosures/ventilation.py` `VentilationPattern` (2 overloads) | `to_cutter(thickness, overcut)` patterns | Migrate to `to_cutter(profile=None)` per CutterProtocol; `thickness` moves to constructor where applicable. (Added 2026-05-14 per TL-reviewer condition TL-1.) |
> | `mechanical/screws/drives.py` `FastenerDrive` ABC + `HexDrive` / `SlottedDrive` / `PhillipsDrive` / `TorxDrive` | Uses older naming `cutter` (not `to_cutter`) as the cutter surface | **Same-name-different-signature drift.** Rename `cutter` → `to_cutter(profile=None)` to align with CutterProtocol; update every call site that invokes `.cutter` on drive instances. (Added 2026-05-14 per TL-reviewer condition TL-1; the original Round 4 survey missed this subtree entirely.) |
>
> **Joint male/female semantics:** Joints are the one family where the positive side (`.male()`) is part of the public API. Joints implement CutterProtocol (via `.to_cutter()`) AND expose `.male(overlap)` as a joint-specific extra. There is NO separate `MateableProtocol` — `male` is a joint thing, not a generalizable cutter-protocol concept. OSS contributors adding a new joint type implement BOTH `.to_cutter()` (required by CutterProtocol) AND `.male()` (joint convention, documented in the joints package).
>
> **Three architectural questions for user:**
>
> 1. **`profile` kwarg vs no-kwarg.** I'm proposing `to_cutter(profile: ToleranceProfile | None = None)` — call site can override the default profile per cut. Alternative: `to_cutter() -> cq.Workplane` (no kwargs); profile pulled exclusively from constructor. Trade-off: kwarg version supports "same screw, two parts with different tolerance profiles" (rare); no-kwarg version is cleaner. Pick.
>
> 2. **Overcut as constructor option vs always-baked.** I'm proposing overcut is ALWAYS baked into the returned cutter (per the project's Known-Modelling-Pitfalls rule about coincident faces). Alternative: expose `overcut: float | None = None` as a constructor option (advanced users override). Trade-off: always-baked = simpler API + harder-to-shoot-foot; configurable = power user friendly. Pick.
>
> 3. **`fit: str` constructor parameter for screws.** I'm proposing `MetricMachineScrew(..., fit="clearance")` and the resulting `.to_cutter()` produces clearance / tap / interference based on the constructor value. Alternative: keep `fit` as a `.to_cutter(fit="tap")` parameter — caller picks per use. Trade-off: constructor-fit = one screw = one cutter shape (clean); call-site-fit = one screw object usable in multiple ways. Pick.

**Requester challenge / contribution:**

> 1. (a) with `profile` kwarg — confirmed.
> 2. Asked back: does "always-baked overcut" cover all current use cases? Do we ever need to disable infinite-overcut?
> 3. Leaning to (b) call-site `fit` parameter.

**Resolution:**

> Q1 locked at (a). Q3 locked at (b) (user lean + TL agreement; Python Protocol allows concrete classes to add optional kwargs without violating structural typing — `MetricMachineScrew.to_cutter(profile=None, fit="clearance")` still satisfies `CutterProtocol`).
>
> Q2 resolution — refined policy: **per-class through-vs-blind, no caller kwarg.** Two distinct overcut concepts exist (entry-face vs terminal-face). Through-cutters overcut both ends; blind-cutters overcut entry only with precise terminal. The current `holes.py` already implicitly chose "blind cases get their own class" (`CaptiveNutPocket` is blind; `ClearanceHole` / `CounterboreHole` / `TeardropHole` are through). Pattern is correct; codify it. New blind variants get their own class (`BlindCounterboreHole` etc.) when needed. There is NO caller-facing "disable overcut" knob — visualization / debug access patterns use `.solid` (positive geometry); `.to_cutter()` is exclusively for subtractive cuts and ALWAYS returns the geometrically correct overcut form for its class.

### Round 5 — Naming, `__init__.py` discipline, constructor ergonomics

**TL proposal:**

> Three consistency sweeps across `models/`. Each one is independently mechanical, but they cluster naturally because they touch the same public-API surface the OSS contributor sees first.
>
> **(5.1) `.solid` property convention.** Currently most generators expose `.solid` as the positive geometry property; joints do NOT (they only have `.male()` / `.female()`). For OSS consistency: **every generator exposes `.solid` as canonical positive geometry.** For joints, `.solid` returns the male side at zero overlap (`.male(overlap=0.0)`) — the "outline of the joint feature" view. Joints still expose `.male(overlap)` as a joint-specific extra; `.to_cutter(profile)` (renamed from `.female()`) is the cutter side per Round 4. Verdict: **add `.solid` property to joints**; keep the joint-specific methods.
>
> **(5.2) `from_size` factory consistency.** Survey:
> - `MetricMachineScrew.from_size("M3", length=10)` ✓
> - `ImperialMachineScrew.from_size("#10-32", length=...)` ✓
> - `WoodScrew(size="3/16", length=25.4, ...)` — no factory; `size` is a constructor kwarg
> - `TorxDrive.from_size("T6")` ✓
> - `MetricHexNut(size="M3")` — TBD; check exists
>
> Proposed rule: **classes with a discrete, named-size catalog use `from_size("NAME", ...)` factory; `__init__` takes raw dimensions.** This separates "factory for standard sizes" from "build a custom one." `WoodScrew` migrates to `from_size("3/16", length=25.4)`. Allows OSS contributors to write `MetricMachineScrew(length=10, major_diameter=3.0, ...)` for non-standard custom sizes without going through the catalog.
>
> **(5.3) Tolerance / profile parameter consistency.** Currently mixed: some classes accept `profile: ToleranceProfile | str` in `__init__`, others accept individual `radial_allowance` / `depth_allowance` floats, others pull from `get_profile()` only at call time. Proposed canonical signature for ANY class that does printed-tolerance-sensitive geometry:
>
> ```python
> def __init__(self, ..., profile: ToleranceProfile | str | None = None): ...
> ```
>
> - `None` → resolved to `get_profile()` (env / fallback default) lazily at first access.
> - `str` → resolved to `get_profile(name)` lazily.
> - `ToleranceProfile` → used directly.
>
> No more `radial_allowance` / `depth_allowance` floats in constructors. Tolerance lives in profile objects; nowhere else.
>
> **(5.4) Constructor parameter naming.** Survey reveals inconsistency:
> - `diameter` vs `dia` vs `d` — proposed: **`diameter` always** (full word, no abbreviation).
> - `length` vs `depth` vs `height` — domain-driven, but pick one per axis convention. Proposed: **`length` for the axial dimension on linear parts (screws, axles, standoffs); `depth` for subtractive features (hole depth, pocket depth); `height` for parts where vertical extent is the dominant dimension (gears, knobs, enclosures).** Within a class, naming is locked.
> - `bore` vs `bore_d` vs `bore_diameter` — proposed: **`bore` if it's a structured type (`RoundBore` / `HexBore` after Gear deepening); `bore_diameter` for raw-float bore.**
> - Type hints: 100% coverage required for public constructors (currently mostly there; gaps in older files like `cq_utils.WithAllowance` accept `cq.Workplane | cq.Shape`).
>
> **(5.5) `__init__.py` re-export discipline.** Survey:
> - `models/__init__.py` — empty.
> - `models/mechanical/__init__.py` — re-exports holes only (partial, inconsistent).
> - `models/mechanical/{screws,nuts,joints,gears}/__init__.py` — re-export base + all concrete classes.
> - `models/mechanical/enclosures/__init__.py` — empty.
> - `models/lego/__init__.py` — re-exports technic cutters only.
> - `models/lego/cutters/__init__.py` — empty.
> - `models/xlego/__init__.py` (→ `lego_adapters/__init__.py` after Round 3) — empty.
>
> Proposed canonical rule: **two-level re-export.** (1) Every leaf subpackage (`screws/`, `nuts/`, `joints/`, `gears/`, `holes` — single-file modules) re-exports its public types. (2) Top-level `models/__init__.py` stays EMPTY; importers go through the namespaced path (`from models.mechanical.screws import MetricMachineScrew`). (3) Mid-level packages like `models/mechanical/__init__.py` either re-export ALL their subpackages' public types (canonical convenience surface) OR re-export nothing (forcing explicit imports). I recommend **re-export nothing at mid-level** — clearer import paths for OSS users who can grep the codebase.
>
> **Cross-cutting question — backward compatibility of renames.**
>
> The Round 4 cutter unification renames `BaseJoint.female()` → `Joint.to_cutter()`. The Round 5 sweep adds `.solid` to joints, migrates `WoodScrew` to `from_size`, deprecates non-profile tolerance kwargs. All of these are **breaking changes for any existing user**. Pre-OSS, no users exist — so we can do them all atomically in one PR with no shim layer. Post-OSS, each would need a deprecation cycle. **Confirm:** atomic-break-pre-OSS is the policy?

**Requester challenge / contribution:**

> User challenged (5.2) and (5.3):
> - **(5.2):** "Do we have use case for this right now? Does it apply to other screw types, or even other mechanical part types?" → Flagging this as a stylistic sweep with thin justification.
> - **(5.3):** "Can the current `ToleranceProfile` handle FDM nicely (may need separate radial and depth allowance)?" → Schema audit request.
>
> No challenge on (5.1), (5.4), (5.5), or the atomic-break-pre-OSS policy.

**Resolution:**

> - **(5.2) DROPPED as forced migration.** TL agrees it's stylistic. Both `Class(size="...")` and `Class.from_size("...")` are acceptable; document the convention without forcing churn. `Gear.from_iso` (new method introduced by Round 2 deepening) stays — that one's a new factory, not a migration.
> - **(5.3) Schema restructured per Option B.** New `ToleranceProfile` shape:
>     ```python
>     @dataclass
>     class FitGrade:
>         radial: float
>         axial: float
>
>     @dataclass
>     class ToleranceProfile:
>         name: str
>         free: FitGrade
>         slip: FitGrade
>         press: FitGrade
>     ```
>   Properly models the asymmetric radial vs axial fit dimensions the user flagged for FDM use cases. Call sites change from `profile.free_fit` → `profile.free.radial` and `profile.z_clearance` → `profile.free.axial` (or `slip.axial`, `press.axial` as appropriate). Default axial values: `0.0` — explicit opt-in for axial fits per-class. Shrinkage scale factor (Option C) DEFERRED post-OSS pending an active shrinkage-tuning use case.
> - **(5.1) `.solid` on joints LOCKED** (silence = consent). Joints expose `.solid` returning `.male(overlap=0.0)`.
> - **(5.4) Constructor naming LOCKED** (silence = consent). `diameter` always; `length` for axial linear parts; `depth` for subtractive features; `height` for vertical-dominant parts; 100% type hints on public constructors.
> - **(5.5) `__init__.py` discipline LOCKED** (silence = consent). Two-level: leaf subpackages re-export; mid-level packages export nothing; top-level `models/__init__.py` empty.
> - **Atomic-break-pre-OSS LOCKED** (silence = consent). All Round 4 + 5 renames land in one PR (or coordinated cluster) with no shim layer. No deprecation cycle pre-OSS.
>
> Round 5 closed.
>
> **Round 5 follow-up (2026-05-13).** User confirmed: "there is no external user at the moment, no need to consider churning." This simplifies the entire brief:
> - The "what would break for a hypothetical existing user" backwards-compat-surfacing discipline becomes moot (R12 documentation-only).
> - The churn classification axis collapses to **implementation effort only** — labels rename from `LH/HB` → `LE/HB`, `MC/MB` → `ME/MB`, `HC/HB` → `HE/HB`. Project-wide effect: every recommendation in this brief is evaluated by implementation cost vs structural benefit, not user pain.
> - Phased implementation plan (R10) can be more aggressive — no rollout constraints; phases driven by implementation-effort sequencing only.
> - "Atomic-break-pre-OSS" terminology retired; everything just lands atomically. Methodology section above updated accordingly.

### Round 6 — Shared infra audit (`cq_utils.py`, `print_settings.py`)

**TL proposal:**

> Round 5 resolution restructured `ToleranceProfile` (the bulk of `print_settings.py`). This round audits what's LEFT in the two shared-infra modules and what an OSS user's import experience looks like.
>
> **(6.1) `cq_utils.py` post-cleanup contents.**
>
> After Round 3 (slipper-gear → experiments, taking `tapered_arm_profile` + `archimedean_spiral_arc` with it), `cq_utils.py` retains:
>
> | Symbol | Purpose | Verdict |
> |---|---|---|
> | `rounded_box(width, depth, height, corner_r, center)` | Axis-aligned box with vertical corner fillets | **Keep** — generic primitive, used across multiple model classes. |
> | `cylinder(radius, height, center)` | Cylinder extruded along +Z from `center` | **Keep** — generic primitive. |
> | `countersunk_hole(bore_r, bore_depth, cs_r, cs_depth, center)` | Countersunk bore | **AUDIT** — overlaps with `mechanical/holes.py::CounterboreHole` (head_type="cone"). Is there a reason both exist? Two-callers-vs-one check needed. If `holes.py` covers all current call sites, the standalone helper is a duplicate seam. |
> | `orient_to_neg_x`, `orient_to_pos_x` | Re-orient a +Z cutter to enter through ±X wall | **AUDIT** — when are these used? If for wall-mount cutters only, perhaps fold into a `WallCutter` adapter or move to `lego_adapters/`. |
> | `WithAllowance` | Shell-offset wrapper | **DEPRECATE per Round 4** — superseded by profile-aware CutterProtocol implementations. |
> | `cut_at_positions(part, cutter, positions, z_offset)` | Subtract `cutter` at every (x, y) position | **Keep** — common pattern; small and focused. |
> | `fillet_z_edges(wp, r_min, r_max, radius)` | Safely fillet Z-aligned edges whose radial centroid falls in range | **AUDIT** — fairly niche. When is this needed? If used by only 1-2 classes, candidate for inlining. |
>
> **Proposed Round 6 actions on `cq_utils.py`:**
> - Keep `rounded_box`, `cylinder`, `cut_at_positions` — clear primitives.
> - Remove `WithAllowance` (per Round 4 deprecation).
> - **Survey completed (2026-05-13)** — all three audit targets are single-caller:
>   - `countersunk_hole` → only used in `xlego/servos/sg90/servo_mount.py` + `servo_mount_half.py` (3 call sites). **Duplicates `CounterboreHole(head_type="cone")` from `holes.py`.** Verdict: **REMOVE** from `cq_utils`; migrate the 3 SG90 call sites to `CounterboreHole.to_cutter()`.
>   - `orient_to_neg_x` / `orient_to_pos_x` → only used in the same two SG90 mount files (4 call sites). Verdict: **MOVE** to a private `vibe_cading/lego_adapters/_wall_helpers.py`. Underscored = clearly private; not part of the OSS-contributor import surface.
>   - `fillet_z_edges` → only used in `xlego/slipper_gear/directional/parts/slipper_spring.py` (1 call site). Verdict: **MOVE to `experiments/`** with `slipper_spring.py` per Round 3.
>
> **Net result for `cq_utils.py` post-Round 6: 10+ exports → 3 exports** (`rounded_box`, `cylinder`, `cut_at_positions`). Dramatically cleaner OSS public surface.
>
> **(6.2) `print_settings.py` post-restructure.**
>
> After Round 5's `ToleranceProfile` change, `print_settings.py` exposes:
> - `ToleranceProfile` — dataclass (new 2D shape).
> - `FitGrade` — sub-dataclass.
> - `get_profile(name=None) -> ToleranceProfile` — resolves name → profile via JSON files.
> - `get_default_profile_name() -> str` — env-var resolver.
> - `_load_json_profiles()` — internal (underscored).
>
> Public OSS-user surface: `from models.print_settings import ToleranceProfile, FitGrade, get_profile`.
>
> **`machine_profiles.json` schema migration** — current JSON schema has flat keys (`z_clearance`, `press_fit`, etc.). New schema needs nested grade objects:
>
> ```json
> {
>     "fdm_standard": {
>         "free":  {"radial": 0.15, "axial": 0.20},
>         "slip":  {"radial": 0.05, "axial": 0.0},
>         "press": {"radial": -0.04, "axial": 0.0}
>     },
>     "resin_precise": {
>         "free":  {"radial": 0.05, "axial": 0.05},
>         "slip":  {"radial": 0.03, "axial": 0.0},
>         "press": {"radial": -0.02, "axial": 0.0}
>     }
> }
> ```
>
> `machine_profiles_user.json` migrates the same way. Both files updated atomically in the same PR as the Python schema change.
>
> **(6.3) Standardize the `.env` parsing helper.**
>
> Both `print_settings.py` and `lego/constants.py` contain their own `.env` parser (~10 lines of duplicated code). Single-adapter speculative seam — only two callers, but they're identical. Two options:
> - **(a) Centralize.** Move to `cq_utils._env_loader` (private) or `models/_internal/env.py` (private). Both callers import.
> - **(b) Leave duplicated.** Two callers, low complexity, no test surface — acceptable.
>
> TL recommendation: **(a) centralize**, but in a clearly-marked private module (`models/_env.py` with underscored helper names). OSS users don't import it; reduces drift between the two copies.

**Requester challenge / contribution:**

> - (6.1): TL surveyed call sites on TL's own initiative (no user pushback needed); single-caller verdict for all three audit targets confirmed.
> - (6.2): approved — `machine_profiles.json` schema breaks atomically with the Python `ToleranceProfile` 2D restructure.
> - (6.3): user clarified the `.env`-as-uncommitted policy (already in place) and asked TL to pick the parser direction.

**Resolution:**

> - **(6.1) LOCKED** per call-site survey. `cq_utils.py` shrinks from 10+ exports to 3 (`rounded_box`, `cylinder`, `cut_at_positions`).
> - **(6.2) LOCKED.** JSON schema migration is atomic with the Python change.
> - **(6.3) LOCKED at (a) centralize.** New private module `models/_env.py` holds the shared parser; `print_settings.py` and `lego/constants.py` import it. `.env.example` added as an implementation-plan deliverable; `.env` itself stays gitignored.
>
> Round 6 closed.

### Round 7.5 — Reviewer-conditions integration (2026-05-14)

After drafting-TL sign-off and Step 3.5 spawn of parallel independent reviewers, both returned **APPROVE-WITH-CONDITIONS** with 14 total conditions (TL: 5, Developer: 9). Conditions applied to this design before re-spawning the same reviewers for confirmation:

**TL conditions:**
1. **Cutter survey completeness** — added `Sg90Servo.to_cutter` (`rc/servo/sg90.py`), both `ventilation.py` cutter classes, and the `FastenerDrive` ABC subtree (`drives.py` — `HexDrive` / `SlottedDrive` / `PhillipsDrive` / `TorxDrive` using the older `cutter()` naming) to the Round 4 cutter migration table.
2. **Gear inheritance facts** — corrected: `HelicalGear` inherits from `SpurGear` (not directly from `Gear`); `RackGear` does NOT inherit from `Gear`. Phase 6 shared primitives become `@classmethod` helpers (`Gear.involute_tooth_profile_2d(module, teeth, pressure_angle)` callable without inheritance) so `RackGear` can consume them without re-parenting.
3. **Stale paths and counts** — Tests T6 paths updated to `vibe_cading.*`; Phase 3 T3.4 class count corrected from "4 classes" to "7 classes" for `holes.py`; `InsertFastener` → `HeatSetInsert` in the Round 4 cutter table; `get_screw_allowances` reference in `docs/screws.md` added to Phase 7 T7.4.
4. **R9 / R10 / R11 / R12 test-mapping** — added T15 covering R9 (effort table presence), R10 (phased plan presence), R11 (Wave C reconciliation note presence). T14 still covers R12.
5. **Phase 1 T1.4 build.toml clause** — dropped the no-op "delete any build.toml entry" since `trailer_hitch_cover.py` is not registered.

**Developer conditions:**
1. **Cross-zone import violation** — RESOLVED by the SG90 misclassification correction documented above. SG90 shaft files stay in `lego_adapters/servos/`; no cross-zone import remains.
2. **CI workflow update** — added Phase 1 task T1.16 covering `.github/workflows/ci.yml` (4 hardcoded `models/` paths).
3. **Tool file path updates** — Phase 1 task T1.13 expanded to enumerate the 6 affected tools (`tools/check_no_main_blocks.py`, `tools/check_license_headers.py`, `tools/gen_engine_api.py`, `tools/model_loader.py`, `tools/view.py`, `tools/preview.py`, `tools/boolean_diff.py`).
4. **engine_api Protocol filter** — added Phase 5 task T5.8 extending `tools/engine_api/extractor.py::_is_discoverable` to filter `typing.Protocol`-derived classes (mirrors existing ABC-exclusion logic).
5. **Polar monotonicity invocation** — T12 / T6.10 reconciled: the monotonicity check is invoked against the `@classmethod` shared primitives (which take parameters), not zero-arg instances. Specifically `Gear.involute_tooth_profile_2d(module=1.0, teeth=20, pressure_angle=20.0)` and similar fixed reference inputs.
6. **Tests scaffolding** — added Phase 0 tasks T0.5–T0.7: scaffold `tests/` directory with `pytest.ini`, `conftest.py`, and a `tests/__init__.py`; add a `pytest` step to `.github/workflows/ci.yml` (covered by T1.16's CI update).
7. **Pre-refactor STEP snapshot** — added Phase 0 task T0.8: `cp -r output/ tmp/pre-refactor-output/` (or equivalent) BEFORE Phase 1 begins, so T2 (volume diff per class) has a reference set.
8. **INSTRUCTIONS.md doc surface** — Phase 7 T7.4 expanded to enumerate the `vibe/INSTRUCTIONS.md` lines referencing `models/` (8 lines including the line-117 Deep-Modules Dual-Lens Rule that this design itself cites).
9. **`HexWheelHub` class rename** — Phase 1 T1.5 locks the new class name as `FreespinHexHub`.

---

### Round 7 — Synthesis (final round before author sign-off)

**TL proposal:**

> No new decisions. This round consolidates Rounds 1–6 into the four required synthesis artifacts: master effort-benefit table (R9), phased implementation plan (R10), Wave C C1/C2 reconciliation (R11), tests mapping every R1–R12, success criteria, known risks. All four are written below in their respective `### Implementation Plan` / `### Tests` / `### Success Criteria` / `### Known Risks & Mitigations` sections (under §"Architecture / Approach" and below). The Module-depth table is finalized with every new Module proposed across all rounds.
>
> Once you confirm the synthesis captures your intent, I'll mark the drafting-TL author sign-off and the workflow proceeds to Step 3.5 (independent fresh-context reviewers — `tl` and `developer` subagents validate against the requirements; domain-expert reviewer skipped since the domain-integrity gate is NO).

**Requester challenge / contribution:**

> _(awaiting final confirmation)_

**Resolution:**

> _(pending final confirmation)_

<!-- Round 7 closes when user confirms; TL marks author sign-off; Step 3.5 begins. -->

---

## Sign-off

### Author sign-off (drafting TL — Step 3 termination)
- [x] Domain expert co-sign  *(N/A — domain integrity gate is NO)*
- [x] Requester sign-off  *(confirmed 2026-05-14 in dialog)*
- [x] Drafting-TL sign-off  *(2026-05-14 — Step 3 terminated; Step 3.5 begins with parallel independent TL + Developer reviewers)*

### Independent reviewer sign-off (fresh-context — Step 3.5 termination)
- [x] Independent TL  *(APPROVE 2026-05-14 re-confirmation; original APPROVE-WITH-CONDITIONS 5/5 resolved)*
- [x] Independent Developer  *(APPROVE 2026-05-14 re-confirmation; original APPROVE-WITH-CONDITIONS 9/9 resolved, including the Dev-1 cross-zone-import architectural blocker)*
- [x] Independent Researcher  *(N/A — domain integrity gate is NO)*

---

## Implementation Status
_Populated by @developer at start of Step 5 Phase A._

- [ ] All Implementation Plan tasks completed
- [ ] Test suite executed — result: _(TBD)_
- [ ] No new linter / static-check errors
- Developer note: _(TBD)_

---

## Post-Implementation Sign-Off

### TL Review
- [ ] **TL sign-off** — implementation matches design; tests pass; no unintended scope creep
- TL review notes: _(TBD)_

### Human Final Approval
- [ ] **Human approved** for merge / release
- Human notes: _(TBD)_

---

## Independent TL Review (fresh context, 2026-05-14)

**Verdict:** APPROVE-WITH-CONDITIONS

The design is strong on methodology, well-grounded in the Deep-Modules Dual-Lens Rule, and the per-base verdicts hold up against the code. The cutter survey is mostly accurate, the package partition is internally consistent after the Round 3 follow-up, and the phased plan is realistic. However, three classes of factual drift between the design narrative and the actual code merit pre-implementation correction: (a) the cutter-survey scope misses three concrete classes (Sg90Servo, ventilation holes, FastenerDrive subtree); (b) the Gear duplication rationale overstates the case — `HelicalGear` inherits from `SpurGear` (not Gear directly), `RackGear` is unparented from Gear entirely, so Phase 6's foundation cannot be consumed by RackGear without an additional parenting step that the plan does not describe; (c) several import-path / class-name / class-count details in the Tests, Phase 3, and Phase 5 sections are stale relative to the Round 3 namespace-rename close. None are architectural blockers; all are easily editable; together they shift implementation effort estimates.

### Strengths

- The Deep-Modules Dual-Lens Rule is applied consistently and produces defensible per-base verdicts. The drift evidence cited for `Screw`/`Nut` (concrete signatures vs ABC signatures) is verifiable at the cited file:line and supports the `replace-with-Protocol` route.
- The `cq_utils` single-caller audit (Round 6.1) is empirically grounded: I confirmed `countersunk_hole`, `orient_to_neg_x/pos_x`, `fillet_z_edges`, `tapered_arm_profile`, and `archimedean_spiral_arc` each have the call sites the brief claims. The 10-exports → 3-exports outcome is honest.
- Round 4's call-site-fit (`fit` kwarg) vs constructor-fit decision, plus the per-class through-vs-blind overcut codification, are sound design responses to the actual hole-class shapes in `models/mechanical/holes.py`. The overcut policy aligns with the project's Known-Modelling-Pitfalls rules.

### Conditions / required edits

1. **Cutter-survey completeness gap (edits §"Round 4 — Cutter protocol unification" migration table and §Implementation Plan Phase 4).** The Round 4 migration table omits three concrete classes that emit cutters in `models/`:
   - `models/rc/servo/sg90.py:453` — `Sg90Servo.to_cutter(clearance, extend_shaft_up)`
   - `models/mechanical/enclosures/ventilation.py:53, 122` — both with `to_cutter(thickness, overcut)`
   - `models/mechanical/screws/drives.py` — `FastenerDrive` ABC and its four subclasses (`HexDrive`, `SlottedDrive`, `PhillipsDrive`, `TorxDrive`) use a different method name `cutter()` (no `to_`), and `FastenerDrive` is an unflagged ABC.
   Add a Phase 4 task line for each, and add a row to the migration table. If any are intentionally out-of-scope, state the rationale in §Out of Scope rather than leaving them silently uncovered.

2. **Gear-deepening foundation must address RackGear's non-parentage (edits §"Architecture / Approach → Gear deepening proposal" and §Implementation Plan Phase 6).** `models/mechanical/gears/rack.py:22` defines `class RackGear:` with no parent — it does NOT inherit from `Gear`. `models/mechanical/gears/helical.py:23` defines `class HelicalGear(SpurGear):` — HelicalGear consumes SpurGear's `_involute` / `_gear_profile_points`, so the duplication claim is overstated. Phase 6's `_gear_blank_with_teeth_2d` / `_involute_tooth_profile_2d` cannot be inherited by `RackGear` without first re-parenting it under `Gear`, and `Gear.__init__(module, teeth, face_width, bore, pressure_angle)` is incompatible with `RackGear.__init__(module, length, face_width, thickness, pressure_angle)` (no `teeth`, no `bore`). Two options to record: (a) re-parent `RackGear` under a new common ancestor / Protocol (and update `Gear.__init__` to be friendlier to rack geometry), or (b) document explicitly that the new shared primitives are static / classmethod helpers consumable without inheritance, and `RackGear` uses them as plain functions. Add the chosen option as a Phase 6 sub-task.

3. **Stale `models.*` paths and class-count drift in Tests + Phase 3 (edits §Tests row T6 and §Implementation Plan Phase 3 T3.4).** The Round 3 final close renamed `models/` → `vibe_cading/` with sibling `parts/`, but:
   - Tests T6 still cites `from models.mechanical.screws…`, `from models.lego_adapters.servos.sg90…`, and `from models.applications.arrma_vorteks_223s…`. Update to `vibe_cading.*` for library content and `parts.arrma_vorteks_223s.*` for project-specific content (the `applications/` nesting was superseded by the Round 3 follow-up — that path will not exist).
   - §Tests Success Criteria §5 mentions `docs/screws.md`; that doc currently references the never-implemented `get_screw_allowances` API. Phase 7 T7.4 covers it in spirit, but call it out explicitly (an OSS user copying the example will hit `ImportError`).
   - Phase 3 T3.4 says "`vibe_cading/mechanical/holes.py` (4 classes)". The file actually contains 7 classes (`ClearanceHole`, `CounterboreHole`, `TeardropHole`, `SlottedHole`, `TaperedHole`, `Keyhole`, `CaptiveNutPocket`) — the migration scope is ~75% larger than stated. Update the count.
   - `mechanical/inserts.py` defines `HeatSetInsert`, not "InsertFastener" as named in §Round 4 migration table and Phase 4 T4.6. Replace the name.

4. **R9/R10/R11 missing from the Tests↔Requirements mapping (edits §Tests table "Maps to" columns).** The req termination contract states *every* functional requirement R1–R12 maps to at least one test row. R9 (effort-vs-benefit classification), R10 (phased plan), and R11 (Wave C reconciliation) currently appear in no row's "Maps to" column. They are meta-deliverables satisfied by §"Effort-vs-benefit master table", §Implementation Plan, and §"Wave C reconciliation" respectively — the same shape as R12's T14 row, which uses "documentation-only" framing. Either (a) extend T14 to claim R9, R10, R11, R12 collectively, or (b) add a T15 documentation-pass row for them. Either resolves the literal req-compliance gap.

5. **Phase 1 build.toml + trailer_hitch_cover (edits §Implementation Plan Phase 1 T1.4).** T1.4 says "Delete `vibe_cading/mechanical/trailer_hitch_cover.py` + any `build.toml` entry." I confirmed there is no `trailer_hitch_cover` entry in `build.toml` today. Drop the "+ any `build.toml` entry" clause to keep the task list accurate, or change to "verify no build.toml entry remains." Minor, but the kind of small inaccuracy that compounds during implementation.

### Open concerns (non-blocking)

- **`models/__init__.py` does not exist today** (the design Round 5.5 calls it "empty"). Functionally equivalent for re-export purposes, but the Phase 1 rename via `git mv models vibe_cading` produces a directory with no `__init__.py` — and any future `pyproject.toml` work will trip on it. *Predicted cost if it bites: ~15 minutes during a future packaging PR to discover and add `vibe_cading/__init__.py`, plus possibly one round of confused contributor reports if a contributor expects `from vibe_cading import …` to work for some symbol.*

- **`xlego/motors/mount_plate.py:21`** accepts `material="PLA"` constructor parameter (matching the `get_screw_allowances` doc-only API). After it moves to `parts/arrma_vorteks_223s/motor_mount_plate.py` in Phase 1, the brief does not specify whether its `material=` kwarg migrates to `profile=` along with the library Phase 3/4 changes. *Predicted cost if left: one downstream Arrma-build regression discovered at the first post-refactor `python build.py` run on `parts.arrma_vorteks_223s.motor_mount_plate.MotorMountPlate` — ~30 minutes to identify and patch when build.py exits with `TypeError: __init__() got unexpected keyword argument 'material'` or a silent profile-not-applied fault.*

- **Round 5.1 `joint.solid` returning `male(overlap=0.0)`.** Conceptually clean, but `overlap=0.0` means the joint occupies exactly the volume it would intersect with the parent body — no extension, no clearance. This may produce a visualization that looks identical to a coincident-face geometry (the joint glued to a notional parent), which is unhelpful for a contributor running `tools/view.py CantileverSnapFit` to learn the part. *Predicted cost if confusing: 1-2 contributor-reported issues that "the snap-fit preview looks wrong"; ~30 minutes to either tune the default overlap or document that `.solid` is the cutter-aligned form and `male(overlap=2.0)` is the natural preview form.*

- **Phase 1's `model_loader.py` two-root behaviour (edits not required but worth flagging).** The current loader inserts both `REPO_ROOT` and `MODELS_DIR` on `sys.path` to support both `from models.X` imports and bare `module.path.ClassName` build.toml entries. After Phase 1, the bare-import shape becomes `vibe_cading.X.ClassName` (a regular package path), so `MODELS_DIR` is no longer needed (and arguably should be removed to prevent shadowing). T1.13 says "verify in a probe" but does not direct the loader to drop the `MODELS_DIR` insertion. *Predicted cost if `MODELS_DIR` stays: ~15 minutes once a developer notices shadow-import behaviour (e.g., a bare `cq_utils` import resolving via `MODELS_DIR` instead of the namespaced `vibe_cading.cq_utils`); not a runtime bug today, but a latent confusion source.*

- **`FastenerDrive` ABC was not on the req's R2 enumeration** (the req lists only Screw/Nut/BaseJoint/Gear/SlipperGearBase). The design followed the req's list, so it is not "wrong against the req" — but the req was incomplete. `FastenerDrive` (drives.py:12, `@abstractmethod def cutter`) is a sixth ABC with a `cutter()` method name that conflicts with the project's `to_cutter()` convention. *Predicted cost if left for post-OSS: a stylistic regression at the first OSS contributor adding a new drive type — they'll either copy the `cutter()` naming (perpetuating the inconsistency) or rename to `to_cutter()` and break callers in `screws/*.py` that call `drive.cutter()`. ~1 hr to grep / fix at that moment.*

### Verification log

1. `models/mechanical/screws/base.py:33` — ABC signature `to_cutter(mode, radial_allowance=0.0, head_recess_depth=0.0)`. **Confirmed.** Drift vs concrete `metric.py:133` `to_cutter(mode, profile=None)` is real.
2. `models/mechanical/nuts/base.py:33` — ABC `to_cutter(radial_allowance=0.15, depth_allowance=0.2)`. **Confirmed.** Drift vs `metric.py:58/133` `to_cutter(profile=None)` for `MetricHexNut`/`MetricSquareNut`; `tnut.py:66` keeps `(radial_allowance, depth_allowance)`. Partial-drift claim correct.
3. `models/mechanical/joints/base.py:33-46` — `BaseJoint(ABC)` with abstract `male(overlap)` + `female(overlap)`. **Confirmed.** Concrete `dovetail.py:44/61` and `snap_fit.py:59/85` match exactly — "no drift" claim correct.
4. `models/mechanical/gears/base.py:19` — `Gear(ABC)` with `__init__` + derived radii + `center_distance_to`. **Confirmed.** Abstract `solid` property present at line 53.
5. `models/mechanical/gears/spur.py:23` — `class SpurGear(Gear)`. **Confirmed.**
6. `models/mechanical/gears/helical.py:23` — `class HelicalGear(SpurGear)`. **Confirmed — design's narrative that "every concrete subclass re-implements involute math independently" is contradicted: HelicalGear inherits `_involute` and `_gear_profile_points` from SpurGear.**
7. `models/mechanical/gears/rack.py:22` — `class RackGear:` with NO parent. **Confirmed — `RackGear` does not inherit from `Gear`. The Module-depth table and Phase 6 deepening cannot apply to `RackGear` without a re-parenting step that the plan omits.**
8. `models/xlego/slipper_gear/directional/base.py:25` — `class SlipperGearBase:` (no ABC, no abstract methods). **Confirmed — name implies extension contract that doesn't exist.**
9. `models/mechanical/holes.py` — 7 classes (`ClearanceHole`, `CounterboreHole`, `TeardropHole`, `SlottedHole`, `TaperedHole`, `Keyhole`, `CaptiveNutPocket`), all using `to_cutter(overcut=100.0)`. **Confirmed — Phase 3 T3.4 undercount of "4 classes" is wrong; should be 7.**
10. `models/mechanical/inserts.py:27` — class is `HeatSetInsert`, not "InsertFastener". `to_cutter(through_hole=False, clearance_d=3.2)`. **Confirmed — design's name is wrong; signature is right.**
11. `models/mechanical/standoffs.py:22` — `class HexStandoff` with `to_cutter(radial_allowance=0.15, depth_allowance=0.2)`. **Confirmed.**
12. `models/lego/cutters/technic_pin_hole.py:26` and `technic_axle_hole.py:24` — `class TechnicPinHole` / `class TechnicAxleHole` expose `.solid` property only, no `to_cutter`. **Confirmed — Round 4's "Add `to_cutter()` method" task is necessary.**
13. `models/cq_utils.py` — 7 exports + 2 curve helpers. Specifically: `rounded_box`, `cylinder`, `countersunk_hole`, `orient_to_neg_x`, `orient_to_pos_x`, `WithAllowance`, `cut_at_positions`, `tapered_arm_profile`, `archimedean_spiral_arc`, `fillet_z_edges`. **Confirmed — design Round 6.1 audit accurate.**
14. Single-caller verifications: `countersunk_hole` used in `servo_mount.py` (3 sites) + `servo_mount_half.py` (2 sites = 5 total; design says "3 SG90 call sites" — close but slightly off, both files combined have 5 actual call expressions). `orient_to_neg_x/pos_x` used in same two files (4 call sites — confirmed). `fillet_z_edges` used in `slipper_spring.py:145` (1 site — confirmed). `tapered_arm_profile` used in `slipper_spring.py:107` (1 site — confirmed). `archimedean_spiral_arc` used in `slipper_ring.py:288` (1 site — confirmed). **Mostly confirmed — minor undercount on `countersunk_hole` (3 → 5 call sites total).**
15. `models/print_settings.py` — `ToleranceProfile(name, z_clearance, press_fit, slip_fit, free_fit)` flat dataclass at line 39. **Confirmed.** No `FitGrade` exists today; Round 5.3 schema is genuinely new.
16. `.env` parser duplication: `models/print_settings.py:20-26` and `models/lego/constants.py:13-19` contain identical 10-line stanzas. **Confirmed — Round 6.3 centralization claim is real.**
17. `models/mechanical/__init__.py` — re-exports only `ClearanceHole`, `CounterboreHole`, `TeardropHole` from holes (a subset, NOT "holes only" as Round 5.5 phrased it; the file actually omits `SlottedHole`, `TaperedHole`, `Keyhole`, `CaptiveNutPocket`). **Confirmed inconsistent. Design framing "re-exports holes only (partial, inconsistent)" is half-right; the "partial" qualifier earns it.**
18. `models/__init__.py` — **DOES NOT EXIST.** Design Round 5.5 says it's "empty"; in fact the file is missing entirely. Functionally equivalent for re-export semantics, but distinct in the filesystem. **Contradicted.**
19. `models/mechanical/screws/__init__.py` — re-exports `Screw`, `MetricMachineScrew`, `WoodScrew`, `PlasticsScrew`, `SetScrew`, `ImperialMachineScrew`. **Confirmed.** Same shape for `nuts/`, `joints/`, `gears/`.
20. `models/mechanical/screws/drives.py:12` — `class FastenerDrive(ABC)` with `@abstractmethod def cutter` at line 20. Four concrete subclasses (`HexDrive`, `SlottedDrive`, `PhillipsDrive`, `TorxDrive`). **Confirmed — this ABC is not addressed anywhere in the design.**
21. `models/rc/servo/sg90.py:453` — `Sg90Servo.to_cutter(clearance, extend_shaft_up)`. **Confirmed — Round 4 migration table does not include this class.**
22. `models/mechanical/enclosures/ventilation.py:53, 122` — two classes both with `to_cutter(thickness, overcut)`. **Confirmed — Round 4 migration table does not include them.**
23. `models/xlego/motors/mount_plate.py:21` — `__init__(... material="PLA")`. **Confirmed — `material=` kwarg lives in code; matches the `get_screw_allowances` doc API; not addressed in Phase 1 move.**
24. `docs/screws.md:100, 103-105` — example uses `from models.print_settings import get_screw_allowances` and `material="PLA"`. **Confirmed — this is the doc-vs-code drift the platform-coordination artifact already flagged; Phase 7 T7.4 implicitly covers it but the brief should call it out by name.**
25. `tools/model_loader.py:25-70` — inserts both `REPO_ROOT` and `MODELS_DIR` on `sys.path`. **Confirmed — Phase 1 T1.13's probe-then-verify approach is workable; the `MODELS_DIR` insertion can be removed after rename, but the plan doesn't direct it.**
26. `.agents/plans/INDEX.md:28-29, 38` — Wave C C1 and Wave C C2 listed as `blocked` on `vibe-cading-platform#4`. **Confirmed.** `tmp/platform-coordination-wave-c.md` cites `get_screw_allowances` / `material=` as the original platform-coord surface — also confirmed.
27. `tmp/structural-review-2026-05-08.md` and `todo.md` — both exist. **Confirmed.**
28. `tests/` directory — **DOES NOT EXIST.** Design refers to `tests/test_protocols.py`, `tests/test_tolerance_profile.py`, `tests/test_imports.py`, `tests/test_cutter_overcut.py`. These are net-new files; the design implicitly relies on creating them but no Phase 0 / Phase 1 task scaffolds the `tests/` directory or `tests/__init__.py`. Minor — they're created at the moment they're written — but should be noted.
29. `build.toml` — no `trailer_hitch_cover` entry exists. Phase 1 T1.4 says to delete "any `build.toml` entry" — there is none. **Contradicted (mild — the task is a no-op for the build.toml clause).**

## Independent Developer Review (fresh context, 2026-05-14)

**Verdict:** APPROVE-WITH-CONDITIONS

The design is methodologically sound, the per-base verdicts hold up, and the phased plan is internally coherent at the *model-code* level. From the developer's seat, however, the plan under-specifies the *infrastructure* edges that Phase 1's rename must touch: CI workflow steps, repo-rooted lint helpers, the engine-api extractor, the polar-monotonicity tool's invocation contract, and the not-yet-existent `tests/` framework are all named in Tests/Success Criteria as if they already work post-rename, but each requires its own edit not enumerated in any phase task. The single architectural blocker is a cross-zone import that the file-moves create: `models/xlego/servos/sg90/servo_mount.py` imports `Shaft` from `xlego/servos/shaft.py` — the former stays in `vibe_cading/lego_adapters/`, the latter moves to `experiments/`, and Success Criterion 11 forbids exactly that link. The rest are mechanically fixable plan edits that should land before Phase 1 begins so the developer doesn't discover them mid-rename.

### Strengths

- The phase dependency graph (Phases 0–4 sequential, 5+6 parallel, 7 final) correctly reflects the actual coupling between cutter-protocol introduction and the Screw/Nut/Joint Protocol conversion. The plan is realistic — there is no execution order that demands a tighter sequence.
- Round 4's per-class through-vs-blind overcut codification matches the existing `holes.py` structure (CaptiveNutPocket already blind-shaped, others through), so the convention is genuinely how the code is already organized — not a retrofit.
- The Round 6 `cq_utils.py` single-caller audit was done correctly and the verdicts are evidence-backed at the file:line level.

### Conditions / required edits

1. **Cross-zone import breaks Success Criterion 11 (edits §Implementation Plan Phase 1 T1.10, and §Out of Scope).** `models/xlego/servos/sg90/servo_mount.py:71` and `models/xlego/servos/sg90/servo_mount_half.py:71` both contain `from models.xlego.servos.shaft import Shaft`. T1.10 moves `xlego/servos/shaft.py` to `experiments/slipper_gear/servo_shaft/`, while the SG90 mount files stay in `vibe_cading/lego_adapters/servos/sg90/`. After Phase 1, the library would import from `experiments/` — directly violating Success Criterion 11 ("No file moved to `experiments/` is imported from inside `vibe_cading/` or `parts/`"). Resolution options to pick between in the design before implementation starts: (a) keep `shaft.py` in `vibe_cading/lego_adapters/servos/sg90/` (it's used by the SG90 mount adapter, not just slipper-gear); (b) extract the subset of `Shaft` the mounts need into the lego_adapters tree and move the residual to experiments; (c) move the SG90 mounts to experiments alongside `shaft.py` (re-classifies SG90 mounts as experiments — contradicts Round 3 decision). Without one of these, Phase 1's atomic-commit will leave the library broken.

2. **CI workflow rename omitted (edits §Implementation Plan Phase 1, add a task T1.16).** `.github/workflows/ci.yml` hardcodes `models/` in four places: line 28 (`find models tools -type f -name '*.py'`), line 45 (`grep -rlE 'if __name__...' models/`), line 50 (`grep -rlE 'from ocp_vscode' models/ tools/`), and the AST-checker step at line 43. After T1.2's global find-and-replace, none of these will match — CI will green-light an empty file set or fail outright. Add T1.16: update `ci.yml` to substitute `vibe_cading parts experiments` (or whichever roots are in scope for each check) for `models`.

3. **Lint-helper hardcoded paths omitted (edits §Implementation Plan Phase 1, add tasks).** Four tool files hardcode `models/` and are required by CI: `tools/check_no_main_blocks.py:70` (`models_dir = repo_root / "models"`), `tools/check_license_headers.py:9` (`glob.glob("models/**/*.py")`), `tools/gen_engine_api.py:60` (`extract_classes([repo_root / "models"])`), and the `MODELS_DIR = REPO_ROOT / "models"` constants in `tools/model_loader.py:100`, `tools/view.py:93`, `tools/preview.py:69`, `tools/boolean_diff.py:56`. The TL review's "Open concerns" #4 mentions `model_loader.py` MODELS_DIR shadowing risk; the developer-side issue is broader — six tool files need edits, plus the docstring/comment text in `model_loader.py` that says "53 from models.X imports" and "MODELS_DIR enables bare-import paths." Add explicit T1.x tasks per file rather than relying on T1.13's "audit" framing.

4. **engine_api extractor cannot enforce "no `*Protocol` types leak" (edits §Implementation Plan Phase 5, add a task; or relax Success Criterion §2).** `tools/engine_api/extractor.py:262-277` (`_is_discoverable`) filters out `ABC`-derived classes and classes with `@abstractmethod` methods — it does NOT filter `typing.Protocol`-derived classes. After Phase 5 introduces `class ScrewProtocol(Protocol):` etc., the extractor will include them in `engine_api.json`. Success Criterion §2 says "no `*Protocol` types leak" and Test T3 asserts the same. To satisfy this, add a Phase 5 task: extend `_is_discoverable` to also exclude classes whose declared base reads as `Protocol` / `typing.Protocol` / `runtime_checkable`-decorated bases. Without this edit, T3 either fails as written or has to relax its assertion.

5. **`tools/check_polar_monotonicity.py` cannot run on Gear shared methods (edits §Tests T12, or §Implementation Plan Phase 6 T6.10).** Lines 64-67 of the tool do `cls = load_class(class_dotted); obj = cls(); pts = getattr(obj, method_name)()`. `Gear()` raises `TypeError` (abstract + required positional args `module, teeth, face_width`). `Gear._gear_blank_with_teeth_2d` and `Gear._involute_tooth_profile_2d` cannot be reached through this tool as written. Options: (a) modify the tool to accept default-construction kwargs (e.g. `--params module=1.0 teeth=20 face_width=5.0`); (b) phrase the test against a *concrete* subclass method, e.g. `SpurGear._gear_blank_with_teeth_2d`; (c) make the new methods `@staticmethod`s or module-level functions so they don't need an instance. Pick one and edit T6.10 and T12 to match the actual invocation contract.

6. **`tests/` framework not scaffolded (edits §Implementation Plan, add a Phase 0 task; edits §Success Criteria).** Tests T4, T5, T6, T13 assume `pytest` (or equivalent) — `tests/test_protocols.py`, `tests/test_tolerance_profile.py`, etc. The repo has no `tests/` dir, no `pytest.ini` / `pyproject.toml` test-config, no CI step that invokes `pytest`. The TL review's open concern #28 noted the directory is missing; from a developer-execution perspective the deeper missing pieces are: a runner declaration (pytest? unittest?), a fixture for repo-root sys.path priming (so test imports of `vibe_cading.*` and `parts.*` resolve), CI integration, and a `tests/__init__.py` if package-style. Add an explicit Phase 0 sub-task to scaffold this, or relax T4/T5/T6/T13 to "manual ad-hoc verification" with a documented invocation recipe.

7. **Pre-refactor STEP snapshot strategy missing (edits §Implementation Plan Phase 1, add a Phase 0 task; edits §Tests T2 / §Success Criteria §1).** Test T2 and Success Criterion §1 require "volume delta < 0.1% per class against the pre-refactor reference." This requires snapshotting `output/*.step` BEFORE Phase 1's mass-rename touches the build, into a stable location (`tmp/pre-refactor-output/` or similar) that survives the rename. Add a T0.x: "Run `python build.py` against the current `models/` tree, then copy `output/` → `tmp/pre-refactor-output/` for reference comparison." Otherwise T2 has no reference to diff against once Phase 1 lands.

8. **Knowledge-base updates undersized at T7.4 (edits §Implementation Plan Phase 7 T7.4).** `vibe/INSTRUCTIONS.md` contains at least 8 `models/`-path references (lines 20, 22, 110, 112, 177, 234, 548, 550, 553) — including the line-117 Deep-Modules Dual-Lens Rule the design itself cites as policy. `docs/templates/design-brief-template.md` has 3 `models.module.ClassName` example invocations. T7.4 says "Update `docs/lego-technic.md` and any other docs referencing the old class names / import paths" — "any other docs" is hand-wavy and leaves the most important file (the canonical instructions) implicit. Enumerate `vibe/INSTRUCTIONS.md`, `docs/screws.md`, `docs/templates/design-brief-template.md`, `docs/lego-technic.md`, and the agent persona files under `vibe/agents/` as explicit edit targets — the contributor-locality value of this brief depends on the canonical instructions being accurate post-merge.

9. **Renamed class name under-specified (edits §Implementation Plan Phase 1 T1.5).** T1.5 says "Update the class name to match (`FreespinHexHub` or current-class-renamed-similarly)." The current class is `HexWheelHub` at `models/rc/hex_wheel_hub.py`. "Or current-class-renamed-similarly" is non-atomic for execution — the developer must guess between `FreespinHexHub`, `FreespinningHexHub`, `IdlerHexHub`, etc. Build.toml entry at line 31 also needs the choice. Lock the name in the brief.

### Open concerns (non-blocking)

- **`tools/view.py` `--assembly` test (T9) is vacuous today.** No `assemble()`-defining module exists in `models/` (`grep -rln "def assemble" models/` is empty). After Phase 1's moves, the experiments-bound `shaft_with_saver.py` (which the INSTRUCTIONS.md example references as a hypothetical assembly) goes to experiments, and no library/parts module replaces it. T9 will pass trivially because it iterates over an empty set. *Predicted cost if left: 5 minutes' rework when a future contributor adds the first real assembly module and discovers the test is a no-op — they have to write the iteration scaffold from scratch.* Reasonable to drop T9 from the Tests table until the first real assembly module ships.

- **`gen_engine_api.py` after rename needs to walk both `vibe_cading/` AND `parts/`** (line 60 currently passes a single root). Currently `parts/arrma_vorteks_223s/*.py` would be missed by the extractor walk. The contract drift is silent — `engine_api.json` would no longer cover the project-specific end-products that are still registered in `build.toml`. *Predicted cost if missed: one re-build cycle on the platform side (~30 minutes) when their consumer discovers an empty section where `parts.*` classes should be; plus one regression-PR loop in this repo to add the second root.* Pair this with condition #3 above.

- **`flake8 .` invocation in CI (`.github/workflows/ci.yml:21`) walks the entire repo without an exclude list.** Post-rename, `experiments/` will exist as a new top-level — currently no `.flake8` / `setup.cfg` / `pyproject.toml` flake8 config to exclude it (verified absence of `.flake8`, no setup.cfg). The slipper-gear code being moved to experiments has known-acceptable style nits today (it's R&D). After Phase 1, those nits surface as CI failures. *Predicted cost if not handled: one CI-red iteration after Phase 1 lands, ~20 minutes to add an exclude or fix the surfaced issues. Adding `experiments` and `tmp` to a `.flake8` exclude list in Phase 0 prevents this.*

- **Sequencing of Phase 5 T5.6 (`__init__.py` re-export updates) vs Phase 5 T5.2 (delete base.py files).** T5.6 removes `Screw`/`Nut`/`BaseJoint` re-exports from `__init__.py` files. T5.2 deletes the `base.py` files those re-exports point at. If T5.2 runs before T5.6, the `__init__.py` import lines fail at import time — any user of `from vibe_cading.mechanical.screws import …` hits `ImportError: cannot import name 'Screw'` because `from .base import Screw` is still at the top of `__init__.py` but `base.py` is gone. *Predicted cost: minutes if discovered immediately, otherwise a confusing CI failure between the two commits. Either fold T5.2 + T5.6 into a single atomic edit or explicitly order T5.6 before T5.2.*

- **No "what package layout breaks if pyproject.toml is added later" check.** The brief's Round 3 follow-up explicitly defers pip-distribution. Fine. But the chosen layout (`vibe_cading/` + sibling `parts/` + sibling `experiments/`) requires the workspace root to be on `sys.path` to import either. A future `pyproject.toml` with `[tool.setuptools.packages.find]` would naturally include `vibe_cading` but NOT `parts` (parts is intentionally not a library package). The implicit decision — `parts/` is reachable only via repo-clone, never via `pip install` — is correct but not stated. *Predicted cost: ~30 minutes when the first pip-distribution PR is drafted and the maintainer rediscovers the policy.* Add one line to §Out of Scope: "Project-specific `parts/` are never pip-distributable; only `vibe_cading/` is."

### Verification log

1. `models/cq_utils.py:130-170` — `orient_to_neg_x` / `orient_to_pos_x` defined. **Confirmed.** Call sites in `xlego/servos/sg90/servo_mount.py:289-290` and `servo_mount_half.py:275-276` (4 total). **Confirmed — matches TL review item 14.**
2. `models/xlego/servos/sg90/servo_mount.py:71` — `from models.xlego.servos.shaft import Shaft`. **Confirmed.** Cross-zone violation: `servo_mount.py` stays in lego_adapters per T1.6; `shaft.py` moves to experiments per T1.10. Verified by reading both files' import blocks.
3. `models/xlego/servos/sg90/servo_mount_half.py:71` — same import shape. **Confirmed.** Same cross-zone violation.
4. `.github/workflows/ci.yml:28,45,50` — three hardcoded `models/` references in lint/check steps. **Confirmed.**
5. `tools/check_no_main_blocks.py:70` — `models_dir = repo_root / "models"`. **Confirmed.** AST walker rooted at hardcoded `models/`.
6. `tools/check_license_headers.py:9` — `glob.glob("models/**/*.py", recursive=True)`. **Confirmed.** Header check hardcoded to `models/`.
7. `tools/gen_engine_api.py:60` — `extract_classes([repo_root / "models"])`. **Confirmed.** Single-root walk; misses `parts/`.
8. `tools/model_loader.py:100, 116-123` — `MODELS_DIR = REPO_ROOT / "models"` and dual sys.path insert. **Confirmed.** Idempotent but no-longer-needed post-rename.
9. `tools/view.py:93`, `tools/preview.py:69`, `tools/boolean_diff.py:56` — each has its own `MODELS_DIR = REPO_ROOT / "models"`. **Confirmed.** Independent constants, three files to update.
10. `tools/engine_api/extractor.py:262-277` — `_is_discoverable` filters `ABC` base and `@abstractmethod`; does NOT filter `Protocol` / `typing.Protocol`. **Confirmed.** Protocol-leak prevention not implemented.
11. `tools/engine_api/extractor.py:354-360` — `demo` classmethod exclusion present. **Confirmed.** Design's Round 7 narrative that demo is the only special-case exclusion is true today.
12. `tools/check_polar_monotonicity.py:64-67` — `cls = load_class(class_dotted); obj = cls(); pts = getattr(obj, method_name)()`. **Confirmed.** No-arg `cls()` invocation cannot satisfy `Gear.__init__(module, teeth, face_width, ...)`.
13. `build.py:25-32` — uses `tools.model_loader.ensure_models_on_path()`. **Confirmed.** Inherits MODELS_DIR coupling.
14. `tests/` directory — `ls tests/` returns "No such file or directory." **Confirmed.** No pytest config in `.github/workflows/ci.yml`, no `.flake8`, no `pyproject.toml`. Test framework genuinely unscaffolded.
15. `build.toml` — 14 `[[build]]` entries; 12 unique module paths. **Confirmed.** Volume comparison surface for T2 = 14 STEPs.
16. `output/*.step` — directory exists at `output/`; contains the current pre-refactor STEPs (e.g. `output/rc/hex_wheel_hub_12mm.step`). **Confirmed.** Reference snapshot possible if captured before Phase 1.
17. `vibe/INSTRUCTIONS.md` line 117 — Deep-Modules — Dual-Lens Rule. **Confirmed.** Citation accurate.
18. `vibe/INSTRUCTIONS.md` — 8 lines contain `models/` or `from models.` (lines 20, 22, 110, 112, 177, 234, 548, 550, 553). **Confirmed.** T7.4 "any other docs" elides this surface.
19. `docs/templates/design-brief-template.md:79, 85, 89` — three example invocations referencing `models.module.ClassName`. **Confirmed.** Template will mislead future design briefs post-rename if not updated.
20. `find /workspaces/vibe-cading/models -name "*.py" | grep -E "assemble" -l` returns empty. `grep -rln "def assemble" models/` returns empty. **Confirmed.** No `assemble()` modules exist; T9 iterates over an empty set.
21. `models/mechanical/gears/rack.py:22` — `class RackGear:` no parent. **Confirmed independently of TL.** T6.8 cannot apply shared `Gear` methods without re-parenting.
22. `.github/workflows/ci.yml:21` — `flake8 .` with no config file (no `.flake8`, no `setup.cfg`, no `[tool.flake8]` in any toml). **Confirmed.** Phase 1's introduction of `experiments/` adds a flake8 walk target with no exclusion.
23. `models/rc/hex_wheel_hub.py` — class `HexWheelHub` (line 6 of the grep output). **Confirmed.** New name not locked in T1.5.
24. `models/xlego/servos/sg90/` lacks `__init__.py`. **Confirmed** (verified via `ls -la`). Same for `models/xlego/motors/` and `models/xlego/servos/`. Namespace packages today; Phase 1 inherits the same.
25. `engine_api.json` — tracked file (verified via `git ls-files`). 545 class entries. **Confirmed.** Regeneration scope after Phase 1.

## Independent TL Review — Re-confirmation (2026-05-14)

**Verdict:** APPROVE

The drafting team's Round 7.5 integration applied substantive edits to the design body for every one of the five conditions I raised, not just a log entry pointing at them. The cutter migration table gained three new rows (Sg90Servo, ventilation, FastenerDrive subtree) at lines 613–615 with matching Phase 4 tasks T4.8 / T4.9 / T4.10. The Gear inheritance facts are now correctly reflected in the Phase 6 reality-check annotation (line 215) and propagated into the task wording for T6.1, T6.7, and T6.8 — the chosen resolution (option b: `@classmethod` helpers consumable without inheritance) cleanly side-steps the need for re-parenting `RackGear`. Stale paths are repaired in Tests T6, Phase 3 T3.4 (class count 4 → 7), and the `InsertFastener` → `HeatSetInsert` rename. R9 / R10 / R11 / R12 now map to T14 + T15 in the Tests table. T1.4 dropped the no-op build.toml clause. No new architectural concerns surfaced during re-check. One residual documentation drift (the Round 2 narrative at lines 51 / 56 / 64 / 80 still asserts "every concrete subclass re-implements involute-tooth math independently" — which is factually wrong because `HelicalGear` inherits from `SpurGear`) does not block implementation: the Phase 6 plan does not depend on that narrative being accurate, and the line-215 reality check provides the corrective signal a future implementer will read. Acceptable as-is given the option-b classmethod resolution makes the duplication claim moot.

### Conditions resolution check

| # | Condition | Resolution | Justification |
|---|---|---|---|
| 1 | Cutter-survey completeness gap | **resolved** | Migration table at lines 613–615 adds Sg90Servo, both `ventilation.py` overloads, and the FastenerDrive ABC + four concrete drives, each annotated with "Added 2026-05-14 per TL-reviewer condition TL-1." Phase 4 gains T4.8 / T4.9 / T4.10 with matching scope, including the older `cutter` → `to_cutter` rename for the drives subtree. |
| 2 | Gear-deepening foundation vs RackGear non-parentage | **partially resolved** | Phase 6 fully repaired: line 215 reality-check annotation + T6.1 / T6.7 / T6.8 / T6.10 all consistently treat shared primitives as `@classmethod` helpers callable without inheritance (option b). The Round 2 architectural narrative at lines 51 / 56 / 64 / 80 still contains the old "every concrete subclass re-implements" framing, which is contradicted by `HelicalGear(SpurGear)`. The chosen Phase 6 design (option b) does not depend on the narrative being accurate, so this is documentation drift, not a plan defect. Future readers should rely on the Phase 6 wording, which is correct. Not blocking. |
| 3 | Stale `models.*` paths + class-count drift in Tests / Phase 3 / Phase 5 | **resolved** | Tests T6 row updated to `vibe_cading.mechanical.screws`, `vibe_cading.lego_adapters.servos.sg90`, `parts.arrma_vorteks_223s.*` (line 259). Phase 3 T3.4 explicitly notes "7 classes per reviewer verification — not 4" (line 189). `HeatSetInsert` (not `InsertFastener`) used in both Round 4 table (line 609) and T4.6 (line 198). `docs/screws.md` `get_screw_allowances` reference called out in T7.4 (line 235). |
| 4 | R9 / R10 / R11 missing from Tests↔Requirements mapping | **resolved** | T15 (line 268) explicitly maps to R9, R10, R11; T14 maps to R12; combined coverage now includes every R1–R12 across at least one test row. |
| 5 | Phase 1 T1.4 build.toml clause inaccuracy | **resolved** | T1.4 (line 157) now reads "Note: not registered in `build.toml` per reviewer verification — no build.toml edit needed for this task." Verified independently: `grep -c trailer_hitch /workspaces/vibe-cading/build.toml` returns 0. |

### New concerns surfaced during re-check (if any)

None blocking. One documentation observation is captured under Condition 2's "partially resolved" status: the Round 2 architectural-rationale narrative at lines 51 / 56 / 64 / 80 reads as if all three concrete gear subclasses independently re-implement involute math, but `HelicalGear` actually inherits from `SpurGear` and consumes its `_involute` / `_gear_profile_points` helpers. *Predicted cost if left: ~5–10 minutes of contributor confusion when a future maintainer reads the Round 2 rationale before the Phase 6 reality check, then opens the gear files and finds the actual inheritance is more nuanced. The Phase 6 plan itself is correct and unaffected, so the cost stays at "minor cognitive overhead during onboarding," not a plan defect.* Acceptable to defer to implementation-time as a one-line clarifying edit by whoever writes the Phase 6 commits.

### Verification log

1. Round 4 migration table rows for Sg90Servo / ventilation / FastenerDrive — **confirmed at lines 613, 614, 615.** Each row contains the "Added 2026-05-14 per TL-reviewer condition TL-1" provenance note.
2. Phase 4 tasks T4.8 (Sg90Servo), T4.9 (ventilation), T4.10 (FastenerDrive subtree) — **confirmed at lines 199, 200, 201.** T4.10 explicitly captures the `cutter` → `to_cutter` rename for the drives subtree.
3. Phase 6 line-215 inheritance reality check — **confirmed.** Wording matches verified code: `HelicalGear(SpurGear)` at `models/mechanical/gears/helical.py:23`, `class RackGear:` (no parent) at `models/mechanical/gears/rack.py:22`. Both re-verified live in this re-spawn.
4. T6.1 / T6.7 / T6.8 — **confirmed.** Shared primitives are `@classmethod` helpers; T6.7 reads "HelicalGear inherits from SpurGear — verify it continues to work"; T6.8 reads "Refactor RackGear.solid to consume Gear.involute_tooth_profile_2d(...) as a @classmethod call + linearize. No inheritance relationship needed."
5. Tests T6 path update — **confirmed at line 259.** All three example imports use the post-rename namespaces (`vibe_cading.mechanical.screws`, `vibe_cading.lego_adapters.servos.sg90`, `parts.arrma_vorteks_223s.*`).
6. Phase 3 T3.4 class-count fix — **confirmed at line 189.** Reads "(7 classes per reviewer verification — not 4)".
7. `HeatSetInsert` rename — **confirmed at lines 609 (migration table) and 198 (T4.6 with reviewer-verified note).**
8. `docs/screws.md` `get_screw_allowances` reference — **confirmed at line 235** within T7.4: "remove / re-explain the `get_screw_allowances` reference (the helper does not exist in the new design)".
9. Tests T15 row — **confirmed at line 268.** Maps-to column reads "R9, R10, R11" with concrete grep-based audit assertions.
10. Phase 1 T1.4 build.toml clause — **confirmed at line 157** with explicit no-op annotation. Live verification: `grep -c trailer_hitch /workspaces/vibe-cading/build.toml` returns 0.
11. Gear inheritance live recheck — **confirmed unchanged.** `grep -n "^class " models/mechanical/gears/{rack,helical,spur}.py` returns:
    - `helical.py:23: class HelicalGear(SpurGear):`
    - `rack.py:22: class RackGear:` (no parent)
    - `spur.py:23: class SpurGear(Gear):`
12. Round 2 narrative drift — **confirmed not repaired** at lines 51 ("every concrete subclass `(SpurGear, HelicalGear, RackGear)` re-implements involute-tooth math"), 56, 64, 80. Phase 6 reality check (line 215) is the operational corrective, and that is sufficient for the plan to land correctly.

## Independent Developer Review — Re-confirmation (2026-05-14)

**Verdict:** APPROVE

The drafting team's Round 7.5 integration applied edits to the design *body* for every one of my nine conditions, not merely a Round 7.5 log entry pointing at them. The single architectural blocker (Dev-1 cross-zone import) is cleanly resolved by the partition-table correction at line 98 (SG90 shaft files stay in `vibe_cading/lego_adapters/servos/`) and the matching Phase 1 T1.10 wording (line 167: "ONLY `vibe_cading/lego_adapters/slipper_gear/` → `experiments/`. The SG90 shaft files ... STAY in `vibe_cading/lego_adapters/servos/`"). Live dependency-graph re-verification — `grep -rn "from models.xlego.servos" models/xlego/slipper_gear/` returns empty — confirms slipper-gear has zero coupling to the SG90 shaft files, so they correctly stay in the library tree and Success Criterion §11 ("no `experiments/` import from inside `vibe_cading/`") is no longer threatened. The remaining eight infrastructure-edge conditions all have concrete task rows in the body (T0.5–T0.8, T1.5, T1.13, T1.16, T5.8, T6.10, T7.4, T15). Two minor under-specifications surfaced and are noted below as non-blocking; neither is a regression versus my original review. The plan is now atomically executable end-to-end.

### Conditions resolution check

| # | Condition | Resolution | Justification |
|---|---|---|---|
| 1 | Cross-zone import (Dev-1) — `servo_mount.py` would import `Shaft` from `experiments/` after Phase 1 | **resolved** | Partition table line 98 reclassifies `{cam_utils, shaft, shaft_body, shaft_crown, shaft_with_saver}.py` as "KEEP as SG90 working assembly in library" with destination `vibe_cading/lego_adapters/servos/`. Phase 1 T1.10 (line 167) explicitly says "ONLY `lego_adapters/slipper_gear/` → `experiments/`. SG90 shaft files STAY." Live recheck: `grep -rn "from models.xlego.servos" models/xlego/slipper_gear/` empty — slipper-gear does not couple to these files, so the reclassification is dependency-graph-supported. |
| 2 | CI workflow rename omitted | **resolved** | T1.16 (line 173) added: "Update `.github/workflows/ci.yml`: 4 hardcoded `models/` path references → `vibe_cading/`. Add the pytest job step deferred from T0.6." Matches the four occurrences I cited (CI lines 28, 43, 45, 50). |
| 3 | Lint-helper hardcoded paths under-enumerated in T1.13 | **resolved** | T1.13 (line 172) now enumerates 10 tools: `build.py`, `check_no_main_blocks.py`, `check_license_headers.py`, `gen_engine_api.py`, `model_loader.py`, `view.py`, `preview.py`, `boolean_diff.py`, `engine_api/extractor.py`, `step_preview.py`. Covers and exceeds the seven I originally enumerated. The audit framing is retained but with concrete file names — the developer no longer has to guess scope. |
| 4 | engine_api extractor cannot enforce "no `*Protocol` types leak" | **resolved** | T5.8 (line 212) added: "Extend `tools/engine_api/extractor.py::_is_discoverable` (line ~266-303) to filter out `typing.Protocol`-derived classes, mirroring the existing ABC-exclusion logic." Directly addresses the Success Criterion §2 / Test T3 enforceability gap. |
| 5 | `tools/check_polar_monotonicity.py` cannot run on `Gear` shared methods | **partially resolved** | T6.10 (line 226) acknowledges the tool currently constructs zero-arg instances and offers two paths ("extend the tool to accept a parameter pack, OR pre-bind the classmethods via a wrapper script under `tmp/`"). T6.1 / T6.2 / T6.3 make the shared primitives `@classmethod`s, so option (c) from my original three options is implicitly selected: an instance is no longer needed because `Gear.involute_tooth_profile_2d(module=…, teeth=…, …)` is callable without one. T12 still cites the old underscore-prefixed name `_gear_blank_with_teeth_2d` (line 265) — minor wording drift versus the new public `gear_blank_with_teeth_2d`; the developer will reconcile during Phase 6 implementation. Not blocking. |
| 6 | `tests/` framework not scaffolded | **resolved** | T0.5–T0.7 (lines 143–145) added: scaffold `tests/__init__.py`, `tests/conftest.py`, `pytest.ini`; add pytest job to CI (folded into T1.16); confirm Python ≥3.10 for `typing.Protocol` maturity. Covers runner declaration, repo-root sys.path priming via `conftest.py`, and CI integration. |
| 7 | Pre-refactor STEP snapshot strategy missing | **resolved** | T0.8 (line 146) added: snapshot pre-refactor build outputs before Phase 1. Minor wording slip: T0.8 says "`cp -r build/ tmp/pre-refactor-build/`" but the actual build path is `output/` (verified live: `output/rc/hex_wheel_hub_12mm.step` etc. exist; no `build/` directory exists). T0.8 hedges with "(or wherever `python build.py` writes STEP files — confirm path from `build.toml`)" so a careful developer will catch this. Not blocking — flagged as a wording polish for whoever drafts the Phase 0 commit. |
| 8 | Knowledge-base updates undersized at T7.4 | **resolved** | T7.4 (lines 233–238) now enumerates `docs/lego-technic.md`, `docs/screws.md` (with the `get_screw_allowances` removal), `vibe/INSTRUCTIONS.md` (~8 lines), `CLAUDE.md`, and historical artifacts (`tmp/structural-review-2026-05-08.md`, `tmp/platform-coordination-wave-c.md`) explicitly marked DO-NOT-mutate. The "any other `docs/*.md`" wildcard at line 234 catches `docs/templates/design-brief-template.md` (verified to contain 3 `models.module.ClassName` refs). The `vibe/agents/*.md` files are not explicitly named but verified empty of `models/` refs (`grep -ln "models/" vibe/agents/*.md` returns empty). Coverage is sufficient. |
| 9 | `HexWheelHub` class rename under-specified | **resolved** | T1.5 (line 158) locks the name: "Rename the class `HexWheelHub` → `FreespinHexHub` (final). Update `build.toml`." No execution ambiguity remains. |

### New concerns surfaced during re-check (if any)

Two minor wording drifts surfaced; both are non-blocking and require only a one-line edit by whoever drafts the relevant phase commit:

- **T12 references the old underscore-prefixed private method name `_gear_blank_with_teeth_2d`** while T6.2 introduces the public `gear_blank_with_teeth_2d` (no underscore) as the `@classmethod` form. T12's "Expected assertion" wording should track Phase 6's renamed-to-public convention. *Predicted cost if left: ~5 minutes of developer confusion during Phase 6 when reconciling the test target with the actual method name; the test will still pass once the developer adjusts the invocation, but the design artifact reads as if there are two different methods.*

- **T0.8 build-output path wording (`build/` vs `output/`).** The actual build target directory is `output/` per `build.toml`'s `output = "…step"` field semantics and live directory listing. T0.8's example command `cp -r build/ tmp/pre-refactor-build/` will silently no-op on a fresh clone (no `build/` directory exists), then T2's volume-diff has no reference set. The parenthetical hedge "(or wherever `python build.py` writes STEP files — confirm path from `build.toml`)" mitigates this for an alert developer. *Predicted cost if a less-careful developer follows the literal `cp` example without verifying: T2 runs against an empty reference set and reports artificial 100% missing-material for every class on first invocation, costing one debugging cycle (~10 minutes) before the developer re-reads T0.8.*

Neither concern blocks implementation. Both can be fixed mid-Phase by the implementing developer.

### Verification log

1. Live re-grep `grep -rn "from models.xlego.servos" models/xlego/slipper_gear/` — **empty.** Slipper-gear has zero imports from the SG90 shaft files; reclassification to "STAY in library" is dependency-graph-supported.
2. Partition table line 98 — **confirmed reads "KEEP as SG90 working assembly in library" with destination `vibe_cading/lego_adapters/servos/`**. Provenance note "(2026-05-14 correction)" present.
3. Phase 1 T1.10 (line 167) — **confirmed reads "Move ONLY `vibe_cading/lego_adapters/slipper_gear/` → `experiments/slipper_gear/`. The SG90 shaft files ... STAY in `vibe_cading/lego_adapters/servos/`"**. Cross-zone import vanishes because both ends co-located in `lego_adapters/servos/`.
4. Phase 1 T1.16 (line 173) — **confirmed present.** Covers the 4 hardcoded `models/` refs in `.github/workflows/ci.yml` + pytest step.
5. Phase 1 T1.13 (line 172) — **confirmed enumerates 10 tools.** Exceeds the 7 I originally cited; explicitly includes `engine_api/extractor.py` and `step_preview.py` that I had not listed but TL review noted.
6. Phase 5 T5.8 (line 212) — **confirmed present.** Mirrors ABC-exclusion logic for `typing.Protocol`-derived classes.
7. Phase 6 T6.10 (line 226) — **confirmed acknowledges zero-arg `cls()` limitation and offers two paths.** Combined with T6.1–T6.3's `@classmethod` shape, option (c) is implicitly selected.
8. Phase 0 T0.5 / T0.6 / T0.7 (lines 143–145) — **confirmed scaffold `tests/__init__.py`, `tests/conftest.py`, `pytest.ini`; pytest job folded into T1.16; Python ≥3.10 noted.**
9. Phase 0 T0.8 (line 146) — **confirmed present** with the `build/`-vs-`output/` wording drift noted above.
10. Phase 7 T7.4 (lines 233–238) — **confirmed enumerates `vibe/INSTRUCTIONS.md`, `docs/screws.md`, `docs/lego-technic.md`, `CLAUDE.md`.** Wildcard `docs/*.md` covers `docs/templates/design-brief-template.md`.
11. Phase 1 T1.5 (line 158) — **confirmed reads "Rename the class `HexWheelHub` → `FreespinHexHub` (final)"**. No ambiguity remains.
12. T15 row (line 268) — **confirmed.** Live re-verification of T15's grep assertions: `grep -c "^| R-" …_design.md` returns 30 (≥29 required); `grep -cE "### Phase [0-7]" …_design.md` returns 8 (=8 required); `grep -c "Wave C reconciliation" …_design.md` returns 5 (≥1 required). T15 self-passes.
13. `models/mechanical/screws/drives.py` — **confirmed `FastenerDrive` ABC + four concrete drives use `cutter()` (not `to_cutter`).** T4.10 correctly captures this same-name-different-signature drift.
14. `models/mechanical/enclosures/ventilation.py` — **confirmed `HexVentilationGrille` + `SlottedVentilationGrille` both define `to_cutter(thickness, overcut)`.** T4.9 wording says "VentilationPattern" but points at the right file; the actual class names are spotted correctly during implementation.
15. `models/rc/servo/sg90.py:453` — **confirmed `Sg90Servo.to_cutter(clearance, extend_shaft_up)` signature.** T4.8 correctly targets this for the `to_cutter(profile=None)` Protocol-conformance migration.
16. `models/cq_utils.py:347` `fillet_z_edges` — **confirmed sole caller is `models/xlego/slipper_gear/directional/parts/slipper_spring.py:145-146`.** T1.11's grouping with the other slipper-gear-only helpers is sound; relocating it to `experiments/slipper_gear/curves.py` removes the last single-adapter speculative seam from `cq_utils.py`.
17. `build.toml` `trailer_hitch_cover` — **confirmed not present** (`grep -c trailer_hitch build.toml` returns 0). T1.4's "no build.toml edit needed" annotation is accurate.
18. Round 7.5 log integrity — **confirmed all nine Developer conditions accounted for in the log (lines 821–830)** and each maps to a concrete body edit verified above.
