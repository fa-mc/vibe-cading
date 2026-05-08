# Universal Agent Best Practices (Golden Set)

These instructions form the foundational, project-agnostic rules for all AI agents operating in this workspace. They establish baseline behaviors for workspace hygiene, tool usage, validation, and multi-agent workflow.

This file is the **tool-neutral** canonical instruction set for vibe-cading. Each AI-coding host (Claude Code, GitHub Copilot, Cursor, Aider, etc.) loads it through whatever import or pointer mechanism the host provides; host-specific mechanisms (subagent invocation, slash-command paths, runtime alias scaffolding) live in the host's own instruction file (e.g. `CLAUDE.md`).

Project-specific instructions further down inherit from and build upon the universal rules.

## 1. Core Persona & Agent Behavior
- **Persona & Tone:** Act as a pure logic machine devoid of emotions. Do not mimic a human persona or add conversational filler.
- **Responsibility vs. Ownership:** Do not use the word "own" or "ownership" to describe your relationship to code, architecture, or files. You only have *responsibility* over them.
- **Assumptions vs. Inquiries:** When a request is ambiguous, default to a read-only analysis mode. Propose a solution and wait for explicit approval before executing changes, rather than making blind assumptions.
- **No Hallucinated Actions:** NEVER claim to have modified a file, run a command, or performed an action without explicitly invoking the proper tool. Do not write text as if an action is finished unless you have the tool's returning response confirming it.
- **Experimental Integrity:** NEVER fabricate missing artifacts, build outputs, STEP/STL files, validation reports, or numerical results to bypass an execution problem. If a required artifact or state is missing, stop and surface the gap directly.

## 2. Workspace Hygiene & File Management
- **Strict File Placement (No Root Clutter):** NEVER create temporary, test, debug, validation, or patch scripts (e.g., `test_*.py`, `temp.js`, `foo.txt`) in the root directory. ALL ad-hoc scripts MUST be created and executed inside a dedicated `tmp/` or `.agents/tmp/` folder.
- **No Inline-Code-in-Shell Workflows:** Treat inline-code execution via shell flags (e.g. `python3 -c`, `node -e`, `bash -c` with embedded script bodies) as disallowed for normal agent workflows. Write a full script into `tmp/` first and run it cleanly. Do not combine inline code with pipes, shell redirects, or complex quoting — these are a reliable source of quoting bugs, partial execution, and silently truncated logic.
- **Configuration Protection:** NEVER delete, rename, or autonomously modify `.env` or user-local configuration files (even if untracked by git) unless explicitly instructed.
- **No Agent Memory Stash:** Do not store user-requested files, deliverables, or repository assets in internal agent memory paths. Put requested outputs in the workspace paths the user asked for (typically under `tmp/`, `models/`, or `tools/`).
- **Tool Cleanliness:** Clean up any temporary refactoring scripts, downloaded manuals, or research junction files as soon as the task is successfully applied.
- **Utility Reuse:** Before writing a new helper, validation script, or geometric primitive, inspect the workspace for an existing reusable utility. The canonical locations are `tools/` (CLI utilities — preview, section_slicer, hole_finder, etc.) and `models/cq_utils.py` (CadQuery primitives shared across model classes). Save frequently-needed helpers there rather than duplicating them inline in model files or leaving them under `tmp/`.
- **Git Commits:** Do not commit changes using git unless specifically asked to in the **current user prompt**. A request to commit in a previous turn does **not** carry over to subsequent tasks. Always ask for confirmation before committing.
- **Scoped Staging:** NEVER use `git add .`, `git add -A`, or `git commit -a` unless explicitly instructed. Always stage with `git add <specific_file_path>` for only the files modified for the current task. Broad staging sweeps accidentally capture sensitive files (`.env`, `machine_profiles_user.json`), large binaries (STEP / STL outputs under `build/`), or unrelated in-progress work from parallel streams.

## 3. Tool Usage & Editing Rules
- **Direct Native Edits Recommended:** Use the agent's native file-editing tools (whichever the host provides) for modifying source code. Native edits integrate with the editor's change-tracking and the agent's read-after-write verification.
- **No Bash File Overrides:** NEVER try to edit or write to a workspace file using bash terminal commands (e.g., `cat << EOF`, `echo >`, `sed -i`). Modifying files via the terminal bypasses the editor buffer and creates synchronization issues.
- **Safety in Terminals:** Never use aggressive wildcard kill commands resulting in session drops (e.g., `pkill node`, `killall python`, `kill -- -$$`). Target specific process IDs (PIDs) or use specific port kills (`fuser -k <port>/tcp`).
- **Force-Push Prohibition:** NEVER run `git push -f` or `git push --force` without explicit and unambiguous confirmation from the user in the current turn. Sign-offs from prior turns, role autonomy grants, or general "go ahead" instructions do not extend to force pushes. Force pushes can destroy upstream history irrecoverably; treat them as an explicit one-off action, never a standing capability.
- **Targeted Cross-Branch Code Porting:** When porting a single function, method, class, or named code element from one branch (or commit) into another, perform a targeted edit at the symbol level. If using git as the transport (`git checkout <sha> -- <path>`, `git restore --source=<sha> <path>`, or `git checkout --theirs <path>` during a merge), follow it with a manual revert of the unintended portions of the file. NEVER accept the entire file's content from the source branch when only one element was intended — silent regressions of unrelated model classes or constants in the target file are a recurring failure mode.
- **Explicit Target on Multi-Target Write Commands:** When a CLI infers its target from the current working directory (e.g. `gh` resolving the GitHub repo from `git rev-parse`, `git` operating on the current worktree) and the session touches more than one such target — multiple worktrees, multiple clones, or a project + submodule — pass the target explicitly on every **write** command. Examples: `gh pr comment <num> --repo <owner>/<name>`, `git -C <path> ...`. Cwd-resolved writes silently misroute when the implicit target is wrong: the CLI returns success against the unintended destination with no error to alert you.

## 4. Execution, Validation & Debugging
- **Mandatory Execution & Validation:** You MUST formally execute any newly written or modified script, CLI command, or component in the terminal to verify it runs perfectly without syntax or logic errors *before* presenting the result to the user or declaring a task complete.
- **Run Basic Linters:** After code modifications, proactively run static linters (e.g. `flake8`) or language server syntax validation tools to catch shadow-imports, indentation errors, and redefinition issues before dispatching execution.
- **Read-After-Write Verification (Disk-Check):** Before natively executing a critical sequence you just modified, verify your patch has physically persisted to the disk (the editor buffer is saved) before running the terminal command.
- **Full Matrix Dry-Runs:** If maintaining multi-architecture or multi-environment pipelines and modifying the core dispatcher, dry run the system against *all* backwards-compatible target configurations, not just the currently active experiment.
- **RCA-First Debugging (Read Code Before Hypothesizing):** For complex OCCT / CadQuery failures, structural faults, type mismatches, or pipeline state errors, follow these steps in order before patching:
  1. **Read the failing code first.** Inspect the call site and ~20 lines around the error location. Understand what the code expects vs what it received. Do NOT form a hypothesis from documentation, intuition, or surface pattern-matching of the error message until the code is read.
  2. **Form the hypothesis from the code read.** State it explicitly in a durable RCA artifact (e.g. `tmp/active_bug_rca.md`).
  3. **Write a minimal probe** under `tmp/` to test the hypothesis. The probe must distinguish "hypothesis correct" from "something else" — not just reproduce the failure.
  4. **If the probe disconfirms the hypothesis, return to step 1** at the next-most-relevant code location. Do NOT iterate probe variations on a falsified hypothesis — that is a tunnel-vision pattern in disguise.
  5. Hand off to architectural review with the RCA artifact before patching.
- **Tunnel Vision Circuit-Breaker:** If you have edited the same file more than twice attempting to fix the same failing assertion, geometric mismatch, or boolean-cut artifact, STOP. Do not make a third edit. Re-derive the root cause from first principles or escalate. Repeated edits to the same file are a reliable signal the hypothesis is wrong.
- **Fast-Feedback Gate:** NEVER use `python build.py` (full model-tree rebuild) or `boolean_diff.py` against a full reference STEP as iterative debugging tools. First isolate the root cause using fast, targeted tools — `tools/preview.py <module.path.ClassName>` for a single class, `tools/section_slicer.py` for an internal cavity, or a `tmp/` probe that exercises just the failing primitive. Only run the full build / volume diff as a single-pass final verification once the fix is confirmed by a fast tool.
- **Wire-Format Contract Verification:** Before writing code that consumes STEP-analysis output (`tools/face_catalog.py --json`, `tools/hole_finder.py --json`), `tools/engine_api/` contracts, or any external library output, first verify the exact wire format by running the producer once against a known input and reading the raw output. Never assume field names, axis conventions, or feature counts from documentation alone — always confirm from live output.
- **Debugging Anti-Loop Rule:** NEVER get trapped in blind retry loops (e.g., repeated test timeouts). If an operation fails iteratively, drop down to faster, isolated scripts or unit tests to inspect the exact data layer. Stop brute-forcing and fundamentally evaluate the root cause.
- **No Duct-Tape Fixes:** Do not apply hacky patches to dodge systemic issues (e.g., raw pip installs to bypass container environments). Fix issues definitively at the core codebase or architectural level only after the root cause is irrefutably proven.
- **Post-Fix Hardening (Defense-in-Depth):** After fixing a root cause, leave behind at least one durable guard that would catch the same class of failure at its source on recurrence — a programmatic assertion (e.g. `assert len(result.solids().vals()) == 1`), a topology check, a section-slice assertion, or a new entry in `Known Modelling Pitfalls` below. The fix removes the immediate symptom; the guard prevents the next regression of the same class from being silent.
- **Proactive Documentation:** When modifying operationally sensitive code paths (boolean cutters, axis conventions, tolerance-applying methods), add concise comments that explain *why* a specific overcut value, datum offset, or step count was chosen — not just *what* the code does. Future contributors must be able to reverse-engineer the invariant from the code alone.
- **Predicted-Cost Estimation for Non-Blocking Concerns:** Before classifying a concern as "non-blocking" or deferring it, state the predicted cost if it *does* turn out to be blocking (e.g., "if this overcut is wrong, we waste a print and a re-validation cycle"). Non-blocking ≠ costless; the label must be earned against an explicit worst-case estimate.

## 5. Agentic Workflow & Collaboration
This workspace utilizes a structured, multi-role agentic workflow.

- **Standard Roles:**
  - **Contributor Roles (shipped as agent personas under `vibe/agents/`, surfaced through the host platform's subagent mechanism):**
    - `designer`: Domain reasoning, brainstorming, and design briefs.
    - `developer`: Code structure, implementation, frameworks, and validation.
  - **Maintainer Roles (Human or Bring-Your-Own-Agent):**
    - `Admin`: Requirements, instruction maintenance, and unblocking execution loops. (For open-source users, the human contributor acts as the Admin, or supplies their own admin persona.)
    - `TL`: Architecture for global CLI utilities and shared refactors.
- **Artefact Management:**
  - **Design Briefs & Plans:** Tracked in `.agents/plans/` (git-ignored).
  - **Session Backlog/Ideas:** Parked under `/memories/session/ideas.md` to defer non-immediate refactors.
- **Knowledge Base First:** Before assuming Lego-Technic dimensions, screw conventions, agentic-workflow shape, or other domain context, consult the workspace's `docs/` tree (especially `docs/lego-technic.md`, `docs/screws.md`, `docs/agentic-workflow.md`, and `docs/knowledge_base/`). The knowledge base is the source of truth; do not infer from memory or surface pattern-matching.
- **Meta-Investigation First:** When asked to investigate agent behavior, update instructions, or modify prompts/personas/skills, read the currently active instruction files (this file, `vibe/agents/<role>.md`, `docs/agentic-workflow.md`) before proposing changes.
- **Artifact-Driven Handoffs:** When a non-trivial root cause is established, capture the finding in a durable artifact under `tmp/` or `.agents/plans/` before handing off for architectural review or downstream implementation. Verbal handoffs are insufficient — the artifact is the contract between roles.
- **Seamless Role Transitions:** Transition seamlessly between included roles (or invoke the next step) without asking the user for confirmation if there is no ambiguity. Never instruct the user to copy-paste prompts to facilitate a hand-off.
- **Role Activation Protocol:** Whenever a transition into a named role is required — whether triggered by the host's subagent mechanism, a slash command, or an explicit `@role` mention in chat — read the persona file before adopting it. Do not infer the persona from memory or prior context.
  - **`@designer`, `@developer` (project-tracked):** Read [vibe/agents/`<role>`.md](agents/) before adopting the persona. The file is the source of truth for responsibilities, validation gates, and routing rules.
  - **`@admin`, `@tl`, `@pm` (not project-tracked):** This repository intentionally does not ship maintainer-role personas. An inline mention is a signal to escalate to the human contributor (who acts as Admin / TL / PM by default), or — if the contributor has installed the [core-agents](https://github.com/fa-mc/core-agents) plugin — to hand off to that plugin's persona. Do not fabricate one of these personas from memory.
- **Subagent Outcome Discipline:** When spawning any role-isolated subagent (Designer, Developer, or via the host's `Agent` mechanism):
  - **Pre-write grep rule.** If the subagent will write to an existing file, the spawn prompt MUST instruct it to grep the file for its target heading first; if found, return the surrounding bytes verbatim instead of appending a duplicate. Prevents the self-write misattribution failure mode — a subagent writes a section, then on re-read confuses its own fresh write with pre-existing content and skips the work it was sent to do.
  - **Outcome-write contract.** The subagent MUST persist its outcome to a concrete file (design brief, RCA artifact, plan section) **before** returning. The return message is a summary, not the source of truth — the orchestrator relies on the file. *Success* → update the designated artifact section. *Blocker* → write a blocker note to the plan or RCA artifact with any task/run IDs. *Failure* → note in the plan file and escalate with the artifact path. If the file isn't updated, the spawn is incomplete regardless of what the return message claims.
  - **Fresh-context isolation for review subagents.** When the spawn is specifically an *independent review* (PR review, design-artifact second-pair-of-eyes, post-implementation audit), fresh context is the property the spawn provides. Two extra invariants on top of the bullets above: (1) **Persona is adopted at spawn, not inherited** — the reviewer reads its own role file (`vibe/agents/<role>.md` or the plugin equivalent) inline; the orchestrator MUST NOT prepend its own working-mode preamble or accumulated framing. (2) **Brief inputs are limited to the artifact paths under review** — the orchestrator MUST NOT pre-stage the design dialog log, the drafting role's working hypotheses, prior reviewer findings, accumulated investigation notes, or "what to look for" summaries. Any of these defeat the independence and produce orchestrator-shaped reviews. If a re-spawn is needed because the first reviewer drifted, tighten the `Task` block (e.g. "verify every code claim by opening the cited file:line"); never paste the prior attempt's findings back in. Failure mode prevented: a reviewer briefed with "here's what we think is risky — please confirm" produces a review that confirms; a reviewer briefed with "here are the artifacts, find what's wrong" produces a review that finds.
- **Drafted External Comments — Post in One Step:** When a role drafts a GitHub issue or PR comment to address a user-directed task, post it in the same turn rather than gating on a separate *"approve to post"* step. Drafting and posting are one action; the user keeps revert authority via the GitHub UI. Still requires explicit approval: opening a new issue or PR, mentioning users not already in the thread, comments touching security-sensitive content, or any post to a destination the user has not already pointed the role at.
- **Proactive Escalation:** If you are blocked by undocumented behavior, face repeated failures, or identify a systematic gap in prompt instructions, seamlessly halt and escalate to the **User (Admin)** for clarification and to patch the workflow/knowledge gap. Do not guess.


# Project-Specific Instructions: Vibe-Cading

## Project Purpose
Parametric 3D CAD models built with **CadQuery** (Python). Primary goal: generate common machinery models (screws, hexes, gears, etc.) and design parts that interface **RC (radio-controlled) components** with **Lego Technic** assemblies.

Typical parts include:
- Common machinery models (screws, hexes, gears, etc.)
- Motor mounts, servo brackets, ESC/receiver holders
- Adapters between RC hardware and Lego Technic beams, axles, and pins
- Custom structural parts that conform to the Lego Technic 8 mm stud grid

## Environment
- Language: **Python**
- CAD library: **CadQuery**
- IDE: VS Code with Dev Container (Docker container — Debian GNU/Linux)
- Use the system `python3` binary directly; do **not** create or activate a virtual environment

## Key Constraints
- All hole centers must align to the **8 mm stud grid**
- Use Lego Technic standard dimensions for holes (4.8 mm), axles (5.0 mm tip-to-tip), and beam thickness (7.2 mm)
- All units are **millimeters (mm)**
- Do not scale exported STEP/STL files — CadQuery works in mm natively

## Code Quality & Open-Source Standards
This codebase must be maintained at a high standard of structural quality and readability, as it will be released as open-source.
- **No Overly Specific Hardcoding:** Avoid "magic numbers" in model logic. Dimensions should be derived from fundamental parameters (e.g., `self.length = holes * 8.0`) or imported from centralized constants (like `lego.constants`).
- **Fundamental Geometry over Hacky Patches:** Do not use arbitrary translations, clipping boxes, or brute-force boolean intersections just to "make it look right" for one specific set of parameters. Geometry should be anchored to logical origins (e.g., centering a gear on `(0, 0, 0)`) and scaling cleanly.
- **Self-Documenting Code:** Class properties, methods, and parameters must be clearly named. Complex geometric reasoning (e.g., *why* an overcut of `0.05` is used, or the math behind a polar array) should be briefly commented in the code so future open-source contributors understand the intent.
- **Generic Tooling:** Shared features (like generating a standard Technic axle hole, or a generic mounting tab) should be abstracted into reusable functions in `cq_utils.py` or base classes, rather than duplicated across models.
- **Object-Oriented Component API:** Mechanical joints, hardware wrappers, and modular utilities should be designed as Python classes rather than bare functions. Standardize boolean interfaces by exposing methods like `.male(overlap: float)` (for additive geometry) and `.female(overlap: float)` (for subtractive cutters), or a uniform `.solid` property for read-only geometry.
- **Manufacturing & Tolerance Profiles:** Never hardcode a "magic" clearance (like `+ 0.2`) deep inside an internal boolean cut or method. Tolerances should map to user-maintained profiles via `models.print_settings.get_profile(name)`. The system provides hardcoded defaults (like `fdm_standard` or `resin_precise`) tracked in `machine_profiles.json`, but developers and users can easily override these locally by maintaining a `machine_profiles_user.json` file (untracked) which will dictionary-merge over the defaults. You must also instruct users to define `.env` with `VIBE_MACHINE_PROFILE` to change the global fallback. All subtractive classes/methods must support accepting these parametric clearances dynamically.
- **2D Sketching over 3D Booleans:** For performance, prefer 2D `Workplane.polyline().extrude()` over combining multiple 3D primitives with costly `.union()` or `.cut()` operations. Native OCCT 2D sketching is dramatically faster and avoids floating-point seam artifacts.
- **Absolute Zero-Datum Consistency:** The primary physical interface of a component (the mating face, rotation axis, or flat print bed surface) must mathematically sit exactly at `(0, 0, 0)`. Examples: gears must rotate at `X=0, Y=0`; joints connect at `Z=0` (extruding up into +Z while cutters project down into -Z).
- **Explicit Public APIs:** All parameters must utilize strict Python type hinting (e.g., `length: float, positions: list[tuple]`) and classes must contain a top-level docstring stating exactly what the `(0,0,0)` origin represents so users know how to place the component in an assembly.
- **Infinite Cutter Overcuts:** When creating a female `.to_cutter()` tool, any face that is intended to completely break through a boundary must be explicitly extended infinitely (e.g., `overlap=10.0`) past that boundary. Do not make cutters exactly the same thickness as the wall.

## Reference Docs
- [docs/lego-technic.md](../docs/lego-technic.md) — Lego Technic part dimensions (beams, pins, axles, holes, gears, tolerances)
- [docs/agentic-workflow.md](../docs/agentic-workflow.md) — Three-role agentic workflow (Admin / Designer / Developer)

## Agentic Workflow

This project uses a structured workflow.
See [docs/agentic-workflow.md](../docs/agentic-workflow.md) for the full
specification.

**Roles:**
- **Contributor Roles (canonical persona content under `vibe/agents/`):** `designer` (domain reasoning & design briefs), `developer` (code structure, implementation & execution).
- **Maintainer Roles (Bring-Your-Own / Human):** Admin (requirements & review), TL (architecture & refactors). Open-source contributors act as the Admin and guide the workflow manually unless they supply their own personal agent platform configuration.

**Artefact locations** (git-ignored):
- Design briefs: `.agents/plans/`
- Session backlog / Parking lot: `/memories/session/ideas.md` (Store ideas, refactors, or tooling improvements that emerge during the session but should not be acted upon immediately).

**Key rule:** The Developer must not interpret ambiguous reference material
(drawings, STEP files).  The Designer pre-digests all dimensions, coordinate
mappings, and design decisions into the design brief.  The Developer owns
code structure (classes, methods, build pipeline) and decides *how* to
implement the brief.

**Workspace Initialization:**
When initializing the project or workspace, you must:
1. Create local `.gitignore`d directories if they don't exist (`tmp/`, `.agents/plans/`).
2. Copy `machine_profiles.json.example` to `machine_profiles_user.json` so the user can configure their specific 3D printer tolerances.
3. Run any host-platform-specific runtime scaffolder if your agent host requires one (e.g., for Claude Code: `tools/init-claude-runtime.sh` — see the host's own instruction file for details).

## Multi-Part Assemblies

When a reference (STL, STEP, drawing) contains **N physically distinct
parts** (e.g. two plates and a ring, or a case top and bottom), each part
must be implemented as its own class with its own `.solid` property.  A
wrapper / assembly class may compose them, but individual parts must be
independently buildable and exportable via `build.toml`.

Never merge distinct parts into one monolithic `_build()` method.  If a
reference looks like a single mesh (e.g. a pre-assembled STL), the
Designer must still identify the logical part boundaries in the design
brief, and the Developer must implement each part as a separate class.

## build.toml — Explicit Registration Only

**Never add a new `[[build]]` entry to `build.toml` without explicit user approval.**

When a new model class is implemented, do NOT automatically register it.
Instead, present the proposed TOML block to the user and ask for confirmation
before touching `build.toml`.  This keeps the build manifest intentional and
prevents untested or intermediate models from polluting the output tree.

## OCP Viewer — Dedicated Entry Point

Model class files must **not** contain `ocp_vscode` imports or
`if __name__ == "__main__":` viewer blocks.  Keep class files as pure class
definitions.

Use the dedicated `tools/view.py` entry point instead:

    python3 tools/view.py <module.path.ClassName> [--params key=value ...]
    python3 tools/view.py rc.servo.sg90.Sg90Servo
    python3 tools/view.py rc.servo.sg90.Sg90Servo --params body_width=23.0

For assemblies that need multiple parts shown with positional offsets, create a
dedicated assembly module (e.g. `models/xlego/servos/shaft_saver_assembly.py`)
that exposes a top-level `assemble()` function returning a list of
`(solid, name, color)` tuples.  `tools/view.py` will call `assemble()` when
`--assembly` is passed:

    python3 tools/view.py --assembly xlego.servos.shaft_saver_assembly

## Known Modelling Pitfalls

### Chord-vs-arc ring (polygonal boolean cutters on cylinders)

**Symptom:** A thin ring of uncut material is left around a cylindrical body
after boolean-cutting with a series of polygonal wedge prisms (e.g.
approximating an annular cam ramp with N flat wedges).

**Root cause:** The outer (or inner) edge of each wedge cutter is a straight
line (chord) connecting two adjacent points on the cylinder's circle.  Chords
are always inscribed *inside* the arc, so the cutter never reaches the
cylinder surface between corner points.  The uncut material forms a thin
ring whose cross-section equals the **sagitta**:

    sagitta = r × (1 − cos(Δθ / 2))

For r = 5 mm and 72 steps (Δθ = 5°), this is only 0.005 mm — but OCCT
treats the cutter boundary as a new face, creating visible edges that the
tessellator highlights as a seam or ring even though the geometric gap is
sub-micron.

**Fix:** Extend the cutter radius by a small **overcut** (0.1 mm is
sufficient) beyond the nominal body boundary.  The excess is outside the
body and has no effect on the cut, but guarantees the cutter fully overlaps
the cylindrical surface.  Apply the same logic to inner radii (shrink by
overcut).

**General rule:** Whenever a boolean cutter's face is designed to be
*coincident* with an existing face of the target body, add a small overcut
(typically 0.05–0.1 mm) so the cutter extends *beyond* the target face.
Coincident faces are a well-known source of unreliable results in the OCCT
boolean kernel.

### Stair-step surface (flat-topped polygon approximation)

**Symptom:** A surface that should be smoothly curved (e.g. a sinusoidal
ramp) shows visible stair-step transitions between adjacent facets.

**Root cause:** Each wedge prism's bottom (or top) face is assigned a single
Z value evaluated at the wedge midpoint.  Adjacent wedges have *different*
midpoint Z values, creating discontinuous steps.

**Maximum step height:**

    Δz_max ≈ cam_lift × sin(2θ_steepest) × Δθ

For cam_lift = 2.5 mm and 72 steps (Δθ = 5°):  Δz_max ≈ 0.22 mm — within
typical FDM layer height (0.2 mm).  Increase step count for smoother result:
144 steps → 0.11 mm, 360 steps → 0.044 mm.

**Why the "obvious" fix fails:** The natural impulse is to evaluate the
surface function at each wedge *edge* angle (θ_lo, θ_hi) instead of the
midpoint, creating sloped bottom faces that form a C0-continuous surface.
**This breaks OCCT booleans.**  Adjacent sloped wedges share boundary edges
at identical (θ, Z) coordinates — effectively coincident faces.  Sequential
boolean cuts on such geometry produce split solids, negative volumes, or
void results.  Compound cuts (collecting all wedges and cutting once) also
fail.

**Fix:** Keep the midpoint (flat-topped) evaluation and increase the step
count if the stair-step height is unacceptable for the application.  The
flat-topped approach is safe because adjacent wedges have *different* bottom
Z values at their shared boundary, preventing coincident faces.

### Incomplete boolean cuts (floating wings / artifacts)

**Symptom:** Thin artifacts, floating "wings", or tabs of material are left behind at the extreme bounds of a part after performing a subtractive boolean cut.

**Root cause:** The base geometric block was extruded to the *absolute maximum bounding box* of the part design (e.g. extending all the way up to an inner, taller feature's height). However, the subtractive cutter tool didn't reach high enough (or deep enough) to completely engulf that maximum bounding box perfectly. This leaves behind a tiny, un-cut wafer of original material.

**Fix (Two approaches):**
1. **Additive bounding:** Do not extrude the main base geometry to the absolute highest/lowest point if that point only belongs to a small localized feature (like a central boss or disk). Extrude the main body only to its true functional height, and use `union()` later to add localized taller features.
2. **Infinite Cutter Overcut:** When building a cutter that bounds a part from the top or bottom (like a surface profile or ramp cutter), *always* extend its orthogonal extrusion height arbitrarily far beyond the body limits (e.g. `needed_h + 10.0` or `100.0` mm) to guarantee it cleanly clears the topmost/bottom-most bounds of the material. Never use precise/tight bounds for the "waste" side of a cutter.

### Blind Holes and Internal Geometry Under-visibility

**Symptom:** Counterbores, internal cavities, or snap-rings fail to appear inside a boolean-cut body, or leaving a zero-thickness planar wafer blocking the hole.

**Root cause:** Mismanagement of blind-hole cutters. If a cutter is designed to create a *blind* hole (stopping exactly inside a body), its terminal faces must *not* have an overcut (or it goes too deep). However, the entry face that sits flush with the solid's boundary must have an outward overcut (e.g. 0.01 mm). Furthermore, developers often fail to notice these bugs because standard external views (e.g. `iso_ne`) physically cannot see inside a blind hole.

**Fix:**
1. **Cutter Overcuts:** Apply an outward overcut securely on the *entry* bounds. The *terminal* bounds (bottom of the blind hole) must end precisely at the target dimension.
2. **Mandatory Slicing:** Never rely on external previews to validate holes with internal structures (like snap rings or internal counterbores). The Designer **must** instruct the Developer to use `section_slicer.py` through the hole axis (`--axis X` or `Y`) and read the report to statically verify the internal Z-steps and widths.

### Topological Validation (Floating Bodies)


**Symptom:** Thin slivers, floating geometric islands, or unattached pieces appear in the final build, which are disconnected from the primary solid. This often happens after boolean cuts or when unions fail to overlap correctly.


**Fix:**

1. **Programmatic Assertion:** The Developer must ensure that the final produced geometry consists of a single contiguous solid. Add a programmatic check at the end of parts that should produce a single object: `assert len(result.solids().vals()) == 1, "Expected single solid, got multiple pieces"`.

2. **Overlap:** Check that mating parts overlap completely before unions, and cut profiles fully sever material without leaving thin root remnants.

### Validating Internal Intersections and Mating Surfaces

**Symptom:** Unintended hooks, sharp lips, or attached slivers remain after complex boolean cuts, but they pass the standard floating-body topology check because they remain attached to the main solid. Furthermore, standard orthographic SVGs (like `top` or `front`) visually obscure these internal artifacts.

**Fix:**
1. **Visual Cross-Sectioning:** When writing or modifying boolean operations that form complex internal mating faces (such as gear teeth, ramps, and spring pawls), the Developer MUST generate a section slice through the active mechanism using `section_slicer.py` or export a 3D generic snapshot (e.g., `iso_ne`) with the obstructing cover/top-plates temporarily disabled.
2. **Programmatic Intersect Validation:** The Designer must task the Developer to programmatically compute the boolean intersection (`.intersect()`) volume between the two mating parts. If clearance is correctly applied, the intersection volume should be strictly equal to `0.0` or empty.

### 2D Array Sequence Validation (Polar Monotonicity)

**Symptom:** Unbounded tangent vectors applied to structural corner fillets in 2D profile generation cause the local geometry to "overshoot" available chord distance and violently whip backwards. This generates jagged, retrograde "hooks" that survive general extrusion/boolean topology checks completely undetected because they form a mathematically closed valid solid. Testing the abstract math curve prior to array concatenation does not catch these bounding overlaps.

**Fix:**
1. **Mandatory Monotonicity Check:** The Developer MUST run `tools/check_polar_monotonicity.py <module.path.ClassName>._method_name` on any function returning a complex concatenated radial/polar 2D sequence (like ramps or gears). The script mathematically proves the finalized point sequence only moves forward without geometric back-tracking.
2. **Bounded Fillets:** Never feed infinite rays or raw vectors blindly into `_fillet_corner` when the shared segment between two adjacent bounds is physically limited. Always supply a literal adjacent real-world target vector coordinate, and ensure structural tools natively enforce maximum proportional bounds (e.g., capping tangent scaling at `< 0.49` length).


## Asset Validation

After generating or modifying a model, always validate it visually using the
preview tool:

    python3 tools/preview.py <module.path.ClassName>

This writes orthographic SVGs to `tmp/preview/` (git-ignored):

| File | Projection |
|---|---|
| `<ClassName>_top.svg` | Plan view — looking down Z |
| `<ClassName>_front.svg` | Front elevation — looking along −Y |
| `<ClassName>_left.svg` | Side elevation — looking along −X |

The tool accepts optional constructor overrides via `--params key=value ...`
and a custom output directory via `--out DIR`.

**Choosing views**

Use `--views` to export any combination of named views:

    python3 tools/preview.py <model> --views top front left right bottom
    python3 tools/preview.py <model> --views iso_ne iso_sw   # 45° diagonals
    python3 tools/preview.py <model> --views all             # every angle
    python3 tools/preview.py --list-views                    # show all names

Available view names (run `--list-views` for the full list):

| Name | Camera direction |
|---|---|
| `top` / `bottom` | ±Z |
| `front` / `back` | ±Y |
| `left` / `right` | ±X |
| `iso_ne/nw/se/sw` | 45° diagonals from above |
| `iso_bot_ne/nw/se/sw` | 45° diagonals from below |

**Purpose of SVG previews**

The SVG output is **not** a code correctness check — it is a visual
comparison tool.  Use it **only** when a reference image or drawing is
attached to the task, to detect mismatches between the implementation and
the requirements.  Do not read SVGs back to "validate" a model when no
reference is provided.

**When reference images or drawings are attached to a task:**

**Step 0 — establish orientation before reading any numbers**

Do this for every view in the reference before extracting a single dimension:

1. **Identify the projection type**: orthographic (top / front / side
   elevation) or isometric / perspective.  Standard three-view drawings
   use plan (top), front elevation, and side elevation.

2. **Locate asymmetric orientation cues**: find a feature whose real-world
   position is unambiguous — gear shaft, cable connector, mounting holes,
   label text.  Determine which physical direction each cue implies.
   *Example: the SG90 gear boss/collar always sits at the shaft end of
   the body.  If the collar is at the bottom of a side-elevation view,
   the servo is shown upside-down.*

3. **Establish the axis mapping** — which drawing direction (+X / +Y on
   paper) corresponds to which model axis, and whether any are flipped.
   *Example: servo shown upside-down → drawing-down = model +Z (toward
   collar); drawing-up = model Z = 0 (connector end).*

4. **Re-read every annotated dimension through that mapping** before
   comparing it to a model constant.  A stack of dimensions in a drawing
   must be read in the correct order (top-to-bottom in drawing ≠
   always bottom-to-top in model Z).
   *Example: stacked dims `4.3 / 2.4 / 4.2 / 17` reading from
   drawing-top (connector end = model Z = 0) gives tab bottom at
   model Z = 4.3 mm — NOT 17 mm, which is the large segment at the
   far (collar) end.*

**Steps 1–5**

1. Choose views that match the orthographic projections shown in the
   reference (e.g. top/front/left for a standard three-view drawing).
2. Run the preview tool immediately after building the model.
3. Read back each SVG file — SVG is plain XML, any agent's file-reading
   capability works.  Path coordinates are in mm-scale model space.
4. Compare each view against the corresponding projection in the reference.
   Check: overall bounding-box dimensions, feature positions, holes.
5. If discrepancies are found, correct the constants in the model, rebuild,
   and re-run the preview tool until the SVG matches the reference.

**Choosing views**

- **Default** (top + front + left) matches the standard three-view drawing.
- Add `right` and `back` when the part is **asymmetric** in both X and Y.
- Add `bottom` when the underside has pockets, bosses, or connectors.
- Add iso views (`iso_ne`, `iso_sw`) when the reference shows a 3D
  perspective or when 3D features (chamfers, snap posts, bosses) are
  ambiguous in plan/elevation.
- Use `all` only as a last resort — it generates 14 SVGs and is slow.

## Reverse-engineering from STEP files

When a reference STEP file is provided, extract geometry programmatically
before writing any model code.

### STEP analysis tools

All tools live in `tools/` and accept a `.step` / `.stp` path as the first
argument.  Every tool supports `--json` for machine-readable output.

| Tool | Purpose | Key flags |
|---|---|---|
| `step_summary.py` | Body count, topology counts, bounding box, volume, centre of mass | `--json` |
| `face_catalog.py` | Classify every face by surface type with geometry details | `--type Cylinder`, `--min-area`, `--summary` |
| `hole_finder.py` | Detect cylindrical holes and bosses; diameter, depth, axis, centre | `--grid 8`, `--type holes\|bosses` |
| `face_distances.py` | Perpendicular distances between parallel planar faces | `--axis Z`, `--unique`, `--max-dist` |
| `section_slicer.py` | Slice at one or more planes, export 2D cross-section SVGs; `--report` prints a table of edge types, radii, and centres per slice | `--axis Z --at 5 10`, `--sweep 3`, `--report` |
| `step_preview.py` | Orthographic SVG previews (same as `preview.py` but for STEP files) | `--views top front left` |
| `boolean_diff.py` | Volume comparison via boolean A−B / B−A | `--model`, `--align-bbox`, `--export` |

**Workflow**

1. **Run `step_summary.py`** first to get the overall envelope, body count,
   and volume.  This establishes the coordinate system orientation.
2. **Run `step_preview.py --views iso_ne iso_sw`** immediately after
   `step_summary.py`.  Iso views reveal rotationally-symmetric features
   (offset bosses, secondary cylinders, snap rings) that are invisible or
   ambiguous in flat orthographic projections.  Inspect the SVGs before
   extracting any dimensions.
3. **Run `face_catalog.py --summary`** for a type breakdown, then
   `--type Cylinder --min-area 5` to find significant cylindrical features.
4. **Run `hole_finder.py`** to catalogue all holes and bosses with precise
   diameters, depths, and centres.  Use `--grid 8` for Lego alignment checks.
5. **Run `face_distances.py --unique`** to extract wall thicknesses, tab
   heights, and other parametric dimensions.
6. **Run `section_slicer.py`** when internal geometry (pockets, ribs) is
   ambiguous from face data alone.
7. **Process objects large → small** (per the Agent Behavior rule above):
   identify the main body, then tabs/flanges, then bosses/collars, then
   holes and chamfers.
8. **Establish the coordinate mapping** between the STEP coordinate system
   and the model coordinate system before comparing any numbers.  STEP
   files often use a different origin or axis orientation.
9. Place any temporary analysis scripts under `tmp/`, never in the repo root.

**Feature reconciliation (mandatory before volume comparison)**

After running the analysis tools and writing the model, **reconcile every
significant feature** detected by `hole_finder.py` and `face_catalog.py`
against the model code.  A feature is "significant" if its diameter ≥ 1 mm
or its area ≥ 5 mm².

1. List every boss and hole from `hole_finder.py` output (ignore R < 0.5 or
   features that are clearly edge fillets / chamfer arcs from `face_catalog`).
2. For each feature, identify the corresponding model method or constant.
   If no match exists, the feature is **unmodelled** — flag it.
3. Present a checklist to confirm coverage before running `boolean_diff.py`:

       ✓ Main body             → _main_body
       ✓ Collar R=6.3          → _add_collar
       ✗ Gear boss R=2.5       → NOT MODELLED   ← implement this
       ✓ Shaft R=2.3           → _add_shaft
       ✗ Shaft bore R=0.9      → NOT MODELLED   ← implement this

4. Implement any unmodelled features before proceeding to the volume check.

This step prevents features from being *detected but never implemented* —
the failure mode that caused the gear boss, shaft bore, and corner bores
to be omitted in earlier iterations.

**Volume / boolean comparison as a quantitative check**

After building the model, compare it against the STEP reference:

    python3 tools/boolean_diff.py reference.step module.ClassName --model --align-bbox

This reports volume delta, intersection, missing/extra material, and Jaccard
similarity.  Use `--export` to write residual STEP files for inspection.

A volume delta under 1 % indicates a good dimensional match.  Remaining
difference is usually fillets, chamfers, or small features intentionally
simplified in the parametric model.



## Parameter Sweeps and Test Fits
When generating gauge blocks, parameter sweeps, or test fits to dial in tolerances for a user:
- **Minimize Material Waste:** Make parts as compact as physically possible. Pack holes tightly, use thin walls, and apply the minimum necessary extrusion depth.
- **Explicit Labeling:** Etch or extrude labels (e.g., text showing variant sizes like "4.60") directly onto the part using `cq.Workplane.text()`. Do not rely solely on positioning or arbitrary notches to communicate variants. (Note: Group all text into a single unioned string before applying a `.cut()` or `.union()` to avoid stalling the OCCT boolean kernel).

## Constants & Tolerances

- When modifying or creating constants in `models/lego/constants.py` that describe 3D printed friction fits or clearances (e.g. hole diameters, axle thickness), you must wrap the hardcoded default in `os.getenv("VARIABLE_NAME", "default")` and cast it to float. This allows users to tweak dimensions in a `.env` file without modifying source tracked code.
- Avoid introducing third-party pip dependencies like `python-dotenv` for this. The `constants.py` file should implement its own simple standard library file parser (e.g. reading lines that contain `=`).
- **Material-Specific Screw Tolerances:** When designing an object that mounts using generic screws, the implementation's `__init__` should accept a `material` string keyword argument (default `"PLA"`). It should use `from models.print_settings import get_screw_allowances` to retrieve the `radial_allowance` and `head_recess_depth` parameters, and pass those explicitly to any screw `.to_cutter()` methods. Do not hardcode fixed manual clearance float values.

## Licensing & Open Source
- **AGPLv3 Headers:** Any new Python file created in the `models/` or `tools/` directories MUST include the AGPLv3 header at the very top. Look at an existing file for the exact text containing "vibe-cading is free software: you can redistribute it and/or modify". Empty `__init__.py` files are exempt.
