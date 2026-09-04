# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/). While the
project is pre-1.0 the public API is not yet stable — see
[`docs/releasing.md`](docs/releasing.md) for the versioning policy (0.x phase) and
the release-cut process.

This changelog starts at the first tagged release. Earlier development history is
not retroactively seeded here — it lives in the git log. Every public-surface PR
from here on adds an entry under `## [Unreleased]`; cutting a release renames that
section to the new version and date.

## [Unreleased]

### Added
- `vibe_cading/mechanical/bearings.py`: `Bearing.blind_pocket_dims()` (static
  method — diameter/depth for a blind bearing pocket, given just an OD and
  width — not registered in `engine_api.json`'s wire contract, which
  catalogs only `__init__` and public classmethod factories, by design) and
  `Bearing.mr85()` (the MR85-2RS preset, matching the existing
  `b608()`/`b623()`/etc. classmethods). Consolidates bearing-pocket-sizing
  math that `FreespinHexHub`, `HexHubNut`, and `BearingHexHousing` each
  previously duplicated independently — `FreespinHexHub` and `HexHubNut`
  now delegate their pocket-dimension properties to the shared formula
  (verified behavior-identical by a regression test that computes each
  consumer's expected diameter/depth independently, from the original
  inline formula against an explicit fit-grade profile — not by
  re-deriving "expected" via the same shared call under test, which
  couldn't catch a drift in the shared formula's own defaults). Pure
  refactor — no consumer's printed geometry changes. See `TODO.md`'s
  "Consolidate blind bearing-pocket sizing" entry (flagged in PR #88's
  review cycle).

### Changed
- `vibe_cading/mechanical/bearings.py`: `MR85_ID`/`MR85_OD`/`MR85_W` now
  live once here (the single source of truth for the `vibe_cading.rc.*`
  hex-hub family) instead of being duplicated in `freespin_hex_hub.py`,
  `hex_hub_bearing/hex_hub_nut.py`, and `hex_hub_bearing/bearing_hex_housing.py`.
  `MR85_ID` was previously importable from `vibe_cading.rc.freespin_hex_hub`
  (unused there) and is no longer — import it from
  `vibe_cading.mechanical.bearings` instead.
- **(minor bump — breaking geometry change to `BearingHexHousing`'s existing
  bearing pocket, see below)** `vibe_cading/rc/hex_hub_bearing/`: `HexHubNut`
  now carries its own blind bearing pocket sunk into its outward (top,
  wheel-facing) face, sized for the identical MR85-2RS bearing seated on the
  shaft side by `BearingHexHousing` (new `bearing_od` / `bearing_width`
  constructor params, default 8.0 mm / 2.5 mm) — both ends of the fused
  `HexHubWithBearing` deliverable now seat a bearing, not just the shaft
  side. Both the new hex-side pocket and the pre-existing shaft-side pocket
  now use `free` fit grade (drop-in/pop-out by hand) rather than the prior
  `press` grade — a behavior change to `BearingHexHousing`'s already-shipped
  printed geometry (pocket diameter 8.08 mm -> 8.30 mm on `fdm_standard`),
  not merely additive, hence the minor version bump — so the bearing is
  user-replaceable at both ends.
  `Bearing.outer_pocket()` gained a `fit: Literal["press", "free", "slip"] =
  "press"` parameter to support this (defaults to the prior behavior for
  every other caller; raises `ValueError` on an unrecognized grade name).

### Fixed
- `vibe_cading/mechanical/holes.py`: `CounterboreHole`'s cylindrical (pan/socket)
  head-recess branch extruded in the wrong Z direction — outward, into open air
  above the entry face — instead of sinking into the part like the sibling cone
  (flat-head) branch. In practice the recess cut almost nothing (or, depending on
  cutter placement, the oversized head diameter punched through the full part
  thickness instead of transitioning back to the shaft diameter). Both `.solid`
  and `.to_cutter()` now sink the recess body downward from the entry face, with
  a small outward overcut at the opening (matching the cone branch's existing
  convention) rather than putting the whole recess on the outward side. No
  shipped model previously exercised this code path (`Arrma223sEscMount`'s
  pan-head ear/motor-mount holes are the first real usage), so no other model's
  geometry changes as a result.
- `vibe_cading/tools/view.py`: no longer reports a false success when no OCP CAD
  Viewer is listening. Previously it printed `Showing <Class>` and exited 0 while
  the model was never transmitted (the underlying connection failure surfaced only
  as a warning). It now resolves the target port, probes it, and aborts with exit 1
  and a message naming both ways to start a viewer. The probe is deliberate:
  `ocp_vscode.get_port()` trusts `OCP_PORT` without checking it, so resolution alone
  would let `OCP_PORT=<dead port>` reopen the same false success.
  `--export` is unaffected — the STEP file is written and the command still exits 0,
  warning on stderr that nothing was displayed, so headless export keeps working in
  scripts and `&&` chains.

### Added
- `docs/viewer.md`: guide to running the OCP CAD Viewer **in a plain browser tab**
  via the standalone server that ships inside `ocp_vscode`
  (`python3 -m ocp_vscode --host 0.0.0.0 --port 3939` → `http://localhost:3939/viewer`),
  with no VS Code required. Covers the client/server split, port forwarding, and
  the "browser tab must be open before you push" behaviour. Port 3939 was already
  in the dev container's `forwardPorts`, so no container change was needed.
- `vibe_cading/print_settings.py` / `vibe_cading/print_profiles.json`: new shipped
  `petg` tolerance-profile tier alongside `fdm_standard` / `resin_precise` / `cnc`
  — looser radial/slip-slot clearances than `fdm_standard` (PETG strings/oozes
  more than PLA) and a smaller press-fit bump (PETG's own flexibility already
  tolerates a snugger fit). See `docs/print-tolerances.md` §3.
- `vibe_cading/rc/arrma_223s_esc_mount.py`: `Arrma223sEscMount`, an
  ESC/receiver-box mount plate replacing the stock Arrma 223S-platform BLX185 3S
  motor plate. Also replaces the unrelated `parts.arrma_vorteks_223s.esc_mount.
  EscMount` (removed — an unmeasured stub with the same footprint role but no
  holes) at the same `build.toml` output path, `rc/vorteks_223s/esc_mount.step`
  — see "Removed" below. Reverse-engineered from an STL-only reference (no STEP available)
  — see `docs/design_plans/2026-08-31-arrma-223s-receiver-mount_design.md` for
  the full measurement method and correction history, including a 2026-09-01
  user-directed resize that overrides several reference dimensions (the physical
  reference part turned out to be the wrong size for the target vehicle).
  `base_thickness` (default 7.0 mm) and `accessory_thickness` (default 5.0 mm)
  are the two independent constructor parameters; `body_thickness` (the
  plate's own full thickness, extruded from Z=0) is a *derived*, read-only
  property equal to `base_thickness + accessory_thickness` (12.0 mm at
  defaults) — not a constructor argument. The accessory thickness is added ON
  TOP OF the base thickness: the plate itself is the full `body_thickness`,
  and the arm + south ear are `accessory_thickness`-tall tabs occupying only
  the plate's own top band, flush with its top face — they do not perch on a
  thinner plate over open air. The north ear was removed; its M2.5 fastener
  is now a round-head (M2.5 pan) counterbore in the plate body itself, entered
  from the bottom (chassis-mating) face: a head-diameter bore runs the whole
  `base_thickness` so the head passes freely through it, and the screw binds
  only on the shoulder at Z=`base_thickness`, clamping just the top
  `accessory_thickness` band — mirroring the south ear's plain bore, which
  likewise clamps only its accessory band. The cutter pre-subtracts the
  profile's `free.axial` allowance so that shoulder lands on `base_thickness`
  exactly, rather than drifting with the active print profile.
  Its X position (shared with the south ear's hole)
  is now derived from the real motor's 37.0 mm body length and 16.0/21.0 mm
  hole-to-edge offsets, centered between the two M3 hole centers, rather than
  a bare measured literal — X = -3.5 at the shipped M3 positions. The south
  ear's fastener is a plain M2.5 clearance hole with no recess, spaced
  exactly 38.0 mm from the relocated hole. Where
  the arm and south ear meet the plate they now butt against its full-height
  vertical side wall over a real 2D area, so only a small (0.02 mm)
  boolean-robustness union overlap is needed there, matching the project's
  existing flush-join convention (`HexHubWithBearing`, `AxleHexHubAdapter`).
  The main body still carries both original motor-mount holes (M3 pan-head
  clearance + top-face counterbore, plus an as-measured relief pocket on one
  hole's back face) alongside a back recess. Defaults to the `petg` tolerance
  profile (heat-adjacent mount).
- `vibe_cading/rc/hex_hub_bearing/`: RC 12 mm hex-wheel-adapter hub fused with
  an MR85-2RS bearing housing (`HexHubNut`, `BearingHexHousing`, and the
  primary deliverable `HexHubWithBearing`, which `.union()`s the two into a
  single printed body with a 0.02 mm boolean-robustness overlap epsilon at the
  flush join — no press-fit register). `HexHubNut`'s through-bore is 6.0 mm
  nominal (`free`-fit-grade), sized as a running-clearance hole around a
  uniform 5 mm-nominal stub axle — matching `FreespinHexHub`'s established
  convention. See `docs/design_plans/2026-08-25-rc-hex-hub-bearing_design.md`.
- `vibe_cading/lego_adapters/axle_hex_hub/`: Lego Technic axle -> 12 mm RC hex
  hub adapter (`AxleCompressionCollet`, `HexInsertHub`, and the primary
  deliverable `AxleHexHubAdapter`, which `.union()`s the two into a single
  printed body with the same 0.02 mm boolean-robustness overlap epsilon
  convention as `HexHubWithBearing`). `AxleCompressionCollet` is a 10 mm OD,
  10 mm-tall slotted split-collet cylinder carrying a keyed cross-shaped
  Technic-axle bore cut to exactly its own height (`free` fit plus a small
  extra radial clearance bump scoped to the bore only), with 2 axial collet
  slots (0.6 mm gap) aligned with the bore's arm-tip axis for an
  off-the-shelf compression collar's grub screws, a raised stop ring 6.5 mm
  from the shaft end limiting collar insertion depth, and two locating
  dimples 90 deg off the slots for the collar's set screws. `HexInsertHub`
  is a 12 mm hex prism carrying a parametrized straight-walled M3-class
  heat-set-insert pocket (`insert_length` default 5.0 mm) with no axle-bore
  feature of its own.
  See `docs/design_plans/2026-08-25-lego-axle-hex-hub-adapter_design.md`.

### Deprecated
- `vibe_cading.rc.freespin_hex_hub.FreespinHexHub` — superseded by
  `vibe_cading.rc.hex_hub_bearing.hex_hub_with_bearing.HexHubWithBearing`
  (same "12 mm hex + MR85-2RS bearing" family, modelled as fused component
  classes with tolerance-profile-driven fit grades on both the bore and the
  bearing pocket). `FreespinHexHub` now emits a `DeprecationWarning` on
  construction; its `build.toml` registration (`rc/hex_wheel_hub_12mm.step`)
  is unchanged pending a separate human decision on migration. May be removed
  in a future release.

### Removed
- `parts.arrma_vorteks_223s.esc_mount.EscMount` — an unmeasured stub (a flat
  notched plate with no holes) for the Arrma 223S ESC mount slot. Replaced by
  `vibe_cading.rc.arrma_223s_esc_mount.Arrma223sEscMount` (see "Added" above),
  reverse-engineered from the vehicle's actual BLX185 3S mount plate, at the
  same `build.toml` output path (`rc/vorteks_223s/esc_mount.step`) since it
  fills the same physical slot. No deprecation cycle — a direct replacement,
  since the two never coexisted as intentionally-distinct parts.

## [0.1.4] - 2026-06-26

### Added
- `BevelGear`: new exported model class — a parametric straight-bevel involute
  gear for intersecting-axis (e.g. 90°/miter) drives, completing the gear family
  alongside `SpurGear` / `HelicalGear` / `RackGear`. Constructor
  `BevelGear(module, teeth, mate_teeth, face_width, bore=None,
  pressure_angle=20.0, shaft_angle=90.0, n_flank=32)`; the pitch-cone angle is
  derived from `(teeth, mate_teeth, shaft_angle)`. Teeth are built via a Tredgold
  scaled-section loft (heel + scaled-toe cross-section, common pitch apex); the
  flat back/mounting face sits at `Z=0`. Reuses the shared `Gear` involute
  primitives, `from_iso`, and composable `Bore` shapes. `mesh_with` is overridden
  to pose an apex-coincident, shaft-angle-tilted mate (visual layout only; the
  parallel-axis `Gear.center_distance_to` is not used).

## [0.1.3] - 2026-06-26

### Added
- `HelicalGear.double_helix`: new optional `bool` parameter (default `False`).
  When `True`, builds a herringbone (double-helical) gear — two opposite-hand
  helical halves of `face_width / 2` meeting at a mid-plane chevron, cancelling
  the axial thrust a single helix produces.
- `HelicalGear.crossed_mesh_with()` / `HelicalGear.crossed_center_distance_to()`:
  pose a pair of single-helical gears on crossed (skew) shafts — crossed-helical
  ("screw") gears — with the shaft angle auto-derived from the two helix angles
  or overridden via `shaft_angle`. Posing only; the base `Gear.mesh_with` /
  `center_distance_to` (parallel-axis) are unchanged.

### Changed
- README sample gallery now features a double-helical `HelicalGear` in place of
  the spur gear.

## [0.1.2] - 2026-06-26

_Documentation and release-tooling only — no library code change; upgrading from
0.1.1 is optional._

### Changed
- README: added a PyPI install section (`pip install vibe_cading` /
  `vibe_cading[mcp]`) and a headless-Linux `libgl1` / OpenGL caveat for
  CadQuery's geometry kernel; standardized agent terminology to "AI agents".
- Release pipeline: PyPI publish is now gated by a per-release required-reviewer
  approval on the `pypi` GitHub Environment (replacing the `PYPI_PUBLISH` repo
  variable).

## [0.1.1] - 2026-06-24

### Added
- `LegoTechnicLLiftarm`: new 90°-bent Lego Technic studless liftarm (L-shaped / bent
  beam) class (`vibe_cading.lego.technic_l_liftarm`), parametric in both arm lengths
  (default 3×5), with chamfered pin holes on the 8 mm stud grid and rounded ends.
- `PrintInPlaceHinge.screw_holes`: new countersunk M3 flat-head mount holes — 2 per
  leaf (4 total) — controlled by `screw_holes: bool` (default `True`).

## [0.1.0] - Initial

### Added
- Initial public release of the `vibe-cading` CadQuery library: parametric
  mechanical models (screws, joints, bearings, axles, gears) and Lego-Technic /
  RC interface parts.
- Tolerance system: `vibe_cading.print_settings.get_profile()` and the
  `ToleranceProfile` shape, with user-overridable `print_profiles*.json` and
  `<machine>__<material>[__<brand>]` profile keys.
- Shared primitives in `vibe_cading.cq_utils` and Lego constants in
  `vibe_cading.lego.constants`.
- `vibe_cading.tools.*` CLI utilities (preview, section slicer, hole finder,
  boolean diff, calibration helper, STEP analysis).
- `engine_api.json` wire contract (carries its own `schema_version`).
- Build provenance: `vibe_cading.__version__` (from package metadata) and
  `vibe_cading.__commit__` (build-stamped git SHA).
- MCP (stdio) interface — `python -m vibe_cading.mcp`: a `vibe_cading.mcp`
  subpackage exposing the engine's deterministic introspection tools
  (`list_engine_classes`, `query_engine_class`, `get_design_context`) plus a
  local `compile_model`, over MCP stdio (JSON-RPC on stdin/stdout — no network
  listener, no API key). `mcp` ships as an optional `[mcp]` extra
  (`pip install -e ".[mcp]"`, pinned `mcp>=1,<2`), so a plain install never
  pulls the SDK's ASGI tree; a two-layer CI guard
  (`tools/check_mcp_import_isolation.py`) enforces that `vibe_cading.mcp` never
  enters the library import graph. `get_design_context` surfaces the curated
  Lego nominal allowlist (incl. the studded-System block nominals) + the live
  tolerance profile + doc pointers. (RFC #41.)
