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
| `TechnicAxle` | `models/lego/technic_axle.py` | Lego Technic cross axle solid, parametric length in stud units |
| `TechnicAxleHole` | `models/lego/technic_axle_hole.py` | Cross axle hole cutter profile for use in boolean operations |
| `AxleSleeve` | `models/technic_ball_bearing/axle_sleeve.py` | Sleeve that seats a Lego Technic axle inside a ball bearing |
| `EscMount` | `models/rc/vorteks_223s/esc_mount.py` | ESC mount plate for the Arrma Vorteks 223S |

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

Claude Code will read `CLAUDE.md`, create the local `tmp/` and `.agents/plans/` folders for tool analysis, copy `machine_profiles.json.example` → `machine_profiles_user.json` so you can configure your manufacturing tolerance profiles, and run `tools/init-claude-runtime.sh` to populate the per-clone `.claude/` runtime aliases that Claude Code uses to discover the project's `designer`/`developer` subagents and slash commands.

> Maintainer-style roles (Admin, TL, PM) are not shipped with this repository. Maintainers who want them install the [core-agents](https://github.com/fa-mc/core-agents) Claude Code plugin per-host and invoke `/core-agents-admin`, `/core-agents-tl`, `/core-agents-pm` (or personal wrappers under `~/.claude/`). Open-source contributors act as the Admin themselves — Claude Code drives the rest of the workflow via the included `designer` and `developer` subagents.

**Manufacturing & Tolerance Profiles:**
This repository uses a global tolerance configuration system to ensure parts fit together correctly based on your specific manufacturing method (e.g. FDM vs Resin 3D printing). 
- **`machine_profiles.json`**: Checked into version control. Contains defaults (like `fdm_standard`, `resin_precise`).
- **`machine_profiles_user.json`**: Untracked (gitignored). Use this to override specific keys in the default profiles or define entirely new profiles without creating a dirty git history. Your keys will be merged into the defaults.
- **`.env`**: Untracked. You can set `VIBE_MACHINE_PROFILE=your_profile_name` here to define the global fallback profile used across all CAD scripts.

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

1. Create a Python file under `models/` (in an appropriate subdirectory).
2. Define a class with a `.solid` property that returns a `cq.Workplane`.
3. Add a `[[build]]` entry to `build.toml`:

```toml
[[build]]
model  = "your_package.your_module.YourClass"
output = "your_package/your_output.step"
[build.params]
param_a = 10.0
param_b = 5.0
```

4. Run `python build.py` to verify the output.

---

## 🧹 Repository Hygiene & AI Dev

This repository uses an AI-first CAD approach and enforces strict separation of code for version control:
* **`models/`**: Purely declarative, reusable CadQuery class definitions and parameters. **Do not put throwaway debug scripts here.**
* **`tmp/`**: This directory is `.gitignore`d. **All** isolated experiments, AI-generated metric checks (e.g. `check_gap_2.py`), parameter sweeps, block gauges, and exported step files for debugging must be placed here.
* **`output/`**: Reserved for the final exported `.step` files generated by `build.py`.

Please keep Pull Requests clean by keeping scratch-pad test scripts restricted strictly to `/tmp/`.

---

## Lego Technic Reference

See [docs/lego-technic.md](docs/lego-technic.md) for a full reference table of Lego Technic dimensions — stud grid, pin holes, axle profiles, beam geometry, and FDM printing tolerances.

Key constants are centralised in [`models/lego/constants.py`](models/lego/constants.py).

---

## License

[MIT](LICENSE)
