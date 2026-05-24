# vibe-cading

A robust, AI-friendly, parametric Code-CAD library written in Python using [CadQuery](https://cadquery.readthedocs.io/).

The purpose of this repository is to provide a universal toolkit of reusable mechanical components (screws, heat-set inserts, hex nuts, joints, bearings, and enclosures). It also features practical examples demonstrating how to use these primitives to build parts that interface **RC (radio-controlled) components** with **Lego Technic** assemblies (motor mounts, ESC holders, axle adapters, etc.).

Models are built with AI assistance via [Claude Code](https://claude.com/claude-code). Project
agent personas and slash commands live under [vibe/agents/](vibe/agents/) and
[vibe/commands/](vibe/commands/) (tracked, tool-neutral); the runtime
`.claude/` tree is per-clone scratch, populated by
[tools/init-claude-runtime.sh](tools/init-claude-runtime.sh).

---

## Models

| Model | Location | Description |
|---|---|---|
| `TechnicAxle` | `vibe_cading/lego/technic_axle.py` | Lego Technic cross axle solid, parametric length in stud units |
| `TechnicAxleHole` | `vibe_cading/lego/cutters/technic_axle_hole.py` | Cross axle hole cutter profile for use in boolean operations |
| `TechnicAxleToBearingSleeve` | `vibe_cading/lego_adapters/technic_axle_to_bearing_sleeve.py` | Sleeve that seats a Lego Technic axle inside a ball bearing |
| `FreespinHexHub` | `vibe_cading/rc/freespin_hex_hub.py` | Freespinning RC hex wheel hub adapter |
| `EscMount` | `parts/arrma_vorteks_223s/esc_mount.py` | ESC mount plate for the Arrma Vorteks 223S |

---

## Examples

Four self-contained scripts under `examples/` demonstrate the library's
canonical usage patterns. Each runs under a vanilla CadQuery install and
writes STEP + SVG output to `examples/build/<name>/` (gitignored):

| Example | What it shows |
|---|---|
| `examples/lego_technic_beam.py` | `LegoTechnicBeam(length_in_studs=5)` from `vibe_cading.lego.technic_beam` |
| `examples/screw_cutter.py` | `MetricMachineScrew.to_cutter(profile=...)` boring a counterbore + clearance into a host block |
| `examples/gear_from_iso.py` | `SpurGear.from_iso(module=1.0, teeth=20, face_width=5.0)` ISO-validated gear factory |
| `examples/snap_fit_hook.py` | `CantileverSnapFit` male hook plus host block cut by `.to_cutter(...)` (two STEP files) |

Run one with:

    python3 examples/lego_technic_beam.py

---

## Dev Setup

This project runs in a **VS Code Dev Container** — no manual installation required.

**Prerequisites:** [Docker](https://www.docker.com/) and the [VS Code Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).

1. Clone the repo and open it in VS Code.
2. When prompted, click **Reopen in Container** (or run `Dev Containers: Reopen in Container` from the command palette).
3. The container builds automatically with Python 3.11, CadQuery, the [OCP CAD Viewer](https://github.com/bernhard-42/vscode-ocp-cad-viewer) extension, and the [Claude Code](https://marketplace.visualstudio.com/items?itemName=Anthropic.claude-code) extension. Your host `~/.claude/` is mounted into the container so any personal Claude Code agents, skills, or settings travel with you.

The OCP viewer backend runs on port **3939** and is forwarded to your host automatically.

### Workspace Initialization

Since this repository is managed via a three-role AI Agentic Workflow, you should initialize your local settings upon cloning the repository.

Open Claude Code in this workspace and ask it to initialize the project, e.g.:
```
please initialize the project
```

Claude Code will read `CLAUDE.md`, create the local `tmp/` and `.agents/plans/` folders for tool analysis, copy `print_profiles.json.example` → `print_profiles_user.json` so you can configure your manufacturing tolerance profiles, and run `tools/init-claude-runtime.sh` to populate the per-clone `.claude/` runtime aliases that Claude Code uses to discover the project's `designer`/`developer` subagents and slash commands.

> Maintainer-style roles (Admin, TL, PM) are not shipped with this repository — the human contributor fills them. As an open-source contributor you act as the Admin yourself: clarifying requirements, approving the designer's brief, and reviewing the developer's output. The included `designer` and `developer` subagents are the complete contributor toolkit and need no additional install. Maintainers who prefer dedicated Admin / TL / PM agents can load their own personas from `~/.claude/`.

**Manufacturing & Tolerance Profiles:**
This repository uses a global tolerance configuration system to ensure parts fit together correctly based on your specific manufacturing method (e.g. FDM vs Resin 3D printing). 
- **`print_profiles.json`**: Checked into version control. Contains defaults (like `fdm_standard`, `resin_precise`).
- **`print_profiles_user.json`**: Untracked (gitignored). Use this to override specific fields in the default profiles or define entirely new profiles without creating a dirty git history. Your fields are recursively deep-merged into the defaults — override a single leaf and the sibling fields inherit from the shipped grade (see [Print Tolerances & Calibration](#print-tolerances--calibration) below).
- **`.env`**: Untracked. You can set `VIBE_PRINT_PROFILE=your_profile_name` here to define the global fallback profile used across all CAD scripts.

---

## Building

Generate all STEP files defined in `build.toml`:

```bash
python build.py
```

Output files are written to `output/` (gitignored — regenerate at any time).

**Options:**

| Flag | Description |
|---|---|
| `--list` | Print configured outputs without building |
| `--config PATH` | Use an alternate TOML config (default: `build.toml`) |

---

## Adding a Model

1. Choose the right home for the new file:
   * **Reusable, project-agnostic library classes** (screws, gears, joints,
     Lego adapters, etc.) live under `vibe_cading/` in an appropriate
     subpackage (`mechanical/`, `lego/`, `lego_adapters/`, `rc/`, ...).
   * **Project- or vehicle-specific parts** (an ESC mount tied to one chassis,
     a motor plate for one truck) live under `parts/<vehicle_or_project>/`.
2. Define a class with a `.solid` property that returns a `cq.Workplane`.
3. Add a `[[build]]` entry to `build.toml`:

```toml
[[build]]
model  = "vibe_cading.your_subpackage.your_module.YourClass"
output = "your_subpackage/your_output.step"
[build.params]
param_a = 10.0
param_b = 5.0
```

4. Run `python build.py` to verify the output.

---

## 🧹 Repository Hygiene & AI Dev

This repository uses an AI-first CAD approach and enforces strict separation of code for version control:
* **`vibe_cading/`**: The reusable, project-agnostic library tree — purely declarative CadQuery class definitions and parameters (screws, nuts, joints, holes, drives, gears, Lego primitives, Lego adapters, RC building blocks). **Do not put throwaway debug scripts here.**
* **`parts/<vehicle_or_project>/`**: Project- or vehicle-specific parts that consume the library (e.g. `parts/arrma_vorteks_223s/`). One sub-folder per real-world target.
* **`tmp/`**: This directory is `.gitignore`d. **All** isolated experiments, AI-generated metric checks (e.g. `check_gap_2.py`), parameter sweeps, block gauges, and exported step files for debugging must be placed here.
* **`output/`**: Reserved for the final exported `.step` files generated by `build.py`.

Please keep Pull Requests clean by keeping scratch-pad test scripts restricted strictly to `/tmp/`.

---

## Lego Technic Reference

See [docs/lego-technic.md](docs/lego-technic.md) for a full reference table of Lego Technic dimensions — stud grid, pin holes, axle profiles, beam geometry, and FDM printing tolerances.

Key constants are centralised in [`vibe_cading/lego/constants.py`](vibe_cading/lego/constants.py).

---

## Print Tolerances & Calibration

Printed fits are printer- and material-dependent: the same model bores a tight hole on one machine and a loose one on another. Dimensional *nominals* in the library are fixed real-world geometry; the per-machine clearance is carried separately by a `ToleranceProfile`. The project ships profiles (`fdm_standard`, `resin_precise`, `cnc`) in `print_profiles.json`; override them per-machine in the gitignored `print_profiles_user.json` and select the active one with `VIBE_PRINT_PROFILE`.

**User key convention.** User-defined profile keys are recommended (not enforced) to follow the `<machine>__<material>[__<brand>]` lexical convention with `__` (double underscore) as the separator — for example `bambu_p1s__pla_overture`, `ender3__petg_polymaker`, `prusa_mk4__pla`. The convention is purely documentary; the loader treats every key as opaque. The shipped fallback keys (`fdm_standard`, `resin_precise`, `cnc`) remain the coarse-default categories and are exempt.

**Field-level deep merge.** Your override file recursively deep-merges onto the shipped defaults, leaf-wins. This means you can calibrate a single value without restating the rest of a fit grade. For example, to bump only `slip.radial`:

```json
// print_profiles_user.json
{
  "fdm_standard": {
    "slip": { "radial": 0.11 }
  }
}
```

The resolved `slip` grade then carries `radial = 0.11` (your override) together with `axial = 0.20` and `slot = 0.10` inherited from the shipped `fdm_standard`. A typo'd leaf key (e.g. `radail`) is silently ignored downstream — the resolved tolerance falls back to the shipped value. A `null` override (e.g. `{"slot": null}`) is rejected with a clear error rather than silently zeroing.

**Calibration helper.** The Lego axle slip fit is the project's canonical calibration target — print the `AxleHoleGauge` model and follow the procedure in [docs/lego-technic.md](docs/lego-technic.md) > *Tuning Tolerances* to convert the fitting hole diameter into a `slip.radial` value for your profile. A single-knob calibration CLI that writes the value into `print_profiles_user.json` for you is on the roadmap (see `TODO.md`).

**Deprecation window.** The legacy file names `machine_profiles.json` / `machine_profiles_user.json` and the legacy env var `VIBE_MACHINE_PROFILE` continue to be honoured during a deprecation window — first consumption per process emits a single warning. The legacy names will be removed at the OSS publication release; the loader prints the rename instruction at first contact.

---

## License

[MIT](LICENSE)
