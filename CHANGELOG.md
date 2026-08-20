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
- `PerpendicularHolesLiftarm`: two default-preserving constructor additions
  (TL round, 2026-08-19 — see
  `docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md` →
  *Reusable classes → TL round — decisions → Q1*). `thickness: float =
  BEAM_THICKNESS` (keyword-only) lets a caller override the beam's Z-extent
  per-instance — e.g. to match a real part's thicker cross-section — without
  moving the shared `BEAM_THICKNESS` constant every other caller relies on.
  `hole_axes` gains a third member, `"none"`, leaving a position unbored so a
  caller can compose its own call-site-local hole geometry at that position
  instead of un-cutting this class's own bore. Both additions preserve every
  existing caller's geometry byte-for-byte (verified: the two registered
  `visual_contracts.toml` rows regenerate with zero byte movement).
- `PoweredUpHubCover` and `PoweredUpHubBatteryTray`: two new exported model
  classes, task 2 of the Powered Up hub battery-box implementation sequence
  (see
  `docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md`). Both
  are read from the LDraw parts library (CC BY 4.0, author Philippe
  Hurbain) as measured facts — no LDraw file or converted geometry is
  committed, only from-scratch CadQuery code.
  `PoweredUpHubCover` is an exact copy of LEGO lid `24853` minus its three
  inner AA-cell divider ribs, with the 15 outer through-slots closed
  (round-13 user decision): the flat 1.2 mm plate, both cantilever latch
  fingers (Ø2.000 mm barb, 13.6 mm wide, 11.2 mm apart), the slide-in
  tongue/ledge at the insertion end, and a locating groove sized to the
  tray's own bottom rim. `PoweredUpHubBatteryTray` repurposes LEGO tray
  `24849` for a Spektrum SPMX812SH2 LiPo pack: both internal transverse
  partitions removed (giving the pack's required 58.000 mm clear length,
  plus a 1.5 mm relief since that figure is otherwise zero-slack), both
  outer end walls and both side walls (with their extraction tabs) kept, a
  new floor, and two new strap-holder slots sized to the confirmed 20.5 mm
  opening. A shared `latch_geometry.LatchGeometry` frozen parameter object
  (barb/hook dimensions plus the derived undercut/catch-width/ramp-angle
  numbers) is the single source of truth the future `HousingBox` catch
  (a separate PR) will import alongside the Cover, so the male and female
  latch halves cannot drift apart.
- `PoweredUpHubHousing`: new exported model class, task 3 of the Powered Up
  hub battery-box implementation sequence (see
  `docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md`). An
  exact copy of the real hub's bottom shell (LDraw `25560`, 72.0 × 71.2 ×
  33.8 mm) with a scoped departure at the two lid-retention regions only
  (a single wall instead of LEGO's real two-skin sandwich, per the design's
  *Single wall at BOTH ends* section). Composes
  `PerpendicularHolesLiftarm(3, ["main", "none", "main"], thickness=8.0)`
  for the four arms (per the TL round's decision), finished locally with an
  envelope trim to the real 23.2 mm arm length, an additive Ø7.2 × 0.4 mm
  boss around each middle hole, and a housing-local three-step middle bore
  (Ø6.4 × 0.8 outer counterbore → Ø4.8 × 6.4 guided → Ø7.2 × 1.6 relief
  opening into the battery cavity). The latch-end catch (derived from
  `PoweredUpHubCover`'s own barb geometry via the shared `LatchGeometry`
  parameter object, absent from LDraw) and the tongue-end rebate (a lap,
  not a snap, fully specified from LDraw) together implement the design's
  complete retention scheme — verified by a zero-volume boolean
  intersection against the built `PoweredUpHubCover` in its seated
  position.

### Fixed
- `PerpendicularHolesLiftarm`: fixed a latent crossed-constant bug in the
  cutter depths — the main bore (which runs along Z, through `thickness`) was
  sized from `BEAM_WIDTH`, and the perp bore (which runs along Y, through
  `BEAM_WIDTH`) was sized from `BEAM_THICKNESS`. This was harmless only
  because `BEAM_WIDTH == BEAM_THICKNESS == 7.8` by coincidence; it would have
  produced blind (non-through) main holes the moment `thickness` diverged
  from `BEAM_WIDTH` (e.g. the new `thickness=8.0` override above). Fixed as a
  precondition of adding the `thickness` kwarg, with a durable regression
  test (`test_thickness_override_main_holes_break_through`) asserting both Z
  faces show through-holes at a diverging thickness.
- `PoweredUpHubBatteryTray`: fixed a `960.4 mm³` interference against
  `PoweredUpHubHousing` (design round 16, Escalation 5) — the tray's outer
  wall was uniform `27.2/26.4 mm` across its full height, numerically
  identical to Housing's own upper-band wall material above its `Z = 22.0 mm`
  step. The wall now steps inward above the tray's own local `Z = 20.800 mm`
  (Housing's step, offset for the tray's `1.2 mm` seated datum) to
  `26.400 mm minus the active profile's free.radial allowance / 25.600 mm`,
  matching Housing's real upper-band inner face with a tolerance-routed gap
  instead of a bare literal. Confirmed by cross-part boolean intersection:
  the targeted wall-vs-wall overlap is fully eliminated (zero interference in
  Housing's upper wall band); a separate, pre-existing lower-band conflict
  between Housing's arm root-bridge gusset and the tray's own (unaffected)
  lower-band wall remains open — see the design brief's Escalation 8.
- `PoweredUpHubHousing`: fixed a `72.6 mm` vs. the exact-copy `72.0 mm`
  target X envelope (design round 16, Escalation 7) — the arms kept the
  shared `PerpendicularHolesLiftarm` class's Cailliau-calibrated
  `BEAM_WIDTH` (half-width `3.9 mm`) rather than the real LDraw half-width
  (`3.6 mm`), and the middle-hole boss/bore, anchored dynamically off the
  arm's own edge, propagated the same `+0.3 mm` overshoot. Fixed with a
  housing-local composition trim (no shared-class change): one additional
  one-sided cut in `_build_arm_and_bore_local` removing arm material beyond
  the real half-width, after which the boss/bore code's existing dynamic
  read self-corrects. Verified via section slice: arm flat face at
  `X = ±35.600 mm`, boss tip at `X = ±36.000 mm`, overall envelope exactly
  `72.000 mm`.
- `PoweredUpHubHousing`: fixed the `259.014 mm³` lower-band interference
  between the arm root-bridge gusset and `PoweredUpHubBatteryTray`'s own
  (unaffected) wall that Escalation 5's fix had unmasked (design round 17,
  Escalation 8). The root bridge's single, uniform wall-reach — sized for
  the wall's narrower *upper* band (`Z ≥ 22.0 mm`) — was applied across the
  arm's *entire* thickness, so it also crossed through the wall's wider
  *lower* band (`Z < 22.0 mm`, where the tray's wall sits) and overshot
  into the tray's own territory there. Fixed with a Z-dependent two-band
  bridge in `_build_arm_and_bore_local`: the upper band (`Z ∈ [22.0, 24.0]`,
  the band that actually fuses the arm to the wall) is unchanged; the lower
  band (`Z ∈ [16.0, 22.0]`) drops the wall-reaching extension entirely,
  backed by a quantified `≈85.8 mm³` fused-overlap margin (the upper band
  alone) proving the floating-arm defect cannot return, plus two runtime
  assertions guarding both the fused-overlap height and the lower-band
  boundary against silent regression. Root-bridge-band interference against
  the tray is now `0.0 mm³` (down from `259.014 mm³`); envelope, cover
  interference (`0.000000 mm³`), and the single-solid guard are unchanged.
  Verifying this fix surfaced a separate, much smaller (`≈4.05 mm³`)
  residual at the `Z = 22.0` wall-step seam itself — Housing's and the
  tray's own independent `0.05 mm` coincident-faces overlap constructions
  each reach slightly past the step into the other part's still-present
  wall material there — confirmed unrelated to the root bridge and left
  open as a new escalation (see the design brief's Escalations).

## [0.1.6] - 2026-08-10

### Added
- `TechnicPinHoleBushing`: new exported model class — a plain round tube
  bushing that fits into a real Lego Technic pin hole (Ø4.8 mm nominal) on
  its outer diameter and carries an independently-graded clearance
  through-bore, bridging a Lego beam pin hole to a machine screw (M3 by
  default; M2/M2.5/M4 via `bore_nominal_diameter`). Constructor
  `TechnicPinHoleBushing(length=BEAM_THICKNESS, fit="slip",
  bore_fit="slip", flange=True, flange_od=5.5, flange_thickness=0.8,
  bore_nominal_diameter=None, profile=None)`.
  `length` is the TOTAL axial span of the whole part (barrel plus the
  nested flange, when enabled) — a caller sets it to the target insertion
  depth (e.g. one beam thickness) and gets exactly that depth back
  regardless of the `flange` flag. OD is computed as
  `PIN_HOLE_DIAMETER - 2 * getattr(profile, fit).radial` — the sign is
  negated relative to every other `fit` consumer in the codebase because
  this is the first *male* (printed-peg-into-real-hole) fit site rather
  than a printed-void site; `fit` defaults to `"slip"` rather than
  `"press"` because a printed-and-measured unit showed shipped `press`
  radial values don't model genuine interference on a real printer — the
  OD lands at the modelled (under-nominal) target and spins freely, i.e.
  it measures as `slip`, not `press`. The bore is independently graded via
  `bore_fit` (ordinary, non-inverted female/void semantics), cut with a
  hand-rolled through-hole cutter (not `ClearanceHole`, which hardcodes
  `free.radial` with no override, and not `MetricMachineScrew.to_cutter()`,
  which would destroy the flange with an oversized counterbore). The
  optional single retaining flange sits strictly below `Z=0`, default
  enabled, sized (Ø5.5 mm default) to nest inside the standard Technic
  pin-hole counterbore recess rather than sit on the beam's flat outer
  face. Registered in `build.toml` — M2 / M2.5 / M3 variants under
  `xlego/bushings/`, each at `length=3.6`. An M4 variant was test-printed
  and found unprintable (wall too thin — M4's clearance bore is
  intrinsically close to the whole barrel OD, fixed by the Lego pin hole)
  and is not registered; the class still constructs one programmatically
  via `bore_nominal_diameter=4.3`.

## [0.1.5] - 2026-06-26

### Added
- `PerpendicularHolesLiftarm`: new exported model class — a parametric thick
  studless Lego-Technic liftarm where each hole position bores along either the
  flat-face axis (+Z, `"main"`) or the narrow side-face axis (±Y, `"perp"`),
  generalizing the LEGO 6435016 / design-2391 "Liftarm Thick with Perpendicular
  Holes" family. Constructor `PerpendicularHolesLiftarm(num_holes, hole_axes=None,
  fit="slip", profile=None)`; `hole_axes=None` defaults to the alternating
  `[perp, main, …]` pattern. Reuses `TechnicPinHole` (rotated 90° for the perp
  bores) and the shared `LegoTechnicBeam` stadium body; counterbored pin holes +
  lead-in chamfers on both axes. Registered in `build.toml`
  (`lego/perpendicular_holes_liftarm_5hole.step`).

### Changed
- `LegoTechnicBeam`: stadium-body construction extracted to a shared module-level
  `stadium_beam_body()` helper (internal refactor, no behavior change).
- `_HoleMouthSelector`: gained an additive `axis="z"|"y"` discriminator; existing
  `LegoTechnicBeam` / `LegoTechnicLLiftarm` call sites are unchanged.

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
