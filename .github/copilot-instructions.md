# Copilot Instructions

## Project Purpose
Parametric 3D CAD models built with **CadQuery** (Python). Primary goal: design parts that interface **RC (radio-controlled) components** with **Lego Technic** assemblies.

Typical parts include:
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

## Reference Docs
- [docs/lego-technic.md](docs/lego-technic.md) — Lego Technic part dimensions (beams, pins, axles, holes, gears, tolerances)
- [docs/agentic-workflow.md](docs/agentic-workflow.md) — Three-role agentic workflow (Overseer / Planner / Developer)

## Agentic Workflow

This project uses a structured three-role workflow for complex tasks.
See [docs/agentic-workflow.md](docs/agentic-workflow.md) for the full
specification.

**Roles:** Overseer (instructions & review), Planner (plans & decisions),
Developer (code & execution).

**Prompt files** in `.github/prompts/`:
- `#overseer` — requirements, instruction maintenance, lookback review
- `#planner` — structured plans, ambiguity resolution, output review
- `#developer` — code, tools, validation, escalation
- `#lookback` — end-of-task reflection and feedback

**Artefact locations** (git-ignored):
- Plans: `tmp/plans/`
- Lookback reports: `tmp/lookback/`

**Key rule:** The Developer must not interpret ambiguous reference material
(drawings, STEP files).  The Planner pre-digests all dimensions, coordinate
mappings, and design decisions into the plan.

## Agent Behavior
- When something is ambiguous, ask for specifications or confirmation rather than making assumptions.
- When a gap or missing guidance is detected in these instructions — e.g. a class of error that the instructions didn't anticipate, an edge case that required reasoning beyond what is documented, or a repeated mistake caused by absent rules — **alert the user immediately** and recommend a concrete addition or amendment to this file.
- When reverse-engineering from STEP files or images, **process objects from large to small** — identify and model the largest / outermost body first, then work inward to smaller features (bosses, holes, fillets, chamfers, etc.).

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

# Copilot workspace instructions

## Temporary / throwaway files
- Never create temporary scripts, analysis helpers, dump utilities, or one-off
  investigation files in the repository root (`/workspaces/cad/`).
- If a temporary file is needed (e.g. `analyze_stp.py`, `dump_coords.py`,
  `inspect_*.py`), place it under `/workspaces/cad/tmp/` instead.
- The `tmp/` directory is git-ignored; files there will not be committed.