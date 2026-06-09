# Contributing to vibe-cading

Welcome! `vibe-cading` is an open-source library for generating parametric 3D CAD models using [CadQuery](https://github.com/CadQuery/cadquery) (Python).

The primary goal is a robust, generic Code-CAD toolkit for mechanical design (fasteners, joints, enclosures), with practical examples showing how to interface domain-specific ecosystems like **RC (radio-controlled) components** and **Lego Technic**.

This project is built using an **AI-first, Agentic Workflow**. Please skim the design principles, the AI workflow, and §5 *Project Conventions That Will Fail Your PR* before opening one.

---

## 📜 1. License & CLA

`vibe-cading` is licensed under **[AGPLv3](LICENSE)**. For a plain-language guide to what that means in practice (printing parts, forking, network deployment, CLA interaction), see [LICENSE-FAQ.md](LICENSE-FAQ.md).

**Contributor License Agreement.** Every PR is checked by the CLA Assistant bot ([`.github/workflows/cla.yml`](.github/workflows/cla.yml)). On your first PR the bot will comment with a link to this file; reply on the PR thread with exactly:

> `I have read the CLA Document and I hereby sign the CLA`

Your signature is recorded in [`signatures/version1/cla.json`](signatures/version1/cla.json) and covers all of your future contributions. By signing, you agree that your contributions are licensed under AGPLv3 and that you have the right to submit them.

**AGPLv3 header.** Every new `.py` file under [`vibe_cading/`](vibe_cading/), [`parts/`](parts/), or [`tools/`](tools/) must carry the AGPLv3 header at the top (copy from any existing file — look for the *"vibe-cading is free software"* block). Empty `__init__.py` files are exempt. This is enforced by [`tools/check_license_headers.py`](tools/check_license_headers.py) which runs inside `python build.py` (and therefore the CI build-smoke step).

---

## 💬 2. Where to Discuss

- **Bug reports & feature requests:** [GitHub Issues](https://github.com/fa-mc/vibe-cading/issues)
- **Design discussion / open-ended questions:** [GitHub Discussions](https://github.com/fa-mc/vibe-cading/discussions) (if enabled) or open an issue tagged `discussion`.

For non-trivial geometry changes, please open an issue first describing the use case — the Designer-side analysis is usually the long pole, and we'd rather collaborate on the brief than rework a PR.

---

## 🛠️ 3. Dev Setup

The repo ships a VS Code Dev Container with everything pre-installed (Python 3.11, CadQuery, OCP CAD Viewer, Claude Code). See [README.md > Dev Setup](README.md#dev-setup) for the click-by-click.

**First-clone checklist:**

1. **Reopen in Container** when VS Code prompts.
2. **Initialize the workspace.** From inside your AI agent host (e.g. Claude Code or Google Antigravity): *"please initialize the project"*. This creates `tmp/` and `.agents/plans/`, copies `print_profiles.json.example` → `print_profiles_user.json`, and runs the host-specific runtime scaffolder ([`tools/init-claude-runtime.sh`](tools/init-claude-runtime.sh) for Claude Code, or [`tools/init-agy-runtime.sh`](tools/init-agy-runtime.sh) for Antigravity) to populate per-clone runtime aliases/skills. (Equivalent manual steps are documented in [vibe/INSTRUCTIONS.md](vibe/INSTRUCTIONS.md) §*Workspace Initialization*.)
3. **Calibrate your printer's `slip.radial`.** The shipped `fdm_standard` profile is a reasonable starting point, but the slip fit for Lego pins/axles is printer-specific. Print the axle gauge and run `python3 tools/calibrate.py slip` — the calibrated value lands in your gitignored `print_profiles_user.json`. Full procedure in [README.md > Print Tolerances & Calibration](README.md#print-tolerances--calibration).
4. **Try an example.** `python3 examples/lego_technic_beam.py` writes a STEP file under `examples/build/` — confirms your environment works end-to-end.

**Local dev loop:**

```bash
python3 tools/preview.py <module.path.ClassName>   # iterate on geometry
python3 tools/view.py    <module.path.ClassName>   # live OCP viewer
python -m pytest tests/ -v                         # unit + smoke tests
python tools/check_no_main_blocks.py               # CI-enforced lint
flake8 .                                           # CI-enforced lint
python build.py                                    # CI-enforced full build smoke
```

Run these locally before opening a PR — they mirror the CI gates (§6).

---

## 🏗️ 4. Core Design Principles

We hold the codebase to a high standard of structural quality and mathematical rigor.

- **Fundamental Geometry over Hacky Patches:** No arbitrary translations, clipping boxes, or brute-force boolean intersections to "make it look right" for one parameter set. Anchor geometry to logical origins (e.g. center a gear on `(0, 0, 0)`) and scale cleanly via parameters.
- **No Magic Numbers:** Derive dimensions from fundamental parameters (`self.length = holes * 8.0`) or import from centralized constants ([`vibe_cading.lego.constants`](vibe_cading/lego/constants.py)).
- **The 8 mm Technic Standard:** All Lego-compatible models align with the 8 mm stud grid. Use standard values for Technic pins (4.8 mm) and axles (5.0 mm). See [docs/lego-technic.md](docs/lego-technic.md).
- **Generic Tooling:** Shared features (axle holes, mounting tabs, fillets) belong in [`vibe_cading/cq_utils.py`](vibe_cading/cq_utils.py) or base classes — not copy-pasted across models.
- **Tolerances via Profiles, Not Magic Floats:** Never hardcode a clearance like `+ 0.2` in a boolean cut. Use `vibe_cading.print_settings.get_profile(...)` and pass the resolved `ToleranceProfile` through. See [docs/print-tolerances.md](docs/print-tolerances.md).
- **All units in millimeters (mm).**

---

## 🤖 5. The Agentic AI Workflow

We strongly recommend using an AI coding host like [Claude Code](https://claude.com/claude-code) for non-trivial geometry work. The repository ships **four contributor subagents** under [`vibe/agents/`](vibe/agents/):

1. **[`admin`](vibe/agents/admin.md)** — workflow governance and the instruction set: clarifies requirements, runs mid-session interventions, initiates the design flow, and orchestrates wrap-ups. Diagnoses and routes; does not write model code, briefs, or blueprints.
2. **[`designer`](vibe/agents/designer.md)** — brainstorms, digests reference material (STEP files, drawings), resolves geometric ambiguities, and writes a *Design Brief* to `.agents/plans/`. Focuses on *what* to build and *why*.
3. **[`tl`](vibe/agents/tl.md)** — code architecture: shared abstractions, base-class and `Protocol`/`ABC` contracts, cross-cutting refactors, and post-implementation architectural review. Invoked for architecturally-significant work only; everyday single-part creation flows Designer → Developer without it.
4. **[`developer`](vibe/agents/developer.md)** — implements the brief: per-part code structure, CadQuery classes, validation tooling. Focuses on *how*.

Only the **`pm`** role (backlog prioritisation across many tasks) is **intentionally not shipped** — the human contributor drives it, and remains the final acceptance authority for merges and project policy above all shipped roles. Maintainers who prefer a dedicated PM agent can load their own persona from `~/.claude/`.

**Canonical instructions.** The tool-neutral instruction set lives at [`vibe/INSTRUCTIONS.md`](vibe/INSTRUCTIONS.md). Every AI host enters through the universal [`AGENTS.md`](AGENTS.md) at the repo root, which routes there; [`CLAUDE.md`](CLAUDE.md) is the thin Claude-Code-specific shim that imports the same file and adds subagent glue. A host that prefers a native file (`.github/copilot-instructions.md`, `.cursor/rules/`, etc.) can add one that likewise imports the canonical instructions; none ship yet. See [docs/agentic-workflow.md](docs/agentic-workflow.md) for the workflow specification.

**How to use the workflow for a complex new model:**

1. Provide reference material (STEP file, spec, drawing) and ask the **designer**: *"use the designer agent to analyze ref.step and produce a brief"*. The brief lands in `.agents/plans/` (gitignored).
2. Review the brief. Approve once dimensions, coordinate system, and visual contract SVG look right.
3. The **developer** auto-transitions on your approval and implements the brief.
4. The developer runs the validation tools (§7) before declaring complete.

*Note: `.agents/` is gitignored and stages AI artefacts locally. Persona/command sources are tracked under [`vibe/agents/`](vibe/agents/) and [`vibe/commands/`](vibe/commands/); Claude Code picks them up via per-clone runtime aliases under `.claude/` populated by [`tools/init-claude-runtime.sh`](tools/init-claude-runtime.sh), while Google Antigravity (agy) generates per-clone command *skills* under `.agents/skills/` via [`tools/init-agy-runtime.sh`](tools/init-agy-runtime.sh) (its personas are loaded directly from the canonical `vibe/agents/` files).*

---

## ⚠️ 6. Project Conventions That Will Fail Your PR

These rules are CI-enforced or workflow-required. Skim them before submitting.

- **AGPLv3 header on new `.py` files** in `vibe_cading/`, `parts/`, `tools/`. Copy from any existing file. Empty `__init__.py` exempt. CI-enforced via `tools/check_license_headers.py` (runs inside `python build.py`).
- **No `if __name__ == "__main__":` blocks under `vibe_cading/` or `parts/`.** Model class files are pure class definitions; use [`tools/view.py`](tools/view.py) to launch the OCP viewer instead. CI-enforced via AST walker [`tools/check_no_main_blocks.py`](tools/check_no_main_blocks.py) + grep belt-and-braces.
- **No `ocp_vscode` imports outside `tools/view.py`.** CI-enforced.
- **`build.toml` registration is explicit.** Never auto-add a `[[build]]` entry for a new class — propose it in your PR description and let the maintainer/reviewer confirm before committing the change. The build manifest is intentional, not derived.
- **Visual Contract Deliverable (CAD tasks).** Any PR introducing a new model class — or changing visible geometry (axis convention, hole pattern, dimensions affecting orientation) — must include a co-located preview SVG (`.agents/plans/<task-slug>_design_iso_ne.svg`) generated via `python3 tools/preview.py`. Numeric specs alone do not surface axis-orientation errors. See [vibe/INSTRUCTIONS.md > Visual Contract Deliverable](vibe/INSTRUCTIONS.md) for the full rule and rationale.
- **`tmp/` for scratch.** All ad-hoc debug scripts, parameter sweeps, gauge probes, and one-off STEP exports live in `tmp/` (gitignored). Never commit them.
- **No inline-code-in-shell.** `python3 -c '<embedded body>'` and `bash -c '<embedded body>'` are disallowed — write a file in `tmp/` first. Quoting bugs and silently-truncated logic are a reliable failure mode.

---

## 🔬 7. Validation Tools

Before opening a PR, validate locally:

| Tool | When to use |
|---|---|
| `python3 tools/preview.py <module.path.ClassName>` | Generate orthographic SVGs (top, front, left, iso_ne) to visually validate orientation and dimensions against drawings. |
| `python3 tools/view.py <module.path.ClassName>` | Launch the OCP CAD Viewer (port 3939) for live 3D inspection. Supports `--demo` and `--assembly`. |
| `python3 tools/section_slicer.py` | Slice a part along an axis to verify internal features (blind holes, snap rings, counterbores) that external views can't show. |
| `python3 tools/boolean_diff.py <reference.step> <module.path.ClassName> --model` | Quantitative volume comparison against a reference STEP file. |
| `python3 tools/calibrate.py [all\|free\|slip\|press]` | Calibrate your `print_profiles_user.json` against a printed gauge (see `--help` for flags). |
| `python -m pytest tests/ -v` | Run the unit + smoke test suite. |

---

## ✅ 8. CI Gates

PRs are gated by two workflows. Both run on `pull_request` (read-only token, fork-safe).

**[`.github/workflows/ci.yml`](.github/workflows/ci.yml)** runs on every PR:

1. `flake8 .` — style + import lint (config in [`.flake8`](.flake8)).
2. `py_compile` over `vibe_cading/`, `parts/`, `tools/` — syntax sanity for every `.py` file.
3. AST check: no `__main__` blocks under `vibe_cading/` or `parts/`.
4. Grep belt-and-braces for the same.
5. No `ocp_vscode` imports outside `tools/view.py`.
6. `python -m pytest tests/ -v` — unit + smoke tests.
7. `python build.py` — full STEP-build smoke (also runs `tools/check_license_headers.py`).
8. **Topology check** — runs [`tools/check_topology.py`](tools/check_topology.py) against every `[[build]]` entry in [`build.toml`](build.toml) and fails on any disconnected-body regression (floating artifacts, failed boolean cuts, un-merged outer components) that the build smoke would silently pass. Three classes are allowlisted as legitimate multi-body assemblies (`ServoMountAssembly`, `SlipperGearSteep`, `PrintInPlaceHinge`); the allowlist is inline in [`.github/workflows/ci.yml`](.github/workflows/ci.yml). To reproduce a CI failure locally, run `python3 tools/check_topology.py <fq.class.path> [--params k=v …] [--ignore N]` for the failing target — see the workflow step for the exact invocation and the per-target `--ignore` values.

**[`.github/workflows/engine-api.yml`](.github/workflows/engine-api.yml)** runs when `vibe_cading/`, `parts/`, `tools/engine_api/`, or `engine_api.json` change:

1. `python3 tools/gen_engine_api.py --check` — regenerates `engine_api.json` in memory and exits non-zero if the on-disk file differs.
2. `python3 tools/validate_engine_api.py` — asserts schema invariants.

If the engine-api gate fails, run `python3 tools/gen_engine_api.py` locally and commit the diff (see §9).

---

## 🔧 9. Adding a Model

1. **Pick the right home:**
   - **Reusable, project-agnostic library classes** (screws, gears, joints, Lego primitives, Lego adapters, RC building blocks) live under [`vibe_cading/`](vibe_cading/) in an appropriate subpackage.
   - **Project- or vehicle-specific parts** (an ESC mount tied to one chassis) live under [`parts/<vehicle_or_project>/`](parts/).
2. **Define a class** with a `.solid` property returning a `cq.Workplane`. Use strict type hints on public parameters. Add a top-level docstring stating what `(0, 0, 0)` represents.
3. **Add the AGPLv3 header** to your new file.
4. **Validate:** preview, view, slice (if internal features), calibrate-aware tolerances.
5. **Regenerate engine_api.json:** `python3 tools/gen_engine_api.py` — commit the diff alongside your class.
6. **Propose a `build.toml` entry** in your PR description (do not auto-add — see §6).

---

## 🎯 10. Print Tolerances & Calibration

This repo uses a profile-driven tolerance system so the same model bores a working slip fit on every printer. The shipped `print_profiles.json` is a calibration **starting point**, not a contract — most contributors override at least `slip.radial` for their machine in the gitignored `print_profiles_user.json`. Set `PRINT_PROFILE=<name>` in `.env` to switch the active profile.

Full calibration workflow, fit-grade taxonomy, and field-level deep-merge semantics: [README.md > Print Tolerances & Calibration](README.md#print-tolerances--calibration) and [docs/print-tolerances.md](docs/print-tolerances.md).

---

## 📦 11. Engine API Artifact

[`engine_api.json`](engine_api.json) at the repo root is a machine-readable index of every public model class in `vibe_cading/**` and `parts/**`. Downstream LLM code-gen tooling consumes it to call engine classes deterministically. It is generated, not hand-written, and **must stay in sync with `vibe_cading/**` + `parts/**`**.

**Regenerate after editing any model class:**

    python3 tools/gen_engine_api.py

That walks the trees with a pure-`ast` extractor (no CadQuery import) and rewrites the file in place. Commit the regenerated artifact alongside your model changes.

**Bumping `schema_version`.** The extractor pins `SCHEMA_VERSION` in [`tools/engine_api/extractor.py`](tools/engine_api/extractor.py); the validator imports the same constant. Bump it whenever the schema shape changes:

- **Major** (`1.0` → `2.0`) for breaking changes — renaming or removing a field, dropping a class, narrowing a `type` annotation, making an optional param required.
- **Minor** (`1.0` → `1.1`) for additive changes — a new top-level field with a default, a new class, a previously-omitted optional param, a new `constructors[].kind` value.

The validator hard-fails on `schema_version` mismatch so the bump is forced to be intentional.

---

Thanks for contributing — we look forward to your PRs!
