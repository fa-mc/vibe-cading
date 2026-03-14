# Servo Mounts

Parametric housings that mount RC servo motors to Lego Technic assemblies.
Each sub-directory targets a specific servo form factor.

The cases are intentionally "not very Lego" — they are custom 3D-printed parts,
but all external interfaces conform to the **Lego Technic 8 mm stud grid**:
side-wall pin holes accept standard Technic pins, and top-face snap posts clip
directly into Technic beams or plates.

## Parts

### `sg90/` — SG90 micro-servo case

| File | Description |
|------|-------------|
| `servo_case_half.py` | Parametric housing — loose-fit variant |
| `servo+box_loose+fit.stp` | Reference STEP (reverse-engineered, CATIA V5 2024-01-31) |

A 24 × 24 mm outer-shell box that wraps around an SG90 (or pin-compatible)
micro-servo body.

**Lego interfaces**

- **Side-wall pin holes** — three Ø 4.8 mm bores per side (X walls), spaced at
  8 mm pitch (Y = +2.4, −5.6, −13.6 mm).  Each bore sits inside a shallow
  1 mm flanged recess so a Technic pin seats flush.
- **Top-face snap posts** — four 2 × 2 clusters of hollow snap posts on the
  8 mm grid, compatible with the stud spacing on Technic beams and plates.
  Posts rise 8 mm above the top plate.

**Servo interface**

- Open-bottom cavity (13.8 × 16.6 mm) accepts the servo body from below.
- Ø 9.6 mm shaft opening in the top plate.
- Two M2 screw bores per side (X direction) for optional mechanical retention.

**Output:** `output/lego/not_very_lego/servo_mount/sg90/servo_case_half.step`
