# Copilot Instructions

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

## Reference Docs
- [docs/lego-technic.md](docs/lego-technic.md) — Lego Technic part dimensions (beams, pins, axles, holes, gears, tolerances)
- [docs/agentic-workflow.md](docs/agentic-workflow.md) — Three-role agentic workflow (Admin / Designer / Developer)

## Agentic Workflow

This project uses a structured three-role workflow for complex tasks.
See [docs/agentic-workflow.md](docs/agentic-workflow.md) for the full
specification.

**Roles:** Admin (instructions & review), Designer (domain reasoning &
design briefs), Developer (code structure, implementation & execution).

**Prompt files** in `.github/prompts/`:
- `#admin` — requirements, instruction maintenance, lookback review
- `#designer` — brainstorming, design briefs, reference analysis, domain decisions
- `#developer` — code structure, implementation, tools, validation, escalation
- `#lookback` — end-of-task reflection and feedback

**Artefact locations** (git-ignored):
- Design briefs: `tmp/plans/`
- Lookback reports: `tmp/lookback/`

**Key rule:** The Developer must not interpret ambiguous reference material
(drawings, STEP files).  The Designer pre-digests all dimensions, coordinate
mappings, and design decisions into the design brief.  The Developer owns
code structure (classes, methods, build pipeline) and decides *how* to
implement the brief.

## Agent Behavior
- When something is ambiguous, ask for specifications or confirmation rather than making assumptions.
- When a gap or missing guidance is detected in these instructions — e.g. a class of error that the instructions didn't anticipate, an edge case that required reasoning beyond what is documented, or a repeated mistake caused by absent rules — **alert the user immediately** and recommend a concrete addition or amendment to this file.
- When reverse-engineering from STEP files or images, **process objects from large to small** — identify and model the largest / outermost body first, then work inward to smaller features (bosses, holes, fillets, chamfers, etc.).

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