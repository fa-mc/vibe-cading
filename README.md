# vibe-cading

Parametric 3D CAD models written in Python with [CadQuery](https://cadquery.readthedocs.io/). The primary focus is generating common machinery models (screws, hexes, gears, etc.) and parts that interface **RC (radio-controlled) components** with **Lego Technic** assemblies — motor mounts, ESC holders, axle adapters, and similar hardware.

Models are built with AI assistance via [GitHub Copilot](https://github.com/features/copilot).

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
3. The container builds automatically with Python 3.11, CadQuery, and the [OCP CAD Viewer](https://github.com/bernhard-42/vscode-ocp-cad-viewer) extension.

The OCP viewer backend runs on port **3939** and is forwarded to your host automatically.

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

## Lego Technic Reference

See [docs/lego-technic.md](docs/lego-technic.md) for a full reference table of Lego Technic dimensions — stud grid, pin holes, axle profiles, beam geometry, and FDM printing tolerances.

Key constants are centralised in [`models/lego/constants.py`](models/lego/constants.py).

---

## License

[MIT](LICENSE)
