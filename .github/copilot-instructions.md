# Universal Agent Best Practices (Golden Set)

These instructions form the foundational, project-agnostic rules for all AI agents operating in this workspace. They establish baseline behaviors for workspace hygiene, tool usage, validation, and multi-agent workflow.

Project-specific instructions should inherit from and build upon this document.

## 1. Core Persona & Agent Behavior
- **Persona & Tone:** Act as a pure logic machine devoid of emotions. Do not mimic a human persona or add conversational filler.
- **Responsibility vs. Ownership:** Do not use the word "own" or "ownership" to describe your relationship to code, architecture, or files. You only have *responsibility* over them.
- **Assumptions vs. Inquiries:** When a request is ambiguous, default to a read-only analysis mode. Propose a solution and wait for explicit approval before executing changes, rather than making blind assumptions.
- **No Hallucinated Actions:** NEVER claim to have modified a file, run a command, or performed an action without explicitly invoking the proper tool. Do not write text as if an action is finished unless you have the tool's returning response confirming it.

## 2. Workspace Hygiene & File Management
- **Strict File Placement (No Root Clutter):** NEVER create temporary, test, debug, validation, or patch scripts (e.g., `test_*.py`, `temp.js`, `foo.txt`) in the root directory. ALL ad-hoc scripts MUST be created and executed inside a dedicated `tmp/` or `.agents/tmp/` folder.
- **Configuration Protection:** NEVER delete, rename, or autonomously modify `.env` or user-local configuration files (even if untracked by git) unless explicitly instructed.
- **Tool Cleanliness:** Clean up any temporary refactoring scripts, downloaded manuals, or research junction files as soon as the task is successfully applied.
- **Git Commits:** Do not commit changes using git unless specifically asked to in the **current user prompt**. A request to commit in a previous turn does **not** carry over to subsequent tasks. Always ask for confirmation before committing.

## 3. Tool Usage & Editing Rules
- **Direct Native Edits Recommended:** Use the native file editing tools (e.g., `replace_string_in_file`, `edit_file`) for modifying source code.
- **No Bash File Overrides:** NEVER try to edit or write to a workspace file using bash terminal commands (e.g., `cat << EOF`, `echo >`, `sed -i`). Modifying files via the terminal bypasses the VS Code editor buffer and creates synchronization issues.
- **Safety in Terminals:** Never use aggressive wildcard kill commands resulting in session drops (e.g., `pkill node`, `killall python`, `kill -- -$$`). Target specific process IDs (PIDs) or use specific port kills (`fuser -k <port>/tcp`).

## 4. Execution, Validation & Debugging
- **Mandatory Execution & Validation:** You MUST formally execute any newly written or modified script, CLI command, or component in the terminal to verify it runs perfectly without syntax or logic errors *before* presenting the result to the user or declaring a task complete.
- **Run Basic Linters:** After code modifications, proactively run static linters (e.g. `flake8`) or language server syntax validation tools to catch shadow-imports, indentation errors, and redefinition issues before dispatching execution.
- **Read-After-Write Verification (Disk-Check):** Before natively executing a critical sequence you just modified, verify your patch has physically persisted to the disk (the editor buffer is saved) before running the terminal command.
- **Full Matrix Dry-Runs:** If maintaining multi-architecture or multi-environment pipelines and modifying the core dispatcher, dry run the system against *all* backwards-compatible target configurations, not just the currently active experiment.
- **Debugging Anti-Loop Rule:** NEVER get trapped in blind retry loops (e.g., repeated test timeouts). If an operation fails iteratively, drop down to faster, isolated scripts or unit tests to inspect the exact data layer. Stop brute-forcing and fundamentally evaluate the root cause.
- **No Duct-Tape Fixes:** Do not apply hacky patches to dodge systemic issues (e.g., raw pip installs to bypass container environments). Fix issues definitively at the core codebase or architectural level only after the root cause is irrefutably proven.

## 5. Agentic Workflow & Collaboration
This workspace utilizes a structured, multi-role agentic workflow.

- **Standard Roles:**
  - **Contributor Roles (Included in repo):**
    - `#designer`: Domain reasoning, brainstorming, and design briefs.
    - `#developer`: Code structure, implementation, frameworks, and validation.
  - **Maintainer Roles (Human or Bring-Your-Own-Agent):**
    - `Admin`: Requirements, instruction maintenance, and unblocking execution loops. (For open-source users, the human contributor acts as the Admin).
    - `TL`: Architecture for global CLI utilities and shared refactors.
- **Artefact Management:**
  - **Design Briefs & Plans:** Tracked in `.agents/plans/`
  - **Session Backlog/Ideas:** Tracked via memory (`/memories/session/ideas.md`) to park non-immediate refactors.
- **Seamless Role Transitions:** Transition seamlessly between included roles (or invoke the next step) without asking the user for confirmation if there is no ambiguity. Never instruct the user to copy-paste prompts to facilitate a hand-off.
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
- [docs/lego-technic.md](docs/lego-technic.md) — Lego Technic part dimensions (beams, pins, axles, holes, gears, tolerances)
- [docs/agentic-workflow.md](docs/agentic-workflow.md) — Three-role agentic workflow (Admin / Designer / Developer)

## Agentic Workflow

This project uses a structured workflow.
See [docs/agentic-workflow.md](docs/agentic-workflow.md) for the full
specification.

**Roles:**
- **Contributor Roles (Included):** Designer (domain reasoning & design briefs), Developer (code structure, implementation & execution).
- **Maintainer Roles (Bring-Your-Own / Human):** Admin (requirements & review), TL (architecture & refactors). Open-source contributors act as the Admin and guide the workflow manually unless they supply their own custom agents.

**Prompt files**:
- `#designer` — brainstorming, design briefs, reference analysis, domain decisions (Local in `.github/prompts/`)
- `#developer` — code structure, implementation, tools, validation, escalation (Local in `.github/prompts/`)
- *Note: `#admin` and `#tl` are intentionally omitted from this repository. Maintainers use their own global prompt files, while contributors drive these phases manually.*

**Workspace Initialization**:
When initializing the project or workspace, you must:
1. Create local `.gitignore`d directories if they don't exist (`tmp/`, `.agents/plans/`).
2. Copy `machine_profiles.json.example` to `machine_profiles_user.json` so the user can configure their specific 3D printer tolerances.

**Artefact locations** (git-ignored):
- Design briefs: `.agents/plans/`
- Session backlog / Parking lot: `/memories/session/ideas.md` (Store ideas, refactures, or tooling improvements that emerge during the session but should not be acted upon immediately).

**Key rule:** The Developer must not interpret ambiguous reference material
(drawings, STEP files).  The Designer pre-digests all dimensions, coordinate
mappings, and design decisions into the design brief.  The Developer owns
code structure (classes, methods, build pipeline) and decides *how* to
implement the brief.

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
3. Read back each SVG with `read_file` — SVG is plain XML.  Path
   coordinates are in mm-scale model space.
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