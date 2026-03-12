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

## Agent Behavior
- When something is ambiguous, ask for specifications or confirmation rather than making assumptions.

# Copilot workspace instructions

## Temporary / throwaway files
- Never create temporary scripts, analysis helpers, dump utilities, or one-off
  investigation files in the repository root (`/workspaces/cad/`).
- If a temporary file is needed (e.g. `analyze_stp.py`, `dump_coords.py`,
  `inspect_*.py`), place it under `/workspaces/cad/tmp/` instead.
- The `tmp/` directory is git-ignored; files there will not be committed.