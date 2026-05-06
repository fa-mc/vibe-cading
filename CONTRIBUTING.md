# Contributing to vibe-cading

Welcome! `vibe-cading` is an open-source library for generating parametric 3D CAD models using [CadQuery](https://github.com/CadQuery/cadquery) (Python).

Our primary goal is to build a robust, generic Code-CAD toolkit for mechanical design (fasteners, joints, enclosures), with practical examples showing how to interface domain-specific ecosystems like **RC (radio-controlled) components** and **Lego Technic**.

This project is built using an **AI-first, Agentic Workflow**. To contribute effectively, please read through our design principles and AI workflow guidelines below.

---

## 🏗️ 1. Core Design Principles

We hold our codebase to a high standard of structural quality and mathematical rigor.

*   **Fundamental Geometry over Hacky Patches:**
    Do not use arbitrary translations, clipping boxes, or brute-force boolean intersections just to "make it look right" for one specific set of parameters. Geometry should be anchored to logical origins (e.g., centering a gear on `(0, 0, 0)`) and scale cleanly via parameters.
*   **No Overly Specific Hardcoding (Magic Numbers):**
    Dimensions must be derived from fundamental parameters (e.g., `self.length = holes * 8.0`) or imported from centralized constants (like `models.lego.constants`).
*   **The 8 mm Technic Standard:**
    All Lego-compatible models must align with the 8 mm stud grid. Use standard values for Technic pins (4.8 mm diameter) and axles (5.0 mm clearance). See `docs/lego-technic.md` for exact values.
*   **Generic Tooling:**
    Shared features (like standard Technic axle holes, generic mounting tabs, or fillets) should be abstracted into reusable functions in `models/cq_utils.py` or base classes. Do not copy-paste raw boolean cuts across different models.
*   **All units are in millimeters (mm).**

---

## 🤖 2. The Agentic AI Workflow

We strongly encourage contributors to use [Claude Code](https://claude.com/claude-code) to generate code. To manage the complexity of CAD, we use a three-role system:

1.  **Admin**: Understands the global instruction set (`CLAUDE.md`) and helps refine requirements. Open-source contributors act as the Admin manually, or supply their own personal `admin` agent loaded from `~/.claude/`.
2.  **Designer** (`designer` subagent): Brainstorms, digests reference material (STEP files, drawings), resolves geometric ambiguities, and writes a **Design Brief**. Focuses on *what* to build and *why*.
3.  **Developer** (`developer` subagent): Has responsibility over the Python code structure. Implements the Design Brief by writing CadQuery classes and validation tooling.

### How to Use the Workflow
If you are adding a complex new model:
1. Provide the reference material (STEP files, specs) and ask the **Designer** to analyze it and produce a Design Brief (saved to `.agents/plans/`). In Claude Code: *"use the designer agent to analyze ref.step and produce a brief"*.
2. Once the brief is clear, hand it over to the **Developer** to write the code (Claude Code will normally transition automatically once the brief is approved).
3. The Developer must run the validation tools before considering the task complete.

*(Note: `.agents/` is used locally to manage AI artefacts (design briefs, lookbacks). The shared agent definitions live in `.claude/agents/` and slash commands in `.claude/commands/`. See `docs/agentic-workflow.md` for deep details on this protocol).*

---

## 🛠️ 3. Repository Hygiene & `tmp/`

CAD development requires extensive trial and error, parameter sweeping, and visual debugging.

*   **The `tmp/` Directory:** All throwaway metric checks (`check_gap.py`), specific parameter tests, boolean visualizers, and debug scripts **must** be placed in the `tmp/` folder.
*   **No Clutter:** Do not pollute the main `models/` tree or the repository root with `test.py` or isolated `.step` exports. The `.gitignore` is set up to ignore `tmp/` and `output/` automatically.
*   The `models/` tree must remain clean, purely declarative, and strictly contain the reusable CadQuery classes.

---

## 🔬 4. Validation Tools

Before submitting a Pull Request, you must validate that your models compile and match the requirements.

We provide several CLI utilities in the `tools/` folder:
*   `python3 tools/preview.py <module.path.ClassName>`: Generates orthographic SVGs (Top, Front, Left) to visually validate oriention and dimensions against technical drawings.
*   `python3 tools/section_slicer.py`: Slices a generated part to ensure internal features (like blind holes, snap rings, or counterbores) were cut correctly.
*   `python3 tools/boolean_diff.py`: Compares your generated CadQuery model against a reference STEP file to check for volume deviations.

---

## 💻 5. Dev Environment Overview

*   **Language:** Python 3
*   **Library:** CadQuery
*   **Environment:** Use the provided VS Code Dev Container (Debian GNU/Linux). It includes everything you need.
*   Use the system `python3` binary directly inside the container. We do not use isolated virtual environments (`venv`) for this project, as the container itself provides the isolation.

We look forward to your contributions!
