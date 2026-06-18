# Requirements: Lego System block generator
<!-- Filename: 2026-06-17-lego-brick-2x3_req.md -->

## Meta
- **Requester**: User (direct prompt)
- **Date**: 2026-06-17
- **Origin**: "generate a 2×3 lego block in the view" → "can we generalize this
  into a block generator?"

## Intent
A parametric generator for the studded Lego **System** block family (bricks,
plates, tiles) on the 8 mm stud grid, usable as a first-party `vibe_cading.lego`
primitive. The originally-requested 2×3 brick is the default instance.

## Requirements
- **R1** — One parametric class spanning the studded-System family; the member
  is a *parameter set*, not a subclass.
- **R2** — Footprint `studs_x × studs_y`, any integers ≥ 1; outer edge per axis
  = `n·STUD_PITCH − play` (real-Lego 0.2 mm pack gap).
- **R3** — Height parametrised in **plate units** (1 plate = 3.2 mm): plate = 1,
  brick = 3, double-brick = 6. Integer units keep blocks on the stacking grid.
- **R4** — Selectable top: studded (brick/plate) or smooth (tile).
- **R5** — Underside hollowed with walls + roof; clutch tubes placed **only**
  where a 2×2 stud cluster exists (both dims ≥ 2). 1×N / 1×1 are hollow-only.
- **R6** — Default instance = 2×3 brick; demonstrable in the OCP viewer.
- **R7** — Convenience factories: `brick`, `plate`, `tile`.
- **R8** — Honour project conventions: zero-datum (bottom clutch rim at Z=0,
  centred XY), single-solid topology, `.solid` property, dimensions from
  `lego.constants` (no magic numbers), AGPL header, no `__main__`/`ocp_vscode`
  in the class file, and the clutch bore sized from a tolerance **profile**
  (not a hardcoded nominal), per the project tolerance convention.

## Out of scope
- Technic-holed bricks, round bricks, slopes/wedges (separate classes).
- `build.toml` registration (requires explicit, separate user approval).
